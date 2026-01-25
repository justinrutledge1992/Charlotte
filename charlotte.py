#!/usr/bin/env python3
"""
Charlotte - Web Page Archiver
A simple yet powerful web scraper for archiving pages from websites.
Named after Charlotte the spider from Charlotte's Web.

"Some spider!"
"""

import requests
from bs4 import BeautifulSoup
import os
import sys
import time
from urllib.parse import urlparse, urljoin
from pathlib import Path
import json
from datetime import datetime
import argparse
import hashlib

try:
    from charlotte_branding import print_small_banner
except ImportError:
    def print_small_banner():
        print("Charlotte 🕷️  - Web Archiver")
        print('"Some Spider!"\n')


class Charlotte:
    def __init__(self, base_url, output_dir="archived_pages", delay=1.0, download_assets=False):
        """
        Initialize Charlotte the web archiver.
        
        Args:
            base_url: Base URL of the website
            output_dir: Directory to save archived pages
            delay: Delay between requests in seconds (be respectful!)
            download_assets: Whether to inline CSS/JS and download images (default: False for lightweight archives)
        """
        self.base_url = base_url
        self.output_dir = Path(output_dir)
        self.delay = delay
        self.download_assets = download_assets
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; Charlotte/1.0; +https://github.com/charlotte-web-archiver)'
        })
        
        # Create output directory structure
        self.output_dir.mkdir(parents=True, exist_ok=True)
        if self.download_assets:
            (self.output_dir / 'images').mkdir(parents=True, exist_ok=True)
        
        # Metadata tracking
        self.metadata = {
            'base_url': base_url,
            'start_time': datetime.now().isoformat(),
            'pages_archived': [],
            'failed_pages': [],
            'images_downloaded': [],
            'css_inlined': 0,
            'js_inlined': 0
        }
        
        # Track downloaded images to avoid duplicates
        self.downloaded_images = {}
    
    def generate_urls(self, pattern, start, end, step=1):
        """
        Generate URLs based on a numeric pattern.
        
        Args:
            pattern: URL pattern with {id} placeholder (e.g., "https://example.com/page/{id}")
            start: Starting number
            end: Ending number (inclusive)
            step: Step size (default: 1)
            
        Returns:
            List of URLs
        """
        return [pattern.format(id=i) for i in range(start, end + 1, step)]
    
    def generate_urls_custom(self, url_list):
        """
        Use a custom list of URLs.
        
        Args:
            url_list: List of URLs to archive
            
        Returns:
            List of URLs
        """
        return url_list
    
    def generate_urls_from_list(self, identifiers, pattern):
        """
        Generate URLs from a list of identifiers (e.g., letters, dates, names).
        
        Args:
            identifiers: List of values to insert into pattern
            pattern: URL pattern with {id} placeholder
            
        Returns:
            List of URLs
        """
        return [pattern.format(id=identifier) for identifier in identifiers]
    
    def sanitize_filename(self, url):
        """
        Create a safe filename from a URL.
        
        Args:
            url: URL to convert to filename
            
        Returns:
            Safe filename string
        """
        parsed = urlparse(url)
        path = parsed.path.strip('/').replace('/', '_')
        if parsed.query:
            path += '_' + parsed.query.replace('&', '_').replace('=', '-')
        
        if not path:
            path = 'index'
        
        # Remove unsafe characters
        safe_chars = '-_.()abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        filename = ''.join(c if c in safe_chars else '_' for c in path)
        
        # Limit length and add extension
        return filename[:200] + '.html'
    
    def fetch_page(self, url):
        """
        Fetch a single web page.
        
        Args:
            url: URL to fetch
            
        Returns:
            Tuple of (content, status_code, error)
        """
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.text, response.status_code, None
        except requests.HTTPError as e:
            # HTTP errors like 404, 403, etc - don't retry, just report
            return None, e.response.status_code if e.response else None, str(e)
        except requests.RequestException as e:
            # Network errors, timeouts, etc
            return None, None, str(e)
    
    def fetch_asset_content(self, asset_url):
        """
        Fetch the content of a CSS or JavaScript file.
        
        Args:
            asset_url: URL of the CSS or JS file
            
        Returns:
            Content as string, or None if failed
        """
        try:
            response = self.session.get(asset_url, timeout=15)
            response.raise_for_status()
            return response.text
        except Exception:
            # Silently fail for assets
            return None
    
    def download_image(self, image_url):
        """
        Download an image file.
        
        Args:
            image_url: URL of the image
            
        Returns:
            Local path relative to output_dir, or None if failed
        """
        # Check if already downloaded
        if image_url in self.downloaded_images:
            return self.downloaded_images[image_url]
        
        try:
            response = self.session.get(image_url, timeout=15)
            response.raise_for_status()
            
            # Create filename from URL hash to avoid issues with complex URLs
            url_hash = hashlib.md5(image_url.encode()).hexdigest()[:12]
            ext = Path(urlparse(image_url).path).suffix or '.jpg'
            
            filename = f"{url_hash}{ext}"
            local_path = self.output_dir / 'images' / filename
            
            # Save image as binary
            with open(local_path, 'wb') as f:
                f.write(response.content)
            
            # Store relative path
            relative_path = f"images/{filename}"
            self.downloaded_images[image_url] = relative_path
            
            self.metadata['images_downloaded'].append({
                'url': image_url,
                'local_path': relative_path
            })
            
            return relative_path
        except Exception:
            # Silently fail for images
            return None
    
    def process_html(self, url, content):
        """
        Process HTML content: inline CSS/JS and download images.
        
        Args:
            url: Original page URL
            content: HTML content
            
        Returns:
            Processed HTML content with inlined CSS/JS and local image paths
        """
        if not self.download_assets:
            return content
        
        soup = BeautifulSoup(content, 'html.parser')
        base_url = url
        
        # Inline CSS stylesheets
        for link in soup.find_all('link', rel='stylesheet'):
            href = link.get('href')
            if href:
                css_url = urljoin(base_url, href)
                print(f"  📄 Fetching CSS: {css_url}")
                css_content = self.fetch_asset_content(css_url)
                
                if css_content:
                    # Create a new <style> tag with the CSS content
                    style_tag = soup.new_tag('style')
                    style_tag.string = css_content
                    # Replace the <link> tag with <style>
                    link.replace_with(style_tag)
                    self.metadata['css_inlined'] += 1
                    print(f"  ✓ Inlined CSS ({len(css_content)} chars)")
                else:
                    print(f"  ✗ Failed to fetch CSS")
        
        # Inline JavaScript files
        for script in soup.find_all('script', src=True):
            src = script.get('src')
            if src:
                js_url = urljoin(base_url, src)
                print(f"  📄 Fetching JS: {js_url}")
                js_content = self.fetch_asset_content(js_url)
                
                if js_content:
                    # Remove src attribute and add content directly
                    del script['src']
                    script.string = js_content
                    self.metadata['js_inlined'] += 1
                    print(f"  ✓ Inlined JS ({len(js_content)} chars)")
                else:
                    print(f"  ✗ Failed to fetch JS")
        
        # Download and update image sources
        for img in soup.find_all('img'):
            src = img.get('src')
            if src:
                img_url = urljoin(base_url, src)
                local_path = self.download_image(img_url)
                if local_path:
                    img['src'] = local_path
        
        # Also handle background images in style attributes
        for tag in soup.find_all(style=True):
            style = tag['style']
            if 'url(' in style:
                # This is a simplified approach - could be enhanced
                import re
                urls = re.findall(r'url\(["\']?([^"\')]+)["\']?\)', style)
                for img_url_fragment in urls:
                    img_url = urljoin(base_url, img_url_fragment)
                    local_path = self.download_image(img_url)
                    if local_path:
                        style = style.replace(img_url_fragment, local_path)
                tag['style'] = style
        
        return str(soup)
    
    def save_page(self, url, content):
        """
        Save page content to file, optionally downloading assets.
        
        Args:
            url: Original URL
            content: Page HTML content
            
        Returns:
            Path to saved file
        """
        filename = self.sanitize_filename(url)
        filepath = self.output_dir / filename
        
        # Process HTML to download assets and update paths
        processed_content = self.process_html(url, content)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(processed_content)
        
        return filepath
    
    def archive_urls(self, urls):
        """
        Archive a list of URLs.
        
        Args:
            urls: List of URLs to archive
        """
        total = len(urls)
        
        for idx, url in enumerate(urls, 1):
            print(f"[{idx}/{total}] Archiving: {url}")
            
            content, status, error = self.fetch_page(url)
            
            if content:
                filepath = self.save_page(url, content)
                self.metadata['pages_archived'].append({
                    'url': url,
                    'filepath': str(filepath),
                    'timestamp': datetime.now().isoformat(),
                    'status_code': status
                })
                print(f"  ✓ Saved to: {filepath}")
            else:
                self.metadata['failed_pages'].append({
                    'url': url,
                    'timestamp': datetime.now().isoformat(),
                    'status_code': status,
                    'error': error
                })
                # Show status code for common HTTP errors
                if status == 404:
                    print(f"  ⊘ Not found (404)")
                elif status == 403:
                    print(f"  ⊘ Forbidden (403)")
                elif status:
                    print(f"  ⊘ Error ({status})")
                else:
                    print(f"  ✗ Failed: {error}")
            
            # Be respectful - don't hammer the server
            if idx < total:
                time.sleep(self.delay)
        
        self.save_metadata()
    
    def save_metadata(self):
        """Save metadata about the archiving session."""
        self.metadata['end_time'] = datetime.now().isoformat()
        self.metadata['total_pages'] = len(self.metadata['pages_archived'])
        self.metadata['failed_count'] = len(self.metadata['failed_pages'])
        self.metadata['total_images'] = len(self.metadata['images_downloaded'])
        
        metadata_path = self.output_dir / 'archive_metadata.json'
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, indent=2)
        
        print(f"\n{'='*60}")
        print(f"Successfully archived: {self.metadata['total_pages']} pages")
        print(f"Failed: {self.metadata['failed_count']} pages")
        if self.download_assets:
            print(f"CSS inlined: {self.metadata['css_inlined']} stylesheets")
            print(f"JS inlined: {self.metadata['js_inlined']} scripts")
            print(f"Images downloaded: {self.metadata['total_images']}")
        print(f"Metadata: {metadata_path}")
        print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(
        description='Charlotte 🕷️  - Archive web pages with predictable URL patterns',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Archive forum threads (lightweight HTML only - recommended)
  python charlotte.py --pattern "https://forum.com/thread/{id}" --start 1 --end 5000
  
  # With full assets (CSS/JS inlined, images downloaded)
  python charlotte.py --pattern "https://example.com/article/{id}" --start 1 --end 100 --with-assets
  
  # Custom delay between requests (be respectful!)
  python charlotte.py --pattern "https://forum.com/thread/{id}" --start 1 --end 1000 --delay 2.0
  
  # Archive every 10th thread
  python charlotte.py --pattern "https://forum.com/post/{id}" --start 0 --end 10000 --step 10

Note: By default, Charlotte saves lightweight HTML-only archives (perfect for forums).
This keeps file sizes small and makes archiving thousands of pages practical.
Use --with-assets to inline CSS/JS and download images for full page preservation.

Charlotte expects many URLs may not exist (404 errors). She'll skip them and continue.
If you're getting rate limited or blocked, increase --delay to 2.0 or higher.

"Some spider!" - Charlotte's Web
        """
    )
    
    parser.add_argument('--pattern', required=True,
                        help='URL pattern with {id} placeholder')
    parser.add_argument('--start', type=int, required=True,
                        help='Starting number for URL pattern')
    parser.add_argument('--end', type=int, required=True,
                        help='Ending number for URL pattern (inclusive)')
    parser.add_argument('--step', type=int, default=1,
                        help='Step size for URL generation (default: 1)')
    parser.add_argument('--output', default='charlotte_archives',
                        help='Output directory (default: charlotte_archives)')
    parser.add_argument('--delay', type=float, default=1.0,
                        help='Delay between requests in seconds (default: 1.0, increase if rate limited)')
    parser.add_argument('--with-assets', action='store_true',
                        help='Include CSS/JS and images (creates larger files, use for rich content)')
    
    args = parser.parse_args()
    
    # Determine the directory where charlotte.exe is located
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        exe_dir = Path(sys.executable).parent
    else:
        # Running as Python script
        exe_dir = Path.cwd()
    
    # Make output path relative to exe directory
    if not Path(args.output).is_absolute():
        output_path = exe_dir / args.output
    else:
        output_path = Path(args.output)
    
    # Create Charlotte archiver
    charlotte = Charlotte(
        base_url=args.pattern.split('{')[0],
        output_dir=str(output_path),
        delay=args.delay,
        download_assets=args.with_assets
    )
    
    # Generate URLs
    urls = charlotte.generate_urls(args.pattern, args.start, args.end, args.step)
    
    print_small_banner()
    print(f"Pattern: {args.pattern}")
    print(f"Range: {args.start} to {args.end} (step: {args.step})")
    print(f"Total URLs: {len(urls)}")
    print(f"Output: {args.output}")
    print(f"Delay: {args.delay}s")
    print(f"Download assets: {'Yes (inline CSS/JS, download images)' if args.with_assets else 'No (lightweight HTML only)'}")
    if args.delay < 1.0:
        print(f"⚠️  Low delay! Increase to 1.0+ if you get blocked")
    print()
    
    # Archive the URLs
    charlotte.archive_urls(urls)
    
    print("\n🕷️  Charlotte has finished weaving! Archiving complete!")


if __name__ == "__main__":
    main()
