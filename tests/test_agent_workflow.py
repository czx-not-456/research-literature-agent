import io
import json
import runpy
import time
import unittest
from pathlib import Path
from zipfile import ZipFile

from research_library.agentarts import AgentArtsError, read_answer

ROOT = Path(__file__).resolve().parents[1] / "docs" / "platform-validation"
PROBE = runpy.run_path(str(ROOT / "scripts" / "probe_agent_workflow.py"))
TRACE = PROBE["WorkflowTrace"]
TOOLS = runpy.run_path(str(ROOT / "skills" / "literature-research" / "scripts" / "literature_tools.py"))


def frame(event, data):
    return f"event: {event}\ndata: {json.dumps(data)}\n\n".encode()


def result(operation, records):
    return "Output:\nLIT_RESEARCH " + json.dumps(
        {"operation": operation, "provider": "Crossref", "status": "ok", "items": records}
    )


def tool_frames(tool_id, operation, value, records, command=None):
    argument = "--query" if operation == "search" else "--doi"
    command = command or f'python3 skills/literature-research/scripts/literature_tools.py {operation} {argument} "{value}"'
    return frame("chat.tool_call", {"tool_call": {
        "tool_call_id": tool_id, "name": "bash", "arguments": {"command": command}
    }}) + frame("chat.tool_result", {"tool_call_id": tool_id, "tool_name": "bash",
                                    "request_id": "sample-request", "result": result(operation, records)})


def work(doi, title):
    return {"doi": doi, "title": title, "year": "2025", "kind": "journal-article", "url": "https://doi.org/" + doi}


def run_trace(trace, frames, works):
    output = {
        "status": "complete", "works": works, "comparison": "The titles emphasize different applications.",
        "missing_evidence": "The evaluation methods need the full text.",
    }
    stream = io.BytesIO(frames + frame("chat.final", {"content": json.dumps(output)}))
    return trace.check_result(read_answer(stream, time.monotonic() + 3, trace.observe))


