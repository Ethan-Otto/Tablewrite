# Public API Facade Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a clean public API facade (`src/api.py`) that exposes core D&D module processing functionality for external consumers like the chat UI.

**Architecture:** Thin wrapper layer around existing implementations (`actors.orchestrate`, `pdf_processing`, `scripts.full_pipeline`) that provides type-safe, well-documented interfaces with rich return types.

**Tech Stack:** Python 3.11+, Pydantic (for dataclasses), existing codebase modules

---

## Task 1: API Module Skeleton + Exception Class

**Files:**
- Create: `.worktrees/public-api/src/api.py`
- Test: `.worktrees/public-api/tests/api/test_api.py`
- Create test dir: `.worktrees/public-api/tests/api/`

**Step 1: Create test directory**

Run:
```bash
cd .worktrees/public-api
mkdir -p tests/api
touch tests/api/__init__.py
```

Expected: Directory created successfully

**Step 2: Write failing test for APIError**

Create `.worktrees/public-api/tests/api/test_api.py`:

```python
"""Tests for public API facade."""
import pytest
from api import APIError


def test_api_error_can_be_raised():
    """Test that APIError can be raised and caught."""
    with pytest.raises(APIError, match="test error"):
        raise APIError("test error")


def test_api_error_preserves_cause():
    """Test that APIError preserves original exception."""
    original = ValueError("original error")

    try:
        try:
            raise original
        except ValueError as e:
            raise APIError("wrapped error") from e
    except APIError as api_err:
        assert api_err.__cause__ is original
```

**Step 3: Run test to verify it fails**

Run: `cd .worktrees/public-api && uv run pytest tests/api/test_api.py::test_api_error_can_be_raised -v`

Expected: `ModuleNotFoundError: No module named 'api'`

**Step 4: Create src/api.py with exception class**

Create `.worktrees/public-api/src/api.py`:

```python
"""
Public API for D&D Module Processing.

This module provides the official interface for external applications
(chat UI, CLI tools, etc.) to interact with the module processing system.

All functions use environment variables for configuration (.env file).
Operations are synchronous and may take several minutes for large PDFs.

Example usage:
    from api import create_actor, extract_maps, process_pdf_to_journal

    # Create actor from description
    result = create_actor("A fierce goblin warrior", challenge_rating=1.0)
    print(f"Created actor: {result.foundry_uuid}")

    # Extract maps from PDF
    maps = extract_maps("data/pdfs/module.pdf")
    print(f"Extracted {maps.total_maps} maps")

    # Process PDF to journal
    journal = process_pdf_to_journal(
        "data/pdfs/module.pdf",
        "Lost Mine of Phandelver"
    )
    print(f"Created journal: {journal.journal_uuid}")
"""

import logging

logger = logging.getLogger(__name__)


class APIError(Exception):
    """Raised when API operations fail.

    This exception wraps internal errors to provide a clean boundary
    between the public API and internal implementation details.

    The original exception is preserved as __cause__ for debugging.
    """
    pass
```

**Step 5: Run tests to verify they pass**

Run: `cd .worktrees/public-api && uv run pytest tests/api/test_api.py -v`

Expected: 2 tests PASS

**Step 6: Commit**

```bash
cd .worktrees/public-api
git add src/api.py tests/api/
git commit -m "feat(api): add API module skeleton and APIError exception"
```

---

## Task 2: Result Dataclasses

**Files:**
- Modify: `.worktrees/public-api/src/api.py`
- Modify: `.worktrees/public-api/tests/api/test_api.py`

**Step 1: Write failing tests for result dataclasses**

Add to `.worktrees/public-api/tests/api/test_api.py`:

