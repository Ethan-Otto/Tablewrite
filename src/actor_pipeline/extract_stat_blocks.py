"""Extract stat blocks from generated XML files."""

import logging
from typing import List
from concurrent.futures import ThreadPoolExecutor, as_completed
from util.gemini import GeminiAPI
from .models import StatBlock
from .parse_stat_blocks import (
    parse_stat_block_with_gemini,
    extract_stat_blocks_from_xml_file
)

logger = logging.getLogger(__name__)

# Max parallel Gemini API calls
MAX_WORKERS = 5


def extract_and_parse_stat_blocks(
    xml_file: str,
    api: GeminiAPI = None
) -> List[StatBlock]:
    """
    Extract stat blocks from XML and parse into structured data.

    Uses XMLDocument model for parsing.

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

    # Extract raw stat blocks using XMLDocument
    raw_stat_blocks = extract_stat_blocks_from_xml_file(xml_file)

    if not raw_stat_blocks:
        logger.info(f"No stat blocks found in {xml_file}")
        return []

    logger.info(f"Parsing {len(raw_stat_blocks)} stat blocks in parallel (max {MAX_WORKERS} workers)...")

    # Parse each stat block in parallel using ThreadPoolExecutor
    parsed_stat_blocks = []

    def parse_single_stat_block(raw_block):
        """Parse a single stat block and return result or None."""
        try:
            return parse_stat_block_with_gemini(raw_block["raw_text"], api=api)
        except Exception as e:
            logger.error(f"Failed to parse stat block '{raw_block['name']}': {e}")
            return None

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all parsing tasks
        future_to_block = {
            executor.submit(parse_single_stat_block, raw_block): raw_block
            for raw_block in raw_stat_blocks
        }

        # Collect results as they complete
        for future in as_completed(future_to_block):
            result = future.result()
            if result is not None:
                parsed_stat_blocks.append(result)

    logger.info(f"Successfully parsed {len(parsed_stat_blocks)}/{len(raw_stat_blocks)} stat blocks")
    return parsed_stat_blocks
