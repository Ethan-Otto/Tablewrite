"""Integration tests for XMLDocument → Journal → HTML workflow."""
import pytest
from pathlib import Path
from models import XMLDocument, Journal


def test_full_workflow_with_real_xml():
    """Test complete workflow: Load XML → Parse → Create Journal → Export HTML"""
    # Find a real XML file
    xml_files = list(Path("output/runs").glob("*/documents/*.xml"))
    if not xml_files:
        pytest.skip("No XML files found in output/runs")

    xml_path = xml_files[0]
    xml_string = xml_path.read_text()

    # Step 1: Parse to XMLDocument
    doc = XMLDocument.from_xml(xml_string)
    assert doc.title
    assert len(doc.pages) > 0

    # Step 2: Create Journal
    journal = Journal.from_xml_document(doc)
    assert len(journal.chapters) > 0

    # Step 3: Export to HTML
    html = journal.to_foundry_html(image_mapping={})
    assert len(html) > 0
    assert "<h1>" in html

    # Step 4: Validate round-trip
    xml_out = doc.to_xml()
    doc2 = XMLDocument.from_xml(xml_out)
    assert doc2.title == doc.title
    assert len(doc2.pages) == len(doc.pages)


def test_journal_preserves_content():
    """Test Journal doesn't lose content during hierarchy flattening"""
    xml_string = """
    <Chapter_01>
      <page number="1">
        <chapter_title>Title</chapter_title>
        <section>Section 1</section>
        <p>Para 1</p>
      </page>
      <page number="2">
        <p>Para 2</p>
        <section>Section 2</section>
        <p>Para 3</p>
      </page>
    </Chapter_01>
    """
    doc = XMLDocument.from_xml(xml_string)
    journal = Journal.from_xml_document(doc)

    # Count all content elements
    total_content = 0
    for chapter in journal.chapters:
        for section in chapter.sections:
            total_content += len(section.content)

    # Should have 3 paragraphs
    assert total_content == 3
