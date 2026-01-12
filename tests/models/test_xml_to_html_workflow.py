"""Integration tests for XML → XMLDocument → Journal → HTML transformation workflow.

This test suite validates the complete document model pipeline:
1. XML parsing to XMLDocument models
2. Stat block extraction from XMLDocument
3. Image reference extraction and registry management
4. Journal creation from XMLDocument with semantic hierarchy
5. HTML generation for FoundryVTT from Journal
"""

import pytest
from pathlib import Path
from models import XMLDocument, Journal, ImageRef, StatBlockRaw


@pytest.mark.smoke
@pytest.mark.unit
def test_xml_document_to_journal_to_html_complete_workflow():
    """Smoke test: Validates complete XML→XMLDocument→Journal→HTML transformation

    This end-to-end test validates:
    - XMLDocument parsing from real XML files
    - Journal creation from XMLDocument with semantic hierarchy
    - HTML export with image mapping
    - Round-trip XML serialization preserves data
    """
    # Use test fixture XML file
    xml_path = Path("tests/fixtures/xml/02_Part_1_Goblin_Arrows.xml")

    assert xml_path.exists(), f"Test XML file not found: {xml_path}"

    xml_string = xml_path.read_text()

    # Step 1: Parse to XMLDocument
    doc = XMLDocument.from_xml(xml_string)
    assert doc.title, "XMLDocument should have a title"
    assert len(doc.pages) > 0, "XMLDocument should have pages"

    # Step 2: Validate XMLDocument structure
    for page in doc.pages:
        assert page.number > 0, "Page numbers should be positive"

    # At least some pages should have content (not all pages may have content - some might be blank)
    pages_with_content = [p for p in doc.pages if len(p.content) > 0]
    assert len(pages_with_content) > 0, "At least some pages should have content"

    # Step 3: Create Journal from XMLDocument
    journal = Journal.from_xml_document(doc)
    assert len(journal.chapters) > 0, "Journal should have chapters"

    # Step 4: Validate Journal structure
    for chapter in journal.chapters:
        assert chapter.title, "Chapters should have titles"
        assert len(chapter.sections) > 0, "Chapters should have sections"

    # Step 5: Export to HTML
    html = journal.to_foundry_html(image_mapping={})
    assert len(html) > 0, "HTML output should not be empty"
    assert "<h1>" in html or "<h2>" in html, "HTML should contain headers"

    # Step 6: Validate round-trip XML serialization
    xml_out = doc.to_xml()
    doc2 = XMLDocument.from_xml(xml_out)
    assert doc2.title == doc.title, "Round-trip should preserve title"
    assert len(doc2.pages) == len(doc.pages), "Round-trip should preserve page count"


@pytest.mark.integration
def test_xmldocument_extracts_stat_blocks_from_xml():
    """Test XMLDocument correctly extracts and preserves stat blocks from XML.

    Validates:
    - StatBlockRaw extraction from XML <stat_block> tags
    - Stat block name and xml_element preservation
    - Integration with XMLDocument parser
    """
    # Find a real XML file with stat blocks
    xml_files = list(Path("output/runs").glob("*/documents/*.xml"))
    if not xml_files:
        pytest.skip("No XML files found in output/runs")

    stat_blocks_found = False
    for xml_path in xml_files:
        xml_string = xml_path.read_text()

        # Check if this file has stat_block tags
        if "<stat_block>" not in xml_string:
            continue

        # Parse with XMLDocument
        doc = XMLDocument.from_xml(xml_string)

        # Extract stat blocks from all pages
        all_stat_blocks = []
        for page in doc.pages:
            for content_item in page.content:
                if content_item.type == "stat_block" and isinstance(content_item.data, StatBlockRaw):
                    all_stat_blocks.append(content_item.data)

        if all_stat_blocks:
            stat_blocks_found = True

            # Validate stat blocks
            for stat_block in all_stat_blocks:
                assert stat_block.name, "Stat block should have a name"
                assert stat_block.xml_element, "Stat block should have xml_element"
                assert len(stat_block.xml_element) > 20, "Stat block xml_element should be substantial"

            break

    if not stat_blocks_found:
        pytest.skip("No stat blocks found in XML files")


