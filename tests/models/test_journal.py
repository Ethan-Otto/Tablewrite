"""Tests for Journal models."""

import pytest
from models.xml_document import XMLDocument
from models.journal import Journal, Chapter, Section, Subsection, Subsubsection, ImageMetadata


class TestJournal:
    """Test Journal class."""

    def test_journal_flattens_pages_to_chapters(self):
        """Test that Journal.from_xml_document() flattens page structure to semantic hierarchy."""
        # Create an XMLDocument with page-based structure
        xml_string = """
<Chapter_1>
  <page number="1">
    <chapter_title>The Adventure Begins</chapter_title>
    <section>Introduction</section>
    <paragraph>This is the introduction paragraph.</paragraph>
    <subsection>Background</subsection>
    <paragraph>This is background information.</paragraph>
  </page>
  <page number="2">
    <paragraph>This continues the background section.</paragraph>
    <section>The Quest</section>
    <paragraph>A new section about the quest.</paragraph>
    <subsection>Quest Details</subsection>
    <paragraph>Details about the quest.</paragraph>
  </page>
</Chapter_1>
"""
        xml_doc = XMLDocument.from_xml(xml_string)

        # Convert to Journal
        journal = Journal.from_xml_document(xml_doc)

        # Verify basic structure
        assert journal.title == "Chapter_1"
        assert journal.source == xml_doc
        assert len(journal.chapters) == 1

        # Verify chapter
        chapter = journal.chapters[0]
        assert chapter.title == "The Adventure Begins"
        assert len(chapter.sections) == 2

        # Verify first section (spans pages 1-2)
        section1 = chapter.sections[0]
        assert section1.title == "Introduction"
        assert len(section1.subsections) == 1

        # Verify subsection that spans pages
        subsection = section1.subsections[0]
        assert subsection.title == "Background"
        # Should have 2 paragraphs (one from page 1, one from page 2)
        assert len(subsection.content) == 2

        # Verify content IDs have been reassigned
        content_id = subsection.content[0].id
        assert content_id.startswith("chapter_0_section_0_")

        # Verify second section
        section2 = chapter.sections[1]
        assert section2.title == "The Quest"
        assert len(section2.subsections) == 1

        # Verify quest subsection
        quest_subsection = section2.subsections[0]
        assert quest_subsection.title == "Quest Details"


class TestImageMetadata:
    """Test ImageMetadata class."""

    def test_image_metadata_creation(self):
        """Test creating ImageMetadata."""
        img_meta = ImageMetadata(
            key="map_001",
            source_page=5,
            type="map"
        )
        assert img_meta.key == "map_001"
        assert img_meta.source_page == 5
        assert img_meta.type == "map"


class TestHierarchyModels:
    """Test Chapter, Section, Subsection, Subsubsection models."""

    def test_chapter_creation(self):
        """Test creating a Chapter."""
        chapter = Chapter(
            title="Test Chapter",
            sections=[]
        )
        assert chapter.title == "Test Chapter"
        assert chapter.sections == []

    def test_section_creation(self):
        """Test creating a Section."""
        section = Section(
            title="Test Section",
            subsections=[],
            content=[]
        )
        assert section.title == "Test Section"
        assert section.subsections == []
        assert section.content == []

    def test_subsection_creation(self):
        """Test creating a Subsection."""
        subsection = Subsection(
            title="Test Subsection",
            subsubsections=[],
            content=[]
        )
        assert subsection.title == "Test Subsection"
        assert subsection.subsubsections == []
        assert subsection.content == []

    def test_subsubsection_creation(self):
        """Test creating a Subsubsection."""
        subsubsection = Subsubsection(
            title="Test Subsubsection",
            content=[]
        )
        assert subsubsection.title == "Test Subsubsection"
        assert subsubsection.content == []


class TestImageRefExtraction:
    """Test ImageRef extraction to image registry."""

    def test_journal_extracts_image_refs_to_registry(self):
        """Test that Journal._extract_image_refs() populates image_registry from XMLDocument."""
        # Create an XMLDocument with ImageRef elements
        xml_string = """
<Chapter_1>
  <page number="5">
    <paragraph>This is a paragraph.</paragraph>
    <image_ref key="page_5_top_battle_map" />
    <paragraph>Another paragraph.</paragraph>
  </page>
  <page number="7">
    <paragraph>Some text.</paragraph>
    <image_ref key="page_7_illustration" />
  </page>
  <page number="10">
    <image_ref key="encounter_map_goblin_cave" />
  </page>
</Chapter_1>
"""
        xml_doc = XMLDocument.from_xml(xml_string)

        # Convert to Journal
        journal = Journal.from_xml_document(xml_doc)

        # Verify image_registry has been populated
        assert len(journal.image_registry) == 3

        # Verify first image ref
        assert "page_5_top_battle_map" in journal.image_registry
        img1 = journal.image_registry["page_5_top_battle_map"]
        assert img1.key == "page_5_top_battle_map"
        assert img1.source_page == 5  # Parsed from key
        assert img1.type == "map"  # Inferred from "battle_map"

        # Verify second image ref
        assert "page_7_illustration" in journal.image_registry
        img2 = journal.image_registry["page_7_illustration"]
        assert img2.key == "page_7_illustration"
        assert img2.source_page == 7  # Parsed from key
        assert img2.type == "illustration"  # Inferred from key

        # Verify third image ref (no page number in key)
        assert "encounter_map_goblin_cave" in journal.image_registry
        img3 = journal.image_registry["encounter_map_goblin_cave"]
        assert img3.key == "encounter_map_goblin_cave"
        assert img3.source_page == 10  # Falls back to actual page number
        assert img3.type == "map"  # Inferred from "map" in key

    def test_image_refs_remain_in_content_stream(self):
        """Test that ImageRef elements stay in content (not removed during extraction)."""
        xml_string = """
<Chapter_1>
  <page number="5">
    <chapter_title>Test Chapter</chapter_title>
    <paragraph>Before image.</paragraph>
    <image_ref key="page_5_map" />
    <paragraph>After image.</paragraph>
  </page>
</Chapter_1>
"""
        xml_doc = XMLDocument.from_xml(xml_string)
        journal = Journal.from_xml_document(xml_doc)

        # Verify ImageRef is in the registry
        assert "page_5_map" in journal.image_registry

        # Verify ImageRef is still in the content
        chapter = journal.chapters[0]
        assert len(chapter.content) == 3
        assert chapter.content[1].type == "image_ref"
        assert chapter.content[1].data.key == "page_5_map"
