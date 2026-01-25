# Charlotte Web Archiver - User Guide

Simple tool for archiving forum threads and web pages.

## Quick Start

1. **Double-click `charlotte_gui.exe`**
2. **Fill in the form:**
   - **URL Pattern**: The website URL with `{id}` where numbers go
   - **Start Number**: First page number to archive
   - **End Number**: Last page number to archive
   - **Delay**: Seconds to wait between requests (1.0 is fine, increase to 2.0 if getting blocked)
   - **Output Folder**: Where to save files (default is fine)

3. **Click "Start Archiving"**
4. **Wait for completion**
5. **Find your files** in the `charlotte_archives` folder next to the .exe

## Example

If you want to archive forum threads from:
- `https://forum.example.com/thread/1`
- `https://forum.example.com/thread/2`
- `https://forum.example.com/thread/3`
- etc.

**Fill in:**
- URL Pattern: `https://forum.example.com/thread/{id}`
- Start Number: `1`
- End Number: `100`
- Delay: `1.0`

**Click "Start Archiving"** and Charlotte will archive threads 1-100!

## Finding the URL Pattern

1. Visit a few pages on the website
2. Look at the URLs in your browser
3. Find where the numbers are
4. Replace that number with `{id}`

**Examples:**
- `https://site.com/page/5` → `https://site.com/page/{id}`
- `https://forum.com/threads/123` → `https://forum.com/threads/{id}`
- `https://blog.com/post-42` → `https://blog.com/post-{id}`

## Tips

- **Start small**: Try archiving 10-20 pages first to test
- **Many 404s are normal**: Not all numbers will exist
- **Increase delay if blocked**: Change from 1.0 to 2.0 or 3.0
- **Be patient**: Large archives take time (1-2 seconds per page)

## Output

Files are saved in `charlotte_archives` folder:
- Plain HTML files (no fancy styling)
- Small file sizes (~10-50 KB each)
- All text content preserved
- Can open in any web browser

## Troubleshooting

**Nothing happens when I click Start**
- Check that all fields are filled in
- Make sure URL has `{id}` in it
- Make sure Start is less than End

**Getting blocked (403 errors)**
- Increase the Delay to 2.0 or higher
- The website may not allow archiving

**All pages are 404**
- Check the URL pattern is correct
- Try visiting one of the URLs in your browser first

---

Questions? The tool is called Charlotte - named after the spider from Charlotte's Web!
