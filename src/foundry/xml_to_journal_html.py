"""Convert XML documents to FoundryVTT journal-ready HTML.

This module reuses the core XML to HTML conversion from pdf_processing/xml_to_html.py
and adds only FoundryVTT-specific modifications if needed.
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, List

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the shared XML to HTML conversion function
from pdf_processing.xml_to_html import xml_to_html_content


def convert_xml_to_journal_data(xml_file_path: str) -> Dict[str, Any]:
    """
    Convert an XML file to journal-ready data structure.

    Uses the shared xml_to_html_content() function from pdf_processing module.
    FoundryVTT journals don't need navigation or full page structure, just content.

    Args:
        xml_file_path: Path to XML file

    Returns:
        Dictionary with journal entry data:
        {
            "name": "Chapter_Name",
            "html": "<h1>...</h1><p>...</p>",
            "metadata": {
                "source_file": "/path/to/file.xml",
                "chapter_number": "01",
                ...
            }
        }
    """
    xml_path = Path(xml_file_path)

    # Convert XML to HTML using shared function
    # include_footers=False to exclude headers/footers from journal pages
    html_content = xml_to_html_content(str(xml_path), include_footers=False)

    # Extract metadata from filename
    filename = xml_path.stem  # Without extension

    # Parse chapter number if present (e.g., "01_Chapter_Name" -> "01")
    parts = filename.split("_", 1)
    chapter_number = parts[0] if parts[0].isdigit() or (len(parts[0]) == 2 and parts[0][0].isdigit()) else None

    metadata = {
        "source_file": str(xml_path),
        "chapter_number": chapter_number,
        "filename": filename,
    }

    return {
        "name": filename,
        "html": html_content,
        "metadata": metadata,
    }


def convert_xml_directory_to_journals(xml_dir_path: str) -> List[Dict[str, Any]]:
    """
    Convert all XML files in a directory to journal data.

    Args:
        xml_dir_path: Path to directory containing XML files

    Returns:
        List of journal data dictionaries
    """
    xml_dir = Path(xml_dir_path)

    if not xml_dir.exists():
        raise ValueError(f"Directory does not exist: {xml_dir_path}")

    journals = []

    for xml_file in sorted(xml_dir.glob("*.xml")):
        journal_data = convert_xml_to_journal_data(str(xml_file))
        journals.append(journal_data)

    return journals
