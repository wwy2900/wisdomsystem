import os
import unittest
from unittest.mock import patch

from utils.dashscope_runtime import build_dashscope_error_payload
from utils.network_env import ensure_no_proxy_hosts


class NetworkEnvTests(unittest.TestCase):
    def test_ensure_no_proxy_hosts_preserves_existing_entries_and_adds_dashscope_when_enabled(self):
        with patch.dict(
            os.environ,
            {
                "NO_PROXY": "localhost,127.0.0.1",
                "no_proxy": "localhost,127.0.0.1",
            },
            clear=False,
        ):
            merged = ensure_no_proxy_hosts(("dashscope.aliyuncs.com", ".aliyuncs.com"), enabled=True)

            self.assertIn("localhost", merged)
            self.assertIn("127.0.0.1", merged)
            self.assertIn("dashscope.aliyuncs.com", merged)
            self.assertIn(".aliyuncs.com", merged)
            self.assertEqual(os.environ["NO_PROXY"], os.environ["no_proxy"])

    def test_ensure_no_proxy_hosts_does_not_append_dashscope_when_disabled(self):
        with patch.dict(
            os.environ,
            {
                "NO_PROXY": "localhost,127.0.0.1",
                "no_proxy": "localhost,127.0.0.1",
                "DASHSCOPE_BYPASS_PROXY": "false",
            },
            clear=False,
        ):
            merged = ensure_no_proxy_hosts(("dashscope.aliyuncs.com", ".aliyuncs.com"))

            self.assertEqual(merged, "localhost,127.0.0.1")
            self.assertNotIn("dashscope.aliyuncs.com", merged)
            self.assertNotIn(".aliyuncs.com", merged)

    def test_build_dashscope_error_payload_classifies_tls_proxy_failures(self):
        error = RuntimeError(
            "HTTPSConnectionPool(host='dashscope.aliyuncs.com', port=443): "
            "Max retries exceeded with url: / (Caused by SSLError(SSLEOFError(8, "
            "'[SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol'))))"
        )

        payload = build_dashscope_error_payload(error)

        self.assertEqual(payload["code"], "dashscope_proxy_tls")
        self.assertIn("proxy/TLS chain", payload["content"])

    def test_build_dashscope_error_payload_classifies_direct_connect_blocks(self):
        error = RuntimeError(
            "HTTPSConnection(host='dashscope.aliyuncs.com', port=443): Failed to establish a new connection: [WinError 10013] blocked"
        )

        payload = build_dashscope_error_payload(error)

        self.assertEqual(payload["code"], "dashscope_direct_blocked")
        self.assertIn("direct connection was blocked", payload["content"])


if __name__ == "__main__":
    unittest.main()
