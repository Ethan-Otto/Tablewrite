"""Shared fixtures for image asset extraction tests."""
import os
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

@pytest.fixture
def test_pdf_path():
    """Path to test PDF with extractable images."""
    return os.path.join(PROJECT_ROOT, "data/pdfs/Strongholds_Followers_extraction_test.pdf")

@pytest.fixture
def test_output_dir(tmp_path):
    """Temporary directory for test outputs."""
    output_dir = tmp_path / "test_image_assets"
    output_dir.mkdir()
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
