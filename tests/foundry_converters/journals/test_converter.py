"""Tests for foundry_converters.journals.converter."""

from pathlib import Path

import pytest
from foundry_converters.journals import convert_xml_to_journal_data
from foundry_converters.journals.converter import (
    convert_xml_directory_to_journals,
    add_uuid_links,
)


@pytest.mark.unit
class TestConvertXmlToJournalData:
    """Tests for convert_xml_to_journal_data function."""

    def test_converts_single_xml_file(self, tmp_path):
        """Should convert a single XML file to journal data structure.

        Uses XML structure that matches xml_to_html_content expectations:
        - title/chapter_title -> h1
        - section (with text) -> h2
        - p -> p
        """
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<chapter>
    <title>Test Chapter</title>
    <section>Introduction
        <p>This is a test paragraph.</p>
    </section>
</chapter>"""

        xml_file = tmp_path / "01_Test_Chapter.xml"
        xml_file.write_text(xml_content)

        result = convert_xml_to_journal_data(str(xml_file))

        assert result["name"] == "01_Test_Chapter"
        assert "<h1>Test Chapter</h1>" in result["html"]
        assert "<h2>Introduction</h2>" in result["html"]
        assert "<p>This is a test paragraph.</p>" in result["html"]
        assert "metadata" in result
        assert result["metadata"]["source_file"] == str(xml_file)

    def test_extracts_chapter_number_from_filename(self, tmp_path):
        """Should extract chapter number from prefixed filenames."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<chapter>
    <title>Chapter One</title>
</chapter>"""

        xml_file = tmp_path / "03_Chapter_One.xml"
        xml_file.write_text(xml_content)

        result = convert_xml_to_journal_data(str(xml_file))

        assert result["metadata"]["chapter_number"] == "03"

    def test_handles_filename_without_chapter_number(self, tmp_path):
        """Should handle filenames without numeric prefix."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<chapter>
    <title>Appendix</title>
</chapter>"""

        xml_file = tmp_path / "Appendix_Items.xml"
        xml_file.write_text(xml_content)

        result = convert_xml_to_journal_data(str(xml_file))

        assert result["metadata"]["chapter_number"] is None
        assert result["name"] == "Appendix_Items"

    def test_converts_boxed_text_to_aside(self, tmp_path):
        """Should convert boxed_text elements to styled aside HTML."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<chapter>
    <boxed_text>
        <p>Read aloud text here.</p>
    </boxed_text>
</chapter>"""

        xml_file = tmp_path / "01_Chapter.xml"
        xml_file.write_text(xml_content)

        result = convert_xml_to_journal_data(str(xml_file))

        assert "<aside" in result["html"]
        assert "Read aloud text here." in result["html"]

    def test_converts_markdown_formatting(self, tmp_path):
        """Should convert markdown bold and italic to HTML tags."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<chapter>
    <p>This is **bold** and *italic* text.</p>
</chapter>"""

        xml_file = tmp_path / "01_Chapter.xml"
        xml_file.write_text(xml_content)

        result = convert_xml_to_journal_data(str(xml_file))

        assert "<strong>bold</strong>" in result["html"]
        assert "<em>italic</em>" in result["html"]


@pytest.mark.unit
class TestConvertXmlDirectoryToJournals:
    """Tests for convert_xml_directory_to_journals function."""

    def test_converts_multiple_xml_files(self, tmp_path):
        """Should convert all XML files in a directory to journal data."""
        xml_dir = tmp_path / "documents"
        xml_dir.mkdir()

        for i in range(1, 4):
            xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<chapter>
    <title>Chapter {i}</title>
    <p>Content for chapter {i}.</p>
</chapter>"""
            (xml_dir / f"0{i}_Chapter_{i}.xml").write_text(xml_content)

        results = convert_xml_directory_to_journals(str(xml_dir))

        assert len(results) == 3
        assert all("name" in r and "html" in r for r in results)
        assert results[0]["name"] == "01_Chapter_1"
        assert results[1]["name"] == "02_Chapter_2"
        assert results[2]["name"] == "03_Chapter_3"

    def test_raises_error_for_nonexistent_directory(self, tmp_path):
        """Should raise ValueError for non-existent directory."""
        with pytest.raises(ValueError, match="Directory does not exist"):
            convert_xml_directory_to_journals(str(tmp_path / "nonexistent"))

    def test_returns_empty_list_for_empty_directory(self, tmp_path):
        """Should return empty list if directory has no XML files."""
        xml_dir = tmp_path / "empty"
        xml_dir.mkdir()

        results = convert_xml_directory_to_journals(str(xml_dir))

        assert results == []


