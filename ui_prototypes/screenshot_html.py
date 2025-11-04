#!/usr/bin/env python3
"""
Screenshot HTML files for visual review.
Requires: playwright
Install with: uv pip install playwright && uv run playwright install chromium
"""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

def screenshot_html(html_path: str, output_path: str = None):
    """Take a screenshot of an HTML file."""
    html_file = Path(html_path)
    if not html_file.exists():
        print(f"Error: {html_path} not found")
        return

    if output_path is None:
        output_path = html_file.with_suffix('.png')

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width': 1400, 'height': 1000})
        page.goto(f'file://{html_file.absolute()}')
        page.screenshot(path=output_path, full_page=True)
        browser.close()

    print(f"Screenshot saved to: {output_path}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python screenshot_html.py <html_file> [output_png]")
        sys.exit(1)

    html_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    screenshot_html(html_path, output_path)