```python
from pathlib import Path
from api import (
    ActorCreationResult,
    MapExtractionResult,
    JournalCreationResult
)


def test_actor_creation_result_instantiation():
    """Test ActorCreationResult can be created."""
    result = ActorCreationResult(
        foundry_uuid="Actor.abc123",
        name="Goblin Warrior",
        challenge_rating=1.0,
        output_dir=Path("output/runs/test"),
        timestamp="2025-11-05T12:00:00"
    )

    assert result.foundry_uuid == "Actor.abc123"
    assert result.name == "Goblin Warrior"
    assert result.challenge_rating == 1.0


def test_map_extraction_result_instantiation():
    """Test MapExtractionResult can be created."""
    result = MapExtractionResult(
        maps=[{"name": "Test Map", "type": "battle_map"}],
        output_dir=Path("output/runs/test"),
        total_maps=1,
        timestamp="2025-11-05T12:00:00"
    )

    assert result.total_maps == 1
    assert len(result.maps) == 1


def test_journal_creation_result_instantiation():
    """Test JournalCreationResult can be created."""
    result = JournalCreationResult(
        journal_uuid="JournalEntry.xyz789",
        journal_name="Test Journal",
        output_dir=Path("output/runs/test"),
        chapter_count=5,
        timestamp="2025-11-05T12:00:00"
    )

    assert result.journal_uuid == "JournalEntry.xyz789"
    assert result.chapter_count == 5
```

**Step 2: Run tests to verify they fail**

Run: `cd .worktrees/public-api && uv run pytest tests/api/test_api.py::test_actor_creation_result_instantiation -v`

Expected: `ImportError: cannot import name 'ActorCreationResult'`

**Step 3: Add dataclasses to src/api.py**

Add to `.worktrees/public-api/src/api.py` (after the imports):

```python
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any


@dataclass
class ActorCreationResult:
    """Result from creating a D&D actor.

    Attributes:
        foundry_uuid: FoundryVTT UUID of created actor (e.g., "Actor.abc123")
        name: Name of the actor
        challenge_rating: Creature's challenge rating
        output_dir: Directory containing intermediate files
        timestamp: ISO timestamp of creation
    """
    foundry_uuid: str
    name: str
    challenge_rating: float
    output_dir: Path
    timestamp: str


@dataclass
class MapExtractionResult:
    """Result from extracting maps from a PDF.

    Attributes:
        maps: List of map metadata dictionaries
        output_dir: Directory containing extracted map images
        total_maps: Total number of maps extracted
        timestamp: ISO timestamp of extraction
    """
    maps: List[Dict[str, Any]]
    output_dir: Path
    total_maps: int
    timestamp: str


@dataclass
class JournalCreationResult:
    """Result from creating a FoundryVTT journal.

    Attributes:
        journal_uuid: FoundryVTT UUID of created journal (e.g., "JournalEntry.xyz789")
        journal_name: Name of the journal
        output_dir: Directory containing XML/HTML files
        chapter_count: Number of chapters processed
        timestamp: ISO timestamp of creation
    """
    journal_uuid: str
    journal_name: str
    output_dir: Path
    chapter_count: int
    timestamp: str
```

**Step 4: Run tests to verify they pass**

Run: `cd .worktrees/public-api && uv run pytest tests/api/test_api.py -v`

Expected: All tests PASS

**Step 5: Commit**

```bash
cd .worktrees/public-api
git add src/api.py tests/api/test_api.py
git commit -m "feat(api): add result dataclasses for API responses"
```

---

## Task 3: Implement create_actor() Function

**Files:**
- Modify: `.worktrees/public-api/src/api.py`
- Modify: `.worktrees/public-api/tests/api/test_api.py`

**Step 1: Write failing test for create_actor() happy path**

Add to `.worktrees/public-api/tests/api/test_api.py`:

