# Charlotte GUI - Essential Files

## Files Required for Building the GUI Executable

### Core Files (Required)
1. **charlotte.py** - Main archiving engine
2. **charlotte_gui.py** - GUI interface
3. **charlotte_branding.py** - Branding/ASCII art
4. **build_gui.py** - Build script to create the .exe
5. **requirements.txt** - Python dependencies

### Documentation (Optional but Recommended)
6. **QUICK_START_GUI.md** - User guide for your friend

---

## What Each File Does

**charlotte.py**
- Core archiving functionality
- Fetches web pages
- Saves HTML files
- Handles errors and retries

**charlotte_gui.py**
- Graphical user interface
- Input forms for URL pattern, start/end numbers
- Progress bar and logging
- Imports and uses charlotte.py

**charlotte_branding.py**
- ASCII art and branding
- Used by charlotte.py (optional but included)

**build_gui.py**
- PyInstaller build script
- Creates charlotte_gui.exe
- Bundles all dependencies

**requirements.txt**
- Lists: requests, beautifulsoup4
- For pip install if running from source

---

## Files You DON'T Need

❌ charlotte.exe (command-line version)
❌ build_exe.py (builds command-line version)
❌ viewer.py (not needed - GUI has its own interface)
❌ test_charlotte.py (testing only)
❌ charlotte-easy.bat (command-line helper)
❌ examples.py (programming examples)
❌ PACKAGING_GUIDE.md (for you, not end user)
❌ PYTHON_INSTALL.md (not needed with .exe)

---

## Minimal Package Structure

```
Charlotte-GUI/
├── charlotte.py              ← Required
├── charlotte_gui.py          ← Required
├── charlotte_branding.py     ← Required
├── build_gui.py             ← Required
├── requirements.txt         ← Required
└── QUICK_START_GUI.md       ← Optional (user guide)
```

---

## To Build

```bash
# Install dependencies
pip install -r requirements.txt

# Build the GUI
python build_gui.py

# Result
dist/charlotte_gui.exe       ← Distribute this!
```

---

## To Distribute to Your Friend

Just send them:
- `charlotte_gui.exe` (from dist folder)
- `QUICK_START_GUI.md` (optional instructions)

That's it!
