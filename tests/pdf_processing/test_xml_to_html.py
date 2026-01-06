"""
Tests for src/xml_to_html.py

Tests XML to HTML conversion including:
- XML parsing and content extraction
- HTML generation
- Navigation link creation
- Error handling for malformed XML
- Output file creation
"""

import pytest
from pathlib import Path
import xml.etree.ElementTree as ET

from pdf_processing.xml_to_html import xml_to_html_content, generate_html_page, main


class TestXMLToHTMLConversion:
    """Test XML to HTML conversion functionality."""

    def test_xml_to_html_simple_content(self, sample_xml_content, test_output_dir):
        """Test conversion of simple XML content to HTML."""
        # Write XML to file
        xml_file = test_output_dir / "test.xml"
        xml_file.write_text(sample_xml_content)

        # Convert to HTML
        html_content = xml_to_html_content(xml_file)

        # Verify HTML was generated
        assert html_content is not None
        assert len(html_content) > 0
        assert isinstance(html_content, str)

    def test_xml_to_html_contains_headings(self, test_output_dir):
        """Test that headings are converted to HTML headings."""
        xml_content = """<test>
            <title>Main Title</title>
            <section>Section Heading</section>
        </test>"""

        xml_file = test_output_dir / "headings.xml"
        xml_file.write_text(xml_content)

        html_content = xml_to_html_content(xml_file)

        # Check for HTML heading tags
        assert "<h1>" in html_content or "<h2>" in html_content

    def test_xml_to_html_contains_paragraphs(self, test_output_dir):
        """Test that paragraphs are converted to HTML paragraphs."""
        xml_content = """<test>
            <p>This is a test paragraph.</p>
        </test>"""

        xml_file = test_output_dir / "paragraphs.xml"
        xml_file.write_text(xml_content)

        html_content = xml_to_html_content(xml_file)

        # Check for HTML paragraph tags
        assert "<p>" in html_content

    def test_xml_to_html_contains_lists(self, test_output_dir):
        """Test that lists are converted to HTML lists."""
        xml_content = """<test>
            <list>
                <item>First item</item>
                <item>Second item</item>
                <item>Third item</item>
            </list>
        </test>"""

        xml_file = test_output_dir / "lists.xml"
        xml_file.write_text(xml_content)

        html_content = xml_to_html_content(xml_file)

        # Check for HTML list tags
        assert "<ul>" in html_content
        assert "<li>" in html_content

    def test_xml_to_html_handles_malformed_xml(self, test_output_dir, sample_malformed_xml):
        """Test that malformed XML is handled gracefully."""
        xml_file = test_output_dir / "malformed.xml"
        xml_file.write_text(sample_malformed_xml)

        html_content = xml_to_html_content(xml_file)

        # Should return error message in HTML
        assert "Error" in html_content or "error" in html_content


class TestHTMLPageGeneration:
    """Test full HTML page generation."""

    def test_generate_html_page_creates_file(self, sample_xml_content, test_output_dir):
        """Test that HTML page file is created."""
        xml_file = test_output_dir / "test.xml"
        xml_file.write_text(sample_xml_content)

        html_file = test_output_dir / "test.html"
        nav_links = [("Test", "test.html")]

        generate_html_page(xml_file, nav_links, html_file)

        # Verify HTML file was created
        assert html_file.exists()

    def test_generate_html_page_structure(self, sample_xml_content, test_output_dir):
        """Test that generated HTML has proper structure."""
        xml_file = test_output_dir / "test.xml"
        xml_file.write_text(sample_xml_content)

        html_file = test_output_dir / "test.html"
        nav_links = [("Test", "test.html")]

        generate_html_page(xml_file, nav_links, html_file)

        html_content = html_file.read_text()

        # Check for essential HTML structure
        assert "<!DOCTYPE html>" in html_content
        assert "<html" in html_content
        assert "<head>" in html_content
        assert "<body>" in html_content
        assert "</html>" in html_content

    def test_generate_html_page_has_navigation(self, sample_xml_content, test_output_dir):
        """Test that generated HTML includes navigation."""
        xml_file = test_output_dir / "test.xml"
        xml_file.write_text(sample_xml_content)

        html_file = test_output_dir / "test.html"
        nav_links = [
            ("Chapter 1", "chapter1.html"),
            ("Chapter 2", "chapter2.html")
        ]

        generate_html_page(xml_file, nav_links, html_file)

        html_content = html_file.read_text()

        # Check for navigation elements
        assert "<nav>" in html_content
        assert "chapter1.html" in html_content
        assert "chapter2.html" in html_content

    def test_generate_html_page_has_css(self, sample_xml_content, test_output_dir):
        """Test that generated HTML includes CSS styling."""
        xml_file = test_output_dir / "test.xml"
        xml_file.write_text(sample_xml_content)

        html_file = test_output_dir / "test.html"
        nav_links = [("Test", "test.html")]

        generate_html_page(xml_file, nav_links, html_file)

        html_content = html_file.read_text()

        # Check for CSS
        assert "<style>" in html_content or "style" in html_content

    def test_generate_html_page_has_title(self, sample_xml_content, test_output_dir):
        """Test that generated HTML has a proper title."""
        xml_file = test_output_dir / "Chapter_01.xml"
        xml_file.write_text(sample_xml_content)

        html_file = test_output_dir / "Chapter_01.html"
        nav_links = [("Test", "test.html")]

        generate_html_page(xml_file, nav_links, html_file)

        html_content = html_file.read_text()

        # Check for title tag
        assert "<title>" in html_content
        assert "Chapter_01" in html_content


