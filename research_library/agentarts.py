"""Server-side client for the documented AgentArts Managed Agent chat API."""

import hashlib
import hmac
import json
import re
import time
from datetime import datetime, timezone
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import uuid4

MAX_LINE = 128 * 1024
MAX_STREAM = 1024 * 1024
MAX_ANSWER = 20_000
IDLE_TIMEOUT = 30
RESPONSE_WINDOW = 90


class AgentArtsError(Exception):
    """A sanitized failure that can be shown in the local interface."""

    def __init__(self, message, *, timeout_phase=None):
        super().__init__(message)
        self.timeout_phase = timeout_phase


class _RejectRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def signed_headers(headers, host, path, region, ak, sk, stamp, token="", *, method="POST"):
    """Sign a fixed AgentArts API path using the APIG V11 IAM protocol."""
    headers = dict(headers, Host=host, **{
        "X-Sdk-Date": stamp,
        "X-Sdk-Content-Sha256": "UNSIGNED-PAYLOAD",
    })
    if token:
        headers["X-Security-Token"] = token
    canonical = sorted((name.lower(), value.strip()) for name, value in headers.items())
    signed = ";".join(name for name, _ in canonical)
    block = "".join(f"{name}:{value}\n" for name, value in canonical)
    request = "\n".join((method, path + "/", "", block, signed, "UNSIGNED-PAYLOAD"))
    scope = f"{stamp[:8]}/{region}/apic"
    algorithm = "V11-HMAC-SHA256"
    message = "\n".join((algorithm, stamp, scope, hashlib.sha256(request.encode()).hexdigest()))
    extracted = hmac.digest(ak.encode(), sk.encode(), "sha256")
    derived = hmac.digest(extracted, scope.encode() + b"\x01", "sha256")
    signature = hmac.digest(derived.hex().encode("ascii"), message.encode(), "sha256").hex()
    headers["Authorization"] = (
        f"{algorithm} Credential={ak}/{scope}, SignedHeaders={signed}, Signature={signature}"
    )
    return headers


def _events(stream, deadline, *, line_limit=MAX_LINE, stream_limit=MAX_STREAM):
    event = ""
    data = []
    size = 0
    while True:
        if time.monotonic() >= deadline:
            raise AgentArtsError(
                "等待 AgentArts 事件流超过本次回答的时间窗口。",
                timeout_phase="response_window_exceeded",
            )
        raw = stream.readline(line_limit + 1)
        size += len(raw)
        if len(raw) > line_limit or size > stream_limit:
            raise AgentArtsError("AgentArts 返回超出本次问答的大小限制。")
        line = raw.rstrip(b"\r\n")
        if not line:
            if data:
                yield event, b"\n".join(data)
            event, data = "", []
            if not raw:
                return
        elif line.startswith(b"event:"):
            event = line[6:].strip().decode("ascii", errors="replace")
        elif line.startswith(b"data:"):
            data.append(line[5:].removeprefix(b" "))


def read_answer(stream, deadline, observer=None):
    segments = []
    output_size = 0
    for event, raw in _events(stream, deadline):
        if event in {"keepalive", "ping"}:
            if observer is not None:
                observer(event, {})
            continue
        try:
            envelope = json.loads(raw)
        except (ValueError, RecursionError):
            raise AgentArtsError("AgentArts 返回了无法解析的流式事件。") from None
        if not isinstance(envelope, dict):
            raise AgentArtsError("AgentArts 返回了无法解析的流式事件。")
        data = envelope.get("data", envelope)
        if event in ("", "message"):
            nested = data.get("event_type") if isinstance(data, dict) else None
            event = envelope.get("event_type") or envelope.get("event") or nested or envelope.get("type")
        if (observer is not None and isinstance(data, dict) and event in (
            "web.response", "chat.tool_call", "chat.tool_update", "chat.tool_result", "chat.delta", "chat.final",
            "chat.error", "chat.interrupt_result", "chat.ask_user_question", "chat.invocation_paused",
        )):
            observer(event, data)
        if event in ("chat.error", "chat.interrupt_result", "chat.ask_user_question", "chat.invocation_paused"):
            raise AgentArtsError("AgentArts 未完成本次问答，请查看平台运行日志。")
        if event not in ("chat.delta", "chat.final"):
            continue
        if not isinstance(data, dict):
            raise AgentArtsError("AgentArts 返回的回答事件缺少数据。")
        content = data.get("content", "")
        if not isinstance(content, str):
            raise AgentArtsError("AgentArts 返回的回答不是文本。")
        if event == "chat.delta":
            output_size += len(content)
            if output_size > MAX_ANSWER:
                raise AgentArtsError("AgentArts 回答超出本次问答的长度限制。")
            segments.append(content)
            continue
        if envelope.get("status", data.get("status", "success")) != "success" or (
            envelope.get("is_complete", data.get("is_complete")) is False
        ):
            raise AgentArtsError("AgentArts 未完成本次问答，请查看平台运行日志。")
        answer = content or "".join(segments)
        if not answer.strip() or len(answer) > MAX_ANSWER:
            raise AgentArtsError("AgentArts 未返回可核验的回答文本。")
        return answer
    raise AgentArtsError("AgentArts 连接在回答完成前关闭。")


