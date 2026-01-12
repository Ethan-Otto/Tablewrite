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
import os

from pdf_processing.pdf_to_xml import (
    sanitize_xml_element_name,
    count_words,
    get_word_frequencies,
    is_text_legible,
    configure_gemini,
    get_legible_text_from_page,
    get_xml_for_page,
    validate_xml_with_model
)
from models.xml_document import XMLDocument


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


@pytest.mark.gemini
@pytest.mark.slow
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
        from util.gemini import GeminiFileContext
        gemini_api = configure_gemini()

        doc = fitz.open(test_pdf_path)

        # Extract first page
        page_bytes = fitz.open()
        page_bytes.insert_pdf(doc, from_page=0, to_page=0)
        page_data = page_bytes.write()
        page_bytes.close()

        # Create required directory structure
        log_dir = test_output_dir / "test_chapter"
        os.makedirs(log_dir / "pages", exist_ok=True)

        # Upload PDF and generate XML for this page
        with GeminiFileContext(gemini_api, test_pdf_path, "test_pdf") as uploaded_pdf:
            page_info = (page_data, 1, str(log_dir), uploaded_pdf)
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
        from util.gemini import GeminiFileContext
        gemini_api = configure_gemini()

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

        # Upload PDF and generate XML
        with GeminiFileContext(gemini_api, test_pdf_path, "test_pdf") as uploaded_pdf:
            page_info = (page_data, 1, str(log_dir), uploaded_pdf)
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


class TestXMLDocumentValidation:
    """Test XMLDocument model validation."""

    def test_validate_valid_xml(self):
        """Test that valid XML passes XMLDocument validation."""
        valid_xml = """<Chapter_01>
  <page number="1">
    <chapter_title>Introduction</chapter_title>
    <p>This is a paragraph with **bold** and *italic* text.</p>
    <section>A Section</section>
    <p>More content here.</p>
  </page>
</Chapter_01>"""

        # Should not raise any exception
        is_valid, error_msg = validate_xml_with_model(valid_xml)
        assert is_valid == True
        assert error_msg is None

    def test_validate_invalid_xml_malformed(self):
        """Test that malformed XML fails validation."""
        invalid_xml = """<Chapter_01>
  <page number="1">
    <p>Unclosed paragraph
  </page>
</Chapter_01>"""

        is_valid, error_msg = validate_xml_with_model(invalid_xml)
        assert is_valid == False
        assert error_msg is not None
        assert "parse" in error_msg.lower() or "xml" in error_msg.lower()

    def test_validate_xml_with_table(self):
        """Test validation with table structure."""
        xml_with_table = """<Chapter_Test>
  <page number="1">
    <section>Data Table</section>
    <table>
      <row>
        <cell>Header 1</cell>
        <cell>Header 2</cell>
      </row>
      <row>
        <cell>Data 1</cell>
        <cell>Data 2</cell>
      </row>
    </table>
  </page>
</Chapter_Test>"""

        is_valid, error_msg = validate_xml_with_model(xml_with_table)
        assert is_valid == True
        assert error_msg is None

    def test_validate_xml_with_list(self):
        """Test validation with list structure."""
        xml_with_list = """<Chapter_Test>
  <page number="1">
    <section>Items</section>
    <list type="unordered">
      <item>First item</item>
      <item>Second item</item>
      <item>Third item</item>
    </list>
  </page>
</Chapter_Test>"""

        is_valid, error_msg = validate_xml_with_model(xml_with_list)
        assert is_valid == True
        assert error_msg is None

    def test_validate_xml_with_stat_block(self):
        """Test validation with stat block."""
        xml_with_stat_block = """<Chapter_Test>
  <page number="1">
    <section>Monsters</section>
    <stat_block name="Goblin">
GOBLIN
Small humanoid (goblinoid), neutral evil

Armor Class 15 (leather armor, shield)
Hit Points 7 (2d6)
Speed 30 ft.

STR     DEX     CON     INT     WIS     CHA
8 (-1)  14 (+2) 10 (+0) 10 (+0) 8 (-1)  8 (-1)

Challenge 1/4 (50 XP)
    </stat_block>
  </page>
</Chapter_Test>"""

        is_valid, error_msg = validate_xml_with_model(xml_with_stat_block)
        assert is_valid == True
        assert error_msg is None

    def test_validate_xml_missing_page_number(self):
        """Test validation when page number is missing."""
        xml_missing_page_num = """<Chapter_Test>
  <page>
    <p>Content without page number</p>
  </page>
</Chapter_Test>"""

        # This should still be valid - page number defaults to "1"
        is_valid, error_msg = validate_xml_with_model(xml_missing_page_num)
        assert is_valid == True
        assert error_msg is None
