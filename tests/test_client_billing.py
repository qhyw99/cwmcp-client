import unittest
import os
import json
import uuid
from unittest.mock import MagicMock, patch, mock_open
from remote_mcp_server import RemoteMCPServer

class TestRemoteMCPServerBilling(unittest.TestCase):

    def setUp(self):
        # Reset env vars
        if "MCP_API_KEY" in os.environ:
            del os.environ["MCP_API_KEY"]

    def test_load_api_key_from_env(self):
        os.environ["MCP_API_KEY"] = "env-key-123"
        server = RemoteMCPServer()
        self.assertEqual(server.api_key, "env-key-123")

    def test_load_api_key_from_config(self):
        mock_config = json.dumps({"api_key": "config-key-456"})
        with patch("builtins.open", mock_open(read_data=mock_config)):
            with patch("os.path.exists", return_value=True):
                server = RemoteMCPServer()
                self.assertEqual(server.api_key, "config-key-456")

    @patch("remote_mcp_server.httpx.Client")
    def test_run_generation_sends_headers(self, mock_client_cls):
        os.environ["MCP_API_KEY"] = "test-key"
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        
        # Mock successful response
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"status": "success"}
        mock_client.post.return_value = mock_resp
        
        server = RemoteMCPServer()
        server.run_contextweave_generation(user_request="hello")
        
        # Verify call arguments
        args, kwargs = mock_client.post.call_args
        self.assertEqual(args[0], "/run")
        self.assertIn("headers", kwargs)
        headers = kwargs["headers"]
        self.assertEqual(headers["X-API-Key"], "test-key")
        self.assertTrue("X-Request-ID" in headers)
        
    @patch("remote_mcp_server.httpx.Client")
    def test_run_generation_handles_402_payment_required(self, mock_client_cls):
        os.environ["MCP_API_KEY"] = "broke-key"
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        
        mock_resp = MagicMock()
        mock_resp.status_code = 402
        mock_client.post.return_value = mock_resp
        
        server = RemoteMCPServer()
        result = server.run_contextweave_generation(user_request="hello")
        
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error"]["code"], "PAYMENT_REQUIRED")

    @patch("remote_mcp_server.httpx.Client")
    def test_run_generation_handles_403_auth_error(self, mock_client_cls):
        # No key set
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_client.post.return_value = mock_resp
        
        server = RemoteMCPServer()
        result = server.run_contextweave_generation(user_request="hello")
        
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error"]["code"], "AUTH_ERROR")

if __name__ == '__main__':
    unittest.main()
