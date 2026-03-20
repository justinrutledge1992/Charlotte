#!/usr/bin/env python3
"""
Charlotte
-------------
Combines Charlotte (Web Scraper) and Thread Weaver (HTML → TXT Converter)
into a single tabbed GUI application.

Charlotte:      Archive forum threads and web pages via URL patterns.
Thread Weaver:  Convert a folder of saved HTML files into chunked .txt
                files ready for Google NotebookLM.

Build to .exe:
    pip install pyinstaller beautifulsoup4 lxml requests
    pyinstaller --onefile --windowed --name "Charlotte" charlotte.py
"""

# ── Dependency bootstrap ───────────────────────────────────────────────────────

import subprocess
import sys

def _ensure(pkg, import_as=None):
    name = import_as or pkg
    try:
        __import__(name)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

_ensure("beautifulsoup4", "bs4")
_ensure("lxml")
_ensure("requests")

# ── Standard imports ───────────────────────────────────────────────────────────

import hashlib
import json
import threading
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
from bs4 import BeautifulSoup


# ══════════════════════════════════════════════════════════════════════════════
#  CHARLOTTE CORE  (web archiver logic)
# ══════════════════════════════════════════════════════════════════════════════

class Charlotte:
    """Fetches and archives web pages."""

    def __init__(self, base_url, output_dir="charlotte_archives",
                 delay=1.0, download_assets=False, cookies=None):
        self.base_url       = base_url
        self.output_dir     = Path(output_dir)
        self.delay          = delay
        self.download_assets = download_assets
        self.session        = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (compatible; Charlotte/1.0; "
                "+https://github.com/spider-weaver)"
            )
        })
        if cookies:
            for name, value in cookies.items():
                self.session.cookies.set(name, value)

        self.output_dir.mkdir(parents=True, exist_ok=True)
        if self.download_assets:
            (self.output_dir / "images").mkdir(parents=True, exist_ok=True)

        self.metadata = {
            "base_url":          base_url,
            "start_time":        datetime.now().isoformat(),
            "pages_archived":    [],
            "failed_pages":      [],
            "images_downloaded": [],
            "css_inlined":       0,
            "js_inlined":        0,
        }
        self.downloaded_images = {}

    # ── URL generation ────────────────────────────────────────────────────────

    def generate_urls(self, pattern, start, end, step=1):
        return [pattern.format(id=i) for i in range(start, end + 1, step)]

    # ── Fetching ──────────────────────────────────────────────────────────────

    def fetch_page(self, url):
        try:
            r = self.session.get(url, timeout=30)
            r.raise_for_status()
            return r.text, r.status_code, None
        except requests.HTTPError as e:
            return None, (e.response.status_code if e.response else None), str(e)
        except requests.RequestException as e:
            return None, None, str(e)

    def fetch_asset_content(self, asset_url):
        try:
            r = self.session.get(asset_url, timeout=15)
            r.raise_for_status()
            return r.text
        except Exception:
            return None

    def download_image(self, image_url):
        if image_url in self.downloaded_images:
            return self.downloaded_images[image_url]
        try:
            r = self.session.get(image_url, timeout=15)
            r.raise_for_status()
            url_hash = hashlib.md5(image_url.encode()).hexdigest()[:12]
            ext      = Path(urlparse(image_url).path).suffix or ".jpg"
            filename = f"{url_hash}{ext}"
            local    = self.output_dir / "images" / filename
            local.write_bytes(r.content)
            rel = f"images/{filename}"
            self.downloaded_images[image_url] = rel
            self.metadata["images_downloaded"].append(
                {"url": image_url, "local_path": rel}
            )
            return rel
        except Exception:
            return None

    # ── HTML processing ───────────────────────────────────────────────────────

    def process_html(self, url, content):
        if not self.download_assets:
            return content
        soup = BeautifulSoup(content, "html.parser")
        for link in soup.find_all("link", rel="stylesheet"):
            href = link.get("href")
            if href:
                css = self.fetch_asset_content(urljoin(url, href))
                if css:
                    tag = soup.new_tag("style")
                    tag.string = css
                    link.replace_with(tag)
                    self.metadata["css_inlined"] += 1
        for script in soup.find_all("script", src=True):
            src = script.get("src")
            if src:
                js = self.fetch_asset_content(urljoin(url, src))
                if js:
                    del script["src"]
                    script.string = js
                    self.metadata["js_inlined"] += 1
        for img in soup.find_all("img"):
            src = img.get("src")
            if src:
                lp = self.download_image(urljoin(url, src))
                if lp:
                    img["src"] = lp
        return str(soup)

    def save_page(self, url, content):
        parsed   = urlparse(url)
        path     = parsed.path.strip("/").replace("/", "_")
        if parsed.query:
            path += "_" + parsed.query.replace("&", "_").replace("=", "-")
        if not path:
            path = "index"
        safe     = "".join(
            c if c in "-_.()abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
            else "_"
            for c in path
        )
        filename = safe[:200] + ".html"
        filepath = self.output_dir / filename
        filepath.write_text(self.process_html(url, content), encoding="utf-8")
        return filepath

    def save_metadata(self):
        self.metadata["end_time"]    = datetime.now().isoformat()
        self.metadata["total_pages"] = len(self.metadata["pages_archived"])
        self.metadata["failed_count"]= len(self.metadata["failed_pages"])
        self.metadata["total_images"]= len(self.metadata["images_downloaded"])
        (self.output_dir / "archive_metadata.json").write_text(
            json.dumps(self.metadata, indent=2), encoding="utf-8"
        )


