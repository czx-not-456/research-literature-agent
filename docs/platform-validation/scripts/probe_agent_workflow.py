"""Run one Managed Agent literature task and validate its observed tool executions."""

import argparse
import json
import re
import shlex
import sys
import time
from collections import Counter
from pathlib import Path, PurePosixPath
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from research_library.__main__ import DEFAULT_ENDPOINT, read_iam
from research_library.agentarts import IDLE_TIMEOUT, AgentArtsChat, AgentArtsError

MARKER = "LIT_RESEARCH "
PROMPT = """公开文献调研任务：请为检索增强生成（retrieval augmented generation）找两篇相关期刊论文，
逐篇核验 DOI，再做一段中文比较。请自己选用已有的 literature-research Skill 来完成查找、选文和核验。
用同一轮对话：先用真实检索，再从工具返回的候选中自行选择两篇，分别读取其 DOI 登记。
请从 Skill 的实际目录定位 scripts/literature_tools.py，用 Bash 中的 python3 运行该脚本。
每次 Bash 只执行一次 search 或一次 verify；实际工具不可用时返回 insufficient_evidence。
只以核验返回的字段为准。比较题名所体现的主题、出版年份或类型，指出需查全文的问题。
没有全文就不输出实验结果、逐字引文或页码。
最终只输出 JSON 对象，字段为 status（complete 或 insufficient_evidence），
works（数组，每条含 doi、title、year、kind、url），comparison（中文），missing_evidence（中文）。
书目字段请原样复制。工具中断或无法验证时如实说明。
"""



SKILL_CHECK_PROMPT = """我要用 literature-research Skill 检索 RAG 学术文献和核验 DOI。这轮仅验证工具启动。
先加载已关联的 literature-research。请检查加载工具给出的实际 Skill 目录或 SKILL.md 文件路径。
若存在这个位置，直接用一次独立 Bash 命令运行 python3 <该 Skill 目录>/scripts/literature_tools.py --help；
将占位符换成工具提供的实际路径，经 Shell 引号保护。SKILL.md 的父目录就是 Skill 目录。
如果没有可用的目录或 SKILL.md 路径，停止并报告 skill_location_unavailable。加载失败则报告 skill_load_failed。
不要列举其他目录、安装软件、读取环境变量或访问 Crossref。
最后只返回一个 JSON 对象 {"outcome":"..."}，根据实际结果从以下值中选一个：
help_ran、skill_load_failed、skill_location_unavailable、script_path_not_found、python_not_available、permission_denied、other_failure。
不要返回路径或原始工具输出。"""
SKILL_CHECK_OUTCOMES = (
    "help_ran", "skill_load_failed", "skill_location_unavailable", "script_path_not_found",
    "python_not_available", "permission_denied", "other_failure",
)


def _json(text):
    if not isinstance(text, str):
        return None
    fenced = re.fullmatch(r"\s*\x60{3}(?:json)?\s*(.*?)\s*\x60{3}\s*", text, re.S | re.I)
    try:
        data = json.loads(fenced.group(1) if fenced else text)
    except (ValueError, RecursionError):
        return None
    return data if isinstance(data, dict) else None


def _command(command):
    if not isinstance(command, str):
        return None
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        args = list(lexer)
    except ValueError:
        return None
    directory = None
    path_chars = r"[~/a-zA-Z0-9_ ./-]+"
    if args[:1] == ["cd"]:
        if len(args) < 4 or args[2] != "&&" or args[1].startswith("-") or not re.fullmatch(path_chars, args[1]):
            return None
        directory, args = PurePosixPath(args[1]), args[3:]
    if len(args) > 1 and args[1] in ("-B", "-u"):
        del args[1]
    if len(args) == 4 and "=" in args[3]:
        args[3:] = args[3].split("=", 1)
    if (len(args) not in (3, 5) or not re.fullmatch(path_chars, args[0]) or not re.fullmatch(path_chars, args[1])
            or not re.fullmatch(r"python(?:3(?:\.[0-9]+)?)?", PurePosixPath(args[0]).name)):
        return None
    script = PurePosixPath(args[1])
    in_scripts = directory and directory.name == "scripts" and script.parts == ("literature_tools.py",)
    if script.parts[-2:] != ("scripts", "literature_tools.py") and not in_scripts:
        return None
    if len(args) == 3 and args[2] in ("--help", "-h"):
        return "check", "--help"
    if len(args) == 5 and (args[2], args[3]) in (("search", "--query"), ("verify", "--doi")):
        return args[2], args[4]
    return None


