"""Shared fixtures for image asset extraction tests."""
import asyncio
import os
import pytest
from config import PROJECT_ROOT


@pytest.fixture
def test_pdf_path():
    """
    Path to the test PDF that contains images suitable for extraction.
    
    Returns:
        str: Filesystem path to the test PDF `data/pdfs/Strongholds_Followers_extraction_test.pdf` within the project root.
    """
    return str(PROJECT_ROOT / "data" / "pdfs" / "Strongholds_Followers_extraction_test.pdf")


@pytest.fixture(scope="session")
def session_test_pdf_path():
    """
    Session-scoped path to the test PDF used for image asset extraction tests.
    
    Returns:
        str: Filesystem path to Strongholds_Followers_extraction_test.pdf inside the project's data/pdfs directory.
    """
    return str(PROJECT_ROOT / "data" / "pdfs" / "Strongholds_Followers_extraction_test.pdf")


@pytest.fixture
def test_output_dir(tmp_path):
    """
    Provide a temporary directory named "test_image_assets" for test outputs.
    
    Returns:
        output_dir (str): String path to the created temporary directory.
    """
    output_dir = tmp_path / "test_image_assets"
    output_dir.mkdir()
    return str(output_dir)


@pytest.fixture(scope="session")
def session_output_dir(tmp_path_factory):
    """
    Create a session-scoped temporary directory for shared image extraction results.
    
    Returns:
        output_dir (str): Path to the created temporary directory.
    """
    output_dir = tmp_path_factory.mktemp("shared_image_assets")
    return str(output_dir)


@pytest.fixture
def check_api_key():
    """
    Ensure the GeminiImageAPI key is available for integration tests.
    
    Loads environment variables from a .env file and calls pytest.skip if the GeminiImageAPI variable is not set.
    
    Returns:
        api_key (str): The GeminiImageAPI value from the environment.
    """
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.getenv("GeminiImageAPI")
    if not api_key:
        pytest.skip("GeminiImageAPI not configured in .env")
    return api_key


@pytest.fixture(scope="session")
def session_check_api_key():
    """
    Ensure the GeminiImageAPI key is available for the test session.
    
    Loads environment variables from a .env file and returns the `GeminiImageAPI` value. If the key is not present, calls `pytest.skip` to skip the test session.
    
    Returns:
        str: The configured GeminiImageAPI key.
    """
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.getenv("GeminiImageAPI")
    if not api_key:
        pytest.skip("GeminiImageAPI not configured in .env")
    return api_key


@pytest.fixture(scope="session")
def shared_extracted_maps(session_test_pdf_path, session_output_dir, session_check_api_key):
    """
    Run map extraction once for the test session and provide the extracted maps alongside the shared output directory.
    
    Returns:
        tuple: (maps, output_dir) where `maps` are the extracted map assets (in the format returned by `extract_maps_from_pdf`) and `output_dir` is the session-scoped output directory path.
    """
    from pdf_processing.image_asset_processing.extract_map_assets import extract_maps_from_pdf

    maps = asyncio.run(extract_maps_from_pdf(
        session_test_pdf_path,
        session_output_dir,
        chapter_name="Test Chapter"
    ))

    return maps, session_output_dir