@pytest.mark.integration
def test_journal_image_registry_and_html_replacement():
    """Test Journal image registry and HTML placeholder replacement.

    Validates:
    - ImageRef parsing from XML <image> tags
    - Image registry population in Journal
    - Placeholder format ({{image:path}})
    - Image URL replacement in HTML export
    """
    # Use a known good XML file - try multiple locations for one with images
    test_paths = [
        Path("output/runs/20251022_180524/documents/05_Part_4_Wave_Echo_Cave.xml"),
        Path("output/runs/20251017_111632/documents/05_Part_4_Wave_Echo_Cave.xml"),
        Path("output/runs/20251022_180524/documents/02_Part_1_Goblin_Arrows.xml"),
    ]

    images_found = False
    for xml_path in test_paths:
        if not xml_path.exists():
            continue

        xml_string = xml_path.read_text()

        # Check if this file has image tags
        if "<image" not in xml_string:
            continue

        # Parse with XMLDocument
        doc = XMLDocument.from_xml(xml_string)

        # Create Journal and check image registry
        journal = Journal.from_xml_document(doc)

        if journal.images:
            images_found = True

            # Validate image metadata
            for img_path, img_meta in journal.images.items():
                assert img_meta.original_path, "Image should have original_path"
                assert img_meta.placeholder, "Image should have placeholder"
                assert img_meta.placeholder.startswith("{{image:"), "Placeholder should use {{image:}} format"
                assert img_meta.alt_text or img_meta.caption, "Image should have alt_text or caption"

            # Test HTML export with image mapping
            image_mapping = {
                img_path: f"https://example.com/{img_path}"
                for img_path in journal.images.keys()
            }
            html = journal.to_foundry_html(image_mapping=image_mapping)

            # Validate images were replaced in HTML
            for img_path, url in image_mapping.items():
                # Check that placeholder was replaced
                placeholder = journal.images[img_path].placeholder
                assert placeholder not in html, f"Placeholder {placeholder} should be replaced"
                # Note: We don't check for the URL directly as HTML structure may vary

            break

    if not images_found:
        pytest.skip("No images found in XML files")


@pytest.mark.integration
def test_minimal_xml_document_converts_to_html():
    """Test that minimal XML documents convert correctly to HTML without errors."""
    minimal_xml = """
    <Chapter_01>
      <page number="1">
        <chapter_title>Test Chapter</chapter_title>
        <p>Single paragraph.</p>
      </page>
    </Chapter_01>
    """

    # Should parse without errors
    doc = XMLDocument.from_xml(minimal_xml)
    assert doc.title == "Chapter_01"
    assert len(doc.pages) == 1

    # Should create journal without errors
    journal = Journal.from_xml_document(doc)
    assert len(journal.chapters) == 1

    # Should export HTML without errors
    html = journal.to_foundry_html(image_mapping={})
    assert len(html) > 0
    assert "Test Chapter" in html
    assert "Single paragraph" in html


@pytest.mark.integration
def test_tables_lists_and_definition_lists_convert_to_html():
    """Test that complex content types (tables, lists, definition lists) convert correctly to HTML."""
    complex_xml = """
    <Chapter_01>
      <page number="1">
        <chapter_title>Complex Content</chapter_title>

        <section>Lists and Tables</section>

        <list>
          <li>First item</li>
          <li>Second item</li>
        </list>

        <table>
          <tr>
            <td>Cell 1</td>
            <td>Cell 2</td>
          </tr>
          <tr>
            <td>Cell 3</td>
            <td>Cell 4</td>
          </tr>
        </table>

        <definition_list>
          <dt>Term 1</dt>
          <dd>Definition 1</dd>
          <dt>Term 2</dt>
          <dd>Definition 2</dd>
        </definition_list>
      </page>
    </Chapter_01>
    """

    # Parse and validate
    doc = XMLDocument.from_xml(complex_xml)
    assert len(doc.pages) == 1

    # Check content types were parsed
    content_types = [item.type for item in doc.pages[0].content]
    assert "list" in content_types
    assert "table" in content_types
    assert "definition_list" in content_types

    # Create journal and export HTML
    journal = Journal.from_xml_document(doc)
    html = journal.to_foundry_html(image_mapping={})

    # Validate HTML contains expected elements
    assert "<ul>" in html or "<ol>" in html, "HTML should contain list"
    assert "table" in html.lower(), "HTML should contain table"
    assert "<dl>" in html, "HTML should contain definition list"


@pytest.mark.integration
def test_multi_page_chapter_flattens_to_journal_hierarchy():
    """Test that multi-page chapters correctly flatten into Journal's semantic hierarchy."""
    multi_page_xml = """
    <Chapter_02>
      <page number="1">
        <chapter_title>Multi-Page Chapter</chapter_title>
        <section>Section 1</section>
        <p>Content on page 1.</p>
      </page>
      <page number="2">
        <section>Section 2</section>
        <p>Content on page 2.</p>
      </page>
      <page number="3">
        <subsection>Subsection 2.1</subsection>
        <p>Content on page 3.</p>
      </page>
    </Chapter_02>
    """

    # Parse and validate
    doc = XMLDocument.from_xml(multi_page_xml)
    assert len(doc.pages) == 3

    # Create journal and validate flattening
    journal = Journal.from_xml_document(doc)
    assert len(journal.chapters) == 1

    chapter = journal.chapters[0]
    assert len(chapter.sections) >= 2, "Should have at least 2 sections"

    # Export HTML and validate structure
    html = journal.to_foundry_html(image_mapping={})
    assert "Section 1" in html
    assert "Section 2" in html
    assert "Subsection 2.1" in html
