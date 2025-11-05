"""Tests for XMLDocument models."""

import pytest
from pathlib import Path
from xml.etree.ElementTree import ParseError

from models.xml_document import (
    XMLDocument,
    XMLPage,
    XMLSection,
    XMLElement,
    XMLParagraph,
    XMLList,
    XMLListItem,
    XMLStatBlock,
    parse_xml_file,
    parse_xml_string,
)


class TestXMLElement:
    """Test base XMLElement class."""

    def test_xml_element_creation(self):
        """Test creating a basic XML element."""
        element = XMLElement(tag="test", text="Test content")
        assert element.tag == "test"
        assert element.text == "Test content"
        assert element.attributes == {}

    def test_xml_element_with_attributes(self):
        """Test creating XML element with attributes."""
        element = XMLElement(
            tag="test",
            text="Content",
            attributes={"id": "123", "class": "test-class"}
        )
        assert element.attributes["id"] == "123"
        assert element.attributes["class"] == "test-class"


class TestXMLParagraph:
    """Test XMLParagraph class."""

    def test_paragraph_creation(self):
        """Test creating a paragraph element."""
        para = XMLParagraph(text="This is a test paragraph.")
        assert para.tag == "p"
        assert para.text == "This is a test paragraph."

    def test_paragraph_with_markdown(self):
        """Test paragraph with markdown formatting."""
        para = XMLParagraph(text="This has **bold** and *italic* text.")
        assert "**bold**" in para.text
        assert "*italic*" in para.text


class TestXMLList:
    """Test XMLList and XMLListItem classes."""

    def test_list_item_creation(self):
        """Test creating a list item."""
        item = XMLListItem(text="First item")
        assert item.tag == "item"
        assert item.text == "First item"

    def test_list_creation(self):
        """Test creating a list with items."""
        items = [
            XMLListItem(text="First item"),
            XMLListItem(text="Second item"),
            XMLListItem(text="Third item"),
        ]
        list_elem = XMLList(items=items)
        assert list_elem.tag == "list"
        assert len(list_elem.items) == 3
        assert list_elem.items[0].text == "First item"
        assert list_elem.items[2].text == "Third item"

    def test_empty_list(self):
        """Test creating an empty list."""
        list_elem = XMLList(items=[])
        assert len(list_elem.items) == 0


class TestXMLStatBlock:
    """Test XMLStatBlock class."""

    def test_stat_block_creation(self):
        """Test creating a stat block element."""
        stat_block = XMLStatBlock(
            name="Goblin",
            content="GOBLIN\nSmall humanoid (goblinoid), neutral evil\n\nArmor Class 15"
        )
        assert stat_block.tag == "stat_block"
        assert stat_block.name == "Goblin"
        assert "Armor Class 15" in stat_block.content

    def test_stat_block_attributes(self):
        """Test stat block has name attribute."""
        stat_block = XMLStatBlock(name="Dragon", content="Dragon stats")
        assert stat_block.attributes["name"] == "Dragon"


class TestXMLSection:
    """Test XMLSection class."""

    def test_section_creation(self):
        """Test creating a section with title."""
        section = XMLSection(title="Introduction", elements=[])
        assert section.tag == "section"
        assert section.title == "Introduction"
        assert len(section.elements) == 0

    def test_section_with_elements(self):
        """Test section with multiple elements."""
        elements = [
            XMLParagraph(text="First paragraph."),
            XMLParagraph(text="Second paragraph."),
            XMLList(items=[XMLListItem(text="Item 1")]),
        ]
        section = XMLSection(title="Test Section", elements=elements)
        assert len(section.elements) == 3
        assert isinstance(section.elements[0], XMLParagraph)
        assert isinstance(section.elements[2], XMLList)


class TestXMLPage:
    """Test XMLPage class."""

    def test_page_creation(self):
        """Test creating a page with number."""
        page = XMLPage(number=1, sections=[])
        assert page.tag == "page"
        assert page.number == 1
        assert len(page.sections) == 0

    def test_page_with_sections(self):
        """Test page with multiple sections."""
        sections = [
            XMLSection(title="Section 1", elements=[]),
            XMLSection(title="Section 2", elements=[]),
        ]
        page = XMLPage(number=1, sections=sections)
        assert len(page.sections) == 2
        assert page.sections[0].title == "Section 1"

    def test_page_number_attribute(self):
        """Test page has number attribute."""
        page = XMLPage(number=5, sections=[])
        assert page.attributes["number"] == "5"


