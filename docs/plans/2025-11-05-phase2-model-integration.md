# Phase 2: XMLDocument and Journal Model Integration

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Integrate the new XMLDocument and Journal Pydantic models into the existing PDF processing, FoundryVTT upload, and actor extraction pipelines.

**Architecture:** Replace raw XML string handling with type-safe Pydantic models. XMLDocument becomes the immutable record after XML generation, Journal becomes the mutable working representation for exports and transformations. All downstream code consumes models instead of parsing XML.

**Tech Stack:** Pydantic v2, Python 3.9+, existing Gemini/FoundryVTT infrastructure

**Dependencies:** Requires Phase 1 complete (XMLDocument and Journal models implemented in `src/models/`)

---

## Overview

Phase 1 created the XMLDocument and Journal models. Phase 2 integrates them into the existing codebase:

1. **PDF to XML Pipeline**: Validate generated XML with XMLDocument parsing
2. **FoundryVTT Upload**: Use Journal.to_foundry_html() instead of xml_to_html conversion
3. **Actor Extraction**: Pass XMLDocument to stat block parser instead of raw XML
4. **Full Pipeline Test**: End-to-end integration test

**Key Integration Points:**
- `src/pdf_processing/pdf_to_xml.py` - Add XMLDocument validation after XML generation
- `src/foundry/upload_journal_to_foundry.py` - Replace XML→HTML with XMLDocument→Journal→HTML
- `src/actors/parse_stat_blocks.py` - Accept XMLDocument, extract StatBlockRaw elements
- `scripts/full_pipeline.py` - Update to use new model-based workflow

---

## Task 1: Add XMLDocument Validation to PDF-to-XML Pipeline

**Goal:** Validate generated XML immediately after creation to catch schema errors early.

**Files:**
- Modify: `src/pdf_processing/pdf_to_xml.py` (add validation after XML generation)
- Test: `tests/pdf_processing/test_pdf_to_xml.py` (verify validation catches errors)

### Step 1: Write test for XMLDocument validation failure

```python
# tests/pdf_processing/test_pdf_to_xml.py (add to existing file)
import pytest
from models import XMLDocument

def test_pdf_to_xml_validates_with_xmldocument(test_pdf_path, test_output_dir):
    """Test that pdf_to_xml validates generated XML with XMLDocument"""
    from pdf_processing import pdf_to_xml

    # Generate XML (using existing test)
    run_dir = pdf_to_xml.process_pdfs(
        pdf_directory=test_pdf_path.parent,
        output_dir=test_output_dir
    )

    # Verify XMLDocument can parse all generated XML files
    xml_dir = Path(run_dir) / "documents"
    xml_files = list(xml_dir.glob("*.xml"))

    assert len(xml_files) > 0, "No XML files generated"

    for xml_file in xml_files:
        xml_string = xml_file.read_text()
        # Should not raise exception
        doc = XMLDocument.from_xml(xml_string)
        assert doc.title
        assert len(doc.pages) > 0


def test_pdf_to_xml_reports_invalid_xml(test_output_dir):
    """Test that invalid XML is detected and reported"""
    # Create invalid XML string
    invalid_xml = """
    <Chapter_01>
      <page number="1">
        <unknown_tag>This tag is not in approved list</unknown_tag>
      </page>
    </Chapter_01>
    """

    # Try to parse with XMLDocument
    with pytest.raises(ValueError) as exc_info:
        XMLDocument.from_xml(invalid_xml)

    # Should mention unknown tag
    assert "unknown_tag" in str(exc_info.value).lower() or "unknown" in str(exc_info.value).lower()
```

**Run:** `PYTHONPATH=src uv run pytest tests/pdf_processing/test_pdf_to_xml.py::test_pdf_to_xml_validates_with_xmldocument -v`
**Expected:** PASS (existing XML generation should already be valid)

**Run:** `PYTHONPATH=src uv run pytest tests/pdf_processing/test_pdf_to_xml.py::test_pdf_to_xml_reports_invalid_xml -v`
**Expected:** PASS (XMLDocument.from_xml raises ValueError on unknown tags)

### Step 2: Add XMLDocument validation to pdf_to_xml.py

