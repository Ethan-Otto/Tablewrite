#!/usr/bin/env python3
"""
Export journal entries from FoundryVTT to local files.

Supports exporting to:
- JSON: Full journal data structure
- HTML: Combined HTML file with all pages
- Individual HTML: Separate HTML file per page
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from foundry.client import FoundryClient
from logging_config import setup_logging

logger = setup_logging(__name__)

# Project root is two levels up from this script (foundry -> src -> root)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def export_to_json(journal_data: dict, output_path: str) -> None:
    """
    Export journal data to JSON file.

    Args:
        journal_data: Journal entry data from FoundryVTT API
        output_path: Path to save JSON file
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(journal_data, f, indent=2, ensure_ascii=False)
    logger.info(f"Exported to JSON: {output_path}")


def export_to_html(journal_data: dict, output_path: str, single_file: bool = True) -> None:
    """
    Export journal data to HTML file(s).

    Args:
        journal_data: Journal entry data from FoundryVTT API
        output_path: Path to save HTML file (or directory for multi-file)
        single_file: If True, combine all pages into one file. If False, create separate files.
    """
    # Extract data from response (API wraps journal data in 'data' key)
    data = journal_data.get('data', journal_data)
    journal_name = data.get('name', 'Untitled Journal')
    pages = data.get('pages', [])

    if not pages:
        logger.warning("No pages found in journal")
        return

    # CSS for HTML files
    css_style = """<style>
        body {
            font-family: 'Bookman Old Style', Georgia, serif;
            line-height: 1.6;
            margin: 2em auto;
            max-width: 900px;
            background: #f5f5dc;
            padding: 20px;
        }
        .page-container {
            background: white;
            padding: 40px;
            margin-bottom: 40px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }
        .page-title {
            font-size: 2em;
            color: #5c3317;
            border-bottom: 3px solid #8b4513;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }
        nav {
            background-color: #8b4513;
            padding: 1em;
            margin-bottom: 20px;
            border-radius: 5px;
        }
        nav a {
            text-decoration: none;
            color: #f5f5dc;
            padding: 0.5em 1em;
            display: inline-block;
        }
        nav a:hover {
            background-color: #5c3317;
            border-radius: 3px;
        }
        h1 { color: #5c3317; font-size: 1.8em; }
        h2 { color: #5c3317; font-size: 1.5em; }
        h3 { color: #5c3317; font-size: 1.3em; }
        h4 { color: #5c3317; font-size: 1.1em; }
        table {
            border-collapse: collapse;
            margin: 1em 0;
            width: 100%;
            background: white;
        }
        table td {
            padding: 0.5em;
            border: 1px solid #8b4513;
        }
        dl { margin: 1em 0; }
        dt { font-weight: bold; margin-top: 0.5em; color: #5c3317; }
        dd { margin-left: 2em; margin-bottom: 0.5em; }
        .export-info {
            text-align: center;
            color: #666;
            font-size: 0.9em;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
        }
    </style>"""

    if single_file:
        # Combine all pages into one HTML file
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{journal_name}</title>
    {css_style}
</head>
<body>
    <nav>
        <strong style="color: #f5f5dc; font-size: 1.2em;">{journal_name}</strong>
"""

        # Add navigation links
        for i, page in enumerate(pages):
            page_name = page.get('name', f'Page {i+1}')
            page_id = f"page-{i}"
            html_content += f'        <a href="#{page_id}">{page_name}</a>\n'

        html_content += "    </nav>\n\n"

        # Add all pages
        for i, page in enumerate(pages):
            page_name = page.get('name', f'Page {i+1}')
            page_id = f"page-{i}"
            page_content = page.get('text', {}).get('content', '<p>No content</p>')

            html_content += f"""    <div class="page-container" id="{page_id}">
        <div class="page-title">{page_name}</div>
        {page_content}
    </div>
"""

        # Add export info
        export_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        html_content += f"""
    <div class="export-info">
        Exported from FoundryVTT on {export_time}<br>
        Journal: {journal_name} | Pages: {len(pages)}
    </div>
