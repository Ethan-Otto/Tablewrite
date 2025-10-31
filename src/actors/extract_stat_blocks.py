"""Extract stat blocks from generated XML files."""

import logging
import xml.etree.ElementTree as ET
from typing import List, Dict
from pathlib import Path
from util.gemini import GeminiAPI
from .models import StatBlock
from .parse_stat_blocks import parse_stat_block_with_gemini

logger = logging.getLogger(__name__)


def extract_stat_blocks_from_xml(xml_file: str) -> List[Dict[str, str]]:
    """
    Extract raw stat block text from XML file.

    Finds all <stat_block name="...">raw text</stat_block> elements.

    Args:
        xml_file: Path to XML file

    Returns:
        List of dicts with 'name' and 'raw_text' keys

    Raises:
        FileNotFoundError: If XML file doesn't exist
        xml.etree.ElementTree.ParseError: If XML is malformed
    """
    xml_path = Path(xml_file)
    if not xml_path.exists():
        raise FileNotFoundError(f"XML file not found: {xml_file}")

    logger.debug(f"Extracting stat blocks from: {xml_file}")

    # Parse XML
    tree = ET.parse(xml_file)
    root = tree.getroot()

    # Find all stat_block elements
    stat_block_elements = root.findall(".//stat_block")

    stat_blocks = []
    for elem in stat_block_elements:
        name = elem.get("name")
        raw_text = elem.text.strip() if elem.text else ""

        if not name:
            logger.warning(f"Found stat_block without name attribute, skipping")
            continue

        if not raw_text:
            logger.warning(f"Stat block '{name}' has no text content, skipping")
            continue

        stat_blocks.append({
            "name": name,
            "raw_text": raw_text
        })

    logger.info(f"Extracted {len(stat_blocks)} stat block(s) from {xml_file}")
    return stat_blocks


def extract_and_parse_stat_blocks(
    xml_file: str,
    api: GeminiAPI = None
) -> List[StatBlock]:
    """
    Extract stat blocks from XML and parse into structured data.

    Args:
        xml_file: Path to XML file
        api: Optional GeminiAPI instance (creates new one if not provided)

    Returns:
        List of parsed StatBlock objects

    Raises:
        FileNotFoundError: If XML file doesn't exist
        ValueError: If parsing fails
    """
    if api is None:
        api = GeminiAPI()

    # Extract raw stat blocks
    raw_stat_blocks = extract_stat_blocks_from_xml(xml_file)

    if not raw_stat_blocks:
        logger.info(f"No stat blocks found in {xml_file}")
        return []

    # Parse each stat block
    parsed_stat_blocks = []
    for raw_block in raw_stat_blocks:
        try:
            stat_block = parse_stat_block_with_gemini(raw_block["raw_text"], api=api)
            parsed_stat_blocks.append(stat_block)
        except Exception as e:
            logger.error(f"Failed to parse stat block '{raw_block['name']}': {e}")
            # Continue with other stat blocks

    logger.info(f"Successfully parsed {len(parsed_stat_blocks)}/{len(raw_stat_blocks)} stat blocks")
    return parsed_stat_blocks