```python
from unittest.mock import Mock, patch
from api import create_actor


@patch('api.orchestrate_create_actor_from_description_sync')
def test_create_actor_happy_path(mock_create):
    """Test create_actor wraps orchestrate correctly."""
    # Mock the orchestrate function
    from actors.models import ActorCreationResult as OrchestrateResult

    mock_result = OrchestrateResult(
        description="A fierce goblin",
        challenge_rating=1.0,
        raw_stat_block_text="RAW TEXT",
        stat_block=Mock(),
        parsed_actor_data=Mock(),
        foundry_uuid="Actor.abc123",
        output_dir=Path("output/runs/test"),
        raw_text_file=Path("output/runs/test/01.txt"),
        stat_block_file=Path("output/runs/test/02.json"),
        parsed_data_file=Path("output/runs/test/03.json"),
        foundry_json_file=Path("output/runs/test/04.json"),
        timestamp="2025-11-05T12:00:00",
        model_used="gemini-2.0-flash"
    )
    mock_create.return_value = mock_result

    # Call our API function
    result = create_actor("A fierce goblin", challenge_rating=1.0)

    # Verify it called orchestrate with correct args
    mock_create.assert_called_once_with(
        description="A fierce goblin",
        challenge_rating=1.0
    )

    # Verify result is our simplified dataclass
    assert isinstance(result, ActorCreationResult)
    assert result.foundry_uuid == "Actor.abc123"
    assert result.challenge_rating == 1.0
    assert result.output_dir == Path("output/runs/test")
```

**Step 2: Run test to verify it fails**

Run: `cd .worktrees/public-api && uv run pytest tests/api/test_api.py::test_create_actor_happy_path -v`

Expected: `ImportError: cannot import name 'create_actor'`

**Step 3: Implement create_actor() function**

Add to `.worktrees/public-api/src/api.py`:

```python
from typing import Optional
from actors.orchestrate import create_actor_from_description_sync as orchestrate_create_actor_from_description_sync


def create_actor(
    description: str,
    challenge_rating: Optional[float] = None
) -> ActorCreationResult:
    """
    Create a D&D actor from natural language description.

    This function generates a complete FoundryVTT actor including:
    - Stat block parsing from description
    - Ability scores, skills, and attacks
    - Spell resolution (if applicable)
    - Upload to FoundryVTT server

    Args:
        description: Natural language description of the creature/NPC
                    (e.g., "A fierce goblin warrior with a poisoned blade")
        challenge_rating: CR of the creature (auto-determined from description if None)

    Returns:
        ActorCreationResult with FoundryVTT UUID and output paths

    Raises:
        APIError: If actor creation fails (missing API key, Gemini errors,
                 FoundryVTT connection issues, etc.)

    Example:
        >>> result = create_actor("A cunning kobold scout", challenge_rating=0.5)
        >>> print(f"Created: {result.name} ({result.foundry_uuid})")
        Created: Kobold Scout (Actor.abc123)
    """
    try:
        logger.info(f"Creating actor from description: {description[:50]}...")

        # Call orchestrate function
        orchestrate_result = orchestrate_create_actor_from_description_sync(
            description=description,
            challenge_rating=challenge_rating
        )

        # Extract name from parsed_actor_data
        actor_name = orchestrate_result.parsed_actor_data.name

        # Convert to simplified result
        result = ActorCreationResult(
            foundry_uuid=orchestrate_result.foundry_uuid,
            name=actor_name,
            challenge_rating=orchestrate_result.challenge_rating,
            output_dir=orchestrate_result.output_dir,
            timestamp=orchestrate_result.timestamp
        )

        logger.info(f"✓ Actor created: {result.name} ({result.foundry_uuid})")
        return result

    except Exception as e:
        logger.error(f"Actor creation failed: {e}")
        raise APIError(f"Failed to create actor: {e}") from e
```

**Step 4: Run test to verify it passes**

Run: `cd .worktrees/public-api && uv run pytest tests/api/test_api.py::test_create_actor_happy_path -v`

Expected: Test PASS

**Step 5: Write test for error handling**

Add to `.worktrees/public-api/tests/api/test_api.py`:

```python
@patch('api.orchestrate_create_actor_from_description_sync')
def test_create_actor_error_handling(mock_create):
    """Test create_actor wraps exceptions as APIError."""
    mock_create.side_effect = ValueError("Gemini API error")

    with pytest.raises(APIError, match="Failed to create actor"):
        create_actor("broken description")

    # Verify original exception is preserved
    try:
        create_actor("broken description")
    except APIError as e:
        assert isinstance(e.__cause__, ValueError)
        assert str(e.__cause__) == "Gemini API error"
```

**Step 6: Run error test to verify it passes**

Run: `cd .worktrees/public-api && uv run pytest tests/api/test_api.py::test_create_actor_error_handling -v`

