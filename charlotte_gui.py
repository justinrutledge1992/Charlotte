#!/usr/bin/env python3
"""
Charlotte GUI - Graphical Interface for Web Archiving
A simple point-and-click interface for archiving forum threads and web pages.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import sys
from pathlib import Path

# Import Charlotte
from charlotte import Charlotte

class CharlotteGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Charlotte Web Archiver")
        self.root.geometry("700x950")
        self.root.resizable(True, True)
        
        # Variables
        self.is_archiving = False
        self.charlotte = None
        
        # Create GUI
        self.create_widgets()
        
    def create_widgets(self):
        # Header
        header_frame = ttk.Frame(self.root, padding="10")
        header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        title_label = ttk.Label(
            header_frame, 
            text="Charlotte Web Archiver", 
            font=('Arial', 16, 'bold')
        )
        title_label.grid(row=0, column=0, sticky=tk.W)
        
        subtitle_label = ttk.Label(
            header_frame, 
            text="Archive forum threads and web pages", 
            font=('Arial', 9)
        )
        subtitle_label.grid(row=1, column=0, sticky=tk.W)
        
        # Input Frame
        input_frame = ttk.LabelFrame(self.root, text="Archive Settings", padding="10")
        input_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10, pady=10)
        
        # URL Pattern
        ttk.Label(input_frame, text="URL Pattern:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.url_pattern_var = tk.StringVar(value="https://forum.com/thread/{id}")
        self.url_pattern_entry = ttk.Entry(input_frame, textvariable=self.url_pattern_var, width=50)
        self.url_pattern_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(
            input_frame, 
            text="Use {id} where the number goes", 
            font=('Arial', 8, 'italic'),
            foreground='gray'
        ).grid(row=1, column=1, sticky=tk.W)
        
        # Start Number
        ttk.Label(input_frame, text="Start Number:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.start_var = tk.StringVar(value="1")
        self.start_entry = ttk.Entry(input_frame, textvariable=self.start_var, width=20)
        self.start_entry.grid(row=2, column=1, sticky=tk.W, pady=5)
        
        # End Number
        ttk.Label(input_frame, text="End Number:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.end_var = tk.StringVar(value="100")
        self.end_entry = ttk.Entry(input_frame, textvariable=self.end_var, width=20)
        self.end_entry.grid(row=3, column=1, sticky=tk.W, pady=5)
        
        # Delay
        ttk.Label(input_frame, text="Delay (seconds):").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.delay_var = tk.StringVar(value="1.0")
        self.delay_entry = ttk.Entry(input_frame, textvariable=self.delay_var, width=20)
        self.delay_entry.grid(row=4, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(
            input_frame, 
            text="Increase if getting blocked (2.0-3.0)", 
            font=('Arial', 8, 'italic'),
            foreground='gray'
        ).grid(row=5, column=1, sticky=tk.W)
        
        # Output Folder
        ttk.Label(input_frame, text="Output Folder:").grid(row=6, column=0, sticky=tk.W, pady=5)
        self.output_var = tk.StringVar(value="charlotte_archives")
        self.output_entry = ttk.Entry(input_frame, textvariable=self.output_var, width=30)
        self.output_entry.grid(row=6, column=1, sticky=tk.W, pady=5)

        # Session Cookies section
        ttk.Separator(input_frame, orient='horizontal').grid(
            row=7, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=8
        )

        cookie_title = ttk.Label(
            input_frame,
            text="Session Cookies (optional — for login-protected forums)",
            font=('Arial', 9, 'bold')
        )
        cookie_title.grid(row=8, column=0, columnspan=2, sticky=tk.W, pady=(0, 4))

        ttk.Label(
            input_frame,
            text="Find these in Firefox DevTools → Storage tab → Cookies",
            font=('Arial', 8, 'italic'),
            foreground='gray'
        ).grid(row=9, column=0, columnspan=2, sticky=tk.W, pady=(0, 6))

        # Cookie table frame
        cookie_frame = ttk.Frame(input_frame)
        cookie_frame.grid(row=10, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=4)

        # Column headers
        ttk.Label(cookie_frame, text="Name", font=('Arial', 8, 'bold')).grid(
            row=0, column=0, padx=(0, 4), pady=(0, 2), sticky=tk.W
        )
        ttk.Label(cookie_frame, text="Value", font=('Arial', 8, 'bold')).grid(
            row=0, column=1, padx=(0, 4), pady=(0, 2), sticky=tk.W
        )

        # List to hold (name_var, value_var) tuples
        self.cookie_rows = []

        self.cookie_table_frame = ttk.Frame(cookie_frame)
        self.cookie_table_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E))

        # Add/Remove buttons
        btn_frame = ttk.Frame(cookie_frame)
        btn_frame.grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=(6, 0))

        ttk.Button(
            btn_frame, text="+ Add Cookie", command=self._add_cookie_row, width=14
        ).grid(row=0, column=0, padx=(0, 6))

        ttk.Button(
            btn_frame, text="− Remove Last", command=self._remove_cookie_row, width=14
        ).grid(row=0, column=1)

        cookie_frame.columnconfigure(1, weight=1)

        # Start with two empty rows
        self._add_cookie_row()
        self._add_cookie_row()
        
        # Make column 1 expandable
        input_frame.columnconfigure(1, weight=1)
        
        # Buttons Frame
        button_frame = ttk.Frame(self.root, padding="10")
        button_frame.grid(row=2, column=0, sticky=(tk.W, tk.E))
        
        self.start_button = ttk.Button(
            button_frame, 
            text="Start Archiving", 
            command=self.start_archiving,
            width=20
        )
        self.start_button.grid(row=0, column=0, padx=5)
        
        self.stop_button = ttk.Button(
            button_frame, 
            text="Stop", 
            command=self.stop_archiving,
            state=tk.DISABLED,
            width=20
        )
        self.stop_button.grid(row=0, column=1, padx=5)
        
        # Progress Frame
        progress_frame = ttk.LabelFrame(self.root, text="Progress", padding="10")
        progress_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10, pady=10)
        
        # Progress bar
        self.progress_var = tk.StringVar(value="Ready to archive")
        self.progress_label = ttk.Label(progress_frame, textvariable=self.progress_var)
        self.progress_label.grid(row=0, column=0, sticky=tk.W, pady=5)
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress_bar.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        
        # Log output
        self.log_text = scrolledtext.ScrolledText(progress_frame, height=15, width=70, wrap=tk.WORD)
        self.log_text.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        progress_frame.columnconfigure(0, weight=1)
        progress_frame.rowconfigure(2, weight=1)
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(3, weight=1)

    def _add_cookie_row(self):
        """Add a new cookie name/value row to the table"""
        idx = len(self.cookie_rows)
        name_var = tk.StringVar()
        value_var = tk.StringVar()

        name_entry = ttk.Entry(self.cookie_table_frame, textvariable=name_var, width=22)
        name_entry.grid(row=idx, column=0, padx=(0, 6), pady=2, sticky=tk.W)

        value_entry = ttk.Entry(self.cookie_table_frame, textvariable=value_var, width=44)
        value_entry.grid(row=idx, column=1, pady=2, sticky=(tk.W, tk.E))

        self.cookie_rows.append((name_var, value_var, name_entry, value_entry))

    def _remove_cookie_row(self):
        """Remove the last cookie row from the table"""
        if not self.cookie_rows:
            return
        name_var, value_var, name_entry, value_entry = self.cookie_rows.pop()
        name_entry.destroy()
        value_entry.destroy()

    def _get_cookies(self):
        """Collect all non-empty cookie name/value pairs from the table"""
        cookies = {}
        for name_var, value_var, _, _ in self.cookie_rows:
            name = name_var.get().strip()
            value = value_var.get().strip()
            if name and value:
                cookies[name] = value
        return cookies

    def log(self, message):
        """Add message to log window"""
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
        
    def validate_inputs(self):
        """Validate user inputs"""
        # Check URL pattern
        url_pattern = self.url_pattern_var.get().strip()
        if not url_pattern:
            messagebox.showerror("Error", "Please enter a URL pattern")
            return False
        if "{id}" not in url_pattern:
            messagebox.showerror("Error", "URL pattern must contain {id}")
            return False
            
        # Check start number
        try:
            start = int(self.start_var.get())
            if start < 0:
                raise ValueError()
        except ValueError:
            messagebox.showerror("Error", "Start number must be a positive integer")
            return False
            
        # Check end number
        try:
            end = int(self.end_var.get())
            if end < start:
                raise ValueError()
        except ValueError:
            messagebox.showerror("Error", "End number must be greater than or equal to start number")
            return False
            
        # Check delay
        try:
            delay = float(self.delay_var.get())
            if delay < 0:
                raise ValueError()
        except ValueError:
            messagebox.showerror("Error", "Delay must be a positive number")
            return False
            
        return True
        
    def start_archiving(self):
        """Start the archiving process"""
        if not self.validate_inputs():
            return
            
        # Disable start button, enable stop button
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.is_archiving = True
        
        # Clear log
        self.log_text.delete(1.0, tk.END)
        
        # Get values
        url_pattern = self.url_pattern_var.get().strip()
        start = int(self.start_var.get())
        end = int(self.end_var.get())
        delay = float(self.delay_var.get())
        output = self.output_var.get().strip()
        cookies = self._get_cookies()
        
        # Start archiving in a separate thread
        thread = threading.Thread(
            target=self.archive_thread,
            args=(url_pattern, start, end, delay, output, cookies),
            daemon=True
        )
        thread.start()
        
    def archive_thread(self, url_pattern, start, end, delay, output, cookies=None):
        """Thread function for archiving"""
        try:
            # Determine output directory (same location as exe)
            if getattr(sys, 'frozen', False):
                exe_dir = Path(sys.executable).parent
            else:
                exe_dir = Path.cwd()
            
            if not Path(output).is_absolute():
                output_path = exe_dir / output
            else:
                output_path = Path(output)
            
            self.log(f"Charlotte Web Archiver")
            self.log(f"Pattern: {url_pattern}")
            self.log(f"Range: {start} to {end}")
            self.log(f"Delay: {delay}s")
            self.log(f"Output: {output_path}")
            self.log(f"Mode: Lightweight (HTML only)")

            if cookies:
                self.log(f"🍪 Session cookies loaded: {', '.join(cookies.keys())}")
            else:
                self.log(f"🔓 No session cookies — archiving as guest")

            self.log("-" * 60)
            
            # Create Charlotte instance
            base_url = url_pattern.split('{')[0]
            charlotte = Charlotte(
                base_url=base_url,
                output_dir=str(output_path),
                delay=delay,
                download_assets=False,
                cookies=cookies if cookies else None
            )
            
            # Generate URLs
            urls = charlotte.generate_urls(url_pattern, start, end)
            total = len(urls)
            
            self.progress_bar['maximum'] = total
            self.progress_bar['value'] = 0
            
            # Archive each URL
            for idx, url in enumerate(urls, 1):
                if not self.is_archiving:
                    self.log("\nArchiving stopped by user")
                    break
                    
                self.progress_var.set(f"Archiving {idx}/{total}: {url}")
                self.log(f"[{idx}/{total}] {url}")
                
                content, status, error = charlotte.fetch_page(url)
                
                if content:
                    filepath = charlotte.save_page(url, content)
                    charlotte.metadata['pages_archived'].append({
                        'url': url,
                        'filepath': str(filepath),
                        'timestamp': Path(filepath).stat().st_mtime,
                        'status_code': status
                    })
                    self.log(f"  ✓ Saved")
                else:
                    charlotte.metadata['failed_pages'].append({
                        'url': url,
                        'timestamp': '',
                        'status_code': status,
                        'error': error
                    })
                    if status == 404:
                        self.log(f"  ⊘ Not found (404)")
                    elif status:
                        self.log(f"  ⊘ Error ({status})")
                    else:
                        self.log(f"  ✗ Failed: {error}")
                
                self.progress_bar['value'] = idx
                self.root.update_idletasks()
                
                # Delay between requests
                if idx < total and self.is_archiving:
                    import time
                    time.sleep(delay)
            
            # Save metadata
            charlotte.save_metadata()
            
            self.log("-" * 60)
            self.log(f"✅ Successfully archived: {len(charlotte.metadata['pages_archived'])} pages")
            self.log(f"❌ Failed: {len(charlotte.metadata['failed_pages'])} pages")
            self.log(f"📁 Output: {output_path}")
            self.log("-" * 60)
            self.log("Archiving complete!")
            
            self.progress_var.set("Complete!")
            messagebox.showinfo(
                "Success", 
                f"Archived {len(charlotte.metadata['pages_archived'])} pages!\n"
                f"Failed: {len(charlotte.metadata['failed_pages'])}\n"
                f"Location: {output_path}"
            )
            
        except Exception as e:
            self.log(f"\n❌ Error: {str(e)}")
            self.progress_var.set("Error occurred")
            messagebox.showerror("Error", f"An error occurred:\n{str(e)}")
            
        finally:
            # Re-enable buttons
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.is_archiving = False
            
    def stop_archiving(self):
        """Stop the archiving process"""
        self.is_archiving = False
        self.stop_button.config(state=tk.DISABLED)
        self.progress_var.set("Stopping...")
        

def main():
    root = tk.Tk()
    app = CharlotteGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()