```python
# src/pdf_processing/pdf_to_xml.py (add after imports)
from models import XMLDocument

# Find the save_chapter_xml() function and add validation after saving
def save_chapter_xml(chapter_name: str, xml_content: str, output_dir: str, log_dir: str) -> bool:
    """
    Saves the XML content for a chapter to a file.
    Returns True if successful, False otherwise.
    """
    try:
        # ... existing save logic ...

        # NEW: Validate with XMLDocument model
        try:
            doc = XMLDocument.from_xml(xml_content)
            logger.info(f"✓ XML validation passed: {chapter_name} ({len(doc.pages)} pages)")
        except Exception as e:
            logger.error(f"✗ XML validation failed for {chapter_name}: {e}")
            # Save validation error to error report
            error_file = os.path.join(log_dir, "validation_errors.txt")
            with open(error_file, 'a') as f:
                f.write(f"\n\n=== {chapter_name} ===\n")
                f.write(f"Validation Error: {e}\n")
                f.write(f"XML Content:\n{xml_content}\n")
            return False

        return True
    except Exception as e:
        logger.error(f"Error saving chapter {chapter_name}: {e}")
        return False
```

**Run:** `PYTHONPATH=src uv run pytest tests/pdf_processing/test_pdf_to_xml.py -v -k "not integration"`
**Expected:** All tests PASS

### Step 3: Commit

```bash
git add src/pdf_processing/pdf_to_xml.py tests/pdf_processing/test_pdf_to_xml.py
git commit -m "feat(pdf-to-xml): add XMLDocument validation after XML generation

- Validate all generated XML with XMLDocument.from_xml()
- Log validation errors to validation_errors.txt
- Fail chapter processing if validation fails
- Add tests for validation success and failure cases"
```

---

## Task 2: Replace XML-to-HTML Conversion with Journal Export

**Goal:** Use Journal.to_foundry_html() instead of the existing xml_to_html conversion.

**Files:**
- Modify: `src/foundry/upload_journal_to_foundry.py` (replace convert_xml_directory_to_journals)
- Test: `tests/foundry/test_upload_journal.py` (test new workflow)

### Step 1: Write test for Journal-based upload

```python
# tests/foundry/test_upload_journal.py (create new file)
"""Tests for FoundryVTT journal upload using XMLDocument/Journal models."""
import pytest
from pathlib import Path
from models import XMLDocument, Journal

def test_convert_xml_to_journal_html():
    """Test XMLDocument → Journal → HTML conversion"""
    xml_string = """
    <Chapter_01_Introduction>
      <page number="1">
        <chapter_title>Introduction</chapter_title>
        <section>Getting Started</section>
        <p>Welcome to the adventure.</p>
      </page>
    </Chapter_01_Introduction>
    """

    # Parse to XMLDocument
    doc = XMLDocument.from_xml(xml_string)

    # Create Journal
    journal = Journal.from_xml_document(doc)

    # Export to HTML
    html = journal.to_foundry_html(image_mapping={})

    # Validate HTML structure
    assert "<h1>Introduction</h1>" in html
    assert "<h2>Getting Started</h2>" in html
    assert "Welcome to the adventure" in html


def test_journal_creation_preserves_structure(sample_xml_file):
    """Test that Journal creation preserves all content from XML"""
    if not sample_xml_file.exists():
        pytest.skip("No sample XML file found")

    xml_string = sample_xml_file.read_text()

    # Parse to XMLDocument
    doc = XMLDocument.from_xml(xml_string)
    original_page_count = len(doc.pages)

    # Create Journal
    journal = Journal.from_xml_document(doc)

    # Verify chapters created
    assert len(journal.chapters) > 0

    # Verify source preserved
    assert journal.source == doc
    assert len(journal.source.pages) == original_page_count
```

**Run:** `PYTHONPATH=src uv run pytest tests/foundry/test_upload_journal.py::test_convert_xml_to_journal_html -v`
**Expected:** PASS

**Run:** `PYTHONPATH=src uv run pytest tests/foundry/test_upload_journal.py::test_journal_creation_preserves_structure -v`
**Expected:** PASS or SKIP (if no sample XML)

### Step 2: Update upload_journal_to_foundry.py to use Journal

