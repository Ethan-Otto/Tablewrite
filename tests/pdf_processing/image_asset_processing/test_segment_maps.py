"""Tests for Gemini Imagen segmentation."""
import pytest
import fitz
from src.pdf_processing.image_asset_processing.segment_maps import (
    segment_with_imagen,
    SegmentationError
)


@pytest.mark.integration
@pytest.mark.slow
class TestSegmentWithImagen:
    def test_segmentation_raises_error_on_invalid_output(self, test_pdf_path, test_output_dir, check_api_key):
        """Test that segmentation validates output and raises error if invalid."""
        # This is a placeholder - actual implementation will test with real Gemini Imagen
        # For now, just verify the function exists and has correct signature
        doc = fitz.open(test_pdf_path)
        page = doc[0]
        pix = page.get_pixmap(dpi=150)
        page_image = pix.pil_tobytes(format="PNG")

        output_path = f"{test_output_dir}/segmented_map.png"

        # This test will be implemented once Gemini Imagen segmentation is working
        # For now, expect NotImplementedError
        with pytest.raises(NotImplementedError):
            segment_with_imagen(page_image, "navigation_map", output_path)
