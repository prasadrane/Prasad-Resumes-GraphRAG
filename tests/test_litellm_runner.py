"""
Unit tests for LiteLLM runner proxy launcher and health check.
"""

import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
from src.proxy.litellm_runner import start_proxy_server, check_proxy_health

class TestLiteLLMRunner(unittest.TestCase):

    def test_start_proxy_server_missing_config(self):
        non_existent_path = Path("non_existent_config.yaml")
        with self.assertRaises(FileNotFoundError):
            start_proxy_server(non_existent_path)

    @patch("shutil.which")
    def test_start_proxy_server_missing_binary(self, mock_which):
        mock_which.return_value = None
        tmp_config = Path(__file__)  # Exists
        with self.assertRaises(RuntimeError) as ctx:
            start_proxy_server(tmp_config)
        self.assertIn("LiteLLM CLI executable not found", str(ctx.exception))

    @patch("urllib.request.urlopen")
    def test_check_proxy_health_active(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        self.assertTrue(check_proxy_health("localhost", 8002))

    @patch("urllib.request.urlopen")
    def test_check_proxy_health_inactive(self, mock_urlopen):
        mock_urlopen.side_effect = Exception("Connection refused")
        self.assertFalse(check_proxy_health("localhost", 8002))

if __name__ == "__main__":
    unittest.main()
