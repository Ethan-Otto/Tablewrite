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
