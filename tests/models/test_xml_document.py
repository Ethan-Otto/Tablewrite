"""Tests for XMLDocument models."""

import pytest
from pathlib import Path
from xml.etree.ElementTree import ParseError

from models.xml_document import (
    XMLDocument,
    Page,
    Content,
    parse_xml_file,
    parse_xml_string,
)


class TestContent:
    """Test Content class."""

    def test_content_creation(self):
        """Test creating a content element."""
        content = Content(
            id="page_1_content_0",
            type="paragraph",
            data="This is a test paragraph."
        )
        assert content.id == "page_1_content_0"
        assert content.type == "paragraph"
        assert content.data == "This is a test paragraph."

    def test_content_immutability(self):
        """Test that content is immutable (frozen)."""
        content = Content(
            id="page_1_content_0",
            type="paragraph",
            data="Test"
        )
        with pytest.raises(Exception):  # Pydantic raises ValidationError
            content.data = "Modified"

    def test_content_with_section_type(self):
        """Test creating section type content."""
        content = Content(
            id="page_1_content_0",
            type="section",
            data="Introduction"
        )
        assert content.type == "section"
        assert content.data == "Introduction"


class TestPage:
    """Test Page class."""

    def test_page_creation(self):
        """Test creating a page."""
        content1 = Content(id="page_1_content_0", type="section", data="Test")
        content2 = Content(id="page_1_content_1", type="paragraph", data="Content")
        page = Page(number=1, content=[content1, content2])

        assert page.number == 1
        assert len(page.content) == 2
        assert page.content[0].type == "section"
        assert page.content[1].type == "paragraph"

    def test_page_immutability(self):
        """Test that page is immutable (frozen)."""
        page = Page(number=1, content=[])
        with pytest.raises(Exception):  # Pydantic raises ValidationError
            page.number = 2

    def test_empty_page(self):
        """Test creating page with no content."""
        page = Page(number=1, content=[])
        assert len(page.content) == 0


class TestXMLDocument:
    """Test XMLDocument class."""

    def test_document_creation(self):
        """Test creating a document."""
        page1 = Page(number=1, content=[])
        page2 = Page(number=2, content=[])
        doc = XMLDocument(title="Chapter_01_Introduction", pages=[page1, page2])

        assert doc.title == "Chapter_01_Introduction"
        assert len(doc.pages) == 2

    def test_document_immutability(self):
        """Test that document is immutable (frozen)."""
        doc = XMLDocument(title="Test", pages=[])
        with pytest.raises(Exception):  # Pydantic raises ValidationError
            doc.title = "Modified"

    def test_from_xml_simple(self):
        """Test parsing simple XML string."""
        xml_string = """<Chapter_01_Introduction>
    <page number="1">
        <section>Introduction</section>
        <paragraph>This is a test paragraph.</paragraph>
    </page>
</Chapter_01_Introduction>"""

        doc = XMLDocument.from_xml(xml_string)
        assert doc.title == "Chapter_01_Introduction"
        assert len(doc.pages) == 1
        assert doc.pages[0].number == 1
        assert len(doc.pages[0].content) == 2

        # Check auto-generated IDs
        assert doc.pages[0].content[0].id == "page_1_content_0"
        assert doc.pages[0].content[1].id == "page_1_content_1"

        # Check content types and data
        assert doc.pages[0].content[0].type == "section"
        assert doc.pages[0].content[0].data == "Introduction"
        assert doc.pages[0].content[1].type == "paragraph"
        assert doc.pages[0].content[1].data == "This is a test paragraph."

    def test_from_xml_multiple_pages(self):
        """Test parsing XML with multiple pages."""
        xml_string = """<Chapter_01>
    <page number="1">
        <section>Section 1</section>
        <paragraph>Page 1 content.</paragraph>
    </page>
    <page number="2">
        <section>Section 2</section>
        <paragraph>Page 2 content.</paragraph>
    </page>
</Chapter_01>"""

        doc = XMLDocument.from_xml(xml_string)
        assert len(doc.pages) == 2
        assert doc.pages[0].number == 1
        assert doc.pages[1].number == 2

        # Check IDs are unique per page
        assert doc.pages[0].content[0].id == "page_1_content_0"
        assert doc.pages[1].content[0].id == "page_2_content_0"

    def test_from_xml_all_content_types(self):
        """Test parsing XML with all content types."""
        xml_string = """<Chapter_01>
    <page number="1">
        <chapter_title>Chapter Title</chapter_title>
        <section>Section</section>
        <subsection>Subsection</subsection>
        <subsubsection>Subsubsection</subsubsection>
        <paragraph>Paragraph text.</paragraph>
    </page>
</Chapter_01>"""

        doc = XMLDocument.from_xml(xml_string)
        content = doc.pages[0].content

        assert len(content) == 5
        assert content[0].type == "chapter_title"
        assert content[1].type == "section"
        assert content[2].type == "subsection"
        assert content[3].type == "subsubsection"
        assert content[4].type == "paragraph"

    def test_from_xml_empty_text(self):
        """Test parsing XML with empty text elements."""
        xml_string = """<Chapter_01>
    <page number="1">
        <section></section>
        <paragraph/>
    </page>
</Chapter_01>"""

        doc = XMLDocument.from_xml(xml_string)
        assert doc.pages[0].content[0].data == ""
        assert doc.pages[0].content[1].data == ""