# ══════════════════════════════════════════════════════════════════════════════
#  THREAD WEAVER CORE  (HTML → chunked TXT logic)
# ══════════════════════════════════════════════════════════════════════════════

MAX_WORDS_PER_CHUNK = 450_000
THREAD_SEPARATOR    = "\n\n" + "=" * 60 + "\n"


def html_to_text(filepath: Path) -> str:
    try:
        raw = filepath.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""
    soup = BeautifulSoup(raw, "lxml")
    for tag in soup(["script", "style", "nav", "header", "footer",
                     "aside", "noscript", "iframe", "form"]):
        tag.decompose()
    text  = soup.get_text(separator="\n", strip=True)
    lines = text.splitlines()
    cleaned, blank_count = [], 0
    for line in lines:
        if line.strip() == "":
            blank_count += 1
            if blank_count <= 1:
                cleaned.append("")
        else:
            blank_count = 0
            cleaned.append(line)
    return "\n".join(cleaned).strip()


def word_count(text: str) -> int:
    return len(text.split())


def run_conversion(input_dir, output_dir, log_fn, progress_fn, done_fn, stop_flag):
    html_files = sorted(input_dir.glob("**/*.htm*"))
    total      = len(html_files)

    if total == 0:
        log_fn("Error: No HTML files found in the selected folder.")
        done_fn(success=False)
        return

    log_fn("Thread Weaver")
    log_fn(f"Input:  {input_dir}")
    log_fn(f"Output: {output_dir}")
    log_fn(f"Files found: {total:,}")
    log_fn("-" * 60)

    output_dir.mkdir(parents=True, exist_ok=True)

    chunk_index = 1
    current_words = 0
    current_lines = []
    files_in_chunk = 0
    summary = []

    def save_chunk():
        nonlocal chunk_index, current_words, current_lines, files_in_chunk
        if not current_lines:
            return
        out_path = output_dir / f"forum_chunk_{chunk_index:02d}.txt"
        out_path.write_text("\n".join(current_lines), encoding="utf-8")
        log_fn(f"  ✓ Chunk {chunk_index:02d} saved — "
               f"{files_in_chunk:,} threads, {current_words:,} words")
        summary.append((out_path.name, files_in_chunk, current_words))
        chunk_index    += 1
        current_words   = 0
        current_lines   = []
        files_in_chunk  = 0

    for i, filepath in enumerate(html_files, 1):
        if stop_flag():
            log_fn("\nConversion stopped by user.")
            break
        progress_fn(i, total)
        text = html_to_text(filepath)
        if not text:
            continue
        entry_words = word_count(text)
        if current_words + entry_words > MAX_WORDS_PER_CHUNK and current_lines:
            save_chunk()
        current_lines.append(THREAD_SEPARATOR)
        current_lines.append(f"THREAD: {filepath.stem}")
        current_lines.append("=" * 60 + "\n")
        current_lines.append(text)
        current_words  += entry_words
        files_in_chunk += 1

    if not stop_flag():
        save_chunk()

    log_fn("-" * 60)
    log_fn(f"Complete! Created {chunk_index - 1} chunk(s).\n")
    log_fn(f"  {'Chunk':<28} {'Threads':>8} {'Words':>10}")
    log_fn(f"  {'-'*28} {'-'*8} {'-'*10}")
    total_words = 0
    for name, count, words in summary:
        log_fn(f"  {name:<28} {count:>8,} {words:>10,}")
        total_words += words
    log_fn(f"  {'-'*28} {'-'*8} {'-'*10}")
    log_fn(f"  {'TOTAL':<28} {len(html_files):>8,} {total_words:>10,}")
    log_fn(f"\n📁 Output folder: {output_dir}")
    done_fn(success=True)


# ══════════════════════════════════════════════════════════════════════════════
#  COMBINED GUI
# ══════════════════════════════════════════════════════════════════════════════

class CharlotteApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Charlotte")
        self.root.geometry("740x760")
        self.root.resizable(True, True)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        self._build_header()
        self._build_notebook()

    # ── Header ────────────────────────────────────────────────────────────────

    def _build_header(self):
        hf = ttk.Frame(self.root, padding="10 8 10 0")
        hf.grid(row=0, column=0, sticky=(tk.W, tk.E))
        ttk.Label(hf, text="Charlotte",
                  font=("Arial", 17, "bold")).grid(row=0, column=0, sticky=tk.W)

    # ── Notebook / tabs ───────────────────────────────────────────────────────

    def _build_notebook(self):
        nb = ttk.Notebook(self.root)
        nb.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S),
                padx=10, pady=8)
        self.root.rowconfigure(1, weight=1)

        # Tab 1 – Charlotte
        charlotte_frame = ttk.Frame(nb, padding=0)
        charlotte_frame.columnconfigure(0, weight=1)
        charlotte_frame.rowconfigure(0, weight=1)
        nb.add(charlotte_frame, text="Web Archiver")
        CharlotteTab(charlotte_frame)

        # Tab 2 – Thread Weaver
        weaver_frame = ttk.Frame(nb, padding=0)
        weaver_frame.columnconfigure(0, weight=1)
        weaver_frame.rowconfigure(0, weight=1)
        nb.add(weaver_frame, text="Thread Weaver")
        ThreadWeaverTab(weaver_frame)


# ══════════════════════════════════════════════════════════════════════════════
#  CHARLOTTE TAB
# ══════════════════════════════════════════════════════════════════════════════

