"""Shared fixtures for image asset extraction tests."""
import asyncio
import os
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


@pytest.fixture
def test_pdf_path():
    """Path to test PDF with extractable images."""
    return os.path.join(PROJECT_ROOT, "data/pdfs/Strongholds_Followers_extraction_test.pdf")


@pytest.fixture(scope="session")
def session_test_pdf_path():
    """Session-scoped path to test PDF."""
    return os.path.join(PROJECT_ROOT, "data/pdfs/Strongholds_Followers_extraction_test.pdf")


@pytest.fixture
def test_output_dir(tmp_path):
    """Temporary directory for test outputs."""
    output_dir = tmp_path / "test_image_assets"
    output_dir.mkdir()
    return str(output_dir)


@pytest.fixture(scope="session")
def session_output_dir(tmp_path_factory):
    """Session-scoped temporary directory for shared extraction results."""
    output_dir = tmp_path_factory.mktemp("shared_image_assets")
    return str(output_dir)


@pytest.fixture
def check_api_key():
    """Verify Gemini API key is configured for integration tests."""
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.getenv("GeminiImageAPI")
    if not api_key:
        pytest.skip("GeminiImageAPI not configured in .env")
    return api_key


@pytest.fixture(scope="session")
def session_check_api_key():
    """Session-scoped API key check."""
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.getenv("GeminiImageAPI")
    if not api_key:
        pytest.skip("GeminiImageAPI not configured in .env")
    return api_key


@pytest.fixture(scope="session")
def shared_extracted_maps(session_test_pdf_path, session_output_dir, session_check_api_key):
    """Session-scoped fixture that runs extraction once and shares results.

    This dramatically reduces test time by avoiding repeated API calls.
    Returns tuple of (maps, output_dir) for tests to use.
    """
    from src.pdf_processing.image_asset_processing.extract_map_assets import extract_maps_from_pdf

    maps = asyncio.run(extract_maps_from_pdf(
        session_test_pdf_path,
        session_output_dir,
        chapter_name="Test Chapter"
    ))

    return maps, session_output_dir