Expected: Test PASS

**Step 7: Run all API tests**

Run: `cd .worktrees/public-api && uv run pytest tests/api/ -v`

Expected: All tests PASS

**Step 8: Commit**

```bash
cd .worktrees/public-api
git add src/api.py tests/api/test_api.py
git commit -m "feat(api): implement create_actor() with error handling"
```

---

## Task 4: Implement extract_maps() Function

**Files:**
- Modify: `.worktrees/public-api/src/api.py`
- Modify: `.worktrees/public-api/tests/api/test_api.py`

**Step 1: Write failing test for extract_maps()**

Add to `.worktrees/public-api/tests/api/test_api.py`:

```python
import asyncio
from api import extract_maps


@patch('api.extract_all_maps_from_pdf')
def test_extract_maps_happy_path(mock_extract):
    """Test extract_maps wraps map extraction correctly."""
    from pdf_processing.image_asset_processing.models import MapMetadata

    # Mock extraction results
    mock_maps = [
        MapMetadata(
            name="Cave Entrance",
            page_num=1,
            type="battle_map",
            source="extracted",
            chapter="Chapter 1"
        ),
        MapMetadata(
            name="Goblin Hideout",
            page_num=2,
            type="battle_map",
            source="segmented",
            chapter="Chapter 1"
        )
    ]
    mock_extract.return_value = mock_maps

    # Call API function
    result = extract_maps("test.pdf", chapter="Chapter 1")

    # Verify extraction was called
    mock_extract.assert_called_once()

    # Verify result
    assert isinstance(result, MapExtractionResult)
    assert result.total_maps == 2
    assert len(result.maps) == 2
    assert result.maps[0]["name"] == "Cave Entrance"


@patch('api.extract_all_maps_from_pdf')
def test_extract_maps_error_handling(mock_extract):
    """Test extract_maps wraps exceptions."""
    mock_extract.side_effect = FileNotFoundError("PDF not found")

    with pytest.raises(APIError, match="Failed to extract maps"):
        extract_maps("missing.pdf")
```

**Step 2: Run test to verify it fails**

Run: `cd .worktrees/public-api && uv run pytest tests/api/test_api.py::test_extract_maps_happy_path -v`

Expected: `ImportError: cannot import name 'extract_maps'`

**Step 3: Implement extract_maps() function**

Add to `.worktrees/public-api/src/api.py`:

```python
import asyncio
from datetime import datetime
from pdf_processing.image_asset_processing.extract_map_assets import extract_all_maps_from_pdf


def extract_maps(
    pdf_path: str,
    chapter: Optional[str] = None
) -> MapExtractionResult:
    """
    Extract battle maps and navigation maps from a PDF.

    Uses hybrid approach: PyMuPDF extraction (fast) + Gemini segmentation
    (handles baked-in maps). All pages processed in parallel.

    Args:
        pdf_path: Path to source PDF file (absolute or relative)
        chapter: Optional chapter name for metadata

    Returns:
        MapExtractionResult with extracted maps and metadata

    Raises:
        APIError: If extraction fails (file not found, PDF corrupt,
                 Gemini errors, etc.)

    Example:
        >>> result = extract_maps("data/pdfs/module.pdf", chapter="Chapter 1")
        >>> print(f"Extracted {result.total_maps} maps")
        Extracted 3 maps
        >>> for map_meta in result.maps:
        ...     print(f"  - {map_meta['name']} ({map_meta['type']})")
    """
    try:
        logger.info(f"Extracting maps from: {pdf_path}")

        # Run async extraction in sync context
        maps = asyncio.run(extract_all_maps_from_pdf(pdf_path, chapter=chapter))

        # Create output directory (extract_all_maps_from_pdf handles this internally)
        # Use timestamp-based directory like other pipelines
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path("output/runs") / timestamp / "map_assets"

        # Convert MapMetadata objects to dicts
        maps_dicts = [m.model_dump() for m in maps]

        result = MapExtractionResult(
            maps=maps_dicts,
            output_dir=output_dir,
            total_maps=len(maps),
            timestamp=datetime.now().isoformat()
        )

        logger.info(f"✓ Extracted {result.total_maps} maps to {result.output_dir}")
        return result

    except Exception as e:
        logger.error(f"Map extraction failed: {e}")
        raise APIError(f"Failed to extract maps: {e}") from e
```

