import os
import unittest
from unittest.mock import patch

from utils.network_env import ensure_no_proxy_hosts


class NetworkEnvTests(unittest.TestCase):
    def test_ensure_no_proxy_hosts_preserves_existing_entries_and_adds_dashscope(self):
        with patch.dict(
            os.environ,
            {
                "NO_PROXY": "localhost,127.0.0.1",
                "no_proxy": "localhost,127.0.0.1",
            },
            clear=False,
        ):
            merged = ensure_no_proxy_hosts(("dashscope.aliyuncs.com", ".aliyuncs.com"))

            self.assertIn("localhost", merged)
            self.assertIn("127.0.0.1", merged)
            self.assertIn("dashscope.aliyuncs.com", merged)
            self.assertIn(".aliyuncs.com", merged)
            self.assertEqual(os.environ["NO_PROXY"], os.environ["no_proxy"])


if __name__ == "__main__":
    unittest.main()
