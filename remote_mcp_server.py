
import os
import json
import httpx
from typing import Optional, Dict, Any, List

class RemoteMCPServer:
    """
    A client-side proxy that communicates with the remote Interleaved Thinking server.
    Handles local file I/O and forwards requests to the backend API.
    """
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        # Increase timeout for long-running generation tasks
        self.client = httpx.Client(base_url=self.base_url, timeout=300.0) 

    def run_d2_generation(self, 
                          test_file: Optional[str] = None, 
                          user_request: Optional[str] = None,
                          initial_d2_code: Optional[str] = None,
                          mode: str = "3", 
                          input_sequence: Optional[list] = None) -> Dict[str, Any]:
        
        # Prepare payload
        payload = {
            "mode": mode,
            "input_sequence": input_sequence,
            "export_svg": True,
            "export_pptx": False
        }

        # Handle Content Source
        if test_file:
            # Client-side: Read and parse the file
            try:
                if not os.path.exists(test_file):
                    return {"status": "error", "error": {"code": "FILE_NOT_FOUND", "message": f"File not found: {test_file}"}}
                
                with open(test_file, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # Parse # Request and # D2
                # Simple logic: Split by # D2, then check for # Request
                # If # Request exists, use it. If not, use everything before # D2 as request.
                
                req_text = ""
                d2_text = ""
                
                if "# D2" in content:
                    parts = content.split("# D2")
                    req_part = parts[0]
                    # Extract D2 code block
                    d2_part = parts[1]
                    if "```d2" in d2_part:
                        try:
                            d2_text = d2_part.split("```d2")[1].split("```")[0].strip()
                        except IndexError:
                             d2_text = d2_part.strip()
                    else:
                        d2_text = d2_part.strip()
                else:
                    req_part = content
                
                if "# Request" in req_part:
                    try:
                        req_text = req_part.split("# Request")[1].strip()
                    except IndexError:
                        req_text = req_part.strip()
                else:
                    req_text = req_part.strip()
                
                payload["user_request"] = req_text
                payload["initial_d2_code"] = d2_text
                # Set test_file to None for the server
                payload["test_file"] = None
                
            except Exception as e:
                return {"status": "error", "error": {"code": "READ_ERROR", "message": f"Failed to read test file: {e}"}}
        else:
            payload["user_request"] = user_request
            payload["initial_d2_code"] = initial_d2_code
            payload["test_file"] = None

        # Call API
        try:
            resp = self.client.post("/run", json=payload)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"status": "error", "error": {"code": "API_ERROR", "message": str(e)}}

    def export_session(self, session_id: str, format: str) -> Dict[str, Any]:
        try:
            resp = self.client.post("/export-session", json={"session_id": session_id, "format": format})
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"status": "error", "error": {"code": "API_ERROR", "message": str(e)}}

    def get_outline_prompt(self, user_request: str = "") -> str:
        try:
            resp = self.client.get("/outline/prompt")
            resp.raise_for_status()
            return resp.json() # Returns string
        except Exception as e:
            return f"Error fetching prompt: {e}"

    def generate_d2_from_outline(self, outline_file_path: str, user_request: str = "") -> Dict[str, Any]:
        import re
        
        # 1. Read Local File
        if not os.path.exists(outline_file_path):
             return {"status": "error", "error": {"code": "FILE_NOT_FOUND", "message": f"File not found: {outline_file_path}"}}
             
        try:
            with open(outline_file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
             return {"status": "error", "error": {"code": "READ_ERROR", "message": f"Failed to read file: {e}"}}

        # 2. Extract JSON (Same logic as original)
        outline_json = ""
        json_match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
        if json_match:
            outline_json = json_match.group(1)
        else:
            # Fallback heuristics
            start_idx = -1
            for i, char in enumerate(content):
                if char in ['{', '[']:
                    start_idx = i
                    break
            if start_idx != -1:
                 candidate = content[start_idx:]
                 if "```" in candidate:
                     candidate = candidate.split("```")[0]
                 outline_json = candidate
            else:
                 outline_json = content # Try full content

        # 3. Call API
        try:
            payload = {"outline_json": outline_json, "user_request": user_request}
            resp = self.client.post("/outline/generate", json=payload)
            resp.raise_for_status()
            result = resp.json()
        except Exception as e:
            return {"status": "error", "error": {"code": "API_ERROR", "message": str(e)}}

        # 4. Append Result to Local File
        if result.get("status") == "ok":
            svg_url = result.get("svg_url")
            
            if svg_url:
                try:
                    append_content = f"\n\n## Generated Diagram\n![D2 Diagram]({svg_url})\n\n[Download SVG]({svg_url})"
                    with open(outline_file_path, "a", encoding="utf-8") as f:
                        f.write(append_content)
                except Exception as e:
                    # Append warning to result
                    warnings = result.get("warnings", [])
                    warnings.append(f"Failed to append to file: {e}")
                    result["warnings"] = warnings

        return result

    def import_d2_code(self, path: str = "ContextWeave") -> Dict[str, Any]:
        # 1. Local File Discovery
        if not os.path.isabs(path):
            path = os.path.abspath(path)
            
        if not os.path.exists(path):
             return {"status": "error", "error": {"code": "PATH_NOT_FOUND", "message": f"Directory not found: {path}"}}
             
        cw_file = None
        check_path = os.path.join(path, "diagram.cw")
        if os.path.exists(check_path):
            cw_file = check_path
        else:
            try:
                files = [f for f in os.listdir(path) if f.endswith(".cw")]
                if files:
                    cw_file = os.path.join(path, files[0])
            except Exception as e:
                 return {"status": "error", "error": {"code": "READ_ERROR", "message": str(e)}}
                 
        if not cw_file:
             return {"status": "error", "error": {"code": "FILE_NOT_FOUND", "message": f"No .cw files found in {path}"}}
             
        try:
            with open(cw_file, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            return {"status": "error", "error": {"code": "READ_ERROR", "message": str(e)}}
            
        # 2. Call API to Import
        try:
            # We treat CW content as D2 for now (backend handles conversion/pass-through)
            payload = {"d2_code": content, "source_name": cw_file}
            resp = self.client.post("/session/import", json=payload)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"status": "error", "error": {"code": "API_ERROR", "message": str(e)}}

    def export_d2_code(self, session_id: str, path: str = "ContextWeave") -> Dict[str, Any]:
        # 1. Call API to get code
        try:
            resp = self.client.post("/session/export", json={"session_id": session_id})
            resp.raise_for_status()
            data = resp.json()
            d2_code = data.get("d2_code")
        except Exception as e:
            return {"status": "error", "error": {"code": "API_ERROR", "message": str(e)}}
            
        # 2. Write to Local File
        if not os.path.isabs(path):
            path = os.path.abspath(path)
            
        if not os.path.exists(path):
            try:
                os.makedirs(path, exist_ok=True)
            except Exception as e:
                return {"status": "error", "error": {"code": "CREATE_DIR_ERROR", "message": str(e)}}
                
        target_file = os.path.join(path, "diagram.cw")
        
        try:
            with open(target_file, "w", encoding="utf-8") as f:
                f.write(d2_code)
        except Exception as e:
            return {"status": "error", "error": {"code": "WRITE_ERROR", "message": str(e)}}
            
        return {
            "status": "ok",
            "file_path": target_file
        }
