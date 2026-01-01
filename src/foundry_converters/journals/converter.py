"""Convert XML documents to FoundryVTT journal-ready HTML.

This module reuses the core XML to HTML conversion from pdf_processing/xml_to_html.py
and adds only FoundryVTT-specific modifications if needed.
"""

import re
from pathlib import Path
from typing import Any

from pdf_processing.xml_to_html import xml_to_html_content


def convert_xml_to_journal_data(xml_file_path: str) -> dict[str, Any]:
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
    chapter_number = (
        parts[0]
        if parts[0].isdigit() or (len(parts[0]) == 2 and parts[0][0].isdigit())
        else None
    )

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


def convert_xml_directory_to_journals(xml_dir_path: str) -> list[dict[str, Any]]:
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


def add_uuid_links(html: str, entity_refs: dict[str, str]) -> str:
    """
    Replace entity mentions in HTML with @UUID links to FoundryVTT entities.

    This function searches for entity names in the HTML and replaces them with
    clickable @UUID links. Works for ANY FoundryVTT entity type: Items, Actors,
    Scenes, Journals, RollTables, etc.

    Args:
        html: Journal HTML content
        entity_refs: Dictionary mapping entity names to their UUIDs
                     Works for any entity type:
                     - Items: {"Hat of Disguise": "Compendium.dnd5e.items.abc123"}
                     - Actors: {"Klarg": "Actor.xyz789"}
                     - Scenes: {"Cragmaw Cave": "Scene.map456"}
                     - Journals: {"Chapter 1": "JournalEntry.abc"}

    Returns:
        HTML with entity mentions replaced by @UUID[uuid]{name} links

    Example:
        >>> html = "<p>You find a Hat of Disguise and meet Klarg.</p>"
        >>> entity_refs = {
        ...     "Hat of Disguise": "Compendium.dnd5e.items.abc123",
        ...     "Klarg": "Actor.xyz789"
        ... }
        >>> add_uuid_links(html, entity_refs)
        '<p>You find a @UUID[Compendium.dnd5e.items.abc123]{Hat of Disguise} and meet @UUID[Actor.xyz789]{Klarg}.</p>'

    Notes:
        - Links are case-sensitive
        - Longer entity names are processed first to avoid partial matches
        - Entities are only linked once per occurrence (no double-linking)
        - Existing @UUID links are preserved
        - Works for all FoundryVTT entity types (Items, Actors, Scenes, etc.)
    """
    if not entity_refs:
        return html

    # Sort entities by length (longest first) to avoid partial matches
    # e.g., "Longsword +1" before "Longsword"
    sorted_entities = sorted(entity_refs.items(), key=lambda x: len(x[0]), reverse=True)

    modified_html = html

    for entity_name, uuid in sorted_entities:
        # Escape special regex characters in entity name
        escaped_name = re.escape(entity_name)

        # Pattern to match entity name NOT already inside @UUID[...]
        # Negative lookbehind: not preceded by @UUID[...
        # Negative lookahead: not followed by ...] or inside {...}
        pattern = rf"(?<!@UUID\[)(?<!\{{)\b({escaped_name})\b(?!\}})"

        # Replace with @UUID link
        replacement = rf"@UUID[{uuid}]{{\1}}"

        modified_html = re.sub(pattern, replacement, modified_html)

    return modified_html