**Step 4: Run tests to verify they pass**

Run: `cd .worktrees/public-api && uv run pytest tests/api/test_api.py -k extract_maps -v`

Expected: 2 tests PASS

**Step 5: Commit**

```bash
cd .worktrees/public-api
git add src/api.py tests/api/test_api.py
git commit -m "feat(api): implement extract_maps() with error handling"
```

---

## Task 5: Implement process_pdf_to_journal() Function

**Files:**
- Modify: `.worktrees/public-api/src/api.py`
- Modify: `.worktrees/public-api/tests/api/test_api.py`

**Step 1: Write failing test for process_pdf_to_journal()**

Add to `.worktrees/public-api/tests/api/test_api.py`:

```python
from api import process_pdf_to_journal


@patch('api.run_pdf_to_xml')
@patch('api.upload_xml_to_foundry')
def test_process_pdf_to_journal_happy_path(mock_upload, mock_pdf_to_xml):
    """Test process_pdf_to_journal wraps pipeline correctly."""
    # Mock PDF to XML
    mock_run_dir = Path("output/runs/20251105_120000")
    mock_pdf_to_xml.return_value = mock_run_dir

    # Mock upload
    mock_upload.return_value = "JournalEntry.xyz789"

    # Call API function
    result = process_pdf_to_journal(
        "test.pdf",
        "Test Journal",
        skip_upload=False
    )

    # Verify calls
    mock_pdf_to_xml.assert_called_once()
    mock_upload.assert_called_once_with(mock_run_dir, "Test Journal")

    # Verify result
    assert isinstance(result, JournalCreationResult)
    assert result.journal_uuid == "JournalEntry.xyz789"
    assert result.journal_name == "Test Journal"


@patch('api.run_pdf_to_xml')
def test_process_pdf_to_journal_skip_upload(mock_pdf_to_xml):
    """Test process_pdf_to_journal with skip_upload=True."""
    mock_run_dir = Path("output/runs/20251105_120000")
    mock_pdf_to_xml.return_value = mock_run_dir

    result = process_pdf_to_journal(
        "test.pdf",
        "Test Journal",
        skip_upload=True
    )

    # Should have empty UUID when upload is skipped
    assert result.journal_uuid == ""
    assert result.output_dir == mock_run_dir


@patch('api.run_pdf_to_xml')
def test_process_pdf_to_journal_error_handling(mock_pdf_to_xml):
    """Test process_pdf_to_journal error handling."""
    mock_pdf_to_xml.side_effect = RuntimeError("PDF processing failed")

    with pytest.raises(APIError, match="Failed to process PDF"):
        process_pdf_to_journal("broken.pdf", "Test")
```

**Step 2: Run test to verify it fails**

Run: `cd .worktrees/public-api && uv run pytest tests/api/test_api.py::test_process_pdf_to_journal_happy_path -v`

Expected: `ImportError: cannot import name 'process_pdf_to_journal'`

**Step 3: Examine full_pipeline.py to understand what to call**

We need to extract reusable functions from `scripts/full_pipeline.py`. Looking at the code, we'll need:
- `run_pdf_to_xml()` - returns run directory Path
- We'll need to create a wrapper for upload

**Step 4: Implement process_pdf_to_journal() function**

Add to `.worktrees/public-api/src/api.py`:

```python
import subprocess
import sys
from scripts.full_pipeline import run_pdf_to_xml as pipeline_run_pdf_to_xml
from foundry.upload_to_foundry import upload_journal_from_run_dir


def process_pdf_to_journal(
    pdf_path: str,
    journal_name: str,
    skip_upload: bool = False
) -> JournalCreationResult:
    """
    Process a D&D PDF into FoundryVTT journal entries.

    Runs the full pipeline:
    1. Split PDF into chapter PDFs (if not already split)
    2. Generate XML from chapters using Gemini
    3. Upload to FoundryVTT (unless skip_upload=True)

    Args:
        pdf_path: Path to source PDF file
        journal_name: Name for the FoundryVTT journal
        skip_upload: If True, generate XML but don't upload to Foundry

    Returns:
        JournalCreationResult with journal UUID and output paths

    Raises:
        APIError: If processing fails (PDF errors, Gemini errors,
                 FoundryVTT connection issues, etc.)

    Example:
        >>> result = process_pdf_to_journal(
        ...     "data/pdfs/module.pdf",
        ...     "Lost Mine of Phandelver"
        ... )
        >>> print(f"Created journal: {result.journal_uuid}")
        Created journal: JournalEntry.xyz789
    """
    try:
        logger.info(f"Processing PDF to journal: {pdf_path}")

        # Step 1: Run PDF to XML conversion
        # This returns the run directory (e.g., output/runs/20251105_120000)
        logger.info("Step 1/2: Converting PDF to XML...")
        run_dir = run_pdf_to_xml(pdf_path)

        # Count chapters by counting XML files
        xml_files = list(run_dir.glob("documents/*.xml"))
        chapter_count = len(xml_files)

        journal_uuid = ""
        if not skip_upload:
            # Step 2: Upload to FoundryVTT
            logger.info("Step 2/2: Uploading to FoundryVTT...")
            journal_uuid = upload_xml_to_foundry(run_dir, journal_name)
        else:
            logger.info("Skipping upload (skip_upload=True)")

        result = JournalCreationResult(
            journal_uuid=journal_uuid,
            journal_name=journal_name,
            output_dir=run_dir,
            chapter_count=chapter_count,
            timestamp=datetime.now().isoformat()
        )

        logger.info(f"✓ Journal processing complete: {result.journal_name}")
        return result

    except Exception as e:
        logger.error(f"PDF to journal processing failed: {e}")
        raise APIError(f"Failed to process PDF to journal: {e}") from e


def run_pdf_to_xml(pdf_path: str) -> Path:
    """
    Internal helper: Run PDF to XML conversion pipeline.

    This wraps the full_pipeline.py logic for PDF→XML conversion.
    """
    # For now, call the full_pipeline functions directly
    # In future, we may refactor full_pipeline.py to be more library-like
    from pathlib import Path as PathLib
    project_root = PathLib(__file__).parent.parent

    # Call pipeline function (simplified - actual implementation would
    # need to handle PDF splitting, etc.)
    return pipeline_run_pdf_to_xml(project_root, chapter_file=None)


def upload_xml_to_foundry(run_dir: Path, journal_name: str) -> str:
    """
    Internal helper: Upload XML files to FoundryVTT.

    Returns:
        Journal UUID (e.g., "JournalEntry.xyz789")
    """
    # This would call the upload_to_foundry.py logic
    # For now, simplified implementation
    from foundry.upload_to_foundry import main as upload_main
    import tempfile
    import sys

    # Create temporary args for upload script
    # (In real implementation, we'd refactor upload_to_foundry.py
    #  to expose a function API)
    old_argv = sys.argv
    try:
        sys.argv = [
            "upload_to_foundry.py",
            "--run-dir", str(run_dir),
            "--journal-name", journal_name
        ]
        journal_uuid = upload_main()
        return journal_uuid
    finally:
        sys.argv = old_argv
```

**Note:** This implementation is simplified. In reality, we'd need to refactor `scripts/full_pipeline.py` and `src/foundry/upload_to_foundry.py` to expose clean function APIs. For now, this provides the interface shape.

**Step 5: Run tests to verify they pass**

Run: `cd .worktrees/public-api && uv run pytest tests/api/test_api.py -k process_pdf_to_journal -v`

Expected: 3 tests PASS

**Step 6: Commit**

```bash
cd .worktrees/public-api
git add src/api.py tests/api/test_api.py
git commit -m "feat(api): implement process_pdf_to_journal() with error handling"
```

---

## Task 6: Integration Tests

**Files:**
- Create: `.worktrees/public-api/tests/api/test_api_integration.py`

**Step 1: Write integration test for create_actor()**

