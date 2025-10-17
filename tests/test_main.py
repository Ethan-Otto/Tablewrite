"""
End-to-end integration tests for the complete PDF → XML → HTML pipeline.

Tests the full workflow:
1. PDF splitting (if needed)
2. PDF to XML conversion using Gemini API
3. XML to HTML conversion

NOTE: These tests make REAL Gemini API calls and will consume API quota.
Run with caution and ensure you have API key configured.
"""

import pytest
from pathlib import Path
import sys
import os
from datetime import datetime
import xml.etree.ElementTree as ET
import fitz

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pdf_processing.pdf_to_xml import (
    configure_gemini,
    process_chapter,
    main as pdf_to_xml_main
)
from pdf_processing.xml_to_html import (
    xml_to_html_content,
    generate_html_page,
    main as xml_to_html_main
)


@pytest.fixture
def test_run_dir(test_output_dir):
    """Create a timestamped test run directory (temporary, auto-cleaned)."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = test_output_dir / "test_runs" / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


@pytest.fixture(scope="session")
def integration_run_dir(integration_test_output_dir):
    """Create a timestamped test run directory for integration tests (persistent, shared across session)."""
    return integration_test_output_dir


@pytest.fixture(scope="session")
def test_documents_dir(integration_run_dir):
    """Create documents directory for XML output (shared across session)."""
    docs_dir = integration_run_dir / "documents"
    docs_dir.mkdir(exist_ok=True)
    return docs_dir


@pytest.fixture(scope="session")
def test_logs_dir(integration_run_dir):
    """Create intermediate logs directory (shared across session)."""
    logs_dir = integration_run_dir / "intermediate_logs"
    logs_dir.mkdir(exist_ok=True)
    return logs_dir


@pytest.fixture(scope="session")
def test_html_dir(test_documents_dir):
    """Create HTML output directory (shared across session)."""
    html_dir = test_documents_dir / "html"
    html_dir.mkdir(exist_ok=True)
    return html_dir


class TestEndToEndPipeline:
    """Test the complete pipeline from PDF to HTML."""

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.requires_api
    @pytest.mark.requires_pdf
    def test_single_page_pipeline(self, test_pdf_path, test_documents_dir, test_logs_dir, test_html_dir, check_api_key):
        """
        Test complete pipeline with a single-page PDF.

        WARNING: Makes REAL Gemini API calls.
        """
        configure_gemini()

        # Step 1: Extract first page as a separate PDF
        doc = fitz.open(test_pdf_path)
        single_page_pdf = test_logs_dir / "test_single_page.pdf"

        single_doc = fitz.open()
        single_doc.insert_pdf(doc, from_page=0, to_page=0)
        single_doc.save(single_page_pdf)
        single_doc.close()
        doc.close()

        # Step 2: Convert PDF to XML
        xml_output_path = test_documents_dir / "test_single_page.xml"
        page_errors = process_chapter(
            str(single_page_pdf),
            str(xml_output_path),
            str(test_logs_dir)
        )

        # Verify XML was created
        assert xml_output_path.exists(), "XML file was not created"
        assert len(page_errors) == 0, f"Page errors occurred: {page_errors}"

        # Verify XML is valid
        tree = ET.parse(xml_output_path)
        root = tree.getroot()
        assert root is not None

        # Check for page element
        pages = root.findall(".//page")
        assert len(pages) >= 1, "XML should contain at least one page element"

        # Step 3: Convert XML to HTML
        html_output_path = test_html_dir / "test_single_page.html"
        nav_links = [("Test Page", "test_single_page.html")]
        generate_html_page(xml_output_path, nav_links, html_output_path)

        # Verify HTML was created
        assert html_output_path.exists(), "HTML file was not created"

        # Verify HTML structure
        html_content = html_output_path.read_text()
        assert "<!DOCTYPE html>" in html_content
        assert "<html" in html_content
        assert "</html>" in html_content
        assert "<body>" in html_content
        assert "</body>" in html_content

        # Verify XML content appears in HTML
        tree = ET.parse(xml_output_path)
        root = tree.getroot()

        # Extract paragraph text from XML
        xml_paragraphs = []
        for p_elem in root.findall(".//p"):
            if p_elem.text and p_elem.text.strip():
                text = p_elem.text.strip()
                if len(text) > 20:  # Only check substantial paragraphs
                    xml_paragraphs.append(text)

        # Verify paragraphs appear in HTML
        found_count = 0
        missing_paragraphs = []
        for paragraph in xml_paragraphs:
            if paragraph in html_content:
                found_count += 1
            else:
                missing_paragraphs.append(paragraph[:50] + "...")

        if len(xml_paragraphs) > 0:
            found_percentage = (found_count / len(xml_paragraphs)) * 100
            assert found_percentage >= 80, \
                f"Only {found_percentage:.1f}% of XML paragraphs found in HTML. Missing: {missing_paragraphs[:3]}"

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.requires_api
    @pytest.mark.requires_pdf
    def test_multi_page_pipeline(self, test_pdf_path, test_documents_dir, test_logs_dir, test_html_dir, check_api_key):
        """
        Test complete pipeline with a multi-page PDF (first 3 pages).

        WARNING: Makes REAL Gemini API calls (3 pages = 3 API calls).
        """
        configure_gemini()

        # Step 1: Extract first 3 pages as a separate PDF
        doc = fitz.open(test_pdf_path)
        multi_page_pdf = test_logs_dir / "test_multi_page.pdf"

        multi_doc = fitz.open()
        multi_doc.insert_pdf(doc, from_page=0, to_page=2)  # First 3 pages
        multi_doc.save(multi_page_pdf)
        multi_doc.close()
        doc.close()

        # Step 2: Convert PDF to XML
        xml_output_path = test_documents_dir / "test_multi_page.xml"
        page_errors = process_chapter(
            str(multi_page_pdf),
            str(xml_output_path),
            str(test_logs_dir)
        )

        # Verify XML was created
        assert xml_output_path.exists(), "XML file was not created"
        assert len(page_errors) == 0, f"Page errors occurred: {page_errors}"

        # Verify XML contains multiple pages
        tree = ET.parse(xml_output_path)
        root = tree.getroot()
        pages = root.findall(".//page")
        assert len(pages) == 3, f"XML should contain 3 page elements, found {len(pages)}"

        # Verify page numbers
        page_numbers = [page.get('number') for page in pages]
        assert page_numbers == ['1', '2', '3'], f"Unexpected page numbers: {page_numbers}"

        # Step 3: Convert XML to HTML
        html_output_path = test_html_dir / "test_multi_page.html"
        nav_links = [("Test Multi-Page", "test_multi_page.html")]
        generate_html_page(xml_output_path, nav_links, html_output_path)

        # Verify HTML was created
        assert html_output_path.exists(), "HTML file was not created"

        # Verify HTML has content from multiple pages
        html_content = html_output_path.read_text()
        assert len(html_content) > 1000, "HTML should contain substantial content from 3 pages"


class TestPipelineOutputStructure:
    """Test the structure of pipeline outputs."""

    @pytest.mark.requires_pdf
    def test_output_directory_structure(self, test_pdf_path, integration_run_dir, monkeypatch):
        """
        Test that the pipeline creates the expected directory structure.

        Uses mocked Gemini API to avoid real API calls.
        """
        documents_dir = integration_run_dir / "documents"
        logs_dir = integration_run_dir / "intermediate_logs"
        documents_dir.mkdir(exist_ok=True)
        logs_dir.mkdir(exist_ok=True)

        # Extract single page first
        doc = fitz.open(test_pdf_path)
        test_pdf = integration_run_dir / "test_chapter.pdf"

        single_doc = fitz.open()
        single_doc.insert_pdf(doc, from_page=0, to_page=0)
        single_pdf_bytes = single_doc.write()
        single_doc.save(test_pdf)
        single_doc.close()
        doc.close()

        # Get actual word count from PDF
        from pdf_processing.pdf_to_xml import get_legible_text_from_page, count_words
        text, _ = get_legible_text_from_page(single_pdf_bytes, 1, str(logs_dir))
        actual_word_count = count_words(text)

        # Mock Gemini API responses
        class MockResponse:
            def __init__(self, text):
                self.text = text

        class MockUploadedFile:
            def __init__(self):
                self.name = "mock_file_123"

        def mock_generate_content(prompt, file_obj=None):
            # Generate mock content with matching word count
            mock_words = " ".join([f"word{i}" for i in range(actual_word_count)])
            return MockResponse(f"<page><p>{mock_words}</p></page>")

        def mock_upload_file(file_path, display_name=None):
            return MockUploadedFile()

        def mock_delete_file(file_name):
            pass

        # Configure mock Gemini API
        configure_gemini()
        from pdf_processing import pdf_to_xml

        # Patch the Gemini API methods
        monkeypatch.setattr(pdf_to_xml.gemini_api, "generate_content", mock_generate_content)
        monkeypatch.setattr(pdf_to_xml.gemini_api, "upload_file", mock_upload_file)
        monkeypatch.setattr(pdf_to_xml.gemini_api, "delete_file", mock_delete_file)

        # Run conversion with mocked API
        xml_output = documents_dir / "test_chapter.xml"
        process_chapter(str(test_pdf), str(xml_output), str(logs_dir))

        # Verify directory structure
        assert documents_dir.exists(), "documents/ directory should exist"
        assert logs_dir.exists(), "intermediate_logs/ directory should exist"

        # Verify chapter log directory
        chapter_log_dir = logs_dir / "test_chapter"
        assert chapter_log_dir.exists(), "Chapter log directory should exist"

        # Verify pages directory
        pages_dir = chapter_log_dir / "pages"
        assert pages_dir.exists(), "pages/ directory should exist"

        # Verify page artifacts
        assert (pages_dir / "page_1.pdf").exists(), "Page PDF should exist"
        assert (pages_dir / "page_1_embedded.txt").exists() or \
               (pages_dir / "page_1_ocr.txt").exists(), "Text extraction output should exist"
        assert (pages_dir / "page_1.xml").exists(), "Page XML should exist"

        # Verify final XML
        assert xml_output.exists(), "Final XML output should exist"
        assert (chapter_log_dir / "final_unverified.xml").exists(), "Unverified XML should exist"


class TestPipelineXMLToHTML:
    """Test XML to HTML conversion in the pipeline."""

    def test_xml_to_html_with_pipeline_output(self, sample_xml_content, test_documents_dir, test_html_dir):
        """Test that pipeline XML converts correctly to HTML."""
        # Create a sample XML file
        xml_file = test_documents_dir / "sample_chapter.xml"
        xml_file.write_text(sample_xml_content)

        # Convert to HTML
        html_file = test_html_dir / "sample_chapter.html"
        nav_links = [("Sample Chapter", "sample_chapter.html")]
        generate_html_page(xml_file, nav_links, html_file)

        # Verify HTML
        assert html_file.exists()
        html_content = html_file.read_text()

        # Check HTML structure
        assert "<!DOCTYPE html>" in html_content
        assert "<nav>" in html_content
        assert "Sample Chapter" in html_content

    def test_xml_content_appears_in_html(self, sample_xml_content, test_documents_dir, test_html_dir):
        """Test that text content from XML appears in the generated HTML."""
        # Create a sample XML file
        xml_file = test_documents_dir / "content_test.xml"
        xml_file.write_text(sample_xml_content)

        # Convert to HTML
        html_file = test_html_dir / "content_test.html"
        nav_links = [("Content Test", "content_test.html")]
        generate_html_page(xml_file, nav_links, html_file)

        # Parse XML to extract text content
        tree = ET.parse(xml_file)
        root = tree.getroot()

        # Get all text content from XML (excluding tag names)
        xml_texts = []
        for elem in root.iter():
            if elem.text and elem.text.strip():
                xml_texts.append(elem.text.strip())
            if elem.tail and elem.tail.strip():
                xml_texts.append(elem.tail.strip())

        # Read generated HTML
        html_content = html_file.read_text()

        # Verify that XML text content appears in HTML
        # Check a reasonable sample of text content (at least 80%)
        # Note: Markdown syntax (**bold**, *italic*) is converted to HTML tags,
        # so we check for word presence rather than exact string matching
        import re
        found_count = 0
        missing_texts = []
        for text in xml_texts:
            # Skip very short text (like single words from tags)
            if len(text) > 10:
                # Extract the core words from the text (stripping markdown and punctuation)
                words = re.findall(r'\w+', text)
                # Check if at least 80% of the words appear in HTML
                found_words = sum(1 for word in words if word in html_content)
                if len(words) > 0 and (found_words / len(words)) >= 0.8:
                    found_count += 1
                else:
                    missing_texts.append(text)

        total_significant_texts = len([t for t in xml_texts if len(t) > 10])
        if total_significant_texts > 0:
            found_percentage = (found_count / total_significant_texts) * 100
            assert found_percentage >= 80, \
                f"Only {found_percentage:.1f}% of XML text content found in HTML. Missing texts: {missing_texts[:3]}"

    def test_multiple_xml_to_html_conversion(self, sample_xml_content, test_documents_dir, test_html_dir):
        """Test converting multiple XML files to HTML with navigation."""
        # Create multiple XML files
        xml_files = []
        for i in range(3):
            xml_file = test_documents_dir / f"chapter_{i+1}.xml"
            xml_file.write_text(sample_xml_content)
            xml_files.append(xml_file)

        # Convert all to HTML
        xml_to_html_main(str(test_documents_dir), str(test_html_dir))

        # Verify all HTML files created
        for i in range(3):
            html_file = test_html_dir / f"chapter_{i+1}.html"
            assert html_file.exists(), f"HTML file {i+1} should exist"

            # Verify navigation links to other chapters
            html_content = html_file.read_text()
            for j in range(3):
                if i != j:
                    assert f"chapter_{j+1}.html" in html_content, \
                        f"Chapter {i+1} should link to chapter {j+1}"


class TestPipelineErrorHandling:
    """Test error handling in the pipeline."""

    def test_empty_pdf_handling(self, test_documents_dir, test_logs_dir, test_output_dir):
        """Test handling of empty/minimal PDF."""
        # Create minimal PDF with no content
        empty_pdf = test_output_dir / "empty.pdf"
        doc = fitz.open()
        page = doc.new_page()
        doc.save(empty_pdf)
        doc.close()

        # This test doesn't call API, just verifies structure
        # In real usage, empty PDFs would be handled by process_chapter
        assert empty_pdf.exists()
        assert fitz.open(empty_pdf).page_count == 1

    def test_invalid_xml_to_html(self, test_documents_dir, test_html_dir):
        """Test HTML generation with invalid XML."""
        # Create invalid XML
        invalid_xml = test_documents_dir / "invalid.xml"
        invalid_xml.write_text("<unclosed>")

        # Try to convert to HTML (should handle gracefully)
        html_content = xml_to_html_content(invalid_xml)

        # Should return error message
        assert isinstance(html_content, str)
        assert "Error" in html_content or "error" in html_content


class TestTimestampedRuns:
    """Test that runs are properly timestamped and isolated."""

    def test_timestamped_run_creation(self, test_output_dir):
        """Test that timestamped run directories are created correctly."""
        test_runs_dir = test_output_dir / "test_runs"
        test_runs_dir.mkdir(exist_ok=True)

        # Create multiple timestamped runs with unique suffixes to avoid collision
        timestamps = []
        for i in range(2):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S") + f"_{i:02d}"
            run_dir = test_runs_dir / timestamp
            run_dir.mkdir(exist_ok=True)
            timestamps.append(timestamp)

            # Create expected subdirectories
            (run_dir / "documents").mkdir(exist_ok=True)
            (run_dir / "intermediate_logs").mkdir(exist_ok=True)
            (run_dir / "documents" / "html").mkdir(exist_ok=True)

            # Verify structure
            assert run_dir.exists()
            assert (run_dir / "documents").exists()
            assert (run_dir / "intermediate_logs").exists()
            assert (run_dir / "documents" / "html").exists()

        # Verify runs are separate
        run_dirs = sorted([d.name for d in test_runs_dir.iterdir() if d.is_dir()])
        assert len(run_dirs) == 2, f"Expected 2 run directories, found {len(run_dirs)}"

    def test_run_isolation(self, test_output_dir):
        """Test that different runs don't interfere with each other."""
        test_runs_dir = test_output_dir / "test_runs"
        test_runs_dir.mkdir(exist_ok=True)

        # Create two runs with different content
        timestamp1 = datetime.now().strftime("%Y%m%d_%H%M%S") + "_01"
        timestamp2 = datetime.now().strftime("%Y%m%d_%H%M%S") + "_02"

        run1_dir = test_runs_dir / timestamp1 / "documents"
        run2_dir = test_runs_dir / timestamp2 / "documents"

        run1_dir.mkdir(parents=True, exist_ok=True)
        run2_dir.mkdir(parents=True, exist_ok=True)

        # Write different content to each run
        (run1_dir / "output.xml").write_text("<run1>content</run1>")
        (run2_dir / "output.xml").write_text("<run2>content</run2>")

        # Verify isolation
        assert (run1_dir / "output.xml").read_text() == "<run1>content</run1>"
        assert (run2_dir / "output.xml").read_text() == "<run2>content</run2>"
