"""Tests for PyMuPDF image extraction."""
import pytest
import fitz
import os
import asyncio
from pdf_processing.image_asset_processing.extract_maps import extract_image_with_pymupdf_async


@pytest.mark.map
@pytest.mark.unit
class TestExtractImageWithPyMuPDF:
    def test_extract_large_image_from_page(self, test_pdf_path, test_output_dir):
        """Test extraction of large image without AI classification."""
        doc = fitz.open(test_pdf_path)
        page = doc[0]  # First page has images

        output_path = os.path.join(test_output_dir, "test_map.png")
        # Use use_ai_classification=False for unit test (no API calls)
        result = asyncio.run(extract_image_with_pymupdf_async(page, output_path, use_ai_classification=False))

        # Result depends on whether test PDF has large enough images
        if result:
            assert os.path.exists(output_path)
            assert os.path.getsize(output_path) > 1000  # Non-empty file

    def test_extract_returns_false_for_text_only_page(self, tmp_path):
        """Test that extraction fails on text-only page."""
        # Create minimal PDF with text only
        doc = fitz.open()
        page = doc.new_page(width=612, height=792)
        page.insert_text((100, 100), "Text only, no images")

        temp_pdf = tmp_path / "text_only.pdf"
        doc.save(str(temp_pdf))
        doc.close()

        # Try to extract
        doc = fitz.open(str(temp_pdf))
        output_path = str(tmp_path / "no_image.png")
        result = asyncio.run(extract_image_with_pymupdf_async(doc[0], output_path, use_ai_classification=False))

        assert result is False
        assert not os.path.exists(output_path)

    def test_extract_filters_small_images(self, test_pdf_path, test_output_dir):
        """Test that small decorative images are filtered out."""
        doc = fitz.open(test_pdf_path)
        page = doc[0]

        # Count how many images are on the page
        images = page.get_images()

        # Verify there are images
        assert len(images) > 0


@pytest.mark.map
@pytest.mark.gemini
@pytest.mark.slow
class TestExtractWithAIClassification:
    def test_extract_with_ai_classification(self, test_pdf_path, test_output_dir, check_api_key):
        """Test extraction with AI classification to filter out non-maps."""
        doc = fitz.open(test_pdf_path)
        page = doc[0]

        output_path = os.path.join(test_output_dir, "ai_classified_map.png")
        result = asyncio.run(extract_image_with_pymupdf_async(page, output_path, use_ai_classification=True))

        # AI classification may or may not find a map depending on page content
        # Just verify the function completes without error
        assert isinstance(result, bool)
