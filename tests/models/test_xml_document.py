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


class TestTableContent:
    """Test Table and TableRow content types."""

    def test_table_parsing_from_xml(self):
        """Test parsing table content from XML."""
        xml_string = """<Chapter_01>
    <page number="1">
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
</Chapter_01>"""

        doc = XMLDocument.from_xml(xml_string)
        assert len(doc.pages[0].content) == 1
        content = doc.pages[0].content[0]
        assert content.type == "table"

    def test_table_to_html_conversion(self):
        """Test table converts to HTML table."""
        xml_string = """<Chapter_01>
    <page number="1">
        <table>
            <row>
                <cell>Name</cell>
                <cell>CR</cell>
            </row>
            <row>
                <cell>Goblin</cell>
                <cell>1/4</cell>
            </row>
        </table>
    </page>
</Chapter_01>"""

        doc = XMLDocument.from_xml(xml_string)
        journal_pages = doc.to_journal_pages()
        html = journal_pages[0]["content"]

        assert "<table>" in html
        assert "<tr>" in html
        assert "<td>Name</td>" in html
        assert "<td>Goblin</td>" in html
        assert "</table>" in html


class TestListContent:
    """Test ListContent for ordered and unordered lists."""

    def test_unordered_list_parsing(self):
        """Test parsing unordered list from XML."""
        xml_string = """<Chapter_01>
    <page number="1">
        <list type="unordered">
            <item>First item</item>
            <item>Second item</item>
            <item>Third item</item>
        </list>
    </page>
</Chapter_01>"""

        doc = XMLDocument.from_xml(xml_string)
        assert len(doc.pages[0].content) == 1
        content = doc.pages[0].content[0]
        assert content.type == "list"

    def test_ordered_list_parsing(self):
        """Test parsing ordered list from XML."""
        xml_string = """<Chapter_01>
    <page number="1">
        <list type="ordered">
            <item>Step one</item>
            <item>Step two</item>
        </list>
    </page>
</Chapter_01>"""

        doc = XMLDocument.from_xml(xml_string)
        content = doc.pages[0].content[0]
        assert content.type == "list"

    def test_unordered_list_to_html(self):
        """Test unordered list converts to HTML <ul>."""
        xml_string = """<Chapter_01>
    <page number="1">
        <list type="unordered">
            <item>Item A</item>
            <item>Item B</item>
        </list>
    </page>
</Chapter_01>"""

        doc = XMLDocument.from_xml(xml_string)
        journal_pages = doc.to_journal_pages()
        html = journal_pages[0]["content"]

        assert "<ul>" in html
        assert "<li>Item A</li>" in html
        assert "<li>Item B</li>" in html
        assert "</ul>" in html

    def test_ordered_list_to_html(self):
        """Test ordered list converts to HTML <ol>."""
        xml_string = """<Chapter_01>
    <page number="1">
        <list type="ordered">
            <item>First</item>
            <item>Second</item>
        </list>
    </page>
</Chapter_01>"""

        doc = XMLDocument.from_xml(xml_string)
        journal_pages = doc.to_journal_pages()
        html = journal_pages[0]["content"]

        assert "<ol>" in html
        assert "<li>First</li>" in html
        assert "<li>Second</li>" in html
        assert "</ol>" in html


class TestDefinitionListContent:
    """Test DefinitionList and DefinitionItem for glossaries."""

    def test_definition_list_parsing(self):
        """Test parsing definition list from XML."""
        xml_string = """<Chapter_01>
    <page number="1">
        <definition_list>
            <definition>
                <term>Hit Points</term>
                <description>A measure of a creature's health.</description>
            </definition>
            <definition>
                <term>Armor Class</term>
                <description>How difficult a creature is to hit.</description>
            </definition>
        </definition_list>
    </page>
</Chapter_01>"""

        doc = XMLDocument.from_xml(xml_string)
        assert len(doc.pages[0].content) == 1
        content = doc.pages[0].content[0]
        assert content.type == "definition_list"

    def test_definition_list_to_html(self):
        """Test definition list converts to HTML <dl>."""
        xml_string = """<Chapter_01>
    <page number="1">
        <definition_list>
            <definition>
                <term>Goblin</term>
                <description>Small humanoid creature.</description>
            </definition>
            <definition>
                <term>Dragon</term>
                <description>Powerful reptilian creature.</description>
            </definition>
        </definition_list>
    </page>
</Chapter_01>"""

        doc = XMLDocument.from_xml(xml_string)
        journal_pages = doc.to_journal_pages()
        html = journal_pages[0]["content"]

        assert "<dl>" in html
        assert "<dt>Goblin</dt>" in html
        assert "<dd>Small humanoid creature.</dd>" in html
        assert "<dt>Dragon</dt>" in html
        assert "<dd>Powerful reptilian creature.</dd>" in html
        assert "</dl>" in html