@pytest.mark.unit
class TestAddUuidLinks:
    """Tests for add_uuid_links function."""

    def test_replaces_entity_mention_with_uuid_link(self):
        """Should replace entity names with @UUID links."""
        html = "<p>You find a Hat of Disguise.</p>"
        entity_refs = {"Hat of Disguise": "Compendium.dnd5e.items.abc123"}

        result = add_uuid_links(html, entity_refs)

        assert "@UUID[Compendium.dnd5e.items.abc123]{Hat of Disguise}" in result

    def test_replaces_multiple_entities(self):
        """Should replace all entity types in HTML."""
        html = "<p>You find a Hat of Disguise and meet Klarg.</p>"
        entity_refs = {
            "Hat of Disguise": "Compendium.dnd5e.items.abc123",
            "Klarg": "Actor.xyz789",
        }

        result = add_uuid_links(html, entity_refs)

        assert "@UUID[Compendium.dnd5e.items.abc123]{Hat of Disguise}" in result
        assert "@UUID[Actor.xyz789]{Klarg}" in result

    def test_handles_empty_entity_refs(self):
        """Should return unchanged HTML when no entity refs provided."""
        html = "<p>Some content here.</p>"

        result = add_uuid_links(html, {})

        assert result == html

    def test_prioritizes_longer_entity_names(self):
        """Should match longer names first to avoid partial matches."""
        html = "<p>You find a Longsword +1 and a Longsword.</p>"
        entity_refs = {
            "Longsword": "Compendium.dnd5e.items.abc",
            "Longsword +1": "Compendium.dnd5e.items.xyz",
        }

        result = add_uuid_links(html, entity_refs)

        assert "@UUID[Compendium.dnd5e.items.xyz]{Longsword +1}" in result
        assert "@UUID[Compendium.dnd5e.items.abc]{Longsword}." in result


@pytest.mark.unit
class TestConvertWithRealData:
    """Integration tests using real fixture XML data."""

    def test_converts_introduction_chapter(self):
        """Should convert the Introduction chapter from real fixture file."""
        fixture_path = (
            Path(__file__).parent.parent.parent / "fixtures" / "xml" / "01_Introduction.xml"
        )

        if not fixture_path.exists():
            pytest.skip(f"Fixture file not found: {fixture_path}")

        result = convert_xml_to_journal_data(str(fixture_path))

        # Verify basic structure
        assert result["name"] == "01_Introduction"
        assert "html" in result

        # Verify expected content from the Introduction chapter
        assert "<h1>INTRODUCTION</h1>" in result["html"]
        assert "Lost Mine of Phandelver" in result["html"]
        assert "RUNNING THE ADVENTURE" in result["html"]
        assert "THE DUNGEON MASTER" in result["html"]

        # Verify boxed text is converted (RULES TO GAME BY section)
        assert "<aside" in result["html"]

        # Verify metadata
        assert result["metadata"]["chapter_number"] == "01"
        assert result["metadata"]["source_file"] == str(fixture_path)

    def test_converts_goblin_arrows_chapter(self):
        """Should convert the Goblin Arrows chapter from real fixture file."""
        fixture_path = (
            Path(__file__).parent.parent.parent
            / "fixtures"
            / "xml"
            / "02_Part_1_Goblin_Arrows.xml"
        )

        if not fixture_path.exists():
            pytest.skip(f"Fixture file not found: {fixture_path}")

        result = convert_xml_to_journal_data(str(fixture_path))

        # Verify basic structure
        assert result["name"] == "02_Part_1_Goblin_Arrows"
        assert "html" in result

        # Verify metadata extraction
        assert result["metadata"]["chapter_number"] == "02"
