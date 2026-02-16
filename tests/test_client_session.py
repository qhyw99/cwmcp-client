import unittest
from unittest.mock import MagicMock, patch
import os
import json
import tempfile
import shutil
import sys

import types
import importlib

fake_mcp_module = types.ModuleType("mcp")
fake_mcp_server_module = types.ModuleType("mcp.server")
fake_mcp_fastmcp_module = types.ModuleType("mcp.server.fastmcp")

class FakeFastMCP:
    def __init__(self, *args, **kwargs):
        pass

    def tool(self):
        def decorator(fn):
            return fn
        return decorator

    def run(self):
        return None

fake_mcp_fastmcp_module.FastMCP = FakeFastMCP

sys.modules["mcp"] = fake_mcp_module
sys.modules["mcp.server"] = fake_mcp_server_module
sys.modules["mcp.server.fastmcp"] = fake_mcp_fastmcp_module

fake_remote_module = types.ModuleType("remote_mcp_server")

class FakeRemoteMCPServer:
    def __init__(self, *args, **kwargs):
        pass

fake_remote_module.RemoteMCPServer = FakeRemoteMCPServer
sys.modules["remote_mcp_server"] = fake_remote_module

if "main" in sys.modules:
    del sys.modules["main"]
main = importlib.import_module("main")

class TestSessionIdPersistence(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.outline_file = os.path.join(self.test_dir, "plan.md")
        with open(self.outline_file, "w") as f:
            f.write("```json\n{}\n```")
        print(f"[test] working_dir={self.test_dir}")
        print(f"[test] outline_file_path={self.outline_file}")
            
        self.mock_backend = MagicMock()
        main.backend = self.mock_backend

    def tearDown(self):
        # Cleanup (disabled for manual inspection)
        # shutil.rmtree(self.test_dir)
        pass

    def test_generate_contextweave_from_outline_saves_session_id(self):
        # Arrange
        fake_session_id = "test-session-123"
        self.mock_backend.generate_contextweave_from_outline.return_value = {
            "status": "ok",
            "session_id": fake_session_id,
            "svg_url": "http://example.com/diag.svg"
        }

        # Act
        # Call the tool function directly
        main.generate_contextweave_from_outline(self.outline_file, "test request")

        # Assert
        session_file = os.path.join(self.test_dir, ".last_session_id")
        print(f"[test] expected_session_file={session_file}")
        print(f"[test] exists={os.path.exists(session_file)}")
        self.assertTrue(os.path.exists(session_file), "Session file should exist")
        
        with open(session_file, "r") as f:
            saved_id = f.read().strip()
        print(f"[test] saved_session_id={saved_id}")
            
        self.assertEqual(saved_id, fake_session_id, "Saved session ID should match")

    def test_run_contextweave_generation_saves_session_id(self):
        # Arrange
        fake_session_id = "run-session-456"
        self.mock_backend.run_contextweave_generation.return_value = {
            "status": "ok",
            "session_id": fake_session_id
        }
        
        # Act
        main.run_contextweave_generation(
            user_request="draw something", 
            working_dir=self.test_dir
        )

        # Assert
        session_file = os.path.join(self.test_dir, ".last_session_id")
        print(f"[test] expected_session_file={session_file}")
        print(f"[test] exists={os.path.exists(session_file)}")
        self.assertTrue(os.path.exists(session_file), f"Session file should exist at {session_file}")
        
        with open(session_file, "r") as f:
            saved_id = f.read().strip()
        print(f"[test] saved_session_id={saved_id}")
            
        self.assertEqual(saved_id, fake_session_id, "Saved session ID should match")

    def test_run_contextweave_generation_reads_session_id(self):
        # Arrange
        existing_id = "existing-session-789"
        session_file = os.path.join(self.test_dir, ".last_session_id")
        with open(session_file, "w") as f:
            f.write(existing_id)
            
        self.mock_backend.run_contextweave_generation.return_value = {"status": "ok"}

        # Act
        main.run_contextweave_generation(
            user_request="update something", 
            working_dir=self.test_dir
        )

        # Assert
        # Verify backend was called with the session_id read from file
        self.mock_backend.run_contextweave_generation.assert_called_with(
            input_file=None,
            user_request="update something",
            session_id=existing_id, # <--- This is what we want to verify
            mode="3",
            input_sequence=None
        )

    def test_edit_contextweave_uses_session_id(self):
        # Arrange
        existing_id = "edit-session-999"
        session_file = os.path.join(self.test_dir, ".last_session_id")
        with open(session_file, "w") as f:
            f.write(existing_id)
            
        self.mock_backend.run_contextweave_generation.return_value = {"status": "ok", "session_id": existing_id}

        # Act
        # Case 1: Implicit session lookup from working_dir
        main.edit_contextweave(
            user_request="change color to red",
            working_dir=self.test_dir
        )

        # Assert
        self.mock_backend.run_contextweave_generation.assert_called_with(
            user_request="change color to red",
            session_id=existing_id,
            mode="3"
        )
        
        # Case 2: Explicit session ID override
        explicit_id = "explicit-session-000"
        main.edit_contextweave(
            user_request="add node",
            working_dir=self.test_dir,
            session_id=explicit_id
        )
        
        self.mock_backend.run_contextweave_generation.assert_called_with(
            user_request="add node",
            session_id=explicit_id,
            mode="3"
        )

    def test_edit_contextweave_fails_without_session(self):
        # Arrange
        # No .last_session_id file created in self.test_dir
        
        # Act
        result_json = main.edit_contextweave(
            user_request="fail please",
            working_dir=self.test_dir
        )
        
        # Assert
        result = json.loads(result_json)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error"]["code"], "NO_SESSION")

if __name__ == "__main__":
    unittest.main()