class TestStatBlockContent:
    """Test StatBlockRaw for preserving complete stat block XML."""

    def test_stat_block_parsing(self):
        """Test parsing stat block from XML preserves raw XML."""
        xml_string = """<Chapter_01>
    <page number="1">
        <stat_block name="Goblin">
GOBLIN
Small humanoid, neutral evil
Armor Class 15
Hit Points 7 (2d6)
        </stat_block>
    </page>
</Chapter_01>"""

        doc = XMLDocument.from_xml(xml_string)
        assert len(doc.pages[0].content) == 1
        content = doc.pages[0].content[0]
        assert content.type == "stat_block"

    def test_stat_block_preserves_name(self):
        """Test stat block preserves name attribute."""
        xml_string = """<Chapter_01>
    <page number="1">
        <stat_block name="Goblin">
GOBLIN
Small humanoid, neutral evil
        </stat_block>
    </page>
</Chapter_01>"""

        doc = XMLDocument.from_xml(xml_string)
        from models.xml_document import StatBlockRaw

        stat_block = doc.pages[0].content[0].data
        assert isinstance(stat_block, StatBlockRaw)
        assert stat_block.name == "Goblin"

    def test_stat_block_preserves_xml(self):
        """Test stat block preserves complete XML element."""
        xml_string = """<Chapter_01>
    <page number="1">
        <stat_block name="Goblin">
GOBLIN
Small humanoid, neutral evil
Armor Class 15
Hit Points 7 (2d6)
        </stat_block>
    </page>
</Chapter_01>"""

        doc = XMLDocument.from_xml(xml_string)
        from models.xml_document import StatBlockRaw

        stat_block = doc.pages[0].content[0].data
        assert isinstance(stat_block, StatBlockRaw)
        assert "GOBLIN" in stat_block.xml_element
        assert "Armor Class 15" in stat_block.xml_element
        assert "Hit Points 7" in stat_block.xml_element


class TestImageRefContent:
    """Test ImageRef for image placeholders."""

    def test_image_ref_parsing(self):
        """Test parsing image_ref from XML."""
        xml_string = """<Chapter_01>
    <page number="5">
        <paragraph>Before image</paragraph>
        <image_ref key="page_5_top_battle_map" />
        <paragraph>After image</paragraph>
    </page>
</Chapter_01>"""

        doc = XMLDocument.from_xml(xml_string)
        assert len(doc.pages[0].content) == 3
        assert doc.pages[0].content[0].type == "paragraph"
        assert doc.pages[0].content[1].type == "image_ref"
        assert doc.pages[0].content[2].type == "paragraph"

    def test_image_ref_preserves_key(self):
        """Test image_ref preserves key attribute."""
        xml_string = """<Chapter_01>
    <page number="5">
        <image_ref key="page_5_top_battle_map" />
    </page>
</Chapter_01>"""

        doc = XMLDocument.from_xml(xml_string)
        from models.xml_document import ImageRef

        img_ref = doc.pages[0].content[0].data
        assert isinstance(img_ref, ImageRef)
        assert img_ref.key == "page_5_top_battle_map"

    def test_image_ref_with_different_keys(self):
        """Test multiple image_refs with different keys."""
        xml_string = """<Chapter_01>
    <page number="5">
        <image_ref key="page_5_map_1" />
        <paragraph>Some text</paragraph>
        <image_ref key="page_5_map_2" />
    </page>
</Chapter_01>"""

        doc = XMLDocument.from_xml(xml_string)
        from models.xml_document import ImageRef

        img_ref1 = doc.pages[0].content[0].data
        img_ref2 = doc.pages[0].content[2].data

        assert isinstance(img_ref1, ImageRef)
        assert isinstance(img_ref2, ImageRef)
        assert img_ref1.key == "page_5_map_1"
        assert img_ref2.key == "page_5_map_2"


