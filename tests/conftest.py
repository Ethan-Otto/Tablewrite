"""
Shared pytest fixtures for D&D Module Converter tests.
"""

import os
import shutil
import pytest
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).parent.parent

# Test paths
TEST_PDF_PATH = PROJECT_ROOT / "data" / "pdfs" / "Lost_Mine_of_Phandelver_test.pdf"
FULL_PDF_PATH = PROJECT_ROOT / "data" / "pdfs" / "Lost_Mine_of_Phandelver.pdf"
TEST_OUTPUT_DIR = PROJECT_ROOT / "tests" / "output"


@pytest.fixture(scope="session")
def project_root():
    """Return the project root directory."""
    return PROJECT_ROOT


@pytest.fixture(scope="session")
def test_pdf_path():
    """Return path to the test PDF file."""
    if not TEST_PDF_PATH.exists():
        pytest.skip(f"Test PDF not found: {TEST_PDF_PATH}")
    return TEST_PDF_PATH


@pytest.fixture(scope="session")
def full_pdf_path():
    """Return path to the full PDF file (for TOC tests)."""
    if not FULL_PDF_PATH.exists():
        pytest.skip(f"Full PDF not found: {FULL_PDF_PATH}")
    return FULL_PDF_PATH


@pytest.fixture(scope="function")
def test_output_dir(tmp_path):
    """
    Return a clean test output directory for each test.
    Uses pytest's tmp_path fixture which is automatically cleaned up.
    """
    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


@pytest.fixture(scope="session")
def persistent_test_output_dir():
    """
    Return the persistent tests/output directory.
    This directory is NOT cleaned up automatically.
    """
    TEST_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return TEST_OUTPUT_DIR


@pytest.fixture(scope="function")
def clean_test_output():
    """
    Clean the persistent tests/output directory before each test.
    Use this when you want to inspect output after test runs.
    """
    if TEST_OUTPUT_DIR.exists():
        shutil.rmtree(TEST_OUTPUT_DIR)
    TEST_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    yield TEST_OUTPUT_DIR
    # Don't clean up after - keep for inspection


@pytest.fixture(scope="session")
def check_api_key():
    """Check if Gemini API key is available."""
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
    api_key = os.getenv("GeminiImageAPI")
    if not api_key:
        pytest.skip("Gemini API key not found. Set GeminiImageAPI in .env file.")
    return api_key


@pytest.fixture(scope="session")
def sample_xml_content():
    """Return sample XML content for testing."""
    return """<Chapter_01_Introduction>
    <page number="1">
        <heading>Introduction</heading>
        <paragraph>This is a test paragraph with some **bold** text and *italic* text.</paragraph>
        <list>
            <item>First item</item>
            <item>Second item</item>
        </list>
    </page>
</Chapter_01_Introduction>"""


@pytest.fixture(scope="session")
def sample_malformed_xml():
    """Return malformed XML for testing error handling."""
    return """<Chapter_01_Introduction>
    <page number="1">
        <heading>Introduction</heading>
        <paragraph>Unclosed paragraph
        <list>
            <item>First item
        </list>
    </page>"""