class CharlotteTab:
    def __init__(self, parent):
        self.parent       = parent
        self.is_archiving = False

        # Scrollable canvas so the settings don't get cramped on small windows
        canvas = tk.Canvas(parent, highlightthickness=0)
        scroll = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)

        inner = ttk.Frame(canvas, padding="10")
        win_id = canvas.create_window((0, 0), window=inner, anchor="nw")

        def on_configure(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
        def on_canvas_width(e):
            canvas.itemconfig(win_id, width=e.width)

        inner.bind("<Configure>", on_configure)
        canvas.bind("<Configure>", on_canvas_width)

        inner.columnconfigure(0, weight=1)
        self._build(inner)

    def _build(self, f):
        # ── Settings ──────────────────────────────────────────────────────────
        sf = ttk.LabelFrame(f, text="Archive Settings", padding="10")
        sf.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 6))
        sf.columnconfigure(1, weight=1)

        def row_label(r, text):
            ttk.Label(sf, text=text).grid(row=r, column=0, sticky=tk.W, pady=4)

        def row_hint(r, text):
            ttk.Label(sf, text=text, font=("Arial", 8, "italic"),
                      foreground="gray").grid(row=r, column=1, sticky=tk.W)

        # URL pattern
        row_label(0, "URL Pattern:")
        self.url_var = tk.StringVar(value="https://forum.com/thread/{id}")
        ttk.Entry(sf, textvariable=self.url_var, width=55).grid(
            row=0, column=1, sticky=(tk.W, tk.E), pady=4)
        row_hint(1, "Use {id} where the number goes")

        # Start / End / Step on one row
        num_frame = ttk.Frame(sf)
        num_frame.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=4)
        for i, (lbl, var_default) in enumerate([
                ("Start:", "1"), ("End:", "100"), ("Step:", "1")]):
            ttk.Label(num_frame, text=lbl).grid(row=0, column=i*2, sticky=tk.W, padx=(0 if i==0 else 20, 4))
            sv = tk.StringVar(value=var_default)
            ttk.Entry(num_frame, textvariable=sv, width=10).grid(row=0, column=i*2+1)
            setattr(self, ["start_var", "end_var", "step_var"][i], sv)

        # Delay
        row_label(3, "Delay (sec):")
        self.delay_var = tk.StringVar(value="1.0")
        delay_f = ttk.Frame(sf)
        delay_f.grid(row=3, column=1, sticky=tk.W, pady=4)
        ttk.Entry(delay_f, textvariable=self.delay_var, width=10).grid(row=0, column=0)
        ttk.Label(delay_f, text="  Increase to 2–3 if getting blocked",
                  font=("Arial", 8, "italic"), foreground="gray").grid(row=0, column=1)

        # Output
        row_label(4, "Output Folder:")
        self.output_var = tk.StringVar(value="charlotte_archives")
        out_f = ttk.Frame(sf)
        out_f.grid(row=4, column=1, sticky=(tk.W, tk.E), pady=4)
        out_f.columnconfigure(0, weight=1)
        ttk.Entry(out_f, textvariable=self.output_var).grid(
            row=0, column=0, sticky=(tk.W, tk.E))
        ttk.Button(out_f, text="Browse…",
                   command=self._pick_output).grid(row=0, column=1, padx=(6, 0))

        # ── Cookies ───────────────────────────────────────────────────────────
        ttk.Separator(sf, orient="horizontal").grid(
            row=5, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=8)
        ttk.Label(sf, text="Session Cookies  (optional – for login-protected forums)",
                  font=("Arial", 9, "bold")).grid(
            row=6, column=0, columnspan=2, sticky=tk.W)
        ttk.Label(sf, text="Firefox DevTools → Storage → Cookies",
                  font=("Arial", 8, "italic"), foreground="gray").grid(
            row=7, column=0, columnspan=2, sticky=tk.W, pady=(0, 6))

        ck_outer = ttk.Frame(sf)
        ck_outer.grid(row=8, column=0, columnspan=2, sticky=(tk.W, tk.E))
        ttk.Label(ck_outer, text="Name", font=("Arial", 8, "bold")).grid(
            row=0, column=0, padx=(0, 4), sticky=tk.W)
        ttk.Label(ck_outer, text="Value", font=("Arial", 8, "bold")).grid(
            row=0, column=1, sticky=tk.W)

        self.cookie_rows = []
        self.cookie_table = ttk.Frame(ck_outer)
        self.cookie_table.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E))

        btn_row = ttk.Frame(ck_outer)
        btn_row.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(6, 0))
        ttk.Button(btn_row, text="+ Add Cookie",
                   command=self._add_cookie_row, width=14).grid(row=0, column=0, padx=(0, 6))
        ttk.Button(btn_row, text="− Remove Last",
                   command=self._remove_cookie_row, width=14).grid(row=0, column=1)

        ck_outer.columnconfigure(1, weight=1)
        self._add_cookie_row()
        self._add_cookie_row()

        # ── Buttons ───────────────────────────────────────────────────────────
        bf = ttk.Frame(f)
        bf.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=6)

        self.start_btn = ttk.Button(bf, text="Start Archiving",
                                    command=self._start, width=20)
        self.start_btn.grid(row=0, column=0, padx=5)

        self.stop_btn = ttk.Button(bf, text="Stop",
                                   command=self._stop, width=20,
                                   state=tk.DISABLED)
        self.stop_btn.grid(row=0, column=1, padx=5)

        # ── Progress ──────────────────────────────────────────────────────────
        pf = ttk.LabelFrame(f, text="Progress", padding="10")
        pf.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=6)
        pf.columnconfigure(0, weight=1)
        pf.rowconfigure(2, weight=1)

        self.progress_var = tk.StringVar(value="Ready to archive")
        ttk.Label(pf, textvariable=self.progress_var).grid(
            row=0, column=0, sticky=tk.W, pady=4)

        self.progress_bar = ttk.Progressbar(pf, mode="determinate")
        self.progress_bar.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=4)

        self.log_text = scrolledtext.ScrolledText(
            pf, height=12, width=70, wrap=tk.WORD, font=("Courier New", 9))
        self.log_text.grid(row=2, column=0,
                           sticky=(tk.W, tk.E, tk.N, tk.S), pady=4)

        f.rowconfigure(2, weight=1)

    # ── Cookie helpers ────────────────────────────────────────────────────────

    def _add_cookie_row(self):
        idx = len(self.cookie_rows)
        nv, vv = tk.StringVar(), tk.StringVar()
        ne = ttk.Entry(self.cookie_table, textvariable=nv, width=22)
        ve = ttk.Entry(self.cookie_table, textvariable=vv, width=44)
        ne.grid(row=idx, column=0, padx=(0, 6), pady=2)
        ve.grid(row=idx, column=1, pady=2)
        self.cookie_rows.append((nv, vv, ne, ve))

    def _remove_cookie_row(self):
        if not self.cookie_rows:
            return
        nv, vv, ne, ve = self.cookie_rows.pop()
        ne.destroy(); ve.destroy()

    def _get_cookies(self):
        return {nv.get().strip(): vv.get().strip()
                for nv, vv, _, _ in self.cookie_rows
                if nv.get().strip() and vv.get().strip()}

    def _pick_output(self):
        p = filedialog.askdirectory(title="Select output folder")
        if p:
            self.output_var.set(p)

    # ── Logging ───────────────────────────────────────────────────────────────

    def _log(self, msg):
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        self.log_text.update_idletasks()

    # ── Validation ────────────────────────────────────────────────────────────

    def _validate(self):
        pattern = self.url_var.get().strip()
        if not pattern:
            messagebox.showerror("Error", "Please enter a URL pattern."); return False
        if "{id}" not in pattern:
            messagebox.showerror("Error", "URL pattern must contain {id}."); return False
        try:
            s = int(self.start_var.get())
            if s < 0: raise ValueError()
        except ValueError:
            messagebox.showerror("Error", "Start must be a non-negative integer."); return False
        try:
            e = int(self.end_var.get())
            if e < int(self.start_var.get()): raise ValueError()
        except ValueError:
            messagebox.showerror("Error", "End must be ≥ Start."); return False
        try:
            st = int(self.step_var.get())
            if st < 1: raise ValueError()
        except ValueError:
            messagebox.showerror("Error", "Step must be a positive integer."); return False
        try:
            d = float(self.delay_var.get())
            if d < 0: raise ValueError()
        except ValueError:
            messagebox.showerror("Error", "Delay must be a non-negative number."); return False
        return True

    # ── Run / Stop ────────────────────────────────────────────────────────────

    def _start(self):
        if not self._validate():
            return
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.is_archiving = True
        self.log_text.delete("1.0", tk.END)
        self.progress_bar["value"] = 0
        self.progress_var.set("Starting…")

        pattern = self.url_var.get().strip()
        start   = int(self.start_var.get())
        end     = int(self.end_var.get())
        step    = int(self.step_var.get())
        delay   = float(self.delay_var.get())
        output  = self.output_var.get().strip()
        cookies = self._get_cookies()

        threading.Thread(
            target=self._worker,
            args=(pattern, start, end, step, delay, output, cookies),
            daemon=True
        ).start()

    def _worker(self, pattern, start, end, step, delay, output, cookies):
        try:
            if getattr(sys, "frozen", False):
                base = Path(sys.executable).parent
            else:
                base = Path.cwd()
            out_path = base / output if not Path(output).is_absolute() else Path(output)

            self._log("Charlotte Web Archiver")
            self._log(f"Pattern: {pattern}")
            self._log(f"Range: {start} → {end}  step {step}")
            self._log(f"Delay: {delay}s")
            self._log(f"Output: {out_path}")
            if cookies:
                self._log(f"🍪 Cookies: {', '.join(cookies.keys())}")
            else:
                self._log("🔓 No cookies — archiving as guest")
            self._log("-" * 60)

            charlotte = Charlotte(
                base_url       = pattern.split("{")[0],
                output_dir     = str(out_path),
                delay          = delay,
                download_assets= False,
                cookies        = cookies or None,
            )
            urls  = charlotte.generate_urls(pattern, start, end, step)
            total = len(urls)
            self.progress_bar["maximum"] = total
            self.progress_bar["value"]   = 0

            for idx, url in enumerate(urls, 1):
                if not self.is_archiving:
                    self._log("\nArchiving stopped by user.")
                    break

                self.progress_var.set(f"Archiving {idx}/{total}: {url}")
                self._log(f"[{idx}/{total}] {url}")
                content, status, error = charlotte.fetch_page(url)

                if content:
                    fp = charlotte.save_page(url, content)
                    charlotte.metadata["pages_archived"].append({
                        "url": url, "filepath": str(fp),
                        "timestamp": datetime.now().isoformat(),
                        "status_code": status,
                    })
                    self._log("  ✓ Saved")
                else:
                    charlotte.metadata["failed_pages"].append({
                        "url": url, "timestamp": datetime.now().isoformat(),
                        "status_code": status, "error": error,
                    })
                    if status == 404:
                        self._log("  ⊘ Not found (404)")
                    elif status:
                        self._log(f"  ⊘ Error ({status})")
                    else:
                        self._log(f"  ✗ Failed: {error}")

                self.progress_bar["value"] = idx
                self.progress_bar.update_idletasks()

                if idx < total and self.is_archiving:
                    time.sleep(delay)

            charlotte.save_metadata()
            archived = len(charlotte.metadata["pages_archived"])
            failed   = len(charlotte.metadata["failed_pages"])
            self._log("-" * 60)
            self._log(f"✅ Archived: {archived}  ❌ Failed: {failed}")
            self._log(f"📁 Output: {out_path}")
            self._log("Archiving complete!")
            self.progress_var.set("Complete!")
            messagebox.showinfo(
                "Done",
                f"Archived {archived} pages!\nFailed: {failed}\nLocation: {out_path}"
            )
        except Exception as e:
            self._log(f"\n❌ Error: {e}")
            self.progress_var.set("Error occurred.")
            messagebox.showerror("Error", f"An error occurred:\n{e}")
        finally:
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            self.is_archiving = False

    def _stop(self):
        self.is_archiving = False
        self.stop_btn.config(state=tk.DISABLED)
        self.progress_var.set("Stopping…")