def _stdout(result):
    wrapper = _json(result) if isinstance(result, str) else result
    if isinstance(wrapper, dict):
        for key in ("stdout", "output", "text"):
            if isinstance(wrapper.get(key), str):
                return wrapper[key]
    return result if isinstance(result, str) else ""


def _payload(result):
    for line in _stdout(result).splitlines():
        line = re.sub(r"^(?:stdout|output):[ \t]*", "", line.strip(), flags=re.I)
        if line.startswith(MARKER):
            return _json(line[len(MARKER):])
    return None


def _failure_label(result):
    wrapper = _json(result) if isinstance(result, str) else result
    stderr = wrapper.get("stderr") if isinstance(wrapper, dict) else None
    text = (_stdout(result) + ("\n" + stderr if isinstance(stderr, str) else "")).lower()
    if "permission denied" in text or "operation not permitted" in text:
        return "permission_denied"
    if ("command not found" in text and "python" in text) or re.search(r"python[0-9.]*:\s*(?:command )?not found", text):
        return "python_not_available"
    if "can't open file" in text or "no such file or directory" in text:
        return "script_or_path_not_found"
    return "missing_structured_stdout"


def _skill_mentions(result):
    text = _stdout(result).casefold()
    return [name for name in ("literature-research", "skill.md", "literature_tools.py") if name in text]


def _exploration_result(result, verb):
    failure = _failure_label(result)
    if failure != "missing_structured_stdout":
        return failure
    wrapper = _json(result) if isinstance(result, str) else result
    if not isinstance(result, str) or isinstance(wrapper, dict):
        if not isinstance(wrapper, dict) or not any(isinstance(wrapper.get(key), str)
                                                    for key in ("stdout", "output", "text")):
            return "exploration_result_unrecognized"
    output = _stdout(result)
    if verb == "find" and re.search(
        r"(?m)^(?:(?:Output|Stdout):[ \t]*)?(?:[./~A-Za-z0-9_-][^:\r\n]*?/)?scripts/literature_tools\.py[ \t]*$",
        output,
        re.I,
    ):
        return "skill_script_path_observed"
    return "exploration_output" if output.strip() else "exploration_no_stdout"


def _command_summary(raw, command):
    if not isinstance(raw, str):
        return {"execution_style": "missing_command", "mentions_skill_script": False,
                "mentions_crossref_host": False, "operation_flags": []}
    if command:
        style = "recognized_skill_command"
    elif "literature_tools.py" in raw:
        style = "unrecognized_skill_command"
    elif re.search(r"\b(?:curl|wget)\b", raw):
        style = "curl_or_wget"
    elif re.search(r"\bpython(?:3(?:\.[0-9]+)?)?\b", raw):
        style = "other_python_command"
    else:
        style = "other_command"
    first = re.match(r"(?:/[-A-Za-z0-9_.]+/)*([A-Za-z]+)(?=\s|\Z)", raw.lstrip())
    verb = first.group(1) if first else ""
    diagnostic_verb = verb if verb in ("find", "ls", "pwd", "stat", "cat", "sed", "grep", "test", "cd",
                                       "which", "command", "type", "echo", "printf") else None
    return {
        "execution_style": style,
        "shell_verb": diagnostic_verb,
        "mentions_skill_script": "literature_tools.py" in raw,
        "mentions_crossref_host": bool(re.search(r"\bapi\.crossref\.org\b", raw, re.I)),
        "operation_flags": [name for name, flag in (("search", "--query"), ("verify", "--doi")) if flag in raw],
    }


def _record(item):
    if not isinstance(item, dict):
        return None
    doi, title, year, kind, url = (item.get(key) for key in ("doi", "title", "year", "kind", "url"))
    if (not isinstance(doi, str) or len(doi) > 210 or not re.fullmatch(r"10\.[0-9]{4,9}/[!-~]+", doi)
            or not isinstance(title, str) or not 1 <= len(title) <= 300
            or not isinstance(kind, str) or len(kind) > 48
            or not isinstance(year, str) or year and not re.fullmatch(r"[0-9]{4}", year)
            or url != "https://doi.org/" + quote(doi, safe="/")):
        return None
    return {"doi": doi, "title": title, "year": year, "kind": kind, "url": url}


class WorkflowTrace:
    def __init__(self):
        self.pending = {}
        self.candidates = set()
        self.verified = {}
        self.steps = []
        self.request_id = None
        self.session_id = None
        self.bash_calls = {}
        self.non_bash_calls = {}

        self.events = Counter()
        self.tools = Counter()
        self.recognized_calls = 0
        self.answer_tail = []
        self.answer_tail_size = 0
        self.final_has_content = False
        self.terminal = None
        self.interrupt_source = None

    def _diagnostics(self, answer_format=None, reason=None):
        return {
            "events": dict(self.events), "tools": dict(self.tools),
            "session_id": self.session_id, "bash_calls": list(self.bash_calls.values()),
            "non_bash_calls": list(self.non_bash_calls.values()),
            "recognized_script_calls": self.recognized_calls, "unpaired_script_calls": len(self.pending),
            "terminal_event": self.terminal, "interrupt_source": self.interrupt_source,
            "answer_format": answer_format, "failure_reason": reason,
        }

    def observe(self, event, payload):
        self.events[event] += 1
        session_id = payload.get("session_id")
        if isinstance(session_id, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,64}", session_id):
            self.session_id = session_id
        request_id = payload.get("request_id")
        if isinstance(request_id, str) and re.fullmatch(r"[\w-]{1,80}", request_id, re.ASCII):
            self.request_id = request_id
        if event in ("chat.final", "chat.error", "chat.interrupt_result", "chat.ask_user_question", "chat.invocation_paused"):
            self.terminal = event
        if event == "chat.final":
            self.final_has_content = bool(payload.get("content"))
        if event == "chat.ask_user_question":
            source = payload.get("source")
            if source in ("permission_interrupt", "confirm_interrupt", "ask_user_interrupt"):
                self.interrupt_source = source
        if event == "chat.delta":
            content = payload.get("content")
            if isinstance(content, str) and self.answer_tail_size + len(content) <= 20_000:
                self.answer_tail.append(content)
                self.answer_tail_size += len(content)
        if event == "chat.tool_call":
            tool = payload.get("tool_call")
            if not isinstance(tool, dict):
                self.tools["other"] += 1
                return
            name = tool.get("name")
            allowed = ("bash", "read_file", "write_file", "edit_file", "glob", "list_files", "grep")
            self.tools[name if name in allowed else "other"] += 1
            call_id = tool.get("tool_call_id")
            if not isinstance(call_id, str) or not 1 <= len(call_id) <= 128:
                return
            if name != "bash":
                if len(self.non_bash_calls) < 12 and call_id not in self.non_bash_calls:
                    label = name if isinstance(name, str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]{0,47}", name) else None
                    self.non_bash_calls[call_id] = {"tool_name": label, "result_observed": False}
                return
            args = tool.get("arguments")
            if isinstance(args, str):
                args = _json(args)
            raw = args.get("command") if isinstance(args, dict) else None
            command = _command(raw)
            if len(self.bash_calls) < 12 and call_id not in self.bash_calls:
                self.bash_calls[call_id] = {"call": len(self.bash_calls) + 1, **_command_summary(raw, command),
                                            "result": "not_observed"}
            if not command:
                return
            operation, value = command
            self.recognized_calls += int(operation != "check")
            selected = operation == "search" or value.casefold() in self.candidates
            self.pending[call_id] = operation, value, selected
        elif event == "chat.tool_update" and payload.get("status") == "error":
            call_id = payload.get("tool_call_id")
            if isinstance(call_id, str):
                diagnostic = self.bash_calls.get(call_id) or self.non_bash_calls.get(call_id)
                if diagnostic is not None:
                    diagnostic["update_status"] = "error"
        elif event == "chat.tool_result":
            self.answer_tail.clear()
            self.answer_tail_size = 0
            call_id = payload.get("tool_call_id")
            tool_name = payload.get("tool_name")
            if not tool_name and isinstance(call_id, str):
                # A result may omit the name, but it still needs an exact call ID.
                if call_id in self.bash_calls:
                    tool_name = "bash"
                elif call_id in self.non_bash_calls:
                    tool_name = self.non_bash_calls[call_id]["tool_name"]
            if tool_name != "bash":
                diagnostic = self.non_bash_calls.get(call_id) if isinstance(call_id, str) else None
                if diagnostic is not None and (diagnostic["tool_name"] is None
                                               or diagnostic["tool_name"] == tool_name):
                    output = payload.get("result")
                    diagnostic["result_observed"] = True
                    diagnostic["result_mentions"] = _skill_mentions(output)
                    failure = _failure_label(output)
                    if failure != "missing_structured_stdout":
                        diagnostic["result_failure"] = failure
                return
            diagnostic = self.bash_calls.get(call_id) if isinstance(call_id, str) else None
            command = self.pending.pop(call_id, None) if isinstance(call_id, str) else None
            result = _payload(payload.get("result"))
            if diagnostic is not None:
                verb = diagnostic.get("shell_verb")
                if not command and verb in ("find", "ls", "cd", "pwd", "stat"):
                    diagnostic["result"] = _exploration_result(payload.get("result"), verb)
                    diagnostic["result_mentions"] = _skill_mentions(payload.get("result"))
                else:
                    diagnostic["result"] = "structured_skill_output" if result else _failure_label(payload.get("result"))
                if result and result.get("operation") in ("search", "verify"):
                    diagnostic["reported_operation"] = result["operation"]
                if result and result.get("status") in ("ok", "empty", "failed"):
                    diagnostic["reported_status"] = result["status"]
            if not command:
                return
            operation, value, selected = command
            if operation == "check":
                output = _stdout(payload.get("result"))
                seen_help = bool(re.search(r"(?im)^[ \t]*(?:(?:stdout|output):[ \t]*)?usage:[ \t]+literature_tools\.py\b", output)
                                 and "{search,verify}" in output)
                code = "skill_cli_help" if seen_help else _failure_label(payload.get("result"))
                if diagnostic is not None:
                    diagnostic["result"] = code
                self.steps.append({"operation": "check", "status": "ok" if seen_help else "failed", "code": code})
                return
            if not result:
                self.steps.append({"operation": operation, "status": "failed",
                                   "code": _failure_label(payload.get("result"))})
                return
            if result.get("operation") != operation or result.get("provider") != "Crossref":
                self.steps.append({"operation": operation, "status": "failed", "code": "unexpected_tool_response"})
                return
            if result.get("status") != "ok":
                code = result.get("code", "empty")
                if not isinstance(code, str) or not re.fullmatch(r"[a-z0-9_]{1,48}", code):
                    code = "tool_error"
                self.steps.append({"operation": operation, "status": "failed", "code": code})
                return
            items = result.get("items")
            if not isinstance(items, list) or not 1 <= len(items) <= 3:
                self.steps.append({"operation": operation, "status": "failed", "code": "invalid_items"})
                return
            items = [record for raw in items if (record := _record(raw))]
            if operation == "search" and items:
                self.candidates.update(item["doi"].casefold() for item in items)
                self.steps.append({"operation": "search", "status": "ok", "results": len(items)})
            elif selected and len(items) == 1 and items[0]["doi"].casefold() == value.casefold():
                self.verified[value.casefold()] = items[0]
                self.steps.append({"operation": "verify", "status": "ok", "doi": items[0]["doi"]})
            else:
                self.steps.append({"operation": operation, "status": "failed", "code": "items_do_not_match_call"})

    def failure(self, error):
        return {"status": "not_verified", "error": str(error), "request_id": self.request_id,
                "diagnostics": self._diagnostics(reason="agent_response_error"), "steps": self.steps}

    def check_skill(self, text=""):
        answer = _json(text)
        if answer is None and not self.final_has_content and self.events["chat.final"]:
            answer = _json("".join(self.answer_tail))
        outcome = (answer or {}).get("outcome")
        checks = [item for item in self.steps if item["operation"] == "check"]
        available = any(item["status"] == "ok" for item in checks)
        if available:
            reason = None
        elif not self.tools["bash"]:
            reason = "no_bash_call_event"
        elif not checks and not self.pending:
            reason = "script_help_command_not_observed"
        elif not checks:
            reason = "script_help_result_not_observed"
        else:
            reason = checks[-1]["code"]
        return {
            "status": "skill_available" if available else "not_verified",
            "mode": "skill_check",
            "request_id": self.request_id,
            "agent_reported_outcome": outcome if outcome in SKILL_CHECK_OUTCOMES else None,
            "diagnostics": self._diagnostics(reason=reason),
            "steps": self.steps,
        }

    def check_result(self, text):
        answer = _json(text)
        answer_format = "json" if answer is not None else "non_json"
        if answer is None and not self.final_has_content and self.events["chat.tool_result"]:
            answer = _json("".join(self.answer_tail))
            if answer is not None:
                answer_format = "json_after_last_tool"
        answer = answer or {}
        works = answer.get("works")
        supplied = [_record(item) for item in works] if isinstance(works, list) and len(works) == 2 else []
        references_match = bool(len(supplied) == 2 and all(supplied)
                                and len({item["doi"].casefold() for item in supplied}) == 2
                                and all(item["kind"] == "journal-article"
                                        and self.verified.get(item["doi"].casefold()) == item for item in supplied))
        comparison = answer.get("comparison")
        gap = answer.get("missing_evidence")
        has_sections = all(isinstance(value, str) and 1 <= len(value.strip()) <= 900 for value in (comparison, gap))
        reported_status = answer.get("status")
        complete = reported_status == "complete"
        if not self.events["chat.tool_call"]:
            reason = "no_tool_call_event"
        elif not self.recognized_calls:
            reason = "no_recognized_literature_script_call"
        elif len(self.verified) < 2:
            reason = "fewer_than_two_verified_dois"
        elif answer_format == "non_json":
            reason = "final_answer_not_json"
        elif not (references_match and has_sections and complete):
            reason = "final_answer_does_not_match_verified_results"
        else:
            reason = None
        return {
            "status": "passed" if reason is None else "not_verified",
            "request_id": self.request_id,
            "diagnostics": self._diagnostics(answer_format=answer_format, reason=reason),
            "steps": self.steps,
            "checks": {"verified_candidates": len(self.verified), "answer_bibliography_matches": references_match,
                       "comparison_and_evidence_gap_present": has_sections, "agent_reported_complete": complete,
                       "agent_reported_status": reported_status if reported_status in (
                           "complete", "insufficient_evidence"
                       ) else None},
            "works": supplied if references_match else [],
            "comparison": comparison if references_match and has_sections else None,
            "missing_evidence": gap if references_match and has_sections else None,
        }


