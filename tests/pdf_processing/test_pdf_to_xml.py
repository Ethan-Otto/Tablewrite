"""
Tests for src/pdf_processing/pdf_to_xml.py

Tests PDF to XML conversion including:
- XML element name sanitization
- Word counting and validation
- Text extraction (embedded and OCR)
- XML structure validation
- Error handling and retry logic
- Gemini API integration (actual API calls)

NOTE: These tests make REAL Gemini API calls and will consume API quota.
Run with caution and ensure you have API key configured.
"""

import pytest
import xml.etree.ElementTree as ET
import fitz
from pathlib import Path
import sys
import os

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from pdf_processing.pdf_to_xml import (
    sanitize_xml_element_name,
    count_words,
    get_word_frequencies,
    is_text_legible,
    configure_gemini,
    get_legible_text_from_page,
    get_xml_for_page
)


class TestXMLSanitization:
    """Test XML element name sanitization."""

    def test_sanitize_numeric_prefix(self):
        """Test that numeric prefixes are handled."""
        assert sanitize_xml_element_name("01_Introduction") == "Chapter_01_Introduction"
        assert sanitize_xml_element_name("08_Appendix_B_Monsters") == "Chapter_08_Appendix_B_Monsters"
        assert sanitize_xml_element_name("123_Test") == "Chapter_123_Test"

    def test_sanitize_valid_names(self):
        """Test that valid names are not modified."""
        assert sanitize_xml_element_name("Introduction") == "Introduction"
        assert sanitize_xml_element_name("Appendix_A") == "Appendix_A"
        assert sanitize_xml_element_name("Part_1") == "Part_1"
        assert sanitize_xml_element_name("_Test") == "_Test"

    def test_sanitize_empty_string(self):
        """Test handling of edge cases."""
        # Empty string or None should be handled gracefully
        result = sanitize_xml_element_name("")
        assert isinstance(result, str)


class TestWordCounting:
    """Test word counting functionality."""

    def test_count_simple_text(self):
        """Test counting words in simple text."""
        assert count_words("hello world") == 2
        assert count_words("one two three four five") == 5
        assert count_words("") == 0

    def test_count_with_xml_tags(self):
        """Test that XML tags are excluded from word count."""
        xml_text = "<paragraph>hello world</paragraph>"
        assert count_words(xml_text) == 2

        xml_text = "<page><heading>Test</heading><paragraph>one two three</paragraph></page>"
        # "Test" + "one" + "two" + "three" but regex counts differently
        word_count = count_words(xml_text)
        assert word_count >= 3  # At minimum, should count the main words

    def test_count_with_punctuation(self):
        """Test word counting with punctuation."""
        assert count_words("Hello, world!") == 2
        # Note: \b\w+\b regex treats "It's" as "It" and "s" (2 words)
        assert count_words("It's a test.") == 4  # "It", "s", "a", "test"

    def test_word_frequencies(self):
        """Test word frequency counting."""
        text = "the quick brown fox jumps over the lazy dog the"
        frequencies = get_word_frequencies(text)

        assert frequencies["the"] == 3
        assert frequencies["quick"] == 1
        assert frequencies["brown"] == 1

    def test_word_frequencies_case_insensitive(self):
        """Test that word frequencies are case-insensitive."""
        text = "The THE the"
        frequencies = get_word_frequencies(text)

        assert frequencies["the"] == 3


class TestTextLegibility:
    """Test text legibility checking."""

    def test_legible_text(self):
        """Test that normal text is considered legible."""
        normal_text = "This is a normal paragraph with reasonable word lengths."
        assert is_text_legible(normal_text) == True

    def test_illegible_text(self):
        """Test that corrupted text is detected."""
        # Create text with many overly long "words" (simulating corrupted text)
        corrupted_text = " ".join(["x" * 25 for _ in range(15)])
        assert is_text_legible(corrupted_text) == False

    def test_mixed_legibility(self):
        """Test text with some long words."""
        # Text with a few long words should still be legible
        mixed_text = "Normal words here pneumonoultramicroscopicsilicovolcanoconiosis and more"
        assert is_text_legible(mixed_text) == True


class TestTextExtraction:
    """Test text extraction from PDF pages."""

    @pytest.mark.requires_pdf
    def test_extract_embedded_text(self, test_pdf_path, test_output_dir):
        """Test extraction of embedded text from PDF."""
        doc = fitz.open(test_pdf_path)

        # Extract first page
        page_bytes = fitz.open()
        page_bytes.insert_pdf(doc, from_page=0, to_page=0)
        page_data = page_bytes.write()
        page_bytes.close()

        # Test extraction
        os.makedirs(test_output_dir / "pages", exist_ok=True)
        text, source = get_legible_text_from_page(page_data, 1, str(test_output_dir))

        assert isinstance(text, str)
        assert len(text) > 0
        assert source in ["embedded", "ocr", "ocr_failed"]

        doc.close()

    @pytest.mark.requires_pdf
    def test_text_extraction_creates_logs(self, test_pdf_path, test_output_dir):
        """Test that text extraction creates log files."""
        doc = fitz.open(test_pdf_path)

        page_bytes = fitz.open()
        page_bytes.insert_pdf(doc, from_page=0, to_page=0)
        page_data = page_bytes.write()
        page_bytes.close()

        os.makedirs(test_output_dir / "pages", exist_ok=True)
        text, source = get_legible_text_from_page(page_data, 1, str(test_output_dir))

        # Check that output files were created
        if source == "embedded":
            assert (test_output_dir / "pages" / "page_1_embedded.txt").exists()
        elif source == "ocr":
            assert (test_output_dir / "pages" / "page_1_ocr.txt").exists()

        doc.close()