class TestXMLDocument:
    """Test XMLDocument class."""

    def test_document_creation(self):
        """Test creating a document with chapter name."""
        doc = XMLDocument(chapter_name="Chapter_01_Introduction", pages=[])
        assert doc.chapter_name == "Chapter_01_Introduction"
        assert len(doc.pages) == 0

    def test_document_with_pages(self):
        """Test document with multiple pages."""
        pages = [
            XMLPage(number=1, sections=[]),
            XMLPage(number=2, sections=[]),
            XMLPage(number=3, sections=[]),
        ]
        doc = XMLDocument(chapter_name="Chapter_01", pages=pages)
        assert len(doc.pages) == 3
        assert doc.pages[1].number == 2

    def test_document_root_tag(self):
        """Test document uses chapter name as root tag."""
        doc = XMLDocument(chapter_name="Chapter_02_Combat", pages=[])
        assert doc.chapter_name == "Chapter_02_Combat"


class TestParseXMLFile:
    """Test parsing XML files into XMLDocument models."""

    def test_parse_simple_chapter(self, tmp_path):
        """Test parsing a simple chapter XML file."""
        xml_content = """<Chapter_01_Introduction>
    <page number="1">
        <section>Introduction</section>
        <p>This is a test paragraph.</p>
    </page>
</Chapter_01_Introduction>"""

        xml_file = tmp_path / "chapter_01.xml"
        xml_file.write_text(xml_content)

        doc = parse_xml_file(xml_file)
        assert doc.chapter_name == "Chapter_01_Introduction"
        assert len(doc.pages) == 1
        assert doc.pages[0].number == 1

    def test_parse_multiple_pages(self, tmp_path):
        """Test parsing XML with multiple pages."""
        xml_content = """<Chapter_01>
    <page number="1">
        <section>Section 1</section>
        <p>Page 1 content.</p>
    </page>
    <page number="2">
        <section>Section 2</section>
        <p>Page 2 content.</p>
    </page>
</Chapter_01>"""

        xml_file = tmp_path / "chapter.xml"
        xml_file.write_text(xml_content)

        doc = parse_xml_file(xml_file)
        assert len(doc.pages) == 2
        assert doc.pages[0].number == 1
        assert doc.pages[1].number == 2

    def test_parse_with_list(self, tmp_path):
        """Test parsing XML with list elements."""
        xml_content = """<Chapter_01>
    <page number="1">
        <section>Test</section>
        <list>
            <item>First item</item>
            <item>Second item</item>
        </list>
    </page>
</Chapter_01>"""

        xml_file = tmp_path / "chapter.xml"
        xml_file.write_text(xml_content)

        doc = parse_xml_file(xml_file)
        page = doc.pages[0]
        # Find the list element in the page's sections
        list_elem = None
        for section in page.sections:
            for elem in section.elements:
                if isinstance(elem, XMLList):
                    list_elem = elem
                    break

        assert list_elem is not None
        assert len(list_elem.items) == 2
        assert list_elem.items[0].text == "First item"

    def test_parse_with_stat_block(self, tmp_path):
        """Test parsing XML with stat block."""
        xml_content = """<Chapter_01>
    <page number="1">
        <section>Goblin Ambush</section>
        <stat_block name="Goblin">GOBLIN
Small humanoid (goblinoid), neutral evil

Armor Class 15 (leather armor, shield)
Hit Points 7 (2d6)</stat_block>
    </page>
</Chapter_01>"""

        xml_file = tmp_path / "chapter.xml"
        xml_file.write_text(xml_content)

        doc = parse_xml_file(xml_file)
        page = doc.pages[0]
        # Find the stat block in the page's sections
        stat_block = None
        for section in page.sections:
            for elem in section.elements:
                if isinstance(elem, XMLStatBlock):
                    stat_block = elem
                    break

        assert stat_block is not None
        assert stat_block.name == "Goblin"
        assert "Armor Class 15" in stat_block.content

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
        <p>Content</p>
    </page>
</Chapter_01>"""

        doc = parse_xml_string(xml_string)
        assert doc.chapter_name == "Chapter_01"
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
        para1 = XMLParagraph(text="First paragraph.")
        para2 = XMLParagraph(text="Second paragraph.")
        section = XMLSection(title="Introduction", elements=[para1, para2])
        page = XMLPage(number=1, sections=[section])
        doc = XMLDocument(chapter_name="Chapter_01", pages=[page])

        journal_pages = doc.to_journal_pages()
        assert len(journal_pages) == 1
        assert journal_pages[0]["name"] == "Page 1"
        assert "content" in journal_pages[0]

    def test_document_multiple_pages_to_journal(self):
        """Test converting multi-page document to journal format."""
        page1 = XMLPage(number=1, sections=[
            XMLSection(title="Intro", elements=[XMLParagraph(text="Page 1")])
        ])
        page2 = XMLPage(number=2, sections=[
            XMLSection(title="Content", elements=[XMLParagraph(text="Page 2")])
        ])
        doc = XMLDocument(chapter_name="Chapter_01", pages=[page1, page2])

        journal_pages = doc.to_journal_pages()
        assert len(journal_pages) == 2
        assert journal_pages[0]["name"] == "Page 1"
        assert journal_pages[1]["name"] == "Page 2"
