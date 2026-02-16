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
mcp = FastMCP("Interleaved Thinking ContextWeave Generator")

import json

def load_config():
    try:
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cwmcp_config.json")
    except NameError:
        # Fallback for when __file__ is not defined (e.g. interactive mode)
        config_path = "cwmcp_config.json"
        
    default_config = {"enable_plan_mode": True}
    
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return {**default_config, **json.load(f)}
        except Exception as e:
            print(f"Warning: Failed to load config file: {e}", file=sys.stderr)
            return default_config
    return default_config

config = load_config()

def conditional_tool(condition):
    def decorator(func):
        if condition:
            return mcp.tool()(func)
        return func
    return decorator

# Redefine as sync functions for FastMCP auto-threading
@mcp.tool()
def run_contextweave_generation(input_file: Optional[str] = None, 
                      user_request: Optional[str] = None,
                      session_id: Optional[str] = None,
                      mode: str = "3", 
                      input_sequence: str = None,
                      working_dir: Optional[str] = None) -> str:
    """
    Create a NEW ContextWeave diagram directly (or run a general generation task).
    This is the PREFERRED and DEFAULT mode for generating diagrams.
    Supports either file-based (legacy) or direct content (user_request) mode.
    
    IMPORTANT: 
    - Use `input_file` to pass the file path instead of putting content in `user_request` to save tokens.
    - To EDIT/MODIFY an existing diagram, use `edit_contextweave` instead.
    - ONLY use the `get_outline_prompt` workflow (Plan Mode) if the user EXPLICITLY requests to "generate a plan first" or "confirm before drawing". Otherwise, use this tool directly.

    Args:
        input_file: Optional path to the input file (e.g. .md or .txt) containing the request or context. Preferred over `user_request` for large inputs.
        user_request: Natural language description of the ContextWeave.
        session_id: Optional. The session ID to continue editing. If not provided, checks working_dir.
        mode: The running mode (default "3" for ContextWeave).
        input_sequence: Optional JSON string of input list (e.g. '["yes", "1"]').
        working_dir: Optional. If provided, attempts to load session_id from '.last_session_id' (if session_id not explicit) and saves new session_id after run.
    """
    import json
    inputs = None
    if input_sequence:
        try:
            inputs = json.loads(input_sequence)
        except:
            return f"Error: input_sequence must be valid JSON string. Got: {input_sequence}"
    
    # Resolve session_id
    current_session_id = session_id
    if not current_session_id and working_dir:
        session_file = os.path.join(working_dir, ".last_session_id")
        if os.path.exists(session_file):
            try:
                with open(session_file, "r", encoding="utf-8") as f:
                    current_session_id = f.read().strip()
            except:
                pass

    result = backend.run_contextweave_generation(
        input_file=input_file, 
        user_request=user_request,
        session_id=current_session_id,
        mode=mode, 
        input_sequence=inputs
    )
    
    # Save new session_id
    if working_dir and result.get("status") == "ok" and "session_id" in result:
        try:
            os.makedirs(working_dir, exist_ok=True)
            session_file_path = os.path.join(working_dir, ".last_session_id")
            with open(session_file_path, "w", encoding="utf-8") as f:
                f.write(result["session_id"])
            result["session_file_path"] = session_file_path
        except Exception as e:
            print(f"Warning: Failed to save session ID: {e}", file=sys.stderr)

    return json.dumps(result, indent=2)

@mcp.tool()
def edit_contextweave(user_request: str, 
                      working_dir: Optional[str] = None, 
                      session_id: Optional[str] = None) -> str:
    """
    Edit/Modify an EXISTING ContextWeave diagram in the current session.
    Use this tool when the user wants to change, update, or refine an existing diagram.
    
    Args:
        user_request: The modification instructions (e.g. "Add a node X", "Change style of Y").
        working_dir: Directory containing the .last_session_id file. Defaults to current if not provided.
        session_id: Explicit session ID (optional). If provided, overrides working_dir lookup.
    """
    import json
    
    # Resolve session_id (Mandatory for edit)
    current_session_id = session_id
    
    # If not explicit, look in working_dir (or current dir if None)
    search_dir = working_dir if working_dir else os.getcwd()
    
    if not current_session_id:
        session_file = os.path.join(search_dir, ".last_session_id")
        if os.path.exists(session_file):
            try:
                with open(session_file, "r", encoding="utf-8") as f:
                    current_session_id = f.read().strip()
            except:
                pass
    
    if not current_session_id:
        return json.dumps({
            "status": "error", 
            "error": {
                "code": "NO_SESSION", 
                "message": "No active session found. Please provide session_id or ensure .last_session_id exists in working_dir."
            }
        }, indent=2)

    # Call backend
    result = backend.run_contextweave_generation(
        user_request=user_request,
        session_id=current_session_id,
        mode="3"
    )
    
    # Update session file if needed (usually ID stays same, but good practice to sync)
    if working_dir and result.get("status") == "ok" and "session_id" in result:
        try:
            os.makedirs(working_dir, exist_ok=True)
            session_file_path = os.path.join(working_dir, ".last_session_id")
            with open(session_file_path, "w", encoding="utf-8") as f:
                f.write(result["session_id"])
            result["session_file_path"] = session_file_path
        except Exception as e:
            print(f"Warning: Failed to save session ID: {e}", file=sys.stderr)

    return json.dumps(result, indent=2)