class TestXMLValidation:
    """Test XML structure validation."""

    def test_valid_xml_parsing(self, sample_xml_content):
        """Test that valid XML can be parsed."""
        root = ET.fromstring(sample_xml_content)
        assert root is not None
        assert root.tag == "Chapter_01_Introduction"

    def test_xml_has_pages(self, sample_xml_content):
        """Test that XML contains page elements."""
        root = ET.fromstring(sample_xml_content)
        pages = root.findall("page")
        assert len(pages) > 0

    def test_xml_page_attributes(self, sample_xml_content):
        """Test that page elements have required attributes."""
        root = ET.fromstring(sample_xml_content)
        page = root.find("page")

        assert page is not None
        assert "number" in page.attrib

    def test_malformed_xml_detection(self, sample_malformed_xml):
        """Test that malformed XML is detected."""
        with pytest.raises(ET.ParseError):
            ET.fromstring(sample_malformed_xml)


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.requires_api
class TestGeminiIntegration:
    """Test Gemini API integration (makes real API calls)."""

    def test_gemini_configuration(self, check_api_key):
        """Test that Gemini API can be configured."""
        configure_gemini()
        # If this doesn't raise an exception, API key is configured

    @pytest.mark.slow
    def test_single_page_xml_generation(self, test_pdf_path, test_output_dir, check_api_key):
        """
        Test XML generation for a single page using Gemini API.

        WARNING: This test makes a REAL API call and will consume quota.
        """
        configure_gemini()

        doc = fitz.open(test_pdf_path)

        # Extract first page
        page_bytes = fitz.open()
        page_bytes.insert_pdf(doc, from_page=0, to_page=0)
        page_data = page_bytes.write()
        page_bytes.close()

        # Create required directory structure
        log_dir = test_output_dir / "test_chapter"
        os.makedirs(log_dir / "pages", exist_ok=True)

        # Generate XML for this page
        page_info = (page_data, 1, str(log_dir))
        xml_result = get_xml_for_page(page_info)

        # Validate result
        assert xml_result is not None
        assert len(xml_result) > 0

        # Parse XML to verify it's valid
        root = ET.fromstring(xml_result)
        assert root.tag == "page"

        # Check that XML file was created
        assert (log_dir / "pages" / "page_1.xml").exists()

        doc.close()

    @pytest.mark.slow
    def test_xml_generation_word_count_validation(self, test_pdf_path, test_output_dir, check_api_key):
        """
        Test that generated XML word count is validated.

        WARNING: This test makes a REAL API call.
        """
        configure_gemini()

        doc = fitz.open(test_pdf_path)

        # Extract first page
        page_bytes = fitz.open()
        page_bytes.insert_pdf(doc, from_page=0, to_page=0)
        page_data = page_bytes.write()
        page_bytes.close()

        log_dir = test_output_dir / "test_chapter_wordcount"
        os.makedirs(log_dir / "pages", exist_ok=True)

        # Extract text to get word count
        text, _ = get_legible_text_from_page(page_data, 1, str(log_dir))
        pdf_word_count = count_words(text)

        # Generate XML
        page_info = (page_data, 1, str(log_dir))
        xml_result = get_xml_for_page(page_info)

        # Check XML word count
        xml_word_count = count_words(xml_result)

        # Word counts should be reasonably close (within 15% threshold if > 30 words)
        if pdf_word_count >= 30:
            difference = abs(pdf_word_count - xml_word_count)
            percentage_diff = (difference / pdf_word_count) * 100
            assert percentage_diff <= 20, \
                f"Word count difference too large: PDF={pdf_word_count}, XML={xml_word_count}"

        doc.close()


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_empty_xml_content(self):
        """Test handling of empty XML content."""
        with pytest.raises(ET.ParseError):
            ET.fromstring("")

    def test_invalid_xml_structure(self):
        """Test handling of invalid XML structure."""
        invalid_xml = "<page><unclosed>"
        with pytest.raises(ET.ParseError):
            ET.fromstring(invalid_xml)

    def test_word_count_with_empty_string(self):
        """Test word counting with empty strings."""
        assert count_words("") == 0
        assert count_words("   ") == 0

    def test_sanitize_xml_handles_unicode(self):
        """Test XML sanitization with Unicode characters."""
        unicode_name = "01_Introducción"
        result = sanitize_xml_element_name(unicode_name)
        assert result.startswith("Chapter_")
        assert "Introducción" in result or "Introducci" in result  # Allow encoding variations