def read_history(stream, deadline):
    """Read available review events and keep a separate end-of-stream flag."""
    messages = []
    total_pages = None
    done = False
    accepted = None
    counts = {"history.message": 0, "web.response": 0, "other": 0}
    fields = {
        "chat.tool_call": ("tool_call",),
        "chat.tool_result": ("tool_result", "tool_call_id", "tool_name", "result"),
        "chat.final": ("content",),
        "chat.error": (),
        "chat.interrupt_result": (),
        "chat.ask_user_question": ("source",),
    }
    for event, raw in _events(stream, deadline, line_limit=2 * 1024 * 1024, stream_limit=8 * 1024 * 1024):
        if event not in ("history.message", "web.response", "", "message"):
            counts["other"] += 1
            continue
        try:
            envelope = json.loads(raw)
        except (ValueError, RecursionError):
            raise AgentArtsError("AgentArts 返回了无法解析的历史事件。") from None
        if not isinstance(envelope, dict):
            raise AgentArtsError("AgentArts 返回的历史事件缺少数据。")
        payload = envelope.get("data", envelope)
        if not isinstance(payload, dict):
            counts["other"] += 1
            continue
        if event in ("", "message"):
            event = envelope.get("event") or envelope.get("event_type") or payload.get("event_type")
        if event == "web.response":
            counts["web.response"] += 1
            if type(payload.get("accepted")) is bool:
                accepted = payload["accepted"]
            continue
        if event != "history.message":
            counts["other"] += 1
            continue
        counts["history.message"] += 1
        pages = payload.get("total_pages")
        if type(pages) is int and 1 <= pages <= 10_000:
            total_pages = pages
        message = payload.get("message")
        if isinstance(message, dict):
            event_type = message.get("event_type")
            if isinstance(event_type, str) and event_type in fields:
                keys = ("event_type", "request_id", "session_id", *fields[event_type])
                messages.append({key: message[key] for key in keys if key in message})
        if payload.get("status") == "done":
            done = True
            break
    return list(reversed(messages)), {
        "done": done, "accepted": accepted, "events": counts, "pages_reported": total_pages,
    }


def _http_diagnostics(error):
    # Print only the public platform error code, trace ID and fixed classifications.
    request_id = (error.headers or {}).get("X-Request-Id")
    payload = {}
    try:
        data = json.loads(error.read(4096))
        if isinstance(data, dict):
            payload = data
    except (ValueError, OSError, HTTPException, RecursionError):
        pass
    finally:
        error.close()

    code = payload.get("error_code")
    request_id = request_id or payload.get("request_id")
    details = []
    if isinstance(code, str) and re.fullmatch(r"(?:APIGW?|AgentArts)\.[0-9]{4,12}", code):
        details.append(f"平台错误码 {code}")
    if isinstance(request_id, str) and re.fullmatch(r"[a-fA-F0-9-]{16,64}", request_id):
        details.append(f"请求 ID {request_id}")
    raw_message = payload.get("error_msg") or payload.get("message")
    message = raw_message.lower() if isinstance(raw_message, str) else ""
    if "signature expired" in message:
        details.append("签名时间超出有效窗口，请同步 Windows 系统时钟")
    elif "token expired" in message or "token expires" in message:
        details.append("请刷新完整的临时凭据")
    return "（" + "，".join(details) + "）" if details else ""