# ══════════════════════════════════════════════════════════════════════════════
#  THREAD WEAVER TAB
# ══════════════════════════════════════════════════════════════════════════════

class ThreadWeaverTab:
    def __init__(self, parent):
        self.parent          = parent
        self._is_running     = False
        self._stop_requested = False
        self._build(parent)

    def _build(self, f):
        f.columnconfigure(0, weight=1)
        f.rowconfigure(2, weight=1)

        # ── Settings ──────────────────────────────────────────────────────────
        sf = ttk.LabelFrame(f, text="Conversion Settings", padding="10")
        sf.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=10, pady=10)
        sf.columnconfigure(1, weight=1)

        # Input folder
        ttk.Label(sf, text="Input Folder:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.input_var = tk.StringVar()
        ttk.Entry(sf, textvariable=self.input_var, width=50).grid(
            row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 6), pady=5)
        ttk.Button(sf, text="Browse…", command=self._pick_input).grid(
            row=0, column=2, pady=5)
        ttk.Label(sf, text="Folder containing your .html files (searched recursively)",
                  font=("Arial", 8, "italic"), foreground="gray").grid(
            row=1, column=1, sticky=tk.W)

        # Output folder
        ttk.Label(sf, text="Output Folder:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.output_var = tk.StringVar()
        ttk.Entry(sf, textvariable=self.output_var, width=50).grid(
            row=2, column=1, sticky=(tk.W, tk.E), padx=(0, 6), pady=5)
        ttk.Button(sf, text="Browse…", command=self._pick_output).grid(
            row=2, column=2, pady=5)
        ttk.Label(sf, text="Where the chunked .txt files will be saved",
                  font=("Arial", 8, "italic"), foreground="gray").grid(
            row=3, column=1, sticky=tk.W)

        # ── Buttons ───────────────────────────────────────────────────────────
        bf = ttk.Frame(f, padding="10 4 10 0")
        bf.grid(row=1, column=0, sticky=(tk.W, tk.E))

        self.start_btn = ttk.Button(bf, text="Start Converting",
                                    command=self._start, width=20)
        self.start_btn.grid(row=0, column=0, padx=5)

        self.stop_btn = ttk.Button(bf, text="Stop", command=self._stop,
                                   width=20, state=tk.DISABLED)
        self.stop_btn.grid(row=0, column=1, padx=5)

        self.open_btn = ttk.Button(bf, text="Open Output Folder",
                                   command=self._open_output,
                                   width=20, state=tk.DISABLED)
        self.open_btn.grid(row=0, column=2, padx=5)

        # ── Progress ──────────────────────────────────────────────────────────
        pf = ttk.LabelFrame(f, text="Progress", padding="10")
        pf.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S),
                padx=10, pady=10)
        pf.columnconfigure(0, weight=1)
        pf.rowconfigure(2, weight=1)

        self.progress_var = tk.StringVar(value="Ready to convert")
        ttk.Label(pf, textvariable=self.progress_var).grid(
            row=0, column=0, sticky=tk.W, pady=5)

        self.progress_bar = ttk.Progressbar(pf, mode="determinate")
        self.progress_bar.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)

        self.log_text = scrolledtext.ScrolledText(
            pf, height=15, width=70, wrap=tk.WORD, font=("Courier New", 9))
        self.log_text.grid(row=2, column=0,
                           sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)

    # ── Folder pickers ────────────────────────────────────────────────────────

    def _pick_input(self):
        p = filedialog.askdirectory(title="Select folder containing HTML files")
        if p:
            self.input_var.set(p)
            if not self.output_var.get():
                self.output_var.set(str(Path(p).parent / "notebooklm_chunks"))

    def _pick_output(self):
        p = filedialog.askdirectory(title="Select output folder")
        if p:
            self.output_var.set(p)

    def _open_output(self):
        p = self.output_var.get()
        if p and Path(p).exists():
            subprocess.Popen(f'explorer "{Path(p)}"')

    # ── Logging ───────────────────────────────────────────────────────────────

    def _log(self, msg):
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        self.log_text.update_idletasks()

    def _set_progress(self, current, total):
        pct = int(current / total * 100)
        self.progress_bar["maximum"] = 100
        self.progress_bar["value"]   = pct
        self.progress_var.set(
            f"Processing file {current:,} of {total:,}  ({pct}%)"
        )
        self.progress_bar.update_idletasks()

    # ── Run / Stop ────────────────────────────────────────────────────────────

    def _start(self):
        inp = self.input_var.get().strip()
        out = self.output_var.get().strip()
        if not inp:
            messagebox.showerror("Error", "Please select an input folder."); return
        if not out:
            messagebox.showerror("Error", "Please select an output folder."); return
        in_dir  = Path(inp)
        out_dir = Path(out)
        if not in_dir.exists():
            messagebox.showerror("Error", f"Input folder not found:\n{in_dir}"); return

        self.log_text.delete("1.0", tk.END)
        self.progress_bar["value"] = 0
        self.progress_var.set("Starting…")
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.open_btn.config(state=tk.DISABLED)
        self._is_running     = True
        self._stop_requested = False

        def done(success):
            self._is_running = False
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            if success:
                self.open_btn.config(state=tk.NORMAL)
                self.progress_bar["value"] = 100
                self.progress_var.set("Complete!")
                messagebox.showinfo(
                    "Done",
                    f"Conversion complete!\nChunks saved to:\n{out_dir}"
                )
            else:
                self.progress_var.set("Stopped.")

        threading.Thread(
            target=run_conversion,
            args=(in_dir, out_dir, self._log, self._set_progress, done,
                  lambda: self._stop_requested),
            daemon=True
        ).start()

    def _stop(self):
        self._stop_requested = True
        self.stop_btn.config(state=tk.DISABLED)
        self.progress_var.set("Stopping…")


# ══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def main():
    root = tk.Tk()
    CharlotteApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
