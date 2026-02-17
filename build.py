import PyInstaller.__main__
import os
import shutil

def build():
    print("Building cwmcp-client...")
    
    # Clean previous builds
    if os.path.exists("build"):
        shutil.rmtree("build")
    if os.path.exists("dist"):
        shutil.rmtree("dist")
        
    PyInstaller.__main__.run([
        'main.py',
        '--name=cwmcp-client',
        '--onefile',
        '--clean',
        # Add any hidden imports if necessary
        # '--hidden-import=mcp', 
    ])
    
    print("Build complete. Executable is in dist/")

if __name__ == "__main__":
    build()