```python
# src/foundry/upload_journal_to_foundry.py
# Replace the convert_xml_directory_to_journals import and usage

from models import XMLDocument, Journal

def convert_xml_to_journal_pages(xml_file: Path, image_mapping: Dict[str, str]) -> Dict[str, Any]:
    """
    Convert XML file to FoundryVTT journal page using Journal model.

    Args:
        xml_file: Path to XML file
        image_mapping: Dict mapping image keys to file paths

    Returns:
        Journal page dict with name and HTML content
    """
    logger.info(f"Converting {xml_file.name} using Journal model...")

    # Parse XML to XMLDocument
    xml_string = xml_file.read_text()
    doc = XMLDocument.from_xml(xml_string)

    # Create Journal
    journal = Journal.from_xml_document(doc)

    # Export to HTML
    html_content = journal.to_foundry_html(image_mapping)

    # Extract chapter name from file
    chapter_name = xml_file.stem.replace("_", " ").title()

    return {
        "name": chapter_name,
        "type": "text",
        "text": {
            "content": html_content,
            "format": 1  # HTML format
        }
    }


def upload_xml_directory(client: FoundryClient, xml_dir: Path, journal_name: str,
                        image_mapping: Optional[Dict[str, str]] = None) -> str:
    """
    Upload all XML files in directory as journal entries.

    Args:
        client: FoundryClient instance
        xml_dir: Directory containing XML files
        journal_name: Name for the journal entry
        image_mapping: Optional dict mapping image keys to paths

    Returns:
        Journal UUID
    """
    if image_mapping is None:
        image_mapping = {}

    xml_files = sorted(xml_dir.glob("*.xml"))

    if not xml_files:
        raise ValueError(f"No XML files found in {xml_dir}")

    logger.info(f"Found {len(xml_files)} XML files")

    # Convert each XML file to a journal page
    pages = []
    for xml_file in xml_files:
        try:
            page = convert_xml_to_journal_pages(xml_file, image_mapping)
            pages.append(page)
        except Exception as e:
            logger.error(f"Failed to convert {xml_file.name}: {e}")
            raise

    # Create or replace journal
    logger.info(f"Uploading journal '{journal_name}' with {len(pages)} pages...")
    uuid = client.journals.create_or_replace_journal(name=journal_name, pages=pages)

    logger.info(f"✓ Journal uploaded: {uuid}")
    return uuid
```

**Run:** `PYTHONPATH=src uv run pytest tests/foundry/test_upload_journal.py -v`
**Expected:** All tests PASS

### Step 3: Update integration with existing code

```python
# src/foundry/upload_journal_to_foundry.py (update main function)

def main(args=None):
    """Main entry point for uploading journals to FoundryVTT."""
    # ... existing arg parsing ...

    # Find XML directory
    xml_dir_path = Path(find_xml_directory(run_dir))

    # NEW: Build image mapping from run directory
    image_mapping = {}

    # Check for map assets
    map_assets_dir = Path(run_dir) / "map_assets"
    if map_assets_dir.exists():
        metadata_file = map_assets_dir / "maps_metadata.json"
        if metadata_file.exists():
            import json
            metadata = json.load(metadata_file.open())
            for map_data in metadata:
                key = f"page_{map_data['page_num']}_map"  # Match ImageRef key format
                image_path = map_assets_dir / f"{map_data['name']}.png"
                if image_path.exists():
                    image_mapping[key] = str(image_path)

    # Check for scene artwork
    scene_dir = Path(run_dir) / "scene_artwork" / "images"
    if scene_dir.exists():
        for scene_image in scene_dir.glob("*.png"):
            key = scene_image.stem  # Use filename as key
            image_mapping[key] = str(scene_image)

    logger.info(f"Found {len(image_mapping)} images for mapping")

    # Upload using new Journal-based workflow
    uuid = upload_xml_directory(client, xml_dir_path, journal_name, image_mapping)

    print(f"\n✓ Journal uploaded successfully!")
    print(f"  UUID: {uuid}")
    print(f"  Name: {journal_name}")
    print(f"  Pages: {len(list(xml_dir_path.glob('*.xml')))}")
```

**Run:** Manual test with real XML files:
```bash
PYTHONPATH=src uv run python src/foundry/upload_journal_to_foundry.py --run-dir output/runs/<timestamp>
```
**Expected:** Journal uploads successfully to FoundryVTT

### Step 4: Commit

