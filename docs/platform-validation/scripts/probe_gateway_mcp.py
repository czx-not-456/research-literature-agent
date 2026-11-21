"""Phase-two probe for the existing AgentArts MCP gateway."""

import argparse
import getpass
import hashlib
import hmac
import json
import os
import re
import sys
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

GATEWAY = "https://research-literature-mcp-gateway-defaultgw-mjrwiobqhe.cn-southwest-2.huaweicloud-agentarts.com/mcp"
PROTOCOL_VERSION = "2025-03-26"
TOOL = "crossref-search_search_papers"
RESPONSE_LIMIT = 1_000_000


class ProbeError(Exception):
    """An error safe to show without disclosing credentials or headers."""


class BlockRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def matching_reply(response, request_id):
    if response.headers.get_content_type() != "text/event-stream":
        body = response.read(RESPONSE_LIMIT + 1)
        if len(body) > RESPONSE_LIMIT:
            raise ProbeError("Response exceeded the probe limit.")
        candidates = (json.loads(body),)
    else:
        candidates = sse_objects(response)

    for message in candidates:
        if isinstance(message, dict) and message.get("id") == request_id:
            return message
    raise ProbeError("No JSON-RPC response matched the request ID.")


def sse_objects(response):
    data = []
    size = 0
    while chunk := response.readline(RESPONSE_LIMIT + 1):
        size += len(chunk)
        if size > RESPONSE_LIMIT:
            raise ProbeError("SSE response exceeded the probe limit.")
        line = chunk.decode("utf-8").rstrip("\r\n")
        if line.startswith("data:"):
            data.append(line[5:].lstrip(" "))
        elif not line and data:
            yield json.loads("\n".join(data))
            data.clear()
    if data:
        yield json.loads("\n".join(data))


def describe_http_error(error):
    fields = [f"HTTP {error.code}"]
    headers = error.headers or {}
    reply = {}
    try:
        body = error.read(8193)
        if len(body) <= 8192:
            decoded = json.loads(body)
            if isinstance(decoded, dict):
                reply = decoded
    except (ValueError, OSError):
        pass

    detail = reply.get("error")
    if not isinstance(detail, dict):
        detail = {}
    codes = (
        reply.get("error_code"), reply.get("code"), detail.get("code"),
        headers.get("X-Apig-Error-Code"),
    )
    for code in codes:
        if type(code) is int and -99999 <= code <= 99999:
            fields.append(f"code={code}")
            break
        if isinstance(code, str) and re.fullmatch(r"[A-Za-z]{2,16}[.-]\d{2,8}", code):
            fields.append(f"code={code}")
            break

    for request_id in (
        headers.get("X-Request-Id"), headers.get("X-Hw-Request-Id"),
        headers.get("X-Apig-Request-Id"), headers.get("X-HuaweiCloud-Request-Id"),
        reply.get("request_id"), reply.get("requestId"),
    ):
        if isinstance(request_id, str) and re.fullmatch(
            r"(?:[a-fA-F0-9]{32}|[a-fA-F0-9]{8}(?:-[a-fA-F0-9]{4}){3}-[a-fA-F0-9]{12})",
            request_id,
        ):
            fields.append(f"request_id={request_id}")
            break

    messages = (reply.get("error_msg"), reply.get("message"), detail.get("message"))
    text = " ".join(message.casefold() for message in messages if isinstance(message, str))
    hints = (
        ("clock_or_timestamp", r"clock skew|request (?:has )?expired|timestamp.*(?:expired|invalid|skew)|(?:invalid|expired).*x-sdk-date|时钟|时间戳"),
        ("security_token", r"security[ -]token|temporary credential|安全令牌|临时凭证"),
        ("access_key", r"access[ -]key|unknown ak|invalid ak|ak not (?:found|exist)|访问密钥"),
        ("signing_algorithm", r"signing algorithm|signature algorithm|签名算法"),
        ("signature", r"signature|signedheaders|签名"),
        ("permission", r"permission|access denied|forbidden|权限|无权"),
        ("authentication", r"authentication|authorization|unauthorized|鉴权|认证"),
    )
    for label, pattern in hints:
        if re.search(pattern, text):
            fields.append(f"hint={label}")
            break
    return "; ".join(fields) + "."


class V11ProbeSigner:
    """Sign this query-free MCP request using the AgentArts SDK V11 wire format."""

    def __init__(self, ak, sk):
        self.ak = ak
        self.sk = sk

    def sign(self, request):
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        scope = f"{timestamp[:8]}/cn-southwest-2/apic"
        algorithm = "V11-HMAC-SHA256"
        headers = request.header_params
        headers["Host"] = request.host
        headers["X-Sdk-Date"] = timestamp
        canonical_headers = {key.lower(): value.strip() for key, value in headers.items()}
        signed_headers = ";".join(sorted(canonical_headers))
        header_block = "".join(f"{key}:{canonical_headers[key]}\n"
                               for key in sorted(canonical_headers))
        path = "/".join(quote(part, safe="~") for part in unquote(request.resource_path).split("/"))
        canonical_request = "\n".join((
            request.method.upper(), path.rstrip("/") + "/", "",
            header_block, signed_headers, "UNSIGNED-PAYLOAD",
        ))
        request_hash = hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
        string_to_sign = "\n".join((algorithm, timestamp, scope, request_hash))
        extracted = hmac.digest(self.ak.encode("utf-8"), self.sk.encode("utf-8"), "sha256")
        expanded = hmac.digest(extracted, scope.encode("utf-8") + b"\x01", "sha256")
        signature = hmac.new(expanded.hex().encode("ascii"), string_to_sign.encode("utf-8"),
                             "sha256").hexdigest()
        headers["Authorization"] = (
            f"{algorithm} Credential={self.ak}/{scope}, "
            f"SignedHeaders={signed_headers}, Signature={signature}"
        )
        return request