class WorkflowTest(unittest.TestCase):
    def setUp(self):
        self.first = work("10.12345/example-a", "Example A")
        self.second = work("10.12345/example-b", "Example B")
        self.papers = [self.first, self.second]

    def test_sse_observer_pairs_search_and_doi_checks(self):
        stream = tool_frames("one", "search", "retrieval", self.papers)
        stream += frame("chat.reasoning", {"content": "Never captured in the report", "request_id": "ignored"})
        for name, record in zip(("two", "three"), self.papers):
            stream += tool_frames(name, "verify", record["doi"], [record])
        result = run_trace(TRACE(), stream, self.papers)
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["request_id"], "sample-request")
        self.assertEqual([item["operation"] for item in result["steps"]], ["search", "verify", "verify"])
        self.assertEqual(result["works"], self.papers)

    def test_unsupported_final_citations_or_wrong_tool_order_cannot_pass(self):
        search = tool_frames("one", "search", "retrieval", self.papers)
        first = tool_frames("two", "verify", self.first["doi"], [self.first])
        second = tool_frames("three", "verify", self.second["doi"], [self.second])
        for stream, results in (
            (b"", self.papers),
            (first + search + second, self.papers),
            (search + first + second, [self.first, {**self.second, "year": "2033"}]),
            (search + first + tool_frames("bad", "verify", self.second["doi"], [self.second], "echo fake"), self.papers),
        ):
            self.assertEqual(run_trace(TRACE(), stream, results)["status"], "not_verified")

    def test_diagnostics_distinguish_missing_tool_event_from_unrecognized_command(self):
        no_tools = run_trace(TRACE(), b"", [])
        self.assertEqual(no_tools["diagnostics"]["failure_reason"], "no_tool_call_event")
        other = tool_frames("a", "search", "retrieval", self.papers, "echo private-command")
        unknown = run_trace(TRACE(), other, self.papers)
        self.assertEqual(unknown["diagnostics"]["failure_reason"], "no_recognized_literature_script_call")
        self.assertEqual(unknown["diagnostics"]["tools"], {"bash": 1})
        self.assertNotIn("private-command", json.dumps(unknown))

    def test_sse_can_parse_wrapped_stdout_and_final_segment_after_tools(self):
        trace = TRACE()
        stream = frame("chat.delta", {"content": "Finding and verifying candidate works."})
        stream += tool_frames("search", "search", "retrieval", self.papers,
                              'cd "/tmp/a skill" && /usr/bin/python3.12 ./scripts/literature_tools.py search --query retrieval')
        for index, record in enumerate(self.papers):
            call_id = f"verify-{index}"
            stream += frame("message", {"event": "chat.tool_call", "data": {"tool_call": {
                "tool_call_id": call_id, "name": "bash", "arguments": {
                    "command": f'python3 -B scripts/literature_tools.py verify --doi="{record["doi"]}"'
                },
            }}})
            result_json = json.dumps({"stdout": result("verify", [record]).replace("Output:\n", "Output: ")})
            stream += frame("chat.tool_result", {"tool_call_id": call_id, "tool_name": "bash", "result": result_json})
        answer = {"status": "complete", "works": self.papers, "comparison": "Compared titles",
                  "missing_evidence": "Full text"}
        stream += frame("chat.delta", {"content": json.dumps(answer)})
        stream += frame("chat.final", {"content": "", "is_complete": True, "request_id": "completed"})
        accepted = trace.check_result(read_answer(io.BytesIO(stream), time.monotonic() + 3, trace.observe))
        self.assertEqual(accepted["status"], "passed")
        self.assertEqual(accepted["diagnostics"]["answer_format"], "json_after_last_tool")
        self.assertEqual(accepted["diagnostics"]["recognized_script_calls"], 3)

    def test_tool_failure_and_permission_prompt_keep_only_sanitized_diagnostics(self):
        trace = TRACE()
        failure = frame("chat.tool_call", {"tool_call": {
            "tool_call_id": "one", "name": "bash", "arguments": {
                "command": "python3 scripts/literature_tools.py search --query retrieval"
            },
        }})
        failure += frame("chat.tool_result", {"tool_call_id": "one", "tool_name": "bash",
                                             "result": "can't open file '/private/internal/folder'"})
        failure += frame("chat.ask_user_question", {"source": "permission_interrupt", "request_id": "ask",
                                                   "questions": [{"question": "private approval text"}]})
        with self.assertRaises(AgentArtsError) as caught:
            read_answer(io.BytesIO(failure), time.monotonic() + 3, trace.observe)
        diagnostic = trace.failure(caught.exception)
        self.assertEqual(diagnostic["diagnostics"]["terminal_event"], "chat.ask_user_question")
        self.assertEqual(diagnostic["diagnostics"]["interrupt_source"], "permission_interrupt")
        self.assertEqual(diagnostic["steps"][0]["code"], "script_or_path_not_found")
        self.assertNotIn("private", json.dumps(diagnostic))

    def test_unmatched_bash_results_are_diagnosed_without_becoming_evidence(self):
        trace = TRACE()
        stream = tool_frames("one", "search", "retrieval", self.papers,
                             "curl 'https://api.crossref.org/works?private-query'")
        stream += frame("chat.tool_call", {"tool_call": {
            "tool_call_id": "two", "name": "bash", "arguments": {
                "command": "python3 -c 'private-code' scripts/literature_tools.py verify --doi private-input"
            },
        }})
        stream += frame("chat.tool_result", {"tool_call_id": "two", "tool_name": "bash",
                                            "result": "can't open file '/private/internal/path'"})
        stream += frame("chat.final", {"content": '{"status":"complete"}',
                                       "session_id": "public-session-ref", "request_id": "request-ref"})
        result = trace.check_result(read_answer(io.BytesIO(stream), time.monotonic() + 3, trace.observe))
        diag = result["diagnostics"]
        self.assertEqual(result["status"], "not_verified")
        self.assertEqual(result["steps"], [])
        self.assertEqual(diag["recognized_script_calls"], 0)
        self.assertEqual(diag["session_id"], "public-session-ref")
        first, second = diag["bash_calls"]
        self.assertEqual(first["execution_style"], "curl_or_wget")
        self.assertTrue(first["mentions_crossref_host"])
        self.assertEqual(first["reported_operation"], "search")
        self.assertEqual(second["execution_style"], "unrecognized_skill_command")
        self.assertEqual(second["result"], "script_or_path_not_found")
        self.assertNotIn("private", json.dumps(result))

    def test_history_request_is_read_only_and_reorders_messages(self):
        from email.message import Message
        from unittest.mock import Mock
        from research_library.agentarts import AgentArtsChat

        session = "fixture-session"
        final = {"event_type": "chat.final", "request_id": "original-request", "session_id": session,
                 "content": '{"status":"insufficient_evidence"}', "reasoning_content": "private reasoning"}
        call = {"event_type": "chat.tool_call", "request_id": "original-request", "session_id": session, "tool_call": {
            "tool_call_id": "a", "name": "bash", "arguments": {
                "command": "find /private -name literature_tools.py"
            },
        }}
        stop = {"status": "done", "total_pages": 1, "session_id": session}
        stream = io.BytesIO(frame("web.response", {"accepted": True}) +
                            frame("history.message", {"message": final}) +
                            frame("history.message", {"message": call}) + frame("history.message", stop))
        stream.headers = Message()
        stream.headers["Content-Type"] = "text/event-stream; charset=utf-8"
        client = AgentArtsChat("https://fixture.cn-southwest-2.huaweicloud-agentarts.com", "agent-huawei-cit",
                              "cn-southwest-2", "example-ak", "example-sk")
        client._opener = Mock()
        client._opener.open.return_value = stream
        messages, history = client.history(session)
        req = client._opener.open.call_args.args[0]
        headers = {name.lower(): value for name, value in req.header_items()}
        self.assertEqual(req.method, "GET")
        self.assertIsNone(req.data)
        self.assertTrue(req.full_url.endswith("/runtimes/managed-agent-huawei-cit/invocations/v1/chat/history"))
        self.assertEqual(headers["x-hw-agentarts-session-id"], session)
        self.assertIn("V11-HMAC-SHA256", headers["authorization"])
        self.assertEqual([m["event_type"] for m in messages], ["chat.tool_call", "chat.final"])
        self.assertNotIn("reasoning_content", messages[-1])
        self.assertEqual(history["pages_reported"], 1)
        self.assertTrue(history["done"])

    def test_history_replay_correlates_existing_request_and_only_emits_safe_verb(self):
        session = "fixture-session"
        request = "original-request"
        shared = {"session_id": session, "request_id": request}
        replay = PROBE["review_history"]
        messages = [
            {**shared, "event_type": "chat.tool_call", "tool_call": {"name": "bash", "tool_call_id": "x",
             "arguments": {"command": "find /private -name literature_tools.py"}}},
            {**shared, "event_type": "chat.tool_result", "tool_result":
             {"tool_name": "bash", "tool_call_id": "x", "result": "private-result"}},
            {**shared, "event_type": "chat.final", "content": '{"status":"insufficient_evidence"}'},
            {**shared, "request_id": "other", "event_type": "chat.tool_call",
             "tool_call": {"name": "bash", "tool_call_id": "other", "arguments": {"command": "pwd"}}},
        ]
        summary = replay(messages, session, request, {"done": True, "pages_reported": 1})
        self.assertEqual(summary["source"], "session_history")
        self.assertEqual(summary["status"], "not_verified")
        self.assertEqual(summary["checks"]["agent_reported_status"], "insufficient_evidence")
        self.assertEqual(summary["history"]["messages_reviewed"], 3)
        self.assertEqual(summary["diagnostics"]["bash_calls"][0]["shell_verb"], "find")
        self.assertEqual(summary["diagnostics"]["recognized_script_calls"], 0)
        self.assertNotIn("private", json.dumps(summary))
        no_request = replay(messages, session, "missing-request", {"done": True, "pages_reported": 1})
        self.assertEqual(no_request["diagnostics"]["failure_reason"], "request_not_found_in_history")

    def test_skill_history_identifies_other_tool_and_subsequent_listing_without_exposing_outputs(self):
        session, request = "fixture-session", "known-request"
        shared = {"request_id": request, "session_id": session}
        messages = [
            {**shared, "event_type": "chat.tool_call", "tool_call": {
                "name": "fixture_skill_loader", "tool_call_id": "a", "arguments": {"path": "/private/test"},
            }},
            {**shared, "event_type": "chat.tool_result", "tool_result": {
                "tool_name": "fixture_skill_loader", "tool_call_id": "a", "result": "literature-research /private/test",
            }},
            {**shared, "event_type": "chat.tool_call", "tool_call": {
                "name": "bash", "tool_call_id": "b", "arguments": {"command": "ls /private/test"},
            }},
            {**shared, "event_type": "chat.tool_result", "tool_result": {
                "tool_name": "bash", "tool_call_id": "b", "result": "SKILL.md\\nprivate-file",
            }},
            {**shared, "event_type": "chat.final", "content": "private final"},
        ]
        summary = PROBE["review_history"](messages, session, request, {"done": True}, skill_check=True)
        self.assertEqual(summary["mode"], "skill_check")
        self.assertEqual(summary["status"], "not_verified")
        diagnostics = summary["diagnostics"]
        self.assertEqual(diagnostics["failure_reason"], "script_help_command_not_observed")
        self.assertEqual(diagnostics["tools"], {"other": 1, "bash": 1})
        self.assertEqual(diagnostics["non_bash_calls"], [{
            "tool_name": "fixture_skill_loader", "result_observed": True, "result_mentions": ["literature-research"],
        }])
        self.assertEqual(diagnostics["bash_calls"][0]["result_mentions"], ["skill.md"])
        self.assertNotIn("private", json.dumps(summary))

    def test_skill_history_pairs_out_of_order_results_and_outer_ids(self):
        from research_library.agentarts import read_history

        session, request = "fixture-session", "fixture-request"
        shared = {"session_id": session, "request_id": request}
        tool_name = "skill_tool"
        wire_messages = [
            {**shared, "event_type": "chat.final", "content": "private response"},
            {**shared, "event_type": "chat.tool_call", "tool_call": {
                "name": tool_name, "tool_call_id": "load", "arguments": {},
            }},
            {**shared, "event_type": "chat.tool_call", "tool_call": {
                "name": "bash", "tool_call_id": "list", "arguments": {"command": "ls /private/project"},
            }},
            {**shared, "event_type": "chat.tool_result", "tool_call_id": "load", "tool_result": {
                "tool_name": tool_name, "result": "literature-research /private/project",
            }},
            {**shared, "event_type": "chat.tool_result", "tool_call_id": "list",
             "result": "SKILL.md"},
        ]
        raw = b"".join(frame("history.message", {"message": message, "total_pages": 1})
                       for message in wire_messages)
        messages, history = read_history(io.BytesIO(raw), time.monotonic() + 3)
        summary = PROBE["review_history"](messages, session, request, history, skill_check=True)
        self.assertEqual(summary["status"], "not_verified")
        self.assertFalse(summary["history"]["done"])
        self.assertEqual(summary["diagnostics"]["failure_reason"], "history_stream_incomplete")
        self.assertEqual(summary["history"]["tool_result_fields"], {
            "with_call_id": 2, "with_tool_name": 1, "with_output": 2,
        })
        self.assertEqual(summary["diagnostics"]["non_bash_calls"], [{
            "tool_name": tool_name, "result_observed": True, "result_mentions": ["literature-research"],
        }])
        self.assertEqual(summary["diagnostics"]["bash_calls"][0]["result_mentions"], ["skill.md"])
        self.assertNotIn("private", json.dumps(summary))

    def test_partial_history_keeps_debug_messages_but_does_not_pass(self):
        from research_library.agentarts import read_history

        session, request = "fixture-session", "original-request"
        message = {"session_id": session, "request_id": request, "event_type": "chat.tool_call", "tool_call": {
            "name": "bash", "tool_call_id": "one", "arguments": {"command": "find . -name literature_tools.py"},
        }}
        data = frame("web.response", {"accepted": True}) + frame("message", {
            "event": "history.message", "data": {"message": message, "total_pages": 1},
        })
        messages, history = read_history(io.BytesIO(data), time.monotonic() + 3)
        self.assertFalse(history["done"])
        self.assertTrue(history["accepted"])
        reviewed = PROBE["review_history"](messages, session, request, history)
        self.assertEqual(reviewed["status"], "not_verified")
        self.assertEqual(reviewed["diagnostics"]["failure_reason"], "history_stream_incomplete")
        self.assertEqual(reviewed["diagnostics"]["bash_calls"][0]["shell_verb"], "find")
        self.assertEqual(reviewed["history"]["messages_reviewed"], 1)

    def test_exploration_can_report_script_discovery_without_exposing_paths_or_passing(self):
        call = frame("chat.tool_call", {"tool_call": {"name": "bash", "tool_call_id": "find",
                     "arguments": {"command": "find /private/skill-test -name literature_tools.py"}}})
        for output, label in (
            ({"stdout": "/private/skill-test/scripts/literature_tools.py\n"}, "skill_script_path_observed"),
            ("Output: skill-test/scripts/literature_tools.py", "skill_script_path_observed"),
            ({"stdout": "", "stderr": ""}, "exploration_no_stdout"),
            ({"stdout": "", "stderr": "find: /private/skill-test: Permission denied"}, "permission_denied"),
            ({"stderr": ""}, "exploration_result_unrecognized"),
        ):
            with self.subTest(label=label):
                trace = TRACE()
                stream = call + frame("chat.tool_result", {"tool_name": "bash", "tool_call_id": "find",
                                                           "result": output})
                stream += frame("chat.final", {"content": "Skill check finished."})
                read_answer(io.BytesIO(stream), time.monotonic() + 3, trace.observe)
                result = trace.check_skill()
                self.assertEqual(result["status"], "not_verified")
                self.assertEqual(result["diagnostics"]["bash_calls"][0]["result"], label)
                self.assertNotIn("skill-test", json.dumps(result))

    def test_live_skill_check_retains_tool_errors_and_treats_final_outcome_as_a_hint(self):
        trace = TRACE()
        stream = frame("chat.tool_call", {"tool_call": {
            "tool_call_id": "load", "name": "skill_tool", "arguments": {"skill": "literature-research"},
        }})
        stream += frame("chat.tool_update", {"tool_call_id": "load", "status": "error", "detail": "private error"})
        stream += frame("chat.tool_result", {"tool_call_id": "load", "result": "Permission denied: /private/path"})
        stream += frame("chat.final", {"content": '{"outcome":"help_ran","details":"private response"}'})
        answer = read_answer(io.BytesIO(stream), time.monotonic() + 3, trace.observe)
        result = trace.check_skill(answer)
        self.assertEqual(result["status"], "not_verified")
        self.assertEqual(result["agent_reported_outcome"], "help_ran")
        self.assertEqual(result["diagnostics"]["non_bash_calls"], [{
            "tool_name": "skill_tool", "result_observed": True, "update_status": "error",
            "result_mentions": [], "result_failure": "permission_denied",
        }])
        self.assertNotIn("private", json.dumps(result))
        self.assertIsNone(trace.check_skill('{"outcome":"private status"}')["agent_reported_outcome"])

    def test_skill_health_requires_paired_cli_help_and_never_counts_as_search(self):
        call = frame("chat.tool_call", {"tool_call": {"name": "bash", "tool_call_id": "help",
                     "arguments": {"command": "python3 /tmp/literature-research/scripts/literature_tools.py --help"}}})
        for output, status, reason in (
            ({"stdout": "Output: usage: literature_tools.py [-h] {search,verify} ..."}, "skill_available", None),
            ({"stdout": "", "stderr": "bash: python3: not found"}, "not_verified", "python_not_available"),
            ({"stdout": "", "stderr": "python3: can't open file '/internal/literature_tools.py'"},
             "not_verified", "script_or_path_not_found"),
        ):
            with self.subTest(reason=reason):
                trace = TRACE()
                stream = call + frame("chat.tool_result", {"tool_name": "bash", "tool_call_id": "help",
                                                           "result": json.dumps(output)})
                stream += frame("chat.final", {"content": "Skill check finished."})
                output_text = read_answer(io.BytesIO(stream), time.monotonic() + 3, trace.observe)
                result = trace.check_skill()
                self.assertEqual(result["status"], status)
                self.assertEqual(result["diagnostics"]["failure_reason"], reason)
                self.assertEqual(result["diagnostics"]["recognized_script_calls"], 0)
                self.assertEqual(trace.check_result(output_text)["status"], "not_verified")
                self.assertNotIn("/internal", json.dumps(result))
        self.assertEqual(TRACE().check_skill()["diagnostics"]["failure_reason"], "no_bash_call_event")

    def test_skill_archive_matches_sources_and_rejects_invalid_doi(self):
        archive = ROOT / "literature-research.zip"
        source = ROOT / "skills" / "literature-research"
        with ZipFile(archive) as bundle:
            self.assertIsNone(bundle.testzip())
            self.assertEqual(len(bundle.namelist()), 2)
            for file in ("SKILL.md", "scripts/literature_tools.py"):
                self.assertEqual(bundle.read("literature-research/" + file), (source / file).read_bytes())
        self.assertTrue(TOOLS["valid_doi"]("10.1234/work"))
        with self.assertRaisesRegex(TOOLS["CitationServiceError"], "invalid_doi"):
            TOOLS["verify"]("https://somewhere.invalid")