def _historical_tool_result(message):
    fields = ("tool_call_id", "tool_name", "result")
    result = {key: message[key] for key in fields if key in message}
    nested = message.get("tool_result")
    if isinstance(nested, dict):
        for key in ("tool_call_id", "tool_name"):
            if isinstance(nested.get(key), str) and nested[key]:
                result[key] = nested[key]
        if "result" in nested and nested["result"] is not None:
            result["result"] = nested["result"]
    return result


def review_history(messages, session_id, request_id, history, *, skill_check=False):
    trace = WorkflowTrace()
    trace.session_id = session_id
    trace.request_id = request_id
    matched = [
        message for message in messages
        if message.get("request_id") == request_id and message.get("session_id", session_id) == session_id
    ]
    if skill_check:
        # The standalone help check pairs by call ID even if history puts its result first.
        matched.sort(key=lambda message: message["event_type"] != "chat.tool_call")
    answer = ""
    result_fields = Counter()
    for message in matched:
        event = message["event_type"]
        payload = message
        if event == "chat.tool_result":
            payload = _historical_tool_result(message)
            result_fields["with_call_id"] += isinstance(payload.get("tool_call_id"), str) and bool(payload["tool_call_id"])
            result_fields["with_tool_name"] += isinstance(payload.get("tool_name"), str) and bool(payload["tool_name"])
            result_fields["with_output"] += isinstance(payload.get("result"), (str, dict))
        trace.observe(event, payload)
        if event == "chat.final":
            answer = payload.get("content", "")
    result = trace.check_skill(answer) if skill_check else trace.check_result(answer)
    if not history["done"]:
        result["status"] = "not_verified"
        result["diagnostics"]["failure_reason"] = "history_stream_incomplete"
    elif not matched:
        result["diagnostics"]["failure_reason"] = "request_not_found_in_history"
    elif trace.terminal != "chat.final":
        result["status"] = "not_verified"
        result["diagnostics"]["failure_reason"] = "history_missing_successful_final"
    result["source"] = "session_history"
    result["history"] = {**history, "messages_reviewed": len(matched), "pages_read": 1}
    if result_fields:
        result["history"]["tool_result_fields"] = dict(result_fields)
    return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--agent", default="agent-huawei-cit")
    parser.add_argument("--region", default="cn-southwest-2")
    parser.add_argument("--history", metavar="SESSION_ID", help="Read an existing session without invoking the model.")
    parser.add_argument("--check-skill", action="store_true",
                        help="Check that the cloud can run the skill CLI, or review that check with --history.")
    parser.add_argument("--request-id", help="Inspect only this request from the selected session.")
    args = parser.parse_args()
    if args.history:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", args.history):
            parser.error("--history requires a valid session ID")
        if not args.request_id or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", args.request_id):
            parser.error("--history requires a valid --request-id")
    elif args.request_id:
        parser.error("--request-id is for --history only")
    trace = WorkflowTrace()
    socket_timeout = 75 if args.check_skill else IDLE_TIMEOUT
    response_window = 120 if args.check_skill else 180
    started = None
    if args.history:
        trace.request_id, trace.session_id = args.request_id, args.history
    try:
        chat = AgentArtsChat(args.endpoint, args.agent, args.region, *read_iam())
        if args.history:
            messages, history = chat.history(args.history)
            result = review_history(messages, args.history, args.request_id, history, skill_check=args.check_skill)
        else:
            prompt = SKILL_CHECK_PROMPT if args.check_skill else PROMPT
            started = time.monotonic()
            answer = chat.ask(prompt, observer=trace.observe, response_window=response_window,
                              socket_timeout=socket_timeout)
            result = trace.check_skill(answer) if args.check_skill else trace.check_result(answer)
    except (ValueError, AgentArtsError) as error:
        result = trace.failure(error)
        if args.history:
            result["source"] = "session_history"
        else:
            if started is not None and isinstance(error, AgentArtsError) and error.timeout_phase:
                result["diagnostics"]["transport"] = {
                    "timeout_phase": error.timeout_phase,
                    "elapsed_seconds": round(time.monotonic() - started, 1),
                    "socket_timeout_seconds": socket_timeout,
                    "response_window_seconds": response_window,
                }
        if args.check_skill:
            result["mode"] = "skill_check"
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] in ("passed", "skill_available") else 1

if __name__ == "__main__":
    sys.exit(main())
