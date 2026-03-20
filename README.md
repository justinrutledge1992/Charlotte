# 🕷️ Charlotte

A combined GUI tool that merges **Charlotte** (web archiver) and **Thread Weaver** (HTML-to-TXT converter) into a single application with a tabbed interface.

---

## Tabs

### 🕷️ Charlotte – Web Archiver
Archive forum threads and web pages using URL patterns with a numeric `{id}` placeholder.

**Settings:**
- **URL Pattern** – e.g. `https://forum.example.com/thread/{id}`
- **Start / End / Step** – numeric range for the `{id}`
- **Delay** – seconds between requests (increase to 2–3 if rate-limited)
- **Output Folder** – where `.html` files are saved
- **Session Cookies** – optional, for login-protected forums (find in Firefox DevTools → Storage → Cookies)

### 🧵 Thread Weaver – HTML Converter
Convert a folder of saved `.html` files into chunked `.txt` files ready for Google NotebookLM.

**Settings:**
- **Input Folder** – folder containing your `.html` files (searched recursively)
- **Output Folder** – where the chunked `.txt` files are saved
- Each chunk stays under **450,000 words** to fit NotebookLM's upload limit

---

## Typical Workflow

1. Use **Charlotte** to archive a forum → produces a folder of `.html` files
2. Switch to **Thread Weaver**, point it at that folder → produces chunked `.txt` files
3. Upload the `.txt` chunks to Google NotebookLM

---

## Running from Source

```bash
pip install beautifulsoup4 lxml requests
python charlotte.py
```

## Building to .exe (Windows)

```bash
build.bat
```

Or manually:
```bash
pip install pyinstaller beautifulsoup4 lxml requests
pyinstaller --onefile --windowed --name "Charlotte" charlotte.py
```

The executable will be in `dist\Charlotte.exe`.

---

*"Some spider!" — Charlotte's Web*
