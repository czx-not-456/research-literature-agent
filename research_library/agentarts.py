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


class _RejectRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def signed_headers(headers, host, path, region, ak, sk, stamp, token=""):
    """Sign a POST to the fixed chat path using the APIG V11 IAM protocol."""
    headers = dict(headers, Host=host, **{
        "X-Sdk-Date": stamp,
        "X-Sdk-Content-Sha256": "UNSIGNED-PAYLOAD",
    })
    if token:
        headers["X-Security-Token"] = token
    canonical = sorted((name.lower(), value.strip()) for name, value in headers.items())
    signed = ";".join(name for name, _ in canonical)
    block = "".join(f"{name}:{value}\n" for name, value in canonical)
    request = "\n".join(("POST", path + "/", "", block, signed, "UNSIGNED-PAYLOAD"))
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


def _events(stream, deadline):
    event = ""
    data = []
    size = 0
    while True:
        if time.monotonic() >= deadline:
            raise AgentArtsError("等待 AgentArts 回答超时。")
        raw = stream.readline(MAX_LINE + 1)
        size += len(raw)
        if len(raw) > MAX_LINE or size > MAX_STREAM:
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


def read_answer(stream, deadline):
    segments = []
    output_size = 0
    for event, raw in _events(stream, deadline):
        if event in {"keepalive", "ping"}:
            continue
        try:
            envelope = json.loads(raw)
        except (ValueError, RecursionError):
            raise AgentArtsError("AgentArts 返回了无法解析的流式事件。") from None
        if not isinstance(envelope, dict):
            raise AgentArtsError("AgentArts 返回了无法解析的流式事件。")
        event = event or envelope.get("event_type") or envelope.get("event") or envelope.get("type")
        if event in ("chat.error", "chat.interrupt_result", "chat.ask_user_question", "chat.invocation_paused"):
            raise AgentArtsError("AgentArts 未完成本次问答，请查看平台运行日志。")
        if event not in ("chat.delta", "chat.final"):
            continue
        data = envelope.get("data", envelope)
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

    def ask(self, prompt):
        body = json.dumps({"query": prompt}, ensure_ascii=False).encode("utf-8")
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        headers = signed_headers(
            {"Content-Type": "application/json", "Accept": "text/event-stream",
             "X-Hw-Agentarts-Session-Id": uuid4().hex},
            self.host, self.path, self.region, self._ak, self._sk, stamp, self._token,
        )
        req = Request(f"https://{self.host}{self.path}", data=body, headers=headers, method="POST")
        deadline = time.monotonic() + RESPONSE_WINDOW
        try:
            with self._opener.open(req, timeout=IDLE_TIMEOUT) as response:
                if response.headers.get_content_type() != "text/event-stream":
                    raise AgentArtsError("AgentArts 返回的内容不是预期的 SSE 事件流。")
                return read_answer(response, deadline)
        except HTTPError as error:
            status = error.code
            error.close()
            if status in (401, 403):
                message = "请核对本地 IAM 密钥权限和智能体的入站认证。"
            elif status == 404:
                message = "请核对智能体名称、访问域名和部署状态。"
            elif status == 429:
                message = "平台限流或配额不足，请稍后再试。"
            else:
                message = "请查看 AgentArts 平台运行日志。"
            raise AgentArtsError(f"AgentArts 请求失败（HTTP {status}）。{message}") from None
        except TimeoutError:
            raise AgentArtsError("等待 AgentArts 回答超时。") from None
        except (URLError, HTTPException, OSError):
            raise AgentArtsError("无法完成与 AgentArts 的连接，请检查网络后再试。") from None