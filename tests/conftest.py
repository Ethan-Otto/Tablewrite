"""
Shared pytest fixtures for D&D Module Converter tests.
"""

import os
import shutil
import sys
import pytest
from pathlib import Path


def pytest_addoption(parser):
    """Add --full flag to run entire test suite"""
    parser.addoption(
        "--full",
        action="store_true",
        default=False,
        help="Run full test suite (skip smoke-only mode)"
    )


def pytest_configure(config):
    """Configure test run based on flags"""
    if config.getoption("--full"):
        # Only clear default marker if no explicit -m flag was provided
        # Check if markexpr is the default from pytest.ini
        if config.option.markexpr == "smoke or (not integration and not slow)":
            config.option.markexpr = ""  # Run all tests


def pytest_sessionfinish(session, exitstatus):
    """Auto-escalate to full suite if default fast tests fail"""
    # Check if auto-escalation is enabled
    auto_escalate = os.getenv("AUTO_ESCALATE", "true").lower() == "true"

    # Check if we're already running full suite or using default markers
    is_full_run = session.config.getoption("--full")
    is_default_markers = session.config.option.markexpr == "smoke or (not integration and not slow)"

    # Only escalate if: default markers + failures + auto-escalate enabled
    if not is_full_run and is_default_markers and exitstatus != 0 and auto_escalate:
        print("\n" + "="*70)
        print("⚠️  Fast tests failed. Running full test suite (including slow/integration)...")
        print("="*70 + "\n")

        # Re-run pytest with full suite
        sys.exit(pytest.main(["--full"] + sys.argv[1:]))


# Project root
PROJECT_ROOT = Path(__file__).parent.parent

# Test paths
TEST_PDF_PATH = PROJECT_ROOT / "data" / "pdfs" / "Lost_Mine_of_Phandelver_test.pdf"
FULL_PDF_PATH = PROJECT_ROOT / "data" / "pdfs" / "Lost_Mine_of_Phandelver.pdf"
TEST_OUTPUT_DIR = PROJECT_ROOT / "tests" / "output"
TEST_RUNS_DIR = PROJECT_ROOT / "tests" / "test_runs"


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


@pytest.fixture(scope="session")
def integration_test_output_dir():
    """
    Return a persistent output directory for integration tests.
    Creates a single timestamped directory under tests/test_runs/ for the
    entire test session to preserve artifacts for inspection.
    All tests in the session share this directory.
    """
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = TEST_RUNS_DIR / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


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
def check_foundry_credentials():
    """Check if FoundryVTT API credentials are available."""
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")

    relay_url = os.getenv("FOUNDRY_RELAY_URL")
    api_key = os.getenv("FOUNDRY_LOCAL_API_KEY")
    client_id = os.getenv("FOUNDRY_LOCAL_CLIENT_ID")

    if not all([relay_url, api_key, client_id]):
        pytest.skip("FoundryVTT credentials not found. Set FOUNDRY_RELAY_URL, FOUNDRY_LOCAL_API_KEY, and FOUNDRY_LOCAL_CLIENT_ID in .env file.")

    return {
        "relay_url": relay_url,
        "api_key": api_key,
        "client_id": client_id
    }


@pytest.fixture(scope="session")
def sample_xml_content():
    """Return sample XML content for testing."""
    return """<Chapter_01_Introduction>
    <page number="1">
        <section>Introduction</section>
        <p>This is a test paragraph with some **bold** text and *italic* text.</p>
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