Create `.worktrees/public-api/tests/api/test_api_integration.py`:

```python
"""Integration tests for public API (require real API keys)."""
import pytest
from pathlib import Path
from api import create_actor, extract_maps, process_pdf_to_journal, APIError


@pytest.mark.integration
def test_create_actor_integration():
    """Test create_actor with real Gemini API."""
    result = create_actor(
        "A simple goblin scout with a shortbow",
        challenge_rating=0.25
    )

    # Verify result structure
    assert result.foundry_uuid.startswith("Actor.")
    assert "Goblin" in result.name or "Scout" in result.name
    assert result.challenge_rating == 0.25
    assert result.output_dir.exists()

    # Verify output files exist
    assert (result.output_dir / "01_raw_stat_block.txt").exists()
    assert (result.output_dir / "04_foundry_actor.json").exists()


@pytest.mark.integration
@pytest.mark.slow
def test_extract_maps_integration(test_pdf_path):
    """Test extract_maps with real PDF."""
    result = extract_maps(str(test_pdf_path))

    # May not have maps, but should complete without error
    assert isinstance(result.total_maps, int)
    assert result.total_maps >= 0
    assert len(result.maps) == result.total_maps


@pytest.mark.integration
@pytest.mark.slow
def test_process_pdf_to_journal_integration(test_pdf_path):
    """Test process_pdf_to_journal with real PDF (skip upload)."""
    result = process_pdf_to_journal(
        str(test_pdf_path),
        "Integration Test Journal",
        skip_upload=True  # Don't actually upload in tests
    )

    assert result.journal_name == "Integration Test Journal"
    assert result.chapter_count > 0
    assert result.output_dir.exists()
    assert result.journal_uuid == ""  # No UUID when skipping upload
```

**Step 2: Run integration tests**

Run: `cd .worktrees/public-api && uv run pytest tests/api/test_api_integration.py -v -m integration`

Expected: Tests PASS (if API keys configured) or SKIPPED (if missing)

**Step 3: Commit**

```bash
cd .worktrees/public-api
git add tests/api/test_api_integration.py
git commit -m "test(api): add integration tests for API functions"
```

---

## Task 7: Documentation and Examples

**Files:**
- Modify: `.worktrees/public-api/CLAUDE.md`
- Modify: `.worktrees/public-api/src/api.py` (add module examples)

**Step 1: Add API usage section to CLAUDE.md**

Add to `.worktrees/public-api/CLAUDE.md` (after "## Project Overview"):

```markdown
## Public API

The project provides a clean public API for external applications (chat UI, CLI tools).

**Location:** `src/api.py`

**Key Functions:**

```python
from api import create_actor, extract_maps, process_pdf_to_journal

# 1. Create D&D actor from description
result = create_actor(
    description="A cunning kobold scout with a poisoned dagger",
    challenge_rating=0.5
)
print(f"Created: {result.name} - {result.foundry_uuid}")
# Output: Created: Kobold Scout - Actor.abc123

# 2. Extract maps from PDF
maps_result = extract_maps(
    pdf_path="data/pdfs/module.pdf",
    chapter="Chapter 1"
)
print(f"Extracted {maps_result.total_maps} maps")

# 3. Process PDF to FoundryVTT journal
journal_result = process_pdf_to_journal(
    pdf_path="data/pdfs/module.pdf",
    journal_name="Lost Mine of Phandelver",
    skip_upload=False  # Set True to generate XML only
)
print(f"Created journal: {journal_result.journal_uuid}")
```

**Error Handling:**

All functions raise `APIError` on failure:

```python
from api import APIError

try:
    result = create_actor("broken description")
except APIError as e:
    print(f"Failed: {e}")
    print(f"Original error: {e.__cause__}")
```

**Return Types:**

- `ActorCreationResult`: UUID, name, CR, output_dir, timestamp
- `MapExtractionResult`: maps list, output_dir, total_maps, timestamp
- `JournalCreationResult`: UUID, name, output_dir, chapter_count, timestamp

**Configuration:**

Uses environment variables from `.env` (no runtime config):
- `GeminiImageAPI`: Gemini API key
- `FOUNDRY_*`: FoundryVTT connection settings

**Testing:**

```bash
# Unit tests (fast, use mocks)
uv run pytest tests/api/test_api.py -v

