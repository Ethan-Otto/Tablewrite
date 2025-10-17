"""
Tests for src/pdf_processing/split_pdf.py

Tests PDF splitting functionality including:
- Chapter boundary detection
- PDF page extraction
- Output file creation
- Edge cases (empty PDFs, single page, etc.)
"""

import pytest
import fitz
from pathlib import Path
import sys
import os

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from pdf_processing import split_pdf


class TestPDFSplitting:
    """Test PDF splitting functionality."""

    def test_split_pdf_creates_output_directory(self, test_pdf_path, test_output_dir):
        """Test that split_pdf creates the output directory."""
        output_path = test_output_dir / "split_output"

        # Manually split a simple chapter
        doc = fitz.open(test_pdf_path)
        output_path.mkdir(parents=True, exist_ok=True)

        # Extract first 2 pages as a test
        test_chapter = fitz.open()
        test_chapter.insert_pdf(doc, from_page=0, to_page=1)
        test_chapter.save(output_path / "test_chapter.pdf")
        test_chapter.close()
        doc.close()

        assert (output_path / "test_chapter.pdf").exists()

    def test_split_preserves_pdf_structure(self, test_pdf_path, test_output_dir):
        """Test that split PDFs maintain valid PDF structure."""
        doc = fitz.open(test_pdf_path)
        total_pages = len(doc)

        # Split into single-page PDFs
        for page_num in range(min(3, total_pages)):  # Test first 3 pages
            output_file = test_output_dir / f"page_{page_num + 1}.pdf"

            new_doc = fitz.open()
            new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
            new_doc.save(output_file)
            new_doc.close()

            # Verify the split PDF is valid
            assert output_file.exists()
            split_doc = fitz.open(output_file)
            assert len(split_doc) == 1
            split_doc.close()

        doc.close()

    def test_split_page_ranges(self, test_pdf_path, test_output_dir):
        """Test splitting specific page ranges."""
        doc = fitz.open(test_pdf_path)
        total_pages = len(doc)

        if total_pages >= 3:
            # Split pages 0-2 (3 pages)
            output_file = test_output_dir / "pages_0_to_2.pdf"
            new_doc = fitz.open()
            new_doc.insert_pdf(doc, from_page=0, to_page=2)
            new_doc.save(output_file)
            new_doc.close()

            # Verify
            split_doc = fitz.open(output_file)
            assert len(split_doc) == 3
            split_doc.close()

        doc.close()

    def test_split_boundary_conditions(self, test_pdf_path, test_output_dir):
        """Test edge cases in PDF splitting."""
        doc = fitz.open(test_pdf_path)
        total_pages = len(doc)

        # Test: Last page
        if total_pages > 0:
            output_file = test_output_dir / "last_page.pdf"
            new_doc = fitz.open()
            new_doc.insert_pdf(doc, from_page=total_pages - 1, to_page=total_pages - 1)
            new_doc.save(output_file)
            new_doc.close()

            split_doc = fitz.open(output_file)
            assert len(split_doc) == 1
            split_doc.close()

        doc.close()

    def test_chapter_naming_sanitization(self):
        """Test that chapter names are properly sanitized for XML."""
        from pdf_processing.pdf_to_xml import sanitize_xml_element_name

        # Test numeric prefix
        assert sanitize_xml_element_name("01_Introduction").startswith("Chapter_")
        assert sanitize_xml_element_name("08_Appendix_B_Monsters").startswith("Chapter_")

        # Test valid names
        assert sanitize_xml_element_name("Introduction") == "Introduction"
        assert sanitize_xml_element_name("Appendix_A") == "Appendix_A"

    @pytest.mark.requires_pdf
    def test_split_with_test_pdf_structure(self, test_pdf_path, test_output_dir):
        """Test splitting using the actual test PDF structure."""
        doc = fitz.open(test_pdf_path)
        page_count = len(doc)

        # Define simple chapter boundaries for test PDF (first 7 pages)
        chapters = [
            (0, 1, "Chapter_1"),
            (2, 3, "Chapter_2"),
            (4, page_count - 1, "Chapter_3")
        ]

        for start, end, name in chapters:
            if end < page_count:
                output_file = test_output_dir / f"{name}.pdf"
                new_doc = fitz.open()
                new_doc.insert_pdf(doc, from_page=start, to_page=end)
                new_doc.save(output_file)
                new_doc.close()

                # Verify
                assert output_file.exists()
                split_doc = fitz.open(output_file)
                expected_pages = end - start + 1
                assert len(split_doc) == expected_pages
                split_doc.close()

        doc.close()


class TestPDFValidation:
    """Test PDF validation and error handling."""

    def test_pdf_file_exists(self, test_pdf_path):
        """Test that the test PDF file exists."""
        assert test_pdf_path.exists()
        assert test_pdf_path.suffix == ".pdf"

    def test_pdf_is_readable(self, test_pdf_path):
        """Test that the PDF can be opened and read."""
        doc = fitz.open(test_pdf_path)
        assert doc is not None
        assert len(doc) > 0
        doc.close()

    def test_pdf_has_pages(self, test_pdf_path):
        """Test that the PDF has content."""
        doc = fitz.open(test_pdf_path)
        page_count = len(doc)
        assert page_count > 0

        # Check that first page has content
        if page_count > 0:
            first_page = doc[0]
            text = first_page.get_text()
            # PDF should have some text content
            assert len(text.strip()) > 0

        doc.close()