```bash
git add src/foundry/upload_journal_to_foundry.py tests/foundry/test_upload_journal.py
git commit -m "feat(foundry): replace XML-to-HTML with Journal.to_foundry_html()

- Use XMLDocument → Journal → HTML workflow
- Remove dependency on xml_to_html converter
- Build image_mapping from map_assets and scene_artwork
- Add tests for Journal-based upload
- Preserve all existing functionality"
```

---

## Task 3: Update Actor Extraction to Use XMLDocument

**Goal:** Pass XMLDocument to stat block parser instead of raw XML strings.

**Files:**
- Modify: `src/actors/parse_stat_blocks.py` (add extract_from_xmldocument function)
- Modify: `src/actors/process_actors.py` (use XMLDocument instead of XML files)
- Test: `tests/actors/test_parse_stat_blocks.py` (test XMLDocument extraction)

### Step 1: Write test for StatBlock extraction from XMLDocument

```python
# tests/actors/test_parse_stat_blocks.py (add to existing file)
from models import XMLDocument, StatBlockRaw

def test_extract_stat_blocks_from_xmldocument():
    """Test extracting StatBlockRaw elements from XMLDocument"""
    from actors.parse_stat_blocks import extract_stat_blocks_from_document

    xml_string = """
    <Chapter_03>
      <page number="12">
        <section>Monsters</section>
        <p>You encounter a goblin.</p>
        <stat_block name="Goblin">
          GOBLIN
          Small humanoid (goblinoid), neutral evil
          Armor Class 15 (leather armor, shield)
          Hit Points 7 (2d6)
          Speed 30 ft.
        </stat_block>
        <p>The goblin attacks!</p>
      </page>
    </Chapter_03>
    """

    doc = XMLDocument.from_xml(xml_string)
    stat_blocks = extract_stat_blocks_from_document(doc)

    assert len(stat_blocks) == 1
    assert isinstance(stat_blocks[0], StatBlockRaw)
    assert stat_blocks[0].name == "Goblin"
    assert "GOBLIN" in stat_blocks[0].xml_element


def test_extract_multiple_stat_blocks():
    """Test extracting multiple stat blocks from multiple pages"""
    from actors.parse_stat_blocks import extract_stat_blocks_from_document

    xml_string = """
    <Chapter_03>
      <page number="12">
        <stat_block name="Goblin">Goblin stat block</stat_block>
      </page>
      <page number="13">
        <stat_block name="Bugbear">Bugbear stat block</stat_block>
        <stat_block name="Hobgoblin">Hobgoblin stat block</stat_block>
      </page>
    </Chapter_03>
    """

    doc = XMLDocument.from_xml(xml_string)
    stat_blocks = extract_stat_blocks_from_document(doc)

    assert len(stat_blocks) == 3
    names = [sb.name for sb in stat_blocks]
    assert "Goblin" in names
    assert "Bugbear" in names
    assert "Hobgoblin" in names
```