class GatewayProbe:
    def __init__(self, signer, request_type, opener, security_token=None):
        self.signer = signer
        self.request_type = request_type
        self.opener = opener
        self.security_token = security_token
        self.session_id = None
        self.protocol_version = None

    def send(self, method, params=None, *, notification=False):
        payload = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            payload["params"] = params
        if not notification:
            payload["id"] = str(uuid.uuid4())
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "X-Sdk-Content-Sha256": "UNSIGNED-PAYLOAD",
        }
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        if self.protocol_version:
            headers["MCP-Protocol-Version"] = self.protocol_version
        if self.security_token:
            headers["X-Security-Token"] = self.security_token

        endpoint = urlsplit(GATEWAY)
        signed = self.signer.sign(self.request_type(
            method="POST", schema=endpoint.scheme, host=endpoint.netloc,
            resource_path=endpoint.path, query_params=[], header_params=headers, body=body,
        ))
        request = Request(GATEWAY, data=body, headers=signed.header_params, method="POST")
        try:
            with self.opener.open(request, timeout=20) as response:
                if notification:
                    if response.status != 202:
                        raise ProbeError(f"{method}: expected HTTP 202, got {response.status}.")
                    return None
                reply = matching_reply(response, payload["id"])
                if method == "initialize":
                    self.session_id = response.headers.get("Mcp-Session-Id")
        except HTTPError as error:
            try:
                diagnosis = describe_http_error(error)
            finally:
                error.close()
            raise ProbeError(f"{method}: {diagnosis}") from None
        except (URLError, TimeoutError):
            raise ProbeError(f"{method}: connection failed or timed out.") from None

        if "error" in reply:
            code = reply["error"].get("code")
            rpc_code = str(code) if type(code) is int else "unknown"
            raise ProbeError(f"{method}: JSON-RPC error {rpc_code}.")
        result = reply.get("result")
        if not isinstance(result, dict):
            raise ProbeError(f"{method}: missing JSON-RPC result.")
        return result

    def connect(self):
        initialization = self.send("initialize", {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "literature-gateway-probe", "version": "0.1.0"},
        })
        if initialization.get("protocolVersion") != PROTOCOL_VERSION:
            raise ProbeError("Gateway returned a different MCP version.")
        self.protocol_version = PROTOCOL_VERSION
        self.send("notifications/initialized", notification=True)


def search_once(probe, query):
    result = probe.send("tools/call", {"name": TOOL, "arguments": {"query": {
        "query.bibliographic": query,
        "rows": 2,
        "filter": "type:journal-article",
        "select": "DOI,title,author,published,URL,type",
    }}})
    if result.get("isError"):
        raise ProbeError("tools/call: the gateway reported a tool error.")
    structured = result.get("structuredContent")
    if structured is None:
        for block in result.get("content", []):
            if block.get("type") == "text":
                structured = json.loads(block["text"])
                break
    if not isinstance(structured, dict) or structured.get("status") != "ok":
        raise ProbeError("tools/call: no successful Crossref result.")
    items = structured.get("message", {}).get("items")
    if not isinstance(items, list):
        raise ProbeError("tools/call: Crossref items missing.")
    return [{"title": item.get("title"), "doi": item.get("DOI"), "url": item.get("URL")}
            for item in items]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", help="Also make one Crossref request with this search topic.")
    parser.add_argument("--signing", choices=("sdk", "v11"), default="sdk",
                        help="Choose standard Huawei SDK signing or the AgentArts V11 comparison.")
    args = parser.parse_args()
    query = args.query.strip() if args.query is not None else None
    if query is not None and not 1 <= len(query) <= 200:
        parser.error("--query must contain 1 to 200 characters.")

    try:
        from huaweicloudsdkcore.sdk_request import SdkRequest
        from huaweicloudsdkcore.signer.signer import Signer
    except ImportError:
        parser.exit(2, "Install huaweicloudsdkcore in the Python environment used for this script.\n")

    ak = os.environ.get("HUAWEICLOUD_SDK_AK")
    sk = os.environ.get("HUAWEICLOUD_SDK_SK")
    if sys.stdin.isatty() and sys.stderr.isatty():
        ak = ak or getpass.getpass("Huawei Cloud AK (hidden): ")
        sk = sk or getpass.getpass("Huawei Cloud SK (hidden): ")
    if not ak or not sk:
        parser.exit(2, "Provide IAM credentials in the current local process or interactive prompt.\n")

    try:
        signer = (V11ProbeSigner(ak, sk) if args.signing == "v11"
                  else Signer(SimpleNamespace(ak=ak, sk=sk)))
        probe = GatewayProbe(signer, SdkRequest, build_opener(BlockRedirects()),
                             os.environ.get("HUAWEICLOUD_SDK_SECURITY_TOKEN"))
        probe.connect()
        tools = probe.send("tools/list").get("tools", [])
        names = [tool["name"] for tool in tools]
        if TOOL not in names:
            raise ProbeError("The Crossref tool was not returned by tools/list.")
        output = {"status": "ok", "scope": "gateway_mcp_only", "tools": names}
        if query is not None:
            output["papers"] = search_once(probe, query)
        print(json.dumps(output, ensure_ascii=False, indent=2))
    except ProbeError as error:
        parser.exit(1, f"{error}\n")
    except (ValueError, KeyError, TypeError, AttributeError):
        parser.exit(1, "Unexpected signing input or gateway response. No raw headers were printed.\n")


if __name__ == "__main__":
    main()
