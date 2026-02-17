# Build and Distribution Spec

## Why
The user wants to distribute the `cwmcp-client` as a standalone binary executable that runs on different operating systems (Windows, macOS, Linux) without requiring a pre-installed Python environment. This simplifies deployment and usage for end-users.

## What Changes
- **Dependency Management**: Add `pyinstaller` to `pyproject.toml` as a dependency (or dev-dependency).
- **Build Script**: Create a `build.py` script to automate the PyInstaller build process, ensuring correct options (like `--onefile`) are used.
- **Code Adaptation**: Update `main.py` and `remote_mcp_server.py` to correctly locate configuration files when running in a "frozen" (PyInstaller) state.
- **CI/CD**: Create a GitHub Actions workflow (`.github/workflows/release.yml`) to automatically build binaries for Windows, macOS, and Linux when a new release (tag) is pushed.
- **Documentation**: Add build instructions to `README.md`.

## Impact
- **Affected Specs**: None.
- **Affected Code**: `main.py`, `remote_mcp_server.py`, `pyproject.toml`.
- **New Files**: `build.py`, `.github/workflows/release.yml`.

## ADDED Requirements
### Requirement: Standalone Binary Build
The system SHALL provide a mechanism to build a self-contained executable for the host platform.
- **Scenario: Local Build**
  - **WHEN** a developer runs `python build.py`
  - **THEN** a standalone executable is created in the `dist/` directory.

### Requirement: Cross-Platform CI/CD
The system SHALL provide a CI/CD configuration to build binaries for multiple platforms.
- **Scenario: Release Build**
  - **WHEN** a git tag (e.g., `v0.1.0`) is pushed
  - **THEN** GitHub Actions builds binaries for Windows (`.exe`), macOS, and Linux.
  - **THEN** artifacts are uploaded to the release.

## MODIFIED Requirements
### Requirement: Configuration Loading
The system SHALL support loading configuration files relative to the executable location when running as a frozen binary.
- **Current Behavior**: Looks relative to `__file__`.
- **New Behavior**: If frozen (PyInstaller), look relative to `sys.executable` (the binary path) first, then fallback to internal/bundled paths if needed (though typically config should be external for user modification).