class TestParseXMLFile:
    """Test parsing XML files into XMLDocument models."""

    def test_parse_simple_file(self, tmp_path):
        """Test parsing a simple XML file."""
        xml_content = """<Chapter_01_Introduction>
    <page number="1">
        <section>Introduction</section>
        <paragraph>This is a test paragraph.</paragraph>
    </page>
</Chapter_01_Introduction>"""

        xml_file = tmp_path / "chapter_01.xml"
        xml_file.write_text(xml_content)

        doc = parse_xml_file(xml_file)
        assert doc.title == "Chapter_01_Introduction"
        assert len(doc.pages) == 1
        assert doc.pages[0].number == 1

    def test_parse_multiple_pages(self, tmp_path):
        """Test parsing XML file with multiple pages."""
        xml_content = """<Chapter_01>
    <page number="1">
        <section>Section 1</section>
        <paragraph>Page 1 content.</paragraph>
    </page>
    <page number="2">
        <section>Section 2</section>
        <paragraph>Page 2 content.</paragraph>
    </page>
</Chapter_01>"""

        xml_file = tmp_path / "chapter.xml"
        xml_file.write_text(xml_content)

        doc = parse_xml_file(xml_file)
        assert len(doc.pages) == 2
        assert doc.pages[0].number == 1
        assert doc.pages[1].number == 2

    def test_parse_nonexistent_file(self):
        """Test parsing nonexistent file raises error."""
        with pytest.raises(FileNotFoundError):
            parse_xml_file(Path("/nonexistent/file.xml"))

    def test_parse_invalid_xml(self, tmp_path):
        """Test parsing invalid XML raises error."""
        xml_file = tmp_path / "invalid.xml"
        xml_file.write_text("<invalid><unclosed>")

        with pytest.raises(ParseError):
            parse_xml_file(xml_file)


class TestParseXMLString:
    """Test parsing XML strings into XMLDocument models."""

    def test_parse_string_simple(self):
        """Test parsing a simple XML string."""
        xml_string = """<Chapter_01>
    <page number="1">
        <section>Test</section>
        <paragraph>Content</paragraph>
    </page>
</Chapter_01>"""

        doc = parse_xml_string(xml_string)
        assert doc.title == "Chapter_01"
        assert len(doc.pages) == 1

    def test_parse_string_invalid_xml(self):
        """Test parsing invalid XML string raises error."""
        with pytest.raises(ParseError):
            parse_xml_string("<invalid><unclosed>")

    def test_parse_empty_string(self):
        """Test parsing empty string raises error."""
        with pytest.raises(ParseError):
            parse_xml_string("")


class TestXMLDocumentToJournal:
    """Test converting XMLDocument to FoundryVTT journal format."""

    def test_document_to_journal_pages(self):
        """Test converting document to journal page format."""
        xml_string = """<Chapter_01>
    <page number="1">
        <section>Introduction</section>
        <paragraph>First paragraph.</paragraph>
        <paragraph>Second paragraph.</paragraph>
    </page>
</Chapter_01>"""

        doc = XMLDocument.from_xml(xml_string)
        journal_pages = doc.to_journal_pages()

        assert len(journal_pages) == 1
        assert journal_pages[0]["name"] == "Page 1"
        assert "content" in journal_pages[0]
        assert "<h2>Introduction</h2>" in journal_pages[0]["content"]
        assert "<p>First paragraph.</p>" in journal_pages[0]["content"]

    def test_document_multiple_pages_to_journal(self):
        """Test converting multi-page document to journal format."""
        xml_string = """<Chapter_01>
    <page number="1">
        <section>Intro</section>
        <paragraph>Page 1</paragraph>
    </page>
    <page number="2">
        <section>Content</section>
        <paragraph>Page 2</paragraph>
    </page>
</Chapter_01>"""

        doc = XMLDocument.from_xml(xml_string)
        journal_pages = doc.to_journal_pages()

        assert len(journal_pages) == 2
        assert journal_pages[0]["name"] == "Page 1"
        assert journal_pages[1]["name"] == "Page 2"

    def test_html_heading_levels(self):
        """Test that content types map to correct HTML heading levels."""
        xml_string = """<Chapter_01>
    <page number="1">
        <chapter_title>Chapter Title</chapter_title>
        <section>Section</section>
        <subsection>Subsection</subsection>
        <subsubsection>Subsubsection</subsubsection>
    </page>
</Chapter_01>"""

        doc = XMLDocument.from_xml(xml_string)
        journal_pages = doc.to_journal_pages()
        html = journal_pages[0]["content"]

        assert "<h1>Chapter Title</h1>" in html
        assert "<h2>Section</h2>" in html
        assert "<h3>Subsection</h3>" in html
        assert "<h4>Subsubsection</h4>" in html

    def test_markdown_conversion(self):
        """Test markdown-style formatting in paragraphs."""
        xml_string = """<Chapter_01>
    <page number="1">
        <paragraph>This has **bold** and *italic* text.</paragraph>
    </page>
</Chapter_01>"""

        doc = XMLDocument.from_xml(xml_string)
        journal_pages = doc.to_journal_pages()
        html = journal_pages[0]["content"]

        assert "<strong>bold</strong>" in html
        assert "<em>italic</em>" in html
        assert "**" not in html  # Markdown should be converted
        assert "*italic*" not in html  # Single asterisks should be converted
