"""Tests for XML to Journal HTML converter."""

import pytest
from pathlib import Path
from src.foundry.xml_to_journal_html import convert_xml_to_journal_data


class TestXMLToJournalConverter:
    """Tests for XML to Journal HTML conversion."""

    def test_convert_single_xml_file(self, tmp_path):
        """Test converting a single XML file to journal data."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<chapter>
    <title>Test Chapter</title>
    <section>
        <heading>Introduction</heading>
        <paragraph>This is a test paragraph.</paragraph>
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

    def test_convert_multiple_xml_files(self, tmp_path):
        """Test converting multiple XML files."""
        xml_dir = tmp_path / "documents"
        xml_dir.mkdir()

        # Create test XML files
        for i in range(1, 4):
            xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<chapter>
    <title>Chapter {i}</title>
    <paragraph>Content for chapter {i}.</paragraph>
</chapter>"""
            (xml_dir / f"0{i}_Chapter_{i}.xml").write_text(xml_content)

        from src.foundry.xml_to_journal_html import convert_xml_directory_to_journals

        results = convert_xml_directory_to_journals(str(xml_dir))

        assert len(results) == 3
        assert all("name" in r and "html" in r for r in results)
        assert results[0]["name"] == "01_Chapter_1"