@mcp.tool()
def export_session_contextweave(session_id: str, format: str) -> str:
    """
    Export a generated ContextWeave visual from a session to a specific format.
    
    Args:
        session_id: The session ID returned by run_contextweave_generation.
        format: The target format ('svg' or 'pptx').
    """
    import json
    result = backend.export_session(session_id=session_id, format=format)
    return json.dumps(result, indent=2)

@conditional_tool(config.get("enable_plan_mode", True))
def get_outline_prompt() -> str:
    """
    Get the system prompt template for generating a ContextWeave outline.
    
    Workflow Step 1 (Plan Mode):
    Use this tool ONLY when the user EXPLICITLY asks to "generate a plan first" or "confirm before drawing".
    If the user just asks to generate/draw a diagram, prefer `run_contextweave_generation` directly.
    
    The client MUST:
    1. Call this tool to get the prompt.
    2. Use an LLM to generate a JSON outline plan based on the user's request and this prompt.
    3. Save the generated JSON outline into a Markdown file (wrapped in ```json ... ```).
    4. Call `generate_contextweave_from_outline` with that file path.
    """
    return backend.get_outline_prompt()

@conditional_tool(config.get("enable_plan_mode", True))
def generate_contextweave_from_outline(outline_file_path: str, user_request: str = "", working_dir: Optional[str] = None) -> str:
    """
    Generate a ContextWeave directly from a confirmed JSON outline plan stored in a file.
    
    Workflow Step 2 (Plan Mode):
    Use this tool AFTER the user has reviewed and confirmed the outline generated in Step 1.
    
    Args:
        outline_file_path: The absolute path to the Markdown file containing the approved outline JSON.
                           The file MUST contain a valid JSON block wrapped in ```json ... ``` code fences.
                           The tool will read the file, extract the JSON, run the generation,
                           and APPEND the generated SVG URL back to this file.
        user_request: The original user request to guide refinement (optional but recommended).
        working_dir: Optional. If provided, saves the returned session_id to '.last_session_id' in this directory. Defaults to the outline file's directory.
    """
    import json
    resolved_working_dir = working_dir or (os.path.dirname(outline_file_path) if outline_file_path else None)
    
    result = backend.generate_contextweave_from_outline(outline_file_path, user_request)
    
    # Save new session_id
    if resolved_working_dir and result.get("status") == "ok" and "session_id" in result:
         try:
             os.makedirs(resolved_working_dir, exist_ok=True)
             session_file_path = os.path.join(resolved_working_dir, ".last_session_id")
             with open(session_file_path, "w", encoding="utf-8") as f:
                 f.write(result["session_id"])
             result["session_file_path"] = session_file_path
         except Exception as e:
             print(f"Warning: Failed to save session ID: {e}", file=sys.stderr)

    return json.dumps(result, indent=2)

@mcp.tool()
def import_contextweave_code(path: str = "ContextWeave", working_dir: Optional[str] = None) -> str:
    """
    Import ContextWeave code from a directory (default: ContextWeave) into a new session.
    Looks for .cw files (ContextWeave format).
    
    Args:
        path: Directory path to import from. Defaults to "ContextWeave".
        working_dir: Optional. If provided, saves the imported session_id to '.last_session_id' in this directory.
    """
    import json
    result = backend.import_contextweave_code(path=path)
    
    if working_dir and result.get("status") == "ok" and "session_id" in result:
        try:
             os.makedirs(working_dir, exist_ok=True)
             session_file_path = os.path.join(working_dir, ".last_session_id")
             with open(session_file_path, "w", encoding="utf-8") as f:
                 f.write(result["session_id"])
             result["session_file_path"] = session_file_path
        except Exception as e:
             # Just warn, don't fail
             print(f"Warning: Failed to save session ID: {e}", file=sys.stderr)

    # Remove d2_code from result to keep output clean
    if "d2_code" in result:
        del result["d2_code"]

    return json.dumps(result, indent=2)

@mcp.tool()
def export_contextweave_code(session_id: str, path: str = "ContextWeave") -> str:
    """
    Export ContextWeave code from a session to a directory (default: ContextWeave).
    Saves as .cw file (ContextWeave format).
    
    Args:
        session_id: The session ID containing the ContextWeave code.
        path: Directory path to export to. Defaults to "ContextWeave".
    """
    import json
    result = backend.export_contextweave_code(session_id=session_id, path=path)
    return json.dumps(result, indent=2)

if __name__ == "__main__":
    # Run the server
    print("Starting Interleaved Thinking MCP Server...", file=sys.stderr)
    mcp.run()
