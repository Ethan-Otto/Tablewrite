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


class TestImageManipulation:
    """Test Journal image manipulation methods."""

    def test_journal_add_image(self):
        """Test that add_image() adds a new image to the registry."""
        # Create a simple journal
        xml_string = """
<Chapter_1>
  <page number="1">
    <chapter_title>Test Chapter</chapter_title>
    <paragraph>Some content.</paragraph>
  </page>
</Chapter_1>
"""
        xml_doc = XMLDocument.from_xml(xml_string)
        journal = Journal.from_xml_document(xml_doc)

        # Verify registry is empty initially
        assert len(journal.image_registry) == 0

        # Add a new image (e.g., scene artwork)
        scene_img = ImageMetadata(
            key="scene_artwork_tavern",
            source_page=1,
            type="illustration",
            description="A cozy tavern interior",
            file_path="/path/to/tavern.png"
        )
        journal.add_image("scene_artwork_tavern", scene_img)

        # Verify image was added
        assert len(journal.image_registry) == 1
        assert "scene_artwork_tavern" in journal.image_registry
        assert journal.image_registry["scene_artwork_tavern"].key == "scene_artwork_tavern"
        assert journal.image_registry["scene_artwork_tavern"].type == "illustration"
        assert journal.image_registry["scene_artwork_tavern"].description == "A cozy tavern interior"

    def test_journal_reposition_image(self):
        """Test that reposition_image() changes image placement."""
        # Create a journal with an existing image
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

        # Verify image exists
        assert "page_5_map" in journal.image_registry
        original_metadata = journal.image_registry["page_5_map"]

        # Initially, insert_before_content_id should be None
        assert original_metadata.insert_before_content_id is None

        # Reposition the image to appear before a specific content ID
        journal.reposition_image("page_5_map", "chapter_0_section_-1_content_5")

        # Verify the metadata was updated
        updated_metadata = journal.image_registry["page_5_map"]
        assert updated_metadata.insert_before_content_id == "chapter_0_section_-1_content_5"

    def test_journal_remove_image(self):
        """Test that remove_image() deletes image from registry."""
        # Create a journal with an existing image
        xml_string = """
<Chapter_1>
  <page number="5">
    <chapter_title>Test Chapter</chapter_title>
    <image_ref key="page_5_map" />
  </page>
</Chapter_1>
"""
        xml_doc = XMLDocument.from_xml(xml_string)
        journal = Journal.from_xml_document(xml_doc)

        # Verify image exists
        assert "page_5_map" in journal.image_registry
        assert len(journal.image_registry) == 1

        # Remove the image
        journal.remove_image("page_5_map")

        # Verify image was removed
        assert "page_5_map" not in journal.image_registry
        assert len(journal.image_registry) == 0

    def test_remove_nonexistent_image_does_nothing(self):
        """Test that removing a non-existent image doesn't raise an error."""
        xml_string = """
<Chapter_1>
  <page number="1">
    <chapter_title>Test Chapter</chapter_title>
    <paragraph>Content.</paragraph>
  </page>
</Chapter_1>
"""
        xml_doc = XMLDocument.from_xml(xml_string)
        journal = Journal.from_xml_document(xml_doc)

        # Try to remove non-existent image
        journal.remove_image("non_existent_key")

        # Should not raise error
        assert len(journal.image_registry) == 0
