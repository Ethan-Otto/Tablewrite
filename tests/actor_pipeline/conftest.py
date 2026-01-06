"""Shared fixtures for actor pipeline tests.

These fixtures cache expensive Gemini API calls so multiple tests can reuse results.
"""

import pytest
from pathlib import Path


@pytest.fixture(scope="module")
def sample_chapter_fixture_path():
    """Path to the sample chapter XML with stat blocks and NPCs."""
    return Path(__file__).parent / "fixtures" / "sample_chapter_with_npcs.xml"


@pytest.fixture(scope="module")
def sample_chapter_xml_content(sample_chapter_fixture_path):
    """Load the sample chapter XML content."""
    return sample_chapter_fixture_path.read_text()


@pytest.fixture(scope="module")
def shared_stat_blocks(check_api_key, sample_chapter_fixture_path):
    """
    Extract stat blocks ONCE and share across all tests in the module.

    This fixture caches the expensive Gemini API call for stat block extraction.
    Multiple tests can use these results without re-calling the API.
    """
    from actor_pipeline.extract_stat_blocks import extract_and_parse_stat_blocks

    stat_blocks = extract_and_parse_stat_blocks(str(sample_chapter_fixture_path))
    return stat_blocks


@pytest.fixture(scope="module")
def shared_npcs(check_api_key, sample_chapter_xml_content):
    """
    Extract NPCs ONCE and share across all tests in the module.

    This fixture caches the expensive Gemini API call for NPC extraction.
    Multiple tests can use these results without re-calling the API.
    """
    from actor_pipeline.extract_npcs import identify_npcs_with_gemini

    npcs = identify_npcs_with_gemini(sample_chapter_xml_content)
    return npcs


@pytest.fixture(scope="module")
def shared_extraction_results(shared_stat_blocks, shared_npcs):
    """
    Combined fixture providing both stat blocks and NPCs.

    Use this when tests need both extracted results.
    """
    return {
        "stat_blocks": shared_stat_blocks,
        "npcs": shared_npcs
    }