</body>
</html>"""

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        logger.info(f"Exported to HTML: {output_path} ({len(pages)} pages)")

    else:
        # Create separate HTML file for each page
        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)

        for i, page in enumerate(pages):
            page_name = page.get('name', f'Page {i+1}')
            page_content = page.get('text', {}).get('content', '<p>No content</p>')

            # Sanitize filename
            safe_filename = "".join(c for c in page_name if c.isalnum() or c in (' ', '-', '_')).strip()
            page_file = output_dir / f"{i:02d}_{safe_filename}.html"

            html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{page_name} - {journal_name}</title>
    {css_style}
</head>
<body>
    <div class="page-container">
        <div class="page-title">{page_name}</div>
        {page_content}
    </div>
    <div class="export-info">
        Exported from FoundryVTT on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
        Journal: {journal_name} | Page {i+1} of {len(pages)}
    </div>
</body>
</html>"""

            with open(page_file, 'w', encoding='utf-8') as f:
                f.write(html_content)

        logger.info(f"Exported to HTML directory: {output_dir} ({len(pages)} pages)")


def export_journal(
    journal_name: str,
    target: str = "local",
    output_format: str = "html",
    output_path: str = None,
    multi_file: bool = False
) -> None:
    """
    Export a journal from FoundryVTT to local file(s).

    Args:
        journal_name: Name of the journal to export
        target: Target environment ('local' or 'forge')
        output_format: Export format ('json', 'html')
        output_path: Path to save exported file(s)
        multi_file: For HTML export, create separate file per page
    """
    # Initialize client
    client = FoundryClient()

    # Find journal
    logger.info(f"Searching for journal: {journal_name}")
    journal = client.get_journal_by_name(journal_name)

    if not journal:
        logger.error(f"Journal not found: {journal_name}")
        sys.exit(1)

    # Get full journal data with pages
    journal_uuid = journal.get('uuid')
    if not journal_uuid:
        journal_id = journal.get('_id') or journal.get('id')
        if journal_id:
            journal_uuid = f"JournalEntry.{journal_id}"

    if not journal_uuid:
        logger.error(f"Could not determine UUID for journal: {journal_name}")
        sys.exit(1)

    logger.info(f"Retrieving journal data: {journal_uuid}")
    journal_data = client.get_journal(journal_uuid)

    # Determine output path
    if not output_path:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = Path(PROJECT_ROOT) / "output" / "exports" / timestamp
        output_dir.mkdir(parents=True, exist_ok=True)

        if output_format == "json":
            output_path = output_dir / f"{journal_name}.json"
        elif output_format == "html":
            if multi_file:
                output_path = output_dir / journal_name
            else:
                output_path = output_dir / f"{journal_name}.html"
    else:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

    # Export
    if output_format == "json":
        export_to_json(journal_data, str(output_path))
    elif output_format == "html":
        export_to_html(journal_data, str(output_path), single_file=not multi_file)
    else:
        logger.error(f"Unknown format: {output_format}")
        sys.exit(1)

    logger.info(f"Export complete!")


def main():
    """Main entry point for journal export script."""
    parser = argparse.ArgumentParser(
        description="Export journal entries from FoundryVTT to local files"
    )
    parser.add_argument(
        "journal_name",
        help="Name of the journal to export"
    )
    parser.add_argument(
        "--target",
        choices=["local", "forge"],
        default="local",
        help="Target FoundryVTT environment (default: local)"
    )
    parser.add_argument(
        "--format",
        choices=["json", "html"],
        default="html",
        help="Export format (default: html)"
    )
    parser.add_argument(
        "--output",
        help="Output path (default: output/exports/<timestamp>/)"
    )
    parser.add_argument(
        "--multi-file",
        action="store_true",
        help="For HTML: create separate file per page (default: single file)"
    )

    args = parser.parse_args()

    # Load environment variables
    load_dotenv()

    export_journal(
        journal_name=args.journal_name,
        target=args.target,
        output_format=args.format,
        output_path=args.output,
        multi_file=args.multi_file
    )


if __name__ == "__main__":
    main()