class AgentArtsChat:
    def __init__(self, endpoint, agent, region, ak, sk, token=""):
        # Only allow the configured regional AgentArts service to receive IAM credentials.
        label = r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
        if not re.fullmatch(label, region):
            raise ValueError("AgentArts 区域格式无效。")
        match = re.fullmatch(
            rf"https://({label}\.{re.escape(region)}\.huaweicloud-agentarts\.com)/?", endpoint
        )
        if not match:
            raise ValueError("请输入对应区域 AgentArts 的 HTTPS 网关域名。")
        runtime = f"managed-{agent}"
        if not re.fullmatch(r"[a-z][a-z0-9-]{0,46}[a-z0-9]", runtime):
            raise ValueError("AgentArts 智能体名称格式无效。")
        if not ak or not sk:
            raise ValueError("需要华为云 AK 和 SK。")
        self.host = match.group(1)
        self.path = f"/runtimes/{runtime}/invocations/v1/chat/completions"
        self.region = region
        self._ak, self._sk, self._token = ak, sk, token
        self._opener = build_opener(_RejectRedirects())

    def history(self, session_id):
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", session_id):
            raise ValueError("AgentArts 会话 ID 格式无效。")
        path = self.path.removesuffix("completions") + "history"
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        headers = signed_headers(
            {"Accept": "text/event-stream", "X-Hw-Agentarts-Session-Id": session_id},
            self.host, path, self.region, self._ak, self._sk, stamp, self._token, method="GET",
        )
        req = Request(f"https://{self.host}{path}", headers=headers, method="GET")
        return self._read_stream(req, read_history, "历史会话查询")

    def _read_stream(self, req, reader, operation):
        try:
            with self._opener.open(req, timeout=IDLE_TIMEOUT) as response:
                if response.headers.get_content_type() != "text/event-stream":
                    raise AgentArtsError("AgentArts 返回的内容不是预期的 SSE 事件流。")
                return reader(response, time.monotonic() + RESPONSE_WINDOW)
        except HTTPError as error:
            status = error.code
            diagnostic = _http_diagnostics(error)
            raise AgentArtsError(f"AgentArts {operation}失败（HTTP {status}）。{diagnostic}") from None
        except TimeoutError:
            raise AgentArtsError(f"等待 AgentArts {operation}超时。") from None
        except (URLError, HTTPException, OSError):
            raise AgentArtsError(f"无法连接 AgentArts 进行{operation}。") from None

    def ask(self, prompt, *, observer=None, response_window=RESPONSE_WINDOW, socket_timeout=IDLE_TIMEOUT):
        body = json.dumps({"query": prompt}, ensure_ascii=False).encode("utf-8")
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        headers = signed_headers(
            {"Content-Type": "application/json", "Accept": "text/event-stream",
             "X-Hw-Agentarts-Session-Id": uuid4().hex},
            self.host, self.path, self.region, self._ak, self._sk, stamp, self._token,
        )
        req = Request(f"https://{self.host}{self.path}", data=body, headers=headers, method="POST")
        deadline = time.monotonic() + response_window
        received_headers = False
        try:
            with self._opener.open(req, timeout=socket_timeout) as response:
                received_headers = True
                if response.headers.get_content_type() != "text/event-stream":
                    raise AgentArtsError("AgentArts 返回的内容不是预期的 SSE 事件流。")
                return read_answer(response, deadline, observer)
        except HTTPError as error:
            status = error.code
            diagnostic = _http_diagnostics(error)
            if status in (401, 403):
                message = "请核对运行时访问域名、IAM 密钥以及入站认证。"
            elif status == 404:
                message = "请核对智能体名称、访问域名和部署状态。"
            elif status == 429:
                message = "平台限流或配额不足，请稍后再试。"
            else:
                message = "请查看 AgentArts 平台运行日志。"
            raise AgentArtsError(f"AgentArts 请求失败（HTTP {status}）。{message}{diagnostic}") from None
        except (URLError, HTTPException, OSError) as error:
            cause = error.reason if isinstance(error, URLError) else error
            if isinstance(cause, TimeoutError):
                if received_headers:
                    raise AgentArtsError(
                        "已收到 HTTP 响应头，读取 AgentArts 事件流时超时。",
                        timeout_phase="waiting_for_stream_data",
                    ) from None
                raise AgentArtsError(
                    "等待 AgentArts HTTP 响应头超时。",
                    timeout_phase="waiting_for_response_headers",
                ) from None
            raise AgentArtsError("无法完成与 AgentArts 的连接，请检查网络后再试。") from None