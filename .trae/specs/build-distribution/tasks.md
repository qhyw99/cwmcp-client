# Tasks

- [x] Task 1: Update dependencies and project configuration
  - [x] Add `pyinstaller` to `pyproject.toml`.
  - [x] Verify `mcp` and `httpx` dependencies are correctly defined.

- [x] Task 2: Adapt code for frozen execution
  - [x] Modify `main.py` `load_config` to check `sys.executable` directory when `getattr(sys, 'frozen', False)` is true.
  - [x] Modify `remote_mcp_server.py` `_load_api_key` and config loading logic similarly to support external config files next to the binary.

- [x] Task 3: Create local build script
  - [x] Create `build.py` that invokes `PyInstaller`.
  - [x] Configure PyInstaller to bundle necessary resources (if any, though config is better external).
  - [x] Use `--onefile` and `--name cwmcp-client`.
  - [x] Verify local build on the current OS.

- [x] Task 4: Setup GitHub Actions for Cross-Platform Build
  - [x] Create `.github/workflows/release.yml`.
  - [x] Configure matrix strategy for `ubuntu-latest`, `windows-latest`, `macos-latest`.
  - [x] Add steps to install Python, dependencies, run PyInstaller, and upload artifacts.

- [x] Task 5: Documentation
  - [x] Create or update `README.md` with "Building from Source" instructions.
