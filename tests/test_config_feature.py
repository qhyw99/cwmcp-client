import unittest
from unittest.mock import MagicMock, patch, mock_open
import sys
import types
import importlib
import os

# 1. Setup Mock MCP Infrastructure
# We need to define these mocks BEFORE importing main
fake_mcp_module = types.ModuleType("mcp")
fake_mcp_server_module = types.ModuleType("mcp.server")
fake_mcp_fastmcp_module = types.ModuleType("mcp.server.fastmcp")

# Global variable to capture the instance created inside main.py
current_fastmcp_instance = None

class FakeFastMCP:
    def __init__(self, name):
        global current_fastmcp_instance
        self.name = name
        self.registered_tools = []
        current_fastmcp_instance = self

    def tool(self):
        def decorator(fn):
            self.registered_tools.append(fn.__name__)
            return fn
        return decorator

    def run(self):
        pass

fake_mcp_fastmcp_module.FastMCP = FakeFastMCP
sys.modules["mcp"] = fake_mcp_module
sys.modules["mcp.server"] = fake_mcp_server_module
sys.modules["mcp.server.fastmcp"] = fake_mcp_fastmcp_module

# Mock remote_mcp_server
fake_remote_module = types.ModuleType("remote_mcp_server")
class FakeRemoteMCPServer:
    def __init__(self, base_url): pass
fake_remote_module.RemoteMCPServer = FakeRemoteMCPServer
sys.modules["remote_mcp_server"] = fake_remote_module

class TestConfigFeature(unittest.TestCase):
    def setUp(self):
        # Ensure we start fresh for each test
        if "main" in sys.modules:
            del sys.modules["main"]
        
    def test_default_config_enables_plan_mode(self):
        """Test that if config file is missing, plan mode is enabled by default."""
        with patch("os.path.exists", return_value=False):
            import main
            importlib.reload(main)
            
        tools = current_fastmcp_instance.registered_tools
        self.assertIn("get_outline_prompt", tools)
        self.assertIn("generate_contextweave_from_outline", tools)
        self.assertIn("run_contextweave_generation", tools)

    def test_config_enable_true(self):
        """Test that enable_plan_mode: true explicitly enables tools."""
        config_content = '{"enable_plan_mode": true}'
        with patch("os.path.exists", return_value=True), \
             patch("builtins.open", mock_open(read_data=config_content)):
            import main
            importlib.reload(main)
            
        tools = current_fastmcp_instance.registered_tools
        self.assertIn("get_outline_prompt", tools)
        self.assertIn("generate_contextweave_from_outline", tools)

    def test_config_disable_false(self):
        """Test that enable_plan_mode: false HIDES the plan mode tools."""
        config_content = '{"enable_plan_mode": false}'
        with patch("os.path.exists", return_value=True), \
             patch("builtins.open", mock_open(read_data=config_content)):
            import main
            importlib.reload(main)
            
        tools = current_fastmcp_instance.registered_tools
        
        # Core tools should remain
        self.assertIn("run_contextweave_generation", tools)
        
        # Plan mode tools should be gone
        self.assertNotIn("get_outline_prompt", tools)
        self.assertNotIn("generate_contextweave_from_outline", tools)

if __name__ == "__main__":
    unittest.main()
