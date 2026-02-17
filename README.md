# CWMCP Client

MCP Client for Interleaved Thinking D2 Generator.

## Building from Source

### Prerequisites

- Python 3.10+
- pip

### Steps

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd cwmcp-client
    ```

2.  **Install dependencies:**
    ```bash
    pip install .
    pip install pyinstaller
    ```

3.  **Run the build script:**
    ```bash
    python build.py
    ```

4.  **Locate the executable:**
    The built executable will be in the `dist/` directory:
    - Windows: `dist/cwmcp-client.exe`
    - Linux/macOS: `dist/cwmcp-client`

## GitHub Actions

This project uses GitHub Actions for cross-platform builds. The workflow is defined in `.github/workflows/release.yml`. It automatically builds for Ubuntu, Windows, and macOS on tag push (v*).