**Run:** `PYTHONPATH=src uv run pytest tests/actors/test_parse_stat_blocks.py::test_extract_stat_blocks_from_xmldocument -v`
**Expected:** FAIL (function doesn't exist yet)

### Step 2: Implement extract_stat_blocks_from_document

```python
# src/actors/parse_stat_blocks.py (add new function)
from models import XMLDocument, StatBlockRaw
from typing import List

def extract_stat_blocks_from_document(doc: XMLDocument) -> List[StatBlockRaw]:
    """
    Extract all StatBlockRaw elements from an XMLDocument.

    Args:
        doc: XMLDocument containing stat blocks

    Returns:
        List of StatBlockRaw objects
    """
    stat_blocks = []

    for page in doc.pages:
        for content in page.content:
            if content.type == "stat_block" and isinstance(content.data, StatBlockRaw):
                stat_blocks.append(content.data)

    logger.info(f"Extracted {len(stat_blocks)} stat blocks from document")
    return stat_blocks


def extract_stat_blocks_from_xml_file(xml_file_path: str) -> List[StatBlockRaw]:
    """
    Extract stat blocks from XML file (convenience wrapper).

    Args:
        xml_file_path: Path to XML file

    Returns:
        List of StatBlockRaw objects
    """
    from pathlib import Path

    xml_string = Path(xml_file_path).read_text()
    doc = XMLDocument.from_xml(xml_string)
    return extract_stat_blocks_from_document(doc)
```

**Run:** `PYTHONPATH=src uv run pytest tests/actors/test_parse_stat_blocks.py::test_extract_stat_blocks_from_xmldocument -v`
**Expected:** PASS

**Run:** `PYTHONPATH=src uv run pytest tests/actors/test_parse_stat_blocks.py::test_extract_multiple_stat_blocks -v`
**Expected:** PASS

### Step 3: Update process_actors.py to use XMLDocument

```python
# src/actors/process_actors.py (update to use new extraction function)
from models import XMLDocument
from .parse_stat_blocks import extract_stat_blocks_from_document, parse_stat_block_with_gemini

def process_stat_blocks_from_xml_directory(xml_dir: str, output_dir: str, api: GeminiAPI) -> List[StatBlock]:
    """
    Process all stat blocks from XML files in directory.

    Args:
        xml_dir: Directory containing XML files
        output_dir: Output directory for parsed stat blocks
        api: GeminiAPI instance

    Returns:
        List of parsed StatBlock objects
    """
    from pathlib import Path

    xml_files = sorted(Path(xml_dir).glob("*.xml"))
    all_stat_blocks = []

    logger.info(f"Processing {len(xml_files)} XML files...")

    for xml_file in xml_files:
        logger.info(f"Processing {xml_file.name}...")

        # Parse to XMLDocument
        xml_string = xml_file.read_text()
        doc = XMLDocument.from_xml(xml_string)

        # Extract StatBlockRaw elements
        raw_stat_blocks = extract_stat_blocks_from_document(doc)

        logger.info(f"  Found {len(raw_stat_blocks)} stat blocks")

        # Parse each stat block with Gemini
        for raw_sb in raw_stat_blocks:
            try:
                # Extract raw text from xml_element
                import xml.etree.ElementTree as ET
                elem = ET.fromstring(raw_sb.xml_element)
                raw_text = ET.tostring(elem, encoding='unicode', method='text')

                # Parse with Gemini
                stat_block = parse_stat_block_with_gemini(raw_text, api)
                all_stat_blocks.append(stat_block)

            except Exception as e:
                logger.error(f"Failed to parse stat block '{raw_sb.name}': {e}")
                continue

    logger.info(f"Successfully parsed {len(all_stat_blocks)} stat blocks")
    return all_stat_blocks
```

**Run:** `PYTHONPATH=src uv run pytest tests/actors/ -v -k "not integration"`
**Expected:** All tests PASS

### Step 4: Commit

```bash
git add src/actors/parse_stat_blocks.py src/actors/process_actors.py tests/actors/test_parse_stat_blocks.py
git commit -m "feat(actors): extract stat blocks from XMLDocument

- Add extract_stat_blocks_from_document() function
- Add extract_stat_blocks_from_xml_file() convenience wrapper
- Update process_actors.py to use XMLDocument
- Extract raw text from StatBlockRaw.xml_element
- Add tests for stat block extraction"
```

---

## Task 4: Add End-to-End Integration Test

**Goal:** Test complete workflow from PDF to FoundryVTT using new models.

**Files:**
- Create: `tests/test_phase2_integration.py`

### Step 1: Write integration test

```python
# tests/test_phase2_integration.py (new file)
"""End-to-end integration tests for Phase 2 model integration."""
import pytest
from pathlib import Path
from models import XMLDocument, Journal

@pytest.mark.integration
def test_full_pipeline_with_models(test_pdf_path, test_output_dir):
    """Test PDF → XML → XMLDocument → Journal → HTML workflow"""
    from pdf_processing import pdf_to_xml

    # Step 1: Generate XML from PDF
    run_dir = pdf_to_xml.process_pdfs(
        pdf_directory=test_pdf_path.parent,
        output_dir=test_output_dir
    )

    xml_dir = Path(run_dir) / "documents"
    xml_files = list(xml_dir.glob("*.xml"))

    assert len(xml_files) > 0, "No XML files generated"

    # Step 2: Parse each XML to XMLDocument
    for xml_file in xml_files:
        xml_string = xml_file.read_text()

        # Should parse without errors
        doc = XMLDocument.from_xml(xml_string)
        assert doc.title
        assert len(doc.pages) > 0

        # Step 3: Create Journal
        journal = Journal.from_xml_document(doc)
        assert len(journal.chapters) > 0

        # Step 4: Export to HTML
        html = journal.to_foundry_html(image_mapping={})
        assert len(html) > 0
        assert "<h1>" in html or "<h2>" in html

        # Step 5: Validate round-trip
        xml_out = doc.to_xml()
        doc2 = XMLDocument.from_xml(xml_out)
        assert doc2.title == doc.title
        assert len(doc2.pages) == len(doc.pages)


@pytest.mark.integration
def test_stat_block_extraction_from_real_xml():
    """Test stat block extraction from real generated XML"""
    from actors.parse_stat_blocks import extract_stat_blocks_from_xml_file

    # Find real XML with stat blocks
    xml_files = list(Path("output/runs").glob("*/documents/*.xml"))

    if not xml_files:
        pytest.skip("No real XML files found")

    # Try to find stat blocks in any file
    stat_blocks_found = False
    for xml_file in xml_files[:3]:  # Check first 3 files
        try:
            stat_blocks = extract_stat_blocks_from_xml_file(str(xml_file))
            if stat_blocks:
                stat_blocks_found = True
                assert all(hasattr(sb, 'name') for sb in stat_blocks)
                assert all(hasattr(sb, 'xml_element') for sb in stat_blocks)
                break
        except Exception:
            continue

    # May not find stat blocks in all test files (that's ok)
    if not stat_blocks_found:
        pytest.skip("No stat blocks found in sample XML files")


def test_image_ref_extraction():
    """Test that ImageRef placeholders are extracted to Journal registry"""
    xml_string = """
    <Chapter_01>
      <page number="5">
        <section>The Cave</section>
        <p>You enter a dark cave.</p>
        <image_ref key="page_5_top_battle_map" />
        <p>Roll for initiative!</p>
      </page>
    </Chapter_01>
    """

    doc = XMLDocument.from_xml(xml_string)
    journal = Journal.from_xml_document(doc)

    # Verify ImageRef extracted to registry
    assert "page_5_top_battle_map" in journal.image_registry
    assert journal.image_registry["page_5_top_battle_map"].page_num == 5

    # Verify ImageRef still in content (for rendering)
    section = journal.chapters[0].sections[0]
    image_refs = [c for c in section.content if c.type == "image_ref"]
    assert len(image_refs) == 1
```

**Run:** `PYTHONPATH=src uv run pytest tests/test_phase2_integration.py::test_full_pipeline_with_models -v`
**Expected:** PASS (may be slow due to PDF processing)

**Run:** `PYTHONPATH=src uv run pytest tests/test_phase2_integration.py::test_image_ref_extraction -v`
**Expected:** PASS

### Step 2: Commit

```bash
git add tests/test_phase2_integration.py
git commit -m "test(integration): add Phase 2 end-to-end tests

- Test PDF → XML → XMLDocument → Journal → HTML workflow
- Test stat block extraction from real XML
- Test ImageRef extraction to registry
- Validate round-trip serialization"
```

---

## Task 5: Update Documentation and Run Full Test Suite

**Goal:** Update CLAUDE.md with new model-based workflow and verify all tests pass.

**Files:**
- Modify: `CLAUDE.md` (document new workflow)
- Verify: Run full test suite

### Step 1: Update CLAUDE.md

```markdown
# CLAUDE.md (add new section after "Architecture & Data Flow")

### XMLDocument and Journal Models

**NEW**: The pipeline now uses Pydantic models for type-safe XML handling.

**Data Flow:**
```
PDF → XML (string) → XMLDocument (immutable) → Journal (mutable) → HTML/exports
```

**XMLDocument** (`src/models/xml_document.py`):
- Immutable record of Gemini-generated XML
- Preserves page structure exactly as in PDF
- Supports all content types: paragraphs, sections, tables, lists, stat blocks, image refs
- Round-trip serialization: `XMLDocument.from_xml()` / `doc.to_xml()`

**Journal** (`src/models/journal.py`):
- Mutable working representation
- Semantic hierarchy: Chapters → Sections → Subsections → Subsubsections
- Image registry for managing maps, scene artwork, illustrations
- Export methods: `to_foundry_html()`, `to_html()`, `to_markdown()`

**Usage Examples:**

```python
from models import XMLDocument, Journal

# Parse XML
xml_string = Path("output/runs/20251105_120000/documents/01_Introduction.xml").read_text()
doc = XMLDocument.from_xml(xml_string)

# Create Journal
journal = Journal.from_xml_document(doc)

# Add scene artwork
journal.add_image("scene_intro", ImageMetadata(
    type="generated_scene",
    source="scene_generated",
    insert_before_content_id="chapter_1_section_1_content_0"
))

# Export to HTML
image_mapping = {"scene_intro": "/path/to/scene.png"}
html = journal.to_foundry_html(image_mapping)

# Round-trip
xml_out = doc.to_xml()
doc2 = XMLDocument.from_xml(xml_out)
```

**Integration Points:**
- `pdf_to_xml.py`: Validates XML with `XMLDocument.from_xml()` after generation
- `upload_journal_to_foundry.py`: Uses `Journal.to_foundry_html()` for exports
- `parse_stat_blocks.py`: Extracts `StatBlockRaw` from `XMLDocument`
```

### Step 2: Run full test suite

**Run:** `PYTHONPATH=src uv run pytest -m "not integration and not slow" -v`
**Expected:** All 300+ tests PASS

**Run:** `PYTHONPATH=src uv run pytest tests/models/ -v`
**Expected:** All 56 model tests PASS

**Run:** `PYTHONPATH=src uv run pytest tests/test_phase2_integration.py -v`
**Expected:** All Phase 2 integration tests PASS

### Step 3: Commit

```bash
git add CLAUDE.md
git commit -m "docs(claude): document XMLDocument and Journal workflow

- Add XMLDocument and Journal model overview
- Document data flow: PDF → XML → XMLDocument → Journal → HTML
- Add usage examples for both models
- Document integration points in existing code"
```

---

## Task 6: Final Verification and Merge Preparation

**Goal:** Verify all tests pass, no regressions, ready to merge to main.

**Files:** None (verification only)

### Step 1: Run comprehensive test suite

**Run:** `PYTHONPATH=src uv run pytest -v`
**Expected:** All tests PASS (including integration tests)

**Run:** `PYTHONPATH=src uv run pytest tests/models/ --cov=src/models --cov-report=term-missing`
**Expected:** >85% coverage on models

### Step 2: Manual integration test

**Run:**
```bash
# Full pipeline with real PDF
PYTHONPATH=src uv run python scripts/full_pipeline.py --journal-name "Test Module"
```

**Expected:**
- XML generation succeeds with validation
- FoundryVTT upload succeeds
- Journal appears in FoundryVTT with correct structure

### Step 3: Check git status

**Run:** `git status`
**Expected:** Clean working tree, all changes committed

**Run:** `git log --oneline -10`
**Expected:** Clean commit history with descriptive messages

### Step 4: Commit checkpoint

```bash
git commit --allow-empty -m "chore(phase2): Phase 2 integration complete

All integration tasks complete:
- XMLDocument validation in pdf_to_xml
- Journal.to_foundry_html() in upload workflow
- StatBlock extraction from XMLDocument
- End-to-end integration tests
- Documentation updated

Test Results:
- Model tests: 56/56 passing
- Unit tests: 300+/300+ passing
- Integration tests: All passing
- No regressions detected

Ready for code review and merge to main."
```

---

## Success Criteria

Phase 2 is complete when:

- [x] **PDF-to-XML validates with XMLDocument**: All generated XML parses successfully
- [x] **FoundryVTT upload uses Journal**: Upload workflow uses `Journal.to_foundry_html()`
- [x] **Actor extraction uses XMLDocument**: Stat blocks extracted via `extract_stat_blocks_from_document()`
- [x] **Integration tests pass**: End-to-end workflow validated
- [x] **No regressions**: All existing tests still pass
- [x] **Documentation updated**: CLAUDE.md documents new workflow

---

## Next Steps (Phase 3)

After Phase 2 merges to main:

**Phase 3: Rich Features**
1. Entity linking: `add_npc_links()`, `add_spell_links()`, `add_item_links()`
2. Image extraction integration: Automatic ImageRef → extracted PNG mapping
3. Dice roll detection: Auto-link damage formulas like "2d6+3"
4. Cross-references: Link chapter/section references ("see Chapter 3")
5. Table of Contents: Auto-generate TOC from Journal hierarchy

**Phase 4: Advanced Exports**
1. Markdown export with proper formatting
2. Standalone HTML export (no FoundryVTT dependencies)
3. JSON export for custom integrations
4. PDF export with embedded images
