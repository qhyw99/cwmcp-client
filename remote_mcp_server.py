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
        
        # Determine timeout priority:
        # 1. Environment Variable INTERLEAVED_THINKING_TIMEOUT
        # 2. Config File (if exists) -> client_timeout
        # 3. Default (300.0)
        
        timeout_val = 3000.0
        
        # Check Env
        # env_val = os.environ.get("INTERLEAVED_THINKING_TIMEOUT")
        # if env_val:
        #     try:
        #         timeout_val = float(env_val)
        #     except ValueError:
        #         pass
        # else:
        #     # Check Config File (config.yaml in project root)
        #     config_paths = [
        #         r"D:\workspace\interleaved-thinking\config.yaml",
        #         os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "interleaved-thinking", "config.yaml")),
        #         os.path.join(os.getcwd(), "config.yaml"),
        #         "config.yaml",
        #     ]
            
        #     for p in config_paths:
        #         if os.path.exists(p):
        #             try:
        #                 with open(p, "r", encoding="utf-8") as f:
        #                     for line in f:
        #                         if line.strip().startswith("client_timeout:"):
        #                             parts = line.split(":")
        #                             if len(parts) >= 2:
        #                                 try:
        #                                     timeout_val = float(parts[1].strip())
        #                                     break
        #                                 except:
        #                                     pass
        #                     else:
        #                         continue 
        #                     break 
        #             except:
        #                 pass
        
        # # Ensure minimum reasonable timeout
        # if timeout_val < 180.0:
        #     timeout_val = 180.0
            
        print(f"[Client] Effective Timeout set to: {timeout_val} seconds", flush=True)

        # Load API Key
        self.api_key = self._load_api_key()

        self.client = httpx.Client(base_url=self.base_url, timeout=timeout_val) 

    def _load_api_key(self) -> Optional[str]:
        """Loads API Key from env or config file."""
        # 1. Environment Variable
        key = os.environ.get("MCP_API_KEY")
        if key:
            return key
            
        # 2. Config File (cwmcp_config.json)
        # Try to find config in typical locations
        config_paths = [
            os.path.join(os.getcwd(), "cwmcp_config.json"),
            os.path.expanduser("~/.cwmcp/config.json"),
            "cwmcp_config.json"
        ]
        
        for path in config_paths:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        key = data.get("api_key")
                        if key:
                            return key
                except Exception:
                    pass
        return None

    def _get_headers(self, request_id: Optional[str] = None) -> Dict[str, str]:
        headers = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        
        if request_id:
            headers["X-Request-ID"] = request_id
        elif "uuid" not in globals():
             import uuid
             headers["X-Request-ID"] = str(uuid.uuid4())
        
        return headers

    def run_contextweave_generation(self, 
                          input_file: Optional[str] = None, 
                          user_request: Optional[str] = None,
                          session_id: Optional[str] = None,
                          mode: str = "3", 
                          input_sequence: Optional[list] = None) -> Dict[str, Any]:
        
        # Prepare payload
        payload = {
            "mode": mode,
            "input_sequence": input_sequence,
            "export_svg": True,
            "export_pptx": False,
            "session_id": session_id
        }

        # Handle Content Source
        if input_file:
            try:
                if not os.path.exists(input_file):
                    return {"status": "error", "error": {"code": "FILE_NOT_FOUND", "message": f"File not found: {input_file}"}}
                
                with open(input_file, "r", encoding="utf-8") as f:
                    content = f.read()
                
                req_text = ""
                d2_text = ""
                
                if "# D2" in content:
                    parts = content.split("# D2")
                    req_part = parts[0]
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
                payload["test_file"] = None
                
            except Exception as e:
                return {"status": "error", "error": {"code": "READ_ERROR", "message": f"Failed to read input file: {e}"}}
        else:
            payload["user_request"] = user_request
            payload["test_file"] = None

        # Call API
        try:
            # Generate Request ID for this specific call
            import uuid
            req_id = str(uuid.uuid4())
            headers = self._get_headers(req_id)
            
            resp = self.client.post("/run", json=payload, headers=headers)
            
            if resp.status_code == 403:
                 return {"status": "error", "error": {"code": "AUTH_ERROR", "message": "Invalid API Key or Missing Key"}}
            if resp.status_code == 402:
                 return {"status": "error", "error": {"code": "PAYMENT_REQUIRED", "message": "Insufficient credits"}}

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

    def generate_contextweave_from_outline(self, outline_file_path: str, user_request: str = "") -> Dict[str, Any]:
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
                    append_content = f"\n\n## Generated ContextWeave\n![ContextWeave Visual]({svg_url})\n\n[Download SVG]({svg_url})"
                    with open(outline_file_path, "a", encoding="utf-8") as f:
                        f.write(append_content)
                except Exception as e:
                    # Append warning to result
                    warnings = result.get("warnings", [])
                    warnings.append(f"Failed to append to file: {e}")
                    result["warnings"] = warnings

        return result

    def import_contextweave_code(self, path: str = "ContextWeave") -> Dict[str, Any]:
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
            payload = {"d2_code": content, "source_name": cw_file}
            resp = self.client.post("/session/import", json=payload)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"status": "error", "error": {"code": "API_ERROR", "message": str(e)}}

    def export_contextweave_code(self, session_id: str, path: str = "ContextWeave") -> Dict[str, Any]:
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
