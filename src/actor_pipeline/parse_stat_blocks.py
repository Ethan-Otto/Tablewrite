"""Parse D&D 5e stat blocks using Gemini."""

import logging
import json
from typing import Optional, List, Dict
from pathlib import Path
from util.gemini import GeminiAPI
from .models import StatBlock

logger = logging.getLogger(__name__)


def parse_stat_block_with_gemini(raw_text: str, api: Optional[GeminiAPI] = None) -> StatBlock:
    """
    Parse a D&D 5e stat block using Gemini.

    Args:
        raw_text: Raw stat block text
        api: Optional GeminiAPI instance (creates new one if not provided)

    Returns:
        Parsed StatBlock object

    Raises:
        ValueError: If parsing fails or result is invalid
        RuntimeError: If Gemini API call fails
    """
    if api is None:
        api = GeminiAPI()

    logger.debug(f"Parsing stat block (length: {len(raw_text)} chars)")

    # Construct parsing prompt
    prompt = f"""Parse this D&D 5e stat block into structured JSON.

Extract the following fields:
- name (string): Creature name
- armor_class (integer): AC value only (not the parenthetical armor type)
- hit_points (integer): HP value only (not the dice formula)
- challenge_rating (float): CR as decimal (1/4 = 0.25, 1/2 = 0.5)
- size (string, optional): Creature size
- type (string, optional): Creature type
- alignment (string, optional): Alignment
- abilities (object, optional): {{STR: int, DEX: int, CON: int, INT: int, WIS: int, CHA: int}}
- speed (string, optional): Speed description
- senses (string, optional): Senses description
- languages (string, optional): Languages
- traits (array of strings, optional): Each special trait as a separate string in array. If no traits, use empty array [].
- actions (array of strings, optional): Each action as a separate string in array. If no actions, use empty array [].

Return ONLY valid JSON with these exact field names. Do not include any markdown formatting or explanation.
If a field has no value, use empty array [] for list fields or null for other optional fields.

Stat block:
{raw_text}"""

    try:
        # Call Gemini
        response = api.generate_content(prompt)
        response_text = response.text.strip()

        # Remove markdown code blocks if present
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            # Remove first and last lines (``` markers)
            response_text = "\n".join(lines[1:-1])
            # Remove language identifier if present
            if response_text.startswith("json"):
                response_text = response_text[4:].strip()

        # Parse JSON
        parsed_data = json.loads(response_text)

        # Add raw_text to parsed data
        parsed_data["raw_text"] = raw_text

        # Create and validate StatBlock
        stat_block = StatBlock(**parsed_data)

        logger.info(f"Successfully parsed stat block: {stat_block.name} (CR {stat_block.challenge_rating})")
        return stat_block

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Gemini response as JSON: {e}")
        logger.debug(f"Response text: {response_text}")
        raise ValueError(f"Invalid JSON from Gemini: {e}") from e

    except Exception as e:
        logger.error(f"Failed to parse stat block: {e}")
        raise RuntimeError(f"Stat block parsing failed: {e}") from e


def extract_stat_blocks_from_document(doc: 'XMLDocument') -> List[Dict[str, str]]:
    """
    Extract raw stat block text from XMLDocument.

    Finds all stat_block content elements across all pages.

    Args:
        doc: XMLDocument instance to extract from

    Returns:
        List of dicts with 'name' and 'raw_text' keys

    Example:
        >>> from models import XMLDocument
        >>> doc = XMLDocument.from_xml(xml_string)
        >>> stat_blocks = extract_stat_blocks_from_document(doc)
        >>> for block in stat_blocks:
        ...     print(f"{block['name']}: {len(block['raw_text'])} chars")
    """
    from models.xml_document import StatBlockRaw

    stat_blocks = []

    # Iterate through all pages and content
    for page in doc.pages:
        for content in page.content:
            # Check if this is a stat_block content type
            if content.type == "stat_block":
                # Extract StatBlockRaw data
                stat_block_raw = content.data
                if isinstance(stat_block_raw, StatBlockRaw):
                    # Parse the XML element to extract text content
                    import xml.etree.ElementTree as ET
                    elem = ET.fromstring(stat_block_raw.xml_element)
                    raw_text = elem.text.strip() if elem.text else ""

                    if not raw_text:
                        logger.warning(f"Stat block '{stat_block_raw.name}' has no text content, skipping")
                        continue

                    stat_blocks.append({
                        "name": stat_block_raw.name,
                        "raw_text": raw_text
                    })

    logger.info(f"Extracted {len(stat_blocks)} stat block(s) from XMLDocument")
    return stat_blocks


def extract_stat_blocks_from_xml_file(xml_file: str) -> List[Dict[str, str]]:
    """
    Extract raw stat block text from XML file using XMLDocument.

    Convenience wrapper that loads XML file, parses to XMLDocument,
    and extracts stat blocks.

    Args:
        xml_file: Path to XML file

    Returns:
        List of dicts with 'name' and 'raw_text' keys

    Raises:
        FileNotFoundError: If XML file doesn't exist
        xml.etree.ElementTree.ParseError: If XML is malformed

    Example:
        >>> stat_blocks = extract_stat_blocks_from_xml_file("chapter_1.xml")
        >>> for block in stat_blocks:
        ...     print(block['name'])
    """
    from models import XMLDocument

    xml_path = Path(xml_file)
    if not xml_path.exists():
        raise FileNotFoundError(f"XML file not found: {xml_file}")

    logger.debug(f"Extracting stat blocks from: {xml_file}")

    # Load and parse XML to XMLDocument
    with open(xml_path, 'r') as f:
        xml_string = f.read()
    doc = XMLDocument.from_xml(xml_string)

    # Extract stat blocks from document
    return extract_stat_blocks_from_document(doc)