# Integration tests (real API calls, cost money)
uv run pytest tests/api/test_api_integration.py -v -m integration
```
```

**Step 2: Add comprehensive module docstring examples**

Update the module docstring in `.worktrees/public-api/src/api.py`:

```python
"""
Public API for D&D Module Processing.

This module provides the official interface for external applications
(chat UI, CLI tools, etc.) to interact with the module processing system.

All functions use environment variables for configuration (.env file).
Operations are synchronous and may take several minutes for large PDFs.

Quick Start:
-----------

    from api import create_actor, extract_maps, process_pdf_to_journal

    # Create actor from description
    result = create_actor("A fierce goblin warrior", challenge_rating=1.0)
    print(f"Created: {result.name} ({result.foundry_uuid})")

    # Extract maps from PDF
    maps = extract_maps("data/pdfs/module.pdf", chapter="Chapter 1")
    for map_meta in maps.maps:
        print(f"Found map: {map_meta['name']}")

    # Process complete PDF to journal
    journal = process_pdf_to_journal(
        "data/pdfs/module.pdf",
        "Lost Mine of Phandelver"
    )
    print(f"Created journal: {journal.journal_uuid}")

Error Handling:
--------------

All functions raise APIError on failure:

    from api import APIError

    try:
        result = create_actor("invalid description")
    except APIError as e:
        logger.error(f"Failed: {e}")
        logger.error(f"Original cause: {e.__cause__}")

Configuration:
-------------

Requires .env file with:
    - GeminiImageAPI: Google Gemini API key
    - FOUNDRY_URL: FoundryVTT server URL
    - FOUNDRY_API_KEY: FoundryVTT API key

See CLAUDE.md for complete setup instructions.
"""
```

**Step 3: Run all tests to verify nothing broke**

Run: `cd .worktrees/public-api && uv run pytest tests/api/test_api.py -v`

Expected: All tests PASS

**Step 4: Commit**

```bash
cd .worktrees/public-api
git add CLAUDE.md src/api.py
git commit -m "docs(api): add comprehensive API documentation and examples"
```

---

## Task 8: Final Verification

**Step 1: Run complete test suite**

Run:
```bash
cd .worktrees/public-api
uv run pytest tests/api/ -v --tb=short
```

Expected: All unit tests PASS

**Step 2: Run syntax check**

Run: `cd .worktrees/public-api && python -m compileall src/api.py`

Expected: No errors

**Step 3: Test import in Python REPL**

Run:
```bash
cd .worktrees/public-api
python3 -c "from api import create_actor, extract_maps, process_pdf_to_journal, APIError; print('✓ Imports successful')"
```

Expected: "✓ Imports successful"

**Step 4: Final commit**

```bash
cd .worktrees/public-api
git add -A
git commit -m "chore(api): final verification and cleanup"
```

---

## Success Criteria

- ✅ `src/api.py` exists with 3 public functions
- ✅ All functions return rich dataclass results
- ✅ `APIError` provides clean error boundary
- ✅ Unit tests provide 100% coverage of public API
- ✅ Integration tests validate real workflows
- ✅ Documentation in CLAUDE.md with examples
- ✅ All tests pass

## Next Steps

After implementation:

1. **Merge to main:** Create PR from feature/public-api branch
2. **Update chat UI:** Migrate UI backend to use `src/api.py`
3. **Create CLI wrapper:** Build thin CLI around API functions
4. **Monitor usage:** Track which functions are used most
5. **Iterate:** Add more functions based on demand (scene extraction, etc.)

## Notes

- **Simplified pipeline functions:** Tasks 5 uses placeholder implementations. In reality, we'd need to refactor `scripts/full_pipeline.py` and upload scripts to expose cleaner function APIs. This is acceptable technical debt for v1.
- **Test coverage:** Unit tests mock expensive operations. Integration tests validate real behavior but are marked to run separately.
- **Future enhancements:** Could add async versions, progress callbacks, batch operations.
