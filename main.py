import asyncio
import sys
import logging
from typing import Optional

# Check if mcp is installed
try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print("Error: 'mcp' package is not installed. Please install it with 'pip install mcp'.", file=sys.stderr)
    sys.exit(1)

from remote_mcp_server import RemoteMCPServer
import os

# Initialize the Facade
# Note: We initialize it globally so it persists across tool calls
# Default to localhost:8000 for the remote server
api_url = os.environ.get("INTERLEAVED_THINKING_API_URL", "http://localhost:8000")
backend = RemoteMCPServer(base_url=api_url)

# Initialize FastMCP Server
mcp = FastMCP("Interleaved Thinking D2 Generator")

# Redefine as sync functions for FastMCP auto-threading
@mcp.tool()
def run_d2_generation(test_file: Optional[str] = None, 
                      user_request: Optional[str] = None,
                      initial_d2_code: Optional[str] = None,
                      mode: str = "3", 
                      input_sequence: str = None) -> str:
    """
    Run the D2 diagram generation process directly.
    Supports either file-based (legacy) or direct content (user_request) mode.
    
    IMPORTANT: Do NOT use this tool if the user asks to "generate a plan first" or "confirm the plan before drawing".
    For those cases, use the `get_outline_prompt` -> (Generate Outline File) -> `generate_d2_from_outline` workflow.

    Args:
        test_file: Optional path to the test file (legacy).
        user_request: Natural language description of the diagram.
        initial_d2_code: Existing D2 code (for edit mode).
        mode: The running mode (default "3" for D2).
        input_sequence: Optional JSON string of input list (e.g. '["yes", "1"]').
    """
    import json
    inputs = None
    if input_sequence:
        try:
            inputs = json.loads(input_sequence)
        except:
            return f"Error: input_sequence must be valid JSON string. Got: {input_sequence}"
            
    result = backend.run_d2_generation(
        test_file=test_file, 
        user_request=user_request,
        initial_d2_code=initial_d2_code,
        mode=mode, 
        input_sequence=inputs
    )
    return json.dumps(result, indent=2)

@mcp.tool()
def export_session_diagram(session_id: str, format: str) -> str:
    """
    Export a generated diagram from a session to a specific format.
    
    Args:
        session_id: The session ID returned by run_d2_generation.
        format: The target format ('svg' or 'pptx').
    """
    import json
    result = backend.export_session(session_id=session_id, format=format)
    return json.dumps(result, indent=2)

@mcp.tool()
def get_outline_prompt() -> str:
    """
    Get the system prompt template for generating a diagram outline.
    
    Workflow Step 1 (Plan Mode):
    Use this tool when the user asks to "generate a plan first" or "confirm before drawing".
    The client MUST:
    1. Call this tool to get the prompt.
    2. Use an LLM to generate a JSON outline plan based on the user's request and this prompt.
    3. Save the generated JSON outline into a Markdown file (wrapped in ```json ... ```).
    4. Call `generate_d2_from_outline` with that file path.
    """
    return backend.get_outline_prompt()

@mcp.tool()
def generate_d2_from_outline(outline_file_path: str, user_request: str = "") -> str:
    """
    Generate a D2 diagram directly from a confirmed JSON outline plan stored in a file.
    
    Workflow Step 2 (Plan Mode):
    Use this tool AFTER the user has reviewed and confirmed the outline generated in Step 1.
    
    Args:
        outline_file_path: The absolute path to the Markdown file containing the approved outline JSON.
                           The file MUST contain a valid JSON block wrapped in ```json ... ``` code fences.
                           The tool will read the file, extract the JSON, run the generation,
                           and APPEND the generated SVG URL back to this file.
        user_request: The original user request to guide refinement (optional but recommended).
    """
    import json
    result = backend.generate_d2_from_outline(outline_file_path, user_request)
    return json.dumps(result, indent=2)

@mcp.tool()
def import_d2_code(path: str = "ContextWeave") -> str:
    """
    Import D2 code from a directory (default: ContextWeave) into a new session.
    Looks for .cw files (ContextWeave format).
    
    Args:
        path: Directory path to import from. Defaults to "ContextWeave".
    """
    import json
    result = backend.import_d2_code(path=path)
    return json.dumps(result, indent=2)

@mcp.tool()
def export_d2_code(session_id: str, path: str = "ContextWeave") -> str:
    """
    Export D2 code from a session to a directory (default: ContextWeave).
    Saves as .cw file (ContextWeave format).
    
    Args:
        session_id: The session ID containing the D2 code.
        path: Directory path to export to. Defaults to "ContextWeave".
    """
    import json
    result = backend.export_d2_code(session_id=session_id, path=path)
    return json.dumps(result, indent=2)

if __name__ == "__main__":
    # Run the server
    print("Starting Interleaved Thinking MCP Server...", file=sys.stderr)
    mcp.run()
