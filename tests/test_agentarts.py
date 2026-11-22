import io
import json
import runpy
import time
import unittest
from datetime import datetime, timezone
from email.message import Message
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
from urllib.error import HTTPError

from research_library.agentarts import AgentArtsChat, AgentArtsError, read_answer, signed_headers


def frame(name, payload):
    return f"event: {name}\r\ndata: {json.dumps(payload)}\r\n\r\n".encode()


class AgentArtsTransportTest(unittest.TestCase):
    def setUp(self):
        self.host = "example.cn-southwest-2.huaweicloud-agentarts.com"
        self.client = AgentArtsChat(f"https://{self.host}", "agent-huawei-cit", "cn-southwest-2", "example-ak", "example-sk")
        self.client._opener = Mock()

    def test_documented_sse_flat_data_and_signed_request(self):
        stream = (
            frame("web.response", {"accepted": True})
            + frame("keepalive", {})
            + frame("chat.reasoning", {"content": "Internal reasoning"})
            + frame("chat.delta", {"content": '{"claims":'})
            + frame("chat.delta", {"content": "[]}"})
            + frame("chat.final", {"content": ""})
        )
        sent = []
        for _ in range(2):
            response = io.BytesIO(stream)
            response.headers = Message()
            response.headers["Content-Type"] = "text/event-stream; charset=UTF-8"
            self.client._opener.open.return_value = response
            self.assertEqual(self.client.ask("论文问题"), '{"claims":[]}')
            req = self.client._opener.open.call_args.args[0]
            self.assertEqual(req.method, "POST")
            self.assertEqual(req.full_url, f"https://{self.host}/runtimes/managed-agent-huawei-cit/invocations/v1/chat/completions")
            self.assertEqual(json.loads(req.data), {"query": "论文问题"})
            headers = {key.lower(): value for key, value in req.header_items()}
            self.assertEqual(headers["x-sdk-content-sha256"], "UNSIGNED-PAYLOAD")
            self.assertTrue(headers["authorization"].startswith("V11-HMAC-SHA256 Credential=example-ak/"))
            self.assertRegex(headers["x-hw-agentarts-session-id"], "^[0-9a-f]{32}$")
            sent.append(headers["x-hw-agentarts-session-id"])
        self.assertNotEqual(*sent)

    def test_v11_signature_matches_existing_gateway_probe(self):
        probe = Path(__file__).resolve().parents[1] / "docs/platform-validation/scripts/probe_gateway_mcp.py"
        previous = runpy.run_path(str(probe))
        cls = previous["V11ProbeSigner"]
        now = datetime(2026, 11, 22, 1, 2, 3, tzinfo=timezone.utc)
        example = {"Accept": "text/event-stream", "X-Hw-Agentarts-Session-Id": "sample"}
        obj = SimpleNamespace(host=self.host, method="POST", resource_path=self.client.path,
                              header_params={**example, "X-Sdk-Content-Sha256": "UNSIGNED-PAYLOAD"})
        with patch.dict(cls.sign.__globals__, {"datetime": Mock(now=Mock(return_value=now))}):
            expected = cls("example-ak", "example-sk").sign(obj).header_params["Authorization"]
        actual = signed_headers(example, self.host, self.client.path, "cn-southwest-2",
                                "example-ak", "example-sk", "20261122T010203Z")
        self.assertEqual(actual["Authorization"], expected)

    def test_terminal_errors_and_incomplete_streams_never_return_partial_answers(self):
        prefix = frame("chat.delta", {"content": "partial content"})
        for terminal in ("chat.error", "chat.ask_user_question", "chat.interrupt_result", "chat.invocation_paused", ""):
            with self.subTest(terminal=terminal), self.assertRaises(AgentArtsError):
                read_answer(io.BytesIO(prefix + (frame(terminal, {}) if terminal else b"")), time.monotonic() + 1)
        with self.assertRaisesRegex(AgentArtsError, "超时"):
            read_answer(io.BytesIO(prefix), time.monotonic() - 1)

    def test_complete_final_and_sanitized_http_errors(self):
        stream = frame("chat.final", {"data": {"content": "final answer", "is_complete": True}})
        self.assertEqual(read_answer(io.BytesIO(stream), time.monotonic() + 1), "final answer")
        self.client._opener.open.side_effect = HTTPError("", 401, "sensitive payload", {}, io.BytesIO(b"do not display"))
        with self.assertRaisesRegex(AgentArtsError, "HTTP 401") as caught:
            self.client.ask("test")
        self.assertNotIn("sensitive payload", str(caught.exception))
        for endpoint in ("http://example.com", "https://example.cn-southwest-2.huaweicloud-agentarts.com.evil.test",
                         f"https://{self.host}@example.com", f"https://{self.host}/unexpected"):
            with self.subTest(endpoint=endpoint), self.assertRaises(ValueError):
                AgentArtsChat(endpoint, "agent", "cn-southwest-2", "ak", "sk")


if __name__ == "__main__":
    unittest.main()