class TestMainFunction:
    """Test the main conversion function."""

    def test_main_converts_multiple_files(self, sample_xml_content, test_output_dir):
        """Test that main function converts multiple XML files."""
        # Create multiple XML files
        xml_dir = test_output_dir / "xml"
        xml_dir.mkdir()

        for i in range(3):
            xml_file = xml_dir / f"chapter_{i+1}.xml"
            xml_file.write_text(sample_xml_content)

        # Convert to HTML
        html_dir = test_output_dir / "html"

        main(xml_dir, html_dir)

        # Verify HTML files were created
        assert html_dir.exists()
        html_files = list(html_dir.glob("*.html"))
        assert len(html_files) == 3

    def test_main_creates_navigation_links(self, sample_xml_content, test_output_dir):
        """Test that main function creates navigation between pages."""
        xml_dir = test_output_dir / "xml"
        xml_dir.mkdir()

        # Create two XML files
        (xml_dir / "chapter_1.xml").write_text(sample_xml_content)
        (xml_dir / "chapter_2.xml").write_text(sample_xml_content)

        # Convert to HTML
        html_dir = test_output_dir / "html"

        main(xml_dir, html_dir)

        # Check that HTML files have navigation to each other
        html_1 = (html_dir / "chapter_1.html").read_text()
        html_2 = (html_dir / "chapter_2.html").read_text()

        # Both files should have navigation links
        assert "chapter_2.html" in html_1
        assert "chapter_1.html" in html_2


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_xml_file(self, test_output_dir):
        """Test handling of empty XML files."""
        xml_file = test_output_dir / "empty.xml"
        xml_file.write_text("")

        html_content = xml_to_html_content(xml_file)

        # Should handle gracefully
        assert isinstance(html_content, str)

    def test_xml_file_with_no_content_elements(self, test_output_dir):
        """Test XML with no title/heading/paragraph elements."""
        xml_content = """<root>
            <unknown_tag>Some content</unknown_tag>
        </root>"""

        xml_file = test_output_dir / "no_elements.xml"
        xml_file.write_text(xml_content)

        html_content = xml_to_html_content(xml_file)

        # Should return something (even if empty)
        assert isinstance(html_content, str)

    def test_xml_with_special_characters(self, test_output_dir):
        """Test XML containing special characters."""
        xml_content = """<root>
            <p>Text with &amp; ampersand &lt; less than &gt; greater than</p>
        </root>"""

        xml_file = test_output_dir / "special_chars.xml"
        xml_file.write_text(xml_content)

        html_content = xml_to_html_content(xml_file)

        # Should handle special characters properly
        assert isinstance(html_content, str)
        assert len(html_content) > 0

    def test_very_long_content(self, test_output_dir):
        """Test handling of very long content."""
        # Create XML with many paragraphs
        paragraphs = "\n".join([f"<p>Paragraph {i}</p>" for i in range(100)])
        xml_content = f"<root>{paragraphs}</root>"

        xml_file = test_output_dir / "long.xml"
        xml_file.write_text(xml_content)

        html_content = xml_to_html_content(xml_file)

        # Should handle large content
        assert isinstance(html_content, str)
        assert len(html_content) > 0
        # Should have many paragraph tags
        assert html_content.count("<p>") >= 50


class TestHTMLOutput:
    """Test properties of HTML output."""

    def test_html_is_valid_structure(self, sample_xml_content, test_output_dir):
        """Test that output HTML has valid structure."""
        xml_file = test_output_dir / "test.xml"
        xml_file.write_text(sample_xml_content)

        html_file = test_output_dir / "test.html"
        nav_links = []

        generate_html_page(xml_file, nav_links, html_file)

        html_content = html_file.read_text()

        # Basic structure checks
        assert html_content.count("<html") == 1
        assert html_content.count("</html>") == 1
        assert html_content.count("<head>") == 1
        assert html_content.count("</head>") == 1
        assert html_content.count("<body>") == 1
        assert html_content.count("</body>") == 1

    def test_html_has_responsive_viewport(self, sample_xml_content, test_output_dir):
        """Test that HTML includes viewport meta tag for responsiveness."""
        xml_file = test_output_dir / "test.xml"
        xml_file.write_text(sample_xml_content)

        html_file = test_output_dir / "test.html"
        nav_links = []

        generate_html_page(xml_file, nav_links, html_file)

        html_content = html_file.read_text()

        # Check for viewport meta tag
        assert "viewport" in html_content.lower()

    def test_html_has_utf8_charset(self, sample_xml_content, test_output_dir):
        """Test that HTML declares UTF-8 charset."""
        xml_file = test_output_dir / "test.xml"
        xml_file.write_text(sample_xml_content)

        html_file = test_output_dir / "test.html"
        nav_links = []

        generate_html_page(xml_file, nav_links, html_file)

        html_content = html_file.read_text()

        # Check for UTF-8 charset
        assert "UTF-8" in html_content or "utf-8" in html_content
