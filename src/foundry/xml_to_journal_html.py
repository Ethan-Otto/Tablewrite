"""Convert XML documents to FoundryVTT journal-ready HTML."""

import os
import sys
from pathlib import Path
from typing import Dict, Any, List
import xml.etree.ElementTree as ET

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def xml_to_html(xml_element: ET.Element, level: int = 0) -> str:
    """
    Convert XML element to HTML recursively.

    Reuses logic from xml_to_html.py but returns string instead of writing file.

    Args:
        xml_element: XML element to convert
        level: Current heading level for nested sections

    Returns:
        HTML string
    """
    html_parts = []

    tag = xml_element.tag
    text = (xml_element.text or "").strip()

    # Map XML tags to HTML
    # title is always h1 (chapter title), heading starts at h2 and increments with nesting
    tag_map = {
        "chapter": ("", ""),  # Container, no HTML tag
        "title": ("<h1>", "</h1>"),
        "heading": (f"<h{min(level + 1, 6)}>", f"</h{min(level + 1, 6)}>"),
        "paragraph": ("<p>", "</p>"),
        "section": ("", ""),  # Container
        "list": ("<ul>", "</ul>"),
        "item": ("<li>", "</li>"),
        "emphasis": ("<em>", "</em>"),
        "strong": ("<strong>", "</strong>"),
    }

    open_tag, close_tag = tag_map.get(tag, ("", ""))

    if text and open_tag:
        html_parts.append(f"{open_tag}{text}{close_tag}")
    elif text:
        html_parts.append(text)

    # Process children
    for child in xml_element:
        child_level = level + 1 if tag == "section" else level
        html_parts.append(xml_to_html(child, child_level))

    return "\n".join(html_parts)


def convert_xml_to_journal_data(xml_file_path: str) -> Dict[str, Any]:
    """
    Convert an XML file to journal-ready data structure.

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

    # Parse XML
    tree = ET.parse(xml_file_path)
    root = tree.getroot()

    # Convert to HTML
    html_content = xml_to_html(root)

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
