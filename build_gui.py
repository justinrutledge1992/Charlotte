"""
Build script to package Charlotte GUI as a standalone executable
Run this to create charlotte_gui.exe for Windows users
"""

import subprocess
import sys

def build_gui_executable():
    """Build Charlotte GUI as a standalone .exe"""
    
    print("="*60)
    print("Building Charlotte GUI Executable")
    print("="*60)
    
    # Check if PyInstaller is installed
    try:
        import PyInstaller
    except ImportError:
        print("\n❌ PyInstaller not found!")
        print("Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    
    # Build command for GUI version
    build_cmd = [
        "pyinstaller",
        "--onefile",                          # Single .exe file
        "--windowed",                         # No console window (GUI only)
        "--name=charlotte_gui",               # Name of the executable
        "--icon=NONE",                        # You can add an icon later
        "--add-data=charlotte.py;.",          # Include charlotte module
        "--add-data=charlotte_branding.py;.", # Include branding
        "--hidden-import=bs4",                # Ensure BeautifulSoup is included
        "--hidden-import=requests",           # Ensure requests is included
        "--hidden-import=tkinter",            # Ensure tkinter is included
        "charlotte_gui.py"
    ]
    
    print("\n🔨 Building GUI executable...")
    print(f"Command: {' '.join(build_cmd)}\n")
    
    try:
        subprocess.check_call(build_cmd)
        print("\n" + "="*60)
        print("✅ Build successful!")
        print("="*60)
        print("\nYour GUI executable is ready:")
        print("📁 Location: dist/charlotte_gui.exe")
        print("\nTo distribute:")
        print("1. Copy dist/charlotte_gui.exe to a folder")
        print("2. Send to your friend")
        print("3. They just double-click it to run!")
        print("\nNo command line needed - just point and click! 🖱️")
        print("\n" + "="*60)
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Build failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    build_gui_executable()