class TestXMLDocumentSerialization:
    """Test XMLDocument serialization with to_xml() method."""

    def test_xmldocument_round_trip(self):
        """Test round-trip conversion: XML → XMLDocument → XML → XMLDocument.

        This validates that to_xml() produces valid XML that can be parsed back
        into an equivalent XMLDocument structure.
        """
        # Original XML with all content types
        original_xml = """<Chapter_01_Introduction>
    <page number="1">
        <chapter_title>Introduction</chapter_title>
        <section>The Story</section>
        <paragraph>This is a **bold** test with *italic* text.</paragraph>
        <table>
            <row>
                <cell>Name</cell>
                <cell>CR</cell>
            </row>
            <row>
                <cell>Goblin</cell>
                <cell>1/4</cell>
            </row>
        </table>
        <list type="unordered">
            <item>First item</item>
            <item>Second item</item>
        </list>
        <list type="ordered">
            <item>Step one</item>
            <item>Step two</item>
        </list>
        <definition_list>
            <definition>
                <term>Hit Points</term>
                <description>A measure of health.</description>
            </definition>
        </definition_list>
        <stat_block name="Goblin">
GOBLIN
Small humanoid, neutral evil
Armor Class 15
        </stat_block>
        <image_ref key="page_1_battle_map" />
    </page>
    <page number="2">
        <section>Second Page</section>
        <paragraph>More content here.</paragraph>
    </page>
</Chapter_01_Introduction>"""

        # First parse: XML → XMLDocument
        doc1 = XMLDocument.from_xml(original_xml)

        # Serialize: XMLDocument → XML
        serialized_xml = doc1.to_xml()

        # Second parse: XML → XMLDocument
        doc2 = XMLDocument.from_xml(serialized_xml)

        # Verify both documents are equivalent
        assert doc1.title == doc2.title
        assert len(doc1.pages) == len(doc2.pages)

        for page1, page2 in zip(doc1.pages, doc2.pages):
            assert page1.number == page2.number
            assert len(page1.content) == len(page2.content)

            for content1, content2 in zip(page1.content, page2.content):
                assert content1.type == content2.type
                # For complex types, compare the model representation
                if isinstance(content1.data, str):
                    assert content1.data == content2.data
                else:
                    # Use model_dump for deep comparison
                    assert content1.data.model_dump() == content2.data.model_dump()


class TestRealXMLIntegration:
    """Test XMLDocument can parse real generated XML files."""

    @pytest.mark.smoke
    @pytest.mark.integration
    def test_xmldocument_parses_real_xml(self):
        """Smoke test: Parse real XML files from pdf_to_xml.py

        This test validates that the XMLDocument model can handle real-world
        XML files produced by pdf_to_xml.py. It gracefully skips if no XML
        files are found (e.g., in fresh worktrees or CI environments).
        """
        # Use the most recent valid XML file
        xml_file = Path("output/runs/20251108_235712/documents/01_Introduction.xml")

        assert xml_file.exists(), f"Test XML file not found: {xml_file}"

        # Parse the real XML file
        xml_string = xml_file.read_text()
        doc = XMLDocument.from_xml(xml_string)

        # Validate basic structure
        assert doc.title.startswith("Chapter_"), f"Expected title to start with 'Chapter_', got: {doc.title}"
        assert len(doc.pages) > 0, "Document should have at least one page"
        assert all(page.number > 0 for page in doc.pages), "All page numbers should be positive"
        assert all(len(page.content) > 0 for page in doc.pages), "All pages should have content"

        # Validate content IDs are unique across entire document
        all_ids = [c.id for page in doc.pages for c in page.content]
        assert len(all_ids) == len(set(all_ids)), "Content IDs must be unique across document"

        # Validate page-based ID format
        for page in doc.pages:
            for idx, content in enumerate(page.content):
                expected_id = f"page_{page.number}_content_{idx}"
                assert content.id == expected_id, f"Expected ID {expected_id}, got {content.id}"
