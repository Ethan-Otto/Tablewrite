"""
Tests for src/pdf_processing/get_toc.py

Tests table of contents extraction including:
- TOC structure validation
- Level hierarchy
- Page number accuracy
- TOC presence detection

NOTE: These tests use the FULL PDF (Lost_Mine_of_Phandelver.pdf) because
the test PDF has a simplified TOC structure.
"""

import pytest
import fitz
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class TestTOCExtraction:
    """Test table of contents extraction."""

    @pytest.mark.requires_pdf
    def test_toc_extraction_full_pdf(self, full_pdf_path):
        """Test TOC extraction from the full PDF."""
        doc = fitz.open(full_pdf_path)
        toc = doc.get_toc()
        doc.close()

        assert len(toc) > 0, "Full PDF should have a table of contents"

    def test_toc_structure(self, full_pdf_path):
        """Test that TOC has proper structure (level, title, page)."""
        doc = fitz.open(full_pdf_path)
        toc = doc.get_toc()
        doc.close()

        for item in toc:
            assert len(item) == 3, "TOC item should have 3 elements: (level, title, page)"
            level, title, page = item

            assert isinstance(level, int), "Level should be an integer"
            assert isinstance(title, str), "Title should be a string"
            assert isinstance(page, int), "Page should be an integer"

            assert level > 0, "Level should be positive"
            assert len(title.strip()) > 0, "Title should not be empty"
            assert page > 0, "Page number should be positive"

    def test_toc_level_hierarchy(self, full_pdf_path):
        """Test that TOC levels form a valid hierarchy."""
        doc = fitz.open(full_pdf_path)
        toc = doc.get_toc()
        doc.close()

        if len(toc) > 0:
            levels = [item[0] for item in toc]

            # All levels should be positive integers
            assert all(isinstance(l, int) and l > 0 for l in levels)

            # Check that level jumps are reasonable (no jumping from 1 to 5, for example)
            for i in range(len(levels) - 1):
                level_diff = abs(levels[i + 1] - levels[i])
                assert level_diff <= 1, "TOC levels should only change by 0 or 1"

    def test_toc_page_numbers_increasing(self, full_pdf_path):
        """Test that TOC page numbers generally increase."""
        doc = fitz.open(full_pdf_path)
        toc = doc.get_toc()
        total_pages = len(doc)
        doc.close()

        page_numbers = [item[2] for item in toc]

        # Page numbers should be within document bounds
        assert all(1 <= p <= total_pages for p in page_numbers), \
            "All page numbers should be within document bounds"

        # Check that page numbers are mostly increasing (allowing for some exceptions)
        increasing_pairs = sum(1 for i in range(len(page_numbers) - 1)
                               if page_numbers[i] <= page_numbers[i + 1])
        total_pairs = len(page_numbers) - 1

        if total_pairs > 0:
            increasing_ratio = increasing_pairs / total_pairs
            assert increasing_ratio >= 0.8, \
                "At least 80% of page numbers should be in increasing order"

    def test_toc_contains_expected_sections(self, full_pdf_path):
        """Test that TOC contains expected D&D module sections."""
        doc = fitz.open(full_pdf_path)
        toc = doc.get_toc()
        doc.close()

        toc_titles = [item[1].lower() for item in toc]
        toc_text = " ".join(toc_titles)

        # Check for common D&D module sections
        expected_keywords = ["introduction", "part", "appendix"]

        found_keywords = [kw for kw in expected_keywords if kw in toc_text]
        assert len(found_keywords) > 0, \
            f"TOC should contain at least one of: {expected_keywords}"

    def test_toc_no_duplicates(self, full_pdf_path):
        """Test that TOC doesn't have exact duplicate entries."""
        doc = fitz.open(full_pdf_path)
        toc = doc.get_toc()
        doc.close()

        # Create tuples of (title, page) to check for duplicates
        entries = [(item[1], item[2]) for item in toc]

        # Check for duplicates
        seen = set()
        duplicates = []
        for entry in entries:
            if entry in seen:
                duplicates.append(entry)
            seen.add(entry)

        assert len(duplicates) == 0, \
            f"TOC should not have duplicate entries. Found: {duplicates}"


class TestTOCWithTestPDF:
    """Test TOC functionality with the smaller test PDF."""

    def test_test_pdf_has_toc(self, test_pdf_path):
        """Test that the test PDF has a TOC."""
        doc = fitz.open(test_pdf_path)
        toc = doc.get_toc()
        doc.close()

        # Test PDF should have a TOC (even if simplified)
        assert isinstance(toc, list), "TOC should be a list"

    def test_empty_toc_handling(self, test_output_dir):
        """Test handling of PDFs with no TOC."""
        # Create a minimal PDF with no TOC
        minimal_pdf = test_output_dir / "minimal.pdf"
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((100, 100), "Test page")
        doc.save(minimal_pdf)
        doc.close()

        # Open and check TOC
        doc = fitz.open(minimal_pdf)
        toc = doc.get_toc()
        doc.close()

        # Should return empty list, not error
        assert isinstance(toc, list)
        assert len(toc) == 0


class TestTOCPageMapping:
    """Test that TOC page numbers map correctly to actual pages."""

    @pytest.mark.requires_pdf
    def test_toc_pages_exist(self, full_pdf_path):
        """Test that all TOC page references exist in the document."""
        doc = fitz.open(full_pdf_path)
        toc = doc.get_toc()
        total_pages = len(doc)

        for level, title, page in toc:
            assert 1 <= page <= total_pages, \
                f"TOC entry '{title}' references page {page}, but document only has {total_pages} pages"

        doc.close()

    def test_toc_pages_have_content(self, full_pdf_path):
        """Test that pages referenced in TOC actually have content."""
        doc = fitz.open(full_pdf_path)
        toc = doc.get_toc()

        # Check first few TOC entries
        for level, title, page_num in toc[:5]:  # Check first 5 entries
            # Convert 1-based page number to 0-based index
            page_index = page_num - 1

            if 0 <= page_index < len(doc):
                page = doc[page_index]
                text = page.get_text().strip()

                assert len(text) > 0, \
                    f"TOC entry '{title}' on page {page_num} should have content"

        doc.close()
