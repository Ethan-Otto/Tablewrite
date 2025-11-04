# Actor Creation Orchestration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement a single async orchestration function that creates complete D&D 5e actors from natural language descriptions and uploads them to FoundryVTT.

**Architecture:** Single async pipeline function (`create_actor_from_description`) that chains: text generation → StatBlock parsing → ParsedActorData parsing → FoundryVTT conversion → upload. All intermediate outputs saved to timestamped directories for debugging. Fail-fast error handling.

**Tech Stack:** Python 3.11+, asyncio, google-genai, pydantic, pytest

---

## Prerequisites

**Current worktree:** `.worktrees/actor-creation-orchestration`
**Branch:** `feature/actor-creation-orchestration`
**Base commit:** Design document committed

**Known issues to address:**
- 11 failing tests due to old `genai.GenerativeModel` mocks (need updating to `genai.Client`)

---

## Task 1: Fix Test Mocks for New google-genai API

**Context:** After migrating from `google-generativeai` to `google-genai`, 11 tests are failing because they mock `genai.GenerativeModel` which doesn't exist in the new API. Need to update mocks to use `genai.Client` and the new API structure.

**Files:**
- Modify: `tests/foundry/actors/test_multiattack.py`
- Modify: `tests/scene_extraction/test_extract_context.py`
- Modify: `tests/scene_extraction/test_identify_scenes.py`

**Step 1: Identify mock patterns**

Run: `grep -n "genai.GenerativeModel" tests/foundry/actors/test_multiattack.py tests/scene_extraction/test_*.py`

Expected: Shows all places mocking old API

**Step 2: Update test_multiattack.py mocks**

Find the mock pattern (around line 82 based on error) and replace:

OLD pattern:
```python
mock_model = Mock()
mock_model.generate_content_async.return_value = mock_response
```

NEW pattern:
```python
mock_client = Mock()
mock_client.models.generate_content_async.return_value = mock_response
with patch('google.genai.Client', return_value=mock_client):
    # test code
```

**Step 3: Update scene_extraction test mocks**

In `test_extract_context.py` and `test_identify_scenes.py`, replace synchronous mocks:

OLD pattern:
```python
@patch('google.genai.GenerativeModel')
def test_something(self, mock_model):
    mock_instance = mock_model.return_value
    mock_instance.generate_content.return_value = mock_response
```

NEW pattern:
```python
@patch('google.genai.Client')
def test_something(self, mock_client_class):
    mock_client = mock_client_class.return_value
    mock_client.models.generate_content.return_value = mock_response
```

**Step 4: Run tests to verify fixes**

Run: `uv run pytest tests/foundry/actors/test_multiattack.py tests/scene_extraction/test_extract_context.py tests/scene_extraction/test_identify_scenes.py -v`

Expected: All 11 previously failing tests now pass

**Step 5: Run full test suite**

Run: `uv run pytest -m "not integration and not slow" -q`

Expected: All unit tests pass (no regressions)

**Step 6: Commit mock updates**

```bash
git add tests/foundry/actors/test_multiattack.py tests/scene_extraction/test_*.py
git commit -m "test: update mocks for new google-genai API

- Replace genai.GenerativeModel with genai.Client mocks
- Update mock patterns for new client.models.generate_content API
- Fixes 11 failing tests after API migration"
```

---

## Task 2: Create ActorCreationResult Model

**Files:**
- Create: `src/actors/create_actor.py`
- Test: `tests/actors/test_create_actor.py`

**Step 1: Write test for ActorCreationResult dataclass**

Create `tests/actors/test_create_actor.py`:

```python
"""Tests for actor creation orchestration."""

import pytest
from pathlib import Path
from actors.create_actor import ActorCreationResult
from actors.models import StatBlock
from foundry.actors.models import ParsedActorData


class TestActorCreationResult:
    """Tests for ActorCreationResult dataclass."""

    def test_actor_creation_result_has_required_fields(self):
        """ActorCreationResult should have all required fields."""
        result = ActorCreationResult(
            actor_uuid="JournalEntry.abc123",
            actor_name="Fire Drake",
            challenge_rating=7.0,
            text_file_path=Path("/tmp/actor.txt"),
            stat_block=None,  # Type hint allows None for test
            parsed_data=None,
            foundry_json={"name": "Fire Drake"},
            output_directory=Path("/tmp/output"),
            metadata={"created": "2025-11-03"}
        )

        assert result.actor_uuid == "JournalEntry.abc123"
        assert result.actor_name == "Fire Drake"
        assert result.challenge_rating == 7.0
        assert result.text_file_path == Path("/tmp/actor.txt")
        assert result.foundry_json == {"name": "Fire Drake"}
        assert result.output_directory == Path("/tmp/output")
        assert result.metadata == {"created": "2025-11-03"}
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/actors/test_create_actor.py::TestActorCreationResult::test_actor_creation_result_has_required_fields -v`

Expected: ImportError or NameError (module doesn't exist)

**Step 3: Create minimal ActorCreationResult dataclass**

Create `src/actors/create_actor.py`:

```python
"""Orchestrate full actor creation pipeline from description to FoundryVTT.

This module provides a single async function that chains together:
  1. Text generation (generate_actor_file.py)
  2. StatBlock parsing (statblock_parser.py)
  3. ParsedActorData parsing (foundry/actors/parser.py)
  4. FoundryVTT conversion (foundry/actors/converter.py)
  5. Actor upload (foundry/actors/manager.py)

All intermediate outputs are saved to timestamped directories for debugging.
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from actors.models import StatBlock
from foundry.actors.models import ParsedActorData

logger = logging.getLogger(__name__)


@dataclass
class ActorCreationResult:
    """Complete result of actor creation pipeline."""

    actor_uuid: str  # FoundryVTT actor UUID
    actor_name: str  # Final actor name
    challenge_rating: float  # Final CR (useful when auto-determined)
    text_file_path: Path  # Generated .txt file
    stat_block: StatBlock  # Parsed stat block
    parsed_data: ParsedActorData  # Detailed parse with attacks/traits
    foundry_json: dict  # FoundryVTT actor JSON
    output_directory: Path  # Where all files saved
    metadata: dict  # Pipeline execution metadata
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/actors/test_create_actor.py::TestActorCreationResult::test_actor_creation_result_has_required_fields -v`

Expected: PASS

**Step 5: Commit ActorCreationResult**

```bash
git add src/actors/create_actor.py tests/actors/test_create_actor.py
git commit -m "feat: add ActorCreationResult dataclass

- Complete result model for actor creation pipeline
- Includes all intermediate outputs and metadata
- Supports debugging with saved file paths"
```

---

## Task 3: Create Output Directory Helper

**Files:**
- Modify: `src/actors/create_actor.py`
- Modify: `tests/actors/test_create_actor.py`

**Step 1: Write test for output directory creation**

Add to `tests/actors/test_create_actor.py`:

```python
import tempfile
from actors.create_actor import create_output_directory


class TestCreateOutputDirectory:
    """Tests for output directory creation."""

    def test_creates_timestamped_directory(self, tmp_path):
        """Should create directory with timestamp and sanitized name."""
        output_dir = create_output_directory(
            actor_name="Fire Drake",
            base_dir=tmp_path
        )

        assert output_dir.exists()
        assert output_dir.parent == tmp_path
        # Format: YYYYMMDD_HHMMSS_fire_drake
        assert "fire_drake" in output_dir.name
        assert len(output_dir.name.split("_")) >= 3  # timestamp + name parts

    def test_sanitizes_actor_name(self, tmp_path):
        """Should remove special characters from actor name."""
        output_dir = create_output_directory(
            actor_name="Grok's Fire-Drake (Ancient)",
            base_dir=tmp_path
        )

        # Should remove apostrophes, hyphens, parentheses
        assert "'" not in output_dir.name
        assert "(" not in output_dir.name
        assert ")" not in output_dir.name

    def test_creates_parent_directories(self, tmp_path):
        """Should create parent directories if they don't exist."""
        base_dir = tmp_path / "actors" / "output"
        output_dir = create_output_directory(
            actor_name="Test",
            base_dir=base_dir
        )

        assert output_dir.exists()
        assert base_dir.exists()
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/actors/test_create_actor.py::TestCreateOutputDirectory -v`

Expected: ImportError (function doesn't exist)

**Step 3: Implement create_output_directory function**

Add to `src/actors/create_actor.py`:

```python
def create_output_directory(
    actor_name: str,
    base_dir: Optional[Path] = None
) -> Path:
    """
    Create timestamped output directory for actor.

    Args:
        actor_name: Actor name (will be sanitized)
        base_dir: Base directory (defaults to output/actors/)

    Returns:
        Path to created directory

    Example:
        >>> create_output_directory("Fire Drake")
        Path("output/actors/20251103_143022_fire_drake")
    """
    if base_dir is None:
        # Default: PROJECT_ROOT/output/actors/
        project_root = Path(__file__).parent.parent.parent
        base_dir = project_root / "output" / "actors"

    # Create timestamp: YYYYMMDD_HHMMSS
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Sanitize actor name: lowercase, remove special chars, replace spaces
    safe_name = actor_name.lower()
    safe_name = safe_name.replace("'", "").replace("-", "_")
    safe_name = safe_name.replace("(", "").replace(")", "")
    safe_name = safe_name.replace(" ", "_")

    # Create directory path
    output_dir = base_dir / f"{timestamp}_{safe_name}"
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Created output directory: {output_dir}")
    return output_dir
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/actors/test_create_actor.py::TestCreateOutputDirectory -v`

Expected: PASS

**Step 5: Commit output directory helper**

```bash
git add src/actors/create_actor.py tests/actors/test_create_actor.py
git commit -m "feat: add output directory creation helper

- Creates timestamped directories (YYYYMMDD_HHMMSS_name)
- Sanitizes actor names for filesystem safety
- Creates parent directories as needed"
```

---

## Task 4: Create Save Intermediate File Helper

**Files:**
- Modify: `src/actors/create_actor.py`
- Modify: `tests/actors/test_create_actor.py`

**Step 1: Write test for save_intermediate_file**

Add to `tests/actors/test_create_actor.py`:

```python
from actors.create_actor import save_intermediate_file


class TestSaveIntermediateFile:
    """Tests for intermediate file saving."""

    def test_saves_text_file(self, tmp_path):
        """Should save text content to file."""
        save_intermediate_file(
            output_dir=tmp_path,
            filename="actor.txt",
            content="Test content"
        )

        saved_file = tmp_path / "actor.txt"
        assert saved_file.exists()
        assert saved_file.read_text() == "Test content"

    def test_saves_json_file(self, tmp_path):
        """Should save dict as JSON."""
        data = {"name": "Fire Drake", "cr": 7}
        save_intermediate_file(
            output_dir=tmp_path,
            filename="data.json",
            content=data
        )

        saved_file = tmp_path / "data.json"
        assert saved_file.exists()
        saved_data = json.loads(saved_file.read_text())
        assert saved_data == data

    def test_saves_pydantic_model_as_json(self, tmp_path):
        """Should save Pydantic model as JSON."""
        from actors.models import StatBlock

        stat_block = StatBlock(
            name="Test Creature",
            raw_text="Test",
            armor_class=15,
            hit_points=50,
            challenge_rating=3.0
        )

        save_intermediate_file(
            output_dir=tmp_path,
            filename="stat_block.json",
            content=stat_block
        )

        saved_file = tmp_path / "stat_block.json"
        assert saved_file.exists()
        saved_data = json.loads(saved_file.read_text())
        assert saved_data["name"] == "Test Creature"
        assert saved_data["armor_class"] == 15
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/actors/test_create_actor.py::TestSaveIntermediateFile -v`

Expected: ImportError (function doesn't exist)

**Step 3: Implement save_intermediate_file function**

Add to `src/actors/create_actor.py`:

```python
from typing import Union
from pydantic import BaseModel


def save_intermediate_file(
    output_dir: Path,
    filename: str,
    content: Union[str, dict, BaseModel]
) -> Path:
    """
    Save intermediate file to output directory.

    Args:
        output_dir: Output directory path
        filename: Filename to save
        content: Content (str, dict, or Pydantic model)

    Returns:
        Path to saved file
    """
    file_path = output_dir / filename

    # Handle different content types
    if isinstance(content, str):
        # Text content
        file_path.write_text(content, encoding="utf-8")
    elif isinstance(content, BaseModel):
        # Pydantic model - convert to JSON
        json_str = content.model_dump_json(indent=2)
        file_path.write_text(json_str, encoding="utf-8")
    elif isinstance(content, dict):
        # Dict - convert to JSON
        json_str = json.dumps(content, indent=2, ensure_ascii=False)
        file_path.write_text(json_str, encoding="utf-8")
    else:
        raise TypeError(f"Unsupported content type: {type(content)}")

    logger.debug(f"Saved intermediate file: {file_path}")
    return file_path
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/actors/test_create_actor.py::TestSaveIntermediateFile -v`

Expected: PASS

**Step 5: Commit save helper**

```bash
git add src/actors/create_actor.py tests/actors/test_create_actor.py
git commit -m "feat: add intermediate file save helper

- Supports str, dict, and Pydantic model content
- Automatic JSON serialization for structured data
- Returns saved file path for tracking"
```

---

## Task 5: Implement Main Pipeline Function (Part 1: Structure)

**Files:**
- Modify: `src/actors/create_actor.py`
- Modify: `tests/actors/test_create_actor.py`

**Step 1: Write test for pipeline function structure**

Add to `tests/actors/test_create_actor.py`:

```python
from unittest.mock import AsyncMock, Mock, patch
from actors.create_actor import create_actor_from_description


@pytest.mark.asyncio
class TestCreateActorFromDescription:
    """Tests for main pipeline function."""

    async def test_creates_output_directory(self, tmp_path):
        """Should create timestamped output directory."""
        with patch('actors.create_actor.generate_actor_from_description', new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = tmp_path / "actor.txt"
            # Mock other pipeline steps to prevent execution
            with patch('actors.create_actor.parse_raw_text_to_statblock', new_callable=AsyncMock):
                with patch('actors.create_actor.parse_stat_block_parallel', new_callable=AsyncMock):
                    with patch('actors.create_actor.convert_to_foundry'):
                        with patch('actors.create_actor.ActorManager'):
                            result = await create_actor_from_description(
                                description="Test creature",
                                challenge_rating=5,
                                output_dir=tmp_path
                            )

        # Should create a timestamped directory
        assert result.output_directory.exists()
        assert result.output_directory.parent == tmp_path

    async def test_returns_actor_creation_result(self, tmp_path):
        """Should return ActorCreationResult with all fields."""
        mock_stat_block = Mock()
        mock_stat_block.name = "Test Creature"
        mock_stat_block.challenge_rating = 5.0

        with patch('actors.create_actor.generate_actor_from_description', new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = tmp_path / "actor.txt"
            with patch('actors.create_actor.parse_raw_text_to_statblock', new_callable=AsyncMock) as mock_parse:
                mock_parse.return_value = mock_stat_block
                with patch('actors.create_actor.parse_stat_block_parallel', new_callable=AsyncMock) as mock_parse_detailed:
                    mock_parsed = Mock()
                    mock_parse_detailed.return_value = mock_parsed
                    with patch('actors.create_actor.convert_to_foundry') as mock_convert:
                        mock_convert.return_value = ({"name": "Test"}, [])
                        with patch('actors.create_actor.ActorManager') as mock_manager:
                            mock_manager.return_value.create_actor.return_value = "Actor.abc123"

                            result = await create_actor_from_description(
                                description="Test creature",
                                challenge_rating=5,
                                output_dir=tmp_path
                            )

        assert isinstance(result, ActorCreationResult)
        assert result.actor_name == "Test Creature"
        assert result.challenge_rating == 5.0
        assert result.actor_uuid == "Actor.abc123"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/actors/test_create_actor.py::TestCreateActorFromDescription -v`

Expected: ImportError or function doesn't exist

**Step 3: Implement function structure (no pipeline logic yet)**

Add to `src/actors/create_actor.py`:

```python
from actors.generate_actor_file import generate_actor_from_description
from actors.statblock_parser import parse_raw_text_to_statblock
from foundry.actors.parser import parse_stat_block_parallel
from foundry.actors.converter import convert_to_foundry
from foundry.actors.manager import ActorManager
from foundry.actors.spell_cache import SpellCache
from foundry.client import FoundryClient


async def create_actor_from_description(
    description: str,
    challenge_rating: Optional[float] = None,
    name: Optional[str] = None,
    bio_context: Optional[str] = None,
    foundry_client: Optional[FoundryClient] = None,
    output_dir: Optional[Path] = None
) -> ActorCreationResult:
    """
    Create complete D&D 5e actor from description and upload to FoundryVTT.

    This orchestrates the full pipeline:
      1. Generate text file (stat block + bio)
      2. Parse to StatBlock
      3. Parse to ParsedActorData
      4. Convert to FoundryVTT format
      5. Upload to FoundryVTT (if client provided)

    All intermediate outputs saved to timestamped directory.

    Args:
        description: Natural language description
        challenge_rating: Optional CR (auto-determined if None)
        name: Optional custom name
        bio_context: Optional biography context
        foundry_client: Optional client for upload (dry run if None)
        output_dir: Optional output directory (defaults to output/actors/)

    Returns:
        ActorCreationResult with all outputs

    Raises:
        ActorCreationError: If any pipeline step fails
    """
    start_time = datetime.now()
    logger.info(f"Starting actor creation: {description[:100]}...")

    # Step 1: Create output directory
    # Temporary name for directory (will update after parsing)
    temp_name = name or "temp_actor"
    output_directory = create_output_directory(temp_name, output_dir)

    try:
        # Step 2: Generate text file
        logger.info("Step 1/5: Generating stat block text...")
        text_file_path = await generate_actor_from_description(
            description=description,
            challenge_rating=challenge_rating,
            name=name,
            bio_context=bio_context,
            output_path=output_directory / "actor.txt"
        )

        # Validate text file exists
        if not text_file_path.exists():
            raise ActorCreationError(f"Text generation failed: {text_file_path} not found")

        # Step 3: Parse to StatBlock
        logger.info("Step 2/5: Parsing stat block...")
        raw_text = text_file_path.read_text()
        stat_block = await parse_raw_text_to_statblock(raw_text)

        # Save StatBlock
        save_intermediate_file(output_directory, "stat_block.json", stat_block)

        # Step 4: Parse to ParsedActorData
        logger.info("Step 3/5: Detailed parsing...")
        spell_cache = None
        if foundry_client:
            spell_cache = SpellCache()
            await spell_cache.load_async()

        parsed_data = await parse_stat_block_parallel(
            stat_block=stat_block,
            spell_cache=spell_cache
        )

        # Save ParsedActorData
        save_intermediate_file(output_directory, "parsed_actor_data.json", parsed_data)

        # Step 5: Convert to FoundryVTT format
        logger.info("Step 4/5: Converting to FoundryVTT format...")
        foundry_json, spell_uuids = convert_to_foundry(
            parsed_data,
            spell_cache=spell_cache
        )

        # Save FoundryVTT JSON
        save_intermediate_file(output_directory, "foundry_actor.json", foundry_json)

        # Step 6: Upload to FoundryVTT (if client provided)
        actor_uuid = None
        if foundry_client:
            logger.info("Step 5/5: Uploading to FoundryVTT...")
            actor_manager = ActorManager(foundry_client)
            actor_uuid = actor_manager.create_actor(foundry_json, spell_uuids=spell_uuids)
            logger.info(f"Actor created: {actor_uuid}")
        else:
            logger.info("Step 5/5: Skipped (no client provided)")
            actor_uuid = "dry_run_no_upload"

        # Save metadata
        end_time = datetime.now()
        metadata = {
            "created_at": start_time.isoformat(),
            "completed_at": end_time.isoformat(),
            "duration_seconds": (end_time - start_time).total_seconds(),
            "description": description,
            "challenge_rating_requested": challenge_rating,
            "challenge_rating_final": stat_block.challenge_rating,
            "actor_name": stat_block.name,
            "uploaded": foundry_client is not None
        }
        save_intermediate_file(output_directory, "metadata.json", metadata)

        # Return result
        return ActorCreationResult(
            actor_uuid=actor_uuid,
            actor_name=stat_block.name,
            challenge_rating=stat_block.challenge_rating,
            text_file_path=text_file_path,
            stat_block=stat_block,
            parsed_data=parsed_data,
            foundry_json=foundry_json,
            output_directory=output_directory,
            metadata=metadata
        )

    except Exception as e:
        # Save error to metadata
        error_metadata = {
            "created_at": start_time.isoformat(),
            "failed_at": datetime.now().isoformat(),
            "error": str(e),
            "error_type": type(e).__name__,
            "description": description
        }
        save_intermediate_file(output_directory, "metadata.json", error_metadata)

        logger.error(f"Actor creation failed: {e}")
        logger.error(f"Partial progress saved to: {output_directory}")
        raise ActorCreationError(
            f"Failed at pipeline step. Partial progress: {output_directory}"
        ) from e


class ActorCreationError(Exception):
    """Raised when actor creation pipeline fails."""
    pass
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/actors/test_create_actor.py::TestCreateActorFromDescription -v`

Expected: PASS

**Step 5: Commit pipeline structure**

```bash
git add src/actors/create_actor.py tests/actors/test_create_actor.py
git commit -m "feat: implement actor creation pipeline structure

- Complete async orchestration function
- Chains all pipeline steps with error handling
- Saves all intermediate outputs
- Metadata tracking with timestamps"
```

---

## Task 6: Add Synchronous Wrapper

**Files:**
- Modify: `src/actors/create_actor.py`
- Modify: `tests/actors/test_create_actor.py`

**Step 1: Write test for synchronous wrapper**

Add to `tests/actors/test_create_actor.py`:

```python
from actors.create_actor import create_actor_sync


def test_create_actor_sync_wrapper(tmp_path):
    """Synchronous wrapper should work."""
    with patch('actors.create_actor.create_actor_from_description', new_callable=AsyncMock) as mock_async:
        mock_result = Mock()
        mock_result.actor_name = "Test"
        mock_async.return_value = mock_result

        result = create_actor_sync(
            description="Test",
            challenge_rating=5,
            output_dir=tmp_path
        )

        assert result.actor_name == "Test"
        mock_async.assert_called_once()
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/actors/test_create_actor.py::test_create_actor_sync_wrapper -v`

Expected: ImportError (function doesn't exist)

**Step 3: Implement synchronous wrapper**

Add to `src/actors/create_actor.py`:

```python
def create_actor_sync(
    description: str,
    challenge_rating: Optional[float] = None,
    name: Optional[str] = None,
    bio_context: Optional[str] = None,
    foundry_client: Optional[FoundryClient] = None,
    output_dir: Optional[Path] = None
) -> ActorCreationResult:
    """
    Synchronous wrapper for create_actor_from_description.

    See create_actor_from_description for full documentation.
    """
    return asyncio.run(create_actor_from_description(
        description, challenge_rating, name, bio_context,
        foundry_client, output_dir
    ))
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/actors/test_create_actor.py::test_create_actor_sync_wrapper -v`

Expected: PASS

**Step 5: Commit sync wrapper**

```bash
git add src/actors/create_actor.py tests/actors/test_create_actor.py
git commit -m "feat: add synchronous wrapper for actor creation

- Convenience function for non-async contexts
- Delegates to async implementation via asyncio.run"
```

---

## Task 7: Add Batch Creation Helper

**Files:**
- Modify: `src/actors/create_actor.py`
- Modify: `tests/actors/test_create_actor.py`

**Step 1: Write test for batch creation**

Add to `tests/actors/test_create_actor.py`:

```python
from actors.create_actor import create_multiple_actors


@pytest.mark.asyncio
async def test_create_multiple_actors(tmp_path):
    """Should create multiple actors in parallel."""
    with patch('actors.create_actor.create_actor_from_description', new_callable=AsyncMock) as mock_create:
        mock_result1 = Mock()
        mock_result1.actor_name = "Actor 1"
        mock_result2 = Mock()
        mock_result2.actor_name = "Actor 2"
        mock_create.side_effect = [mock_result1, mock_result2]

        descriptions = [
            ("Fire Drake", 7),
            ("Ice Drake", None)  # Auto CR
        ]

        results = await create_multiple_actors(
            descriptions=descriptions,
            foundry_client=None
        )

        assert len(results) == 2
        assert results[0].actor_name == "Actor 1"
        assert results[1].actor_name == "Actor 2"
        assert mock_create.call_count == 2
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/actors/test_create_actor.py::test_create_multiple_actors -v`

Expected: ImportError (function doesn't exist)

**Step 3: Implement batch creation**

Add to `src/actors/create_actor.py`:

```python
async def create_multiple_actors(
    descriptions: list[tuple[str, Optional[float]]],
    foundry_client: Optional[FoundryClient] = None,
    output_dir: Optional[Path] = None
) -> list[ActorCreationResult]:
    """
    Create multiple actors in parallel.

    Args:
        descriptions: List of (description, challenge_rating) tuples
        foundry_client: Optional client for upload
        output_dir: Optional output directory

    Returns:
        List of ActorCreationResult objects

    Example:
        >>> results = await create_multiple_actors([
        ...     ("Fire Drake", 7),
        ...     ("Ice Drake", None),  # Auto CR
        ...     ("Storm Drake", 15)
        ... ])
    """
    tasks = [
        create_actor_from_description(
            description=desc,
            challenge_rating=cr,
            foundry_client=foundry_client,
            output_dir=output_dir
        )
        for desc, cr in descriptions
    ]

    logger.info(f"Creating {len(tasks)} actors in parallel...")
    return await asyncio.gather(*tasks)
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/actors/test_create_actor.py::test_create_multiple_actors -v`

Expected: PASS

**Step 5: Commit batch helper**

```bash
git add src/actors/create_actor.py tests/actors/test_create_actor.py
git commit -m "feat: add batch actor creation helper

- Parallel creation using asyncio.gather
- Supports mixed explicit and auto CR
- Returns list of ActorCreationResult"
```

---

## Task 8: Add Integration Test

**Files:**
- Create: `tests/actors/test_create_actor_integration.py`

**Step 1: Write integration test**

Create `tests/actors/test_create_actor_integration.py`:

```python
"""Integration tests for actor creation orchestration.

These tests make REAL Gemini API calls and are marked as integration tests.
Run with: pytest -m integration
"""

import pytest
from pathlib import Path
from actors.create_actor import create_actor_from_description


@pytest.mark.integration
@pytest.mark.asyncio
class TestActorCreationIntegration:
    """Integration tests with real Gemini API calls."""

    async def test_creates_complete_actor_with_explicit_cr(self, tmp_path):
        """Should create complete actor with all intermediate files."""
        result = await create_actor_from_description(
            description="A small crystalline spider that feeds on magical energy",
            challenge_rating=3,
            bio_context="Found in wizard tower ruins",
            foundry_client=None,  # Dry run - no upload
            output_dir=tmp_path
        )

        # Check result
        assert result.actor_name
        assert result.challenge_rating == 3.0
        assert result.actor_uuid == "dry_run_no_upload"

        # Check intermediate files exist
        assert result.text_file_path.exists()
        assert (result.output_directory / "stat_block.json").exists()
        assert (result.output_directory / "parsed_actor_data.json").exists()
        assert (result.output_directory / "foundry_actor.json").exists()
        assert (result.output_directory / "metadata.json").exists()

        # Check stat block has reasonable values
        assert result.stat_block.armor_class > 0
        assert result.stat_block.hit_points > 0
        assert len(result.stat_block.actions) > 0

    async def test_creates_actor_with_auto_cr(self, tmp_path):
        """Should determine appropriate CR from description."""
        result = await create_actor_from_description(
            description="An ancient dragon with reality-warping powers who destroyed entire kingdoms",
            foundry_client=None,
            output_dir=tmp_path
        )

        # Should auto-determine high CR
        assert result.challenge_rating >= 15.0
        assert "dragon" in result.actor_name.lower() or "ancient" in result.actor_name.lower()

    async def test_creates_simple_low_cr_creature(self, tmp_path):
        """Should handle simple low-CR creatures."""
        result = await create_actor_from_description(
            description="A common goblin warrior",
            challenge_rating=0.25,
            foundry_client=None,
            output_dir=tmp_path
        )

        assert result.challenge_rating == 0.25
        assert result.stat_block.armor_class <= 15  # Low CR = low AC
        assert result.stat_block.hit_points <= 20  # Low CR = low HP
```

**Step 2: Run integration test (requires API key)**

Run: `uv run pytest tests/actors/test_create_actor_integration.py -v -m integration`

Expected: PASS (if GEMINI_API_KEY set), or SKIP (if no API key)

**Step 3: Commit integration test**

```bash
git add tests/actors/test_create_actor_integration.py
git commit -m "test: add integration tests for actor creation

- Tests complete pipeline with real Gemini API
- Validates all intermediate outputs
- Tests both explicit and auto CR determination"
```

---

## Task 9: Update Documentation

**Files:**
- Modify: `CLAUDE.md`
- Create: `docs/actor-creation-usage.md`

**Step 1: Add usage examples to CLAUDE.md**

Add new section to `CLAUDE.md` after the "Common Commands" section:

```markdown
## Actor Creation

Generate complete D&D 5e actors from descriptions using AI:

```bash
# Create actor with explicit CR (no upload)
uv run python -c "
from actors.create_actor import create_actor_sync
result = create_actor_sync('A fire-breathing drake with crystalline scales', challenge_rating=7)
print(f'Created: {result.actor_name} (CR {result.challenge_rating})')
print(f'Files: {result.output_directory}')
"

# Create actor with auto CR determination
uv run python -c "
from actors.create_actor import create_actor_sync
result = create_actor_sync('An ancient lich with reality-warping powers')
print(f'Gemini chose CR {result.challenge_rating}')
"

# Upload to FoundryVTT
uv run python -c "
from actors.create_actor import create_actor_sync
from foundry.client import FoundryClient

client = FoundryClient(target='local')
result = create_actor_sync('A mutated sea creature', challenge_rating=5, foundry_client=client)
print(f'Uploaded: {result.actor_uuid}')
"
```
```

**Step 2: Create detailed usage documentation**

Create `docs/actor-creation-usage.md`:

```markdown
# Actor Creation Usage Guide

## Overview

The `create_actor_from_description()` function provides a complete pipeline for generating D&D 5e actors from natural language descriptions and optionally uploading them to FoundryVTT.

## Basic Usage

### Async API

```python
from actors.create_actor import create_actor_from_description
from foundry.client import FoundryClient

# Create actor with explicit CR
result = await create_actor_from_description(
    description="A fire-breathing drake with crystalline scales",
    challenge_rating=7
)

# Create actor with auto-determined CR
result = await create_actor_from_description(
    description="An ancient lich with reality-warping powers"
)

# Upload to FoundryVTT
client = FoundryClient(target="local")
result = await create_actor_from_description(
    description="A mutated sea creature",
    challenge_rating=5,
    foundry_client=client
)
```

### Synchronous API

```python
from actors.create_actor import create_actor_sync

result = create_actor_sync(
    description="A goblin warrior",
    challenge_rating=0.25
)
```

### Batch Creation

```python
from actors.create_actor import create_multiple_actors

descriptions = [
    ("Fire Drake", 7),
    ("Ice Drake", None),  # Auto CR
    ("Storm Drake", 15)
]

results = await create_multiple_actors(descriptions)
```

## Result Structure

```python
@dataclass
class ActorCreationResult:
    actor_uuid: str              # FoundryVTT UUID
    actor_name: str              # Final name
    challenge_rating: float      # Final CR
    text_file_path: Path         # Generated .txt
    stat_block: StatBlock        # Parsed stat block
    parsed_data: ParsedActorData # Detailed parse
    foundry_json: dict           # FoundryVTT format
    output_directory: Path       # All files location
    metadata: dict               # Execution metadata
```

## Output Files

All intermediate files saved to `output/actors/<timestamp>_<actor_name>/`:

- `actor.txt` - Generated stat block + bio
- `stat_block.json` - Basic StatBlock parsing
- `parsed_actor_data.json` - Detailed ParsedActorData
- `foundry_actor.json` - FoundryVTT format
- `metadata.json` - Pipeline metadata

## Error Handling

The pipeline uses fail-fast error handling. On failure:
- Partial progress saved to output directory
- Detailed error in `metadata.json`
- Exception raised with output directory path

```python
try:
    result = await create_actor_from_description(...)
except ActorCreationError as e:
    print(f"Failed: {e}")
    # Check output directory for partial files
```

## Examples

### Low-CR Creature
```python
result = await create_actor_from_description(
    description="A common goblin warrior with a rusty sword",
    challenge_rating=0.25
)
```

### Mid-CR Creature
```python
result = await create_actor_from_description(
    description="A fire elemental bound to an ancient forge",
    challenge_rating=5,
    bio_context="Awakened during ritual gone wrong"
)
```

### High-CR Boss
```python
result = await create_actor_from_description(
    description="An ancient dragon lich with necromantic powers",
    challenge_rating=21,
    name="Dracolich Vorgathax"
)
```

### Auto CR Determination
```python
# Gemini analyzes power level and chooses CR
result = await create_actor_from_description(
    description="A shadowy assassin with teleportation and invisibility",
    bio_context="Leader of the Nightblade Guild"
)
print(f"Gemini chose CR {result.challenge_rating}")
```
```

**Step 3: Commit documentation**

```bash
git add CLAUDE.md docs/actor-creation-usage.md
git commit -m "docs: add actor creation usage guide

- Add common commands to CLAUDE.md
- Create comprehensive usage guide
- Include examples for all CR ranges
- Document error handling and outputs"
```

---

## Task 10: Final Testing and Verification

**Files:**
- Run comprehensive test suite

**Step 1: Run all unit tests**

Run: `uv run pytest -m "not integration and not slow" -v`

Expected: All tests pass

**Step 2: Run integration tests**

Run: `uv run pytest -m integration -v`

Expected: All integration tests pass (requires API key)

**Step 3: Test manually with real example**

Run:
```bash
uv run python -c "
from actors.create_actor import create_actor_sync
result = create_actor_sync('A crystalline spider that feeds on magical energy', challenge_rating=3)
print(f'Created: {result.actor_name}')
print(f'CR: {result.challenge_rating}')
print(f'Output: {result.output_directory}')
"
```

Expected: Creates actor, prints details, saves all files

**Step 4: Verify output files**

Run: `ls -la output/actors/*/`

Expected: See all intermediate files (actor.txt, *.json, metadata.json)

**Step 5: Final commit**

```bash
git add -A
git commit -m "chore: final verification and testing

- All unit tests passing
- Integration tests verified
- Manual testing confirmed
- Ready for code review"
```

---

## Completion Checklist

- [ ] Task 1: Fix test mocks for new google-genai API
- [ ] Task 2: Create ActorCreationResult model
- [ ] Task 3: Create output directory helper
- [ ] Task 4: Create save intermediate file helper
- [ ] Task 5: Implement main pipeline function
- [ ] Task 6: Add synchronous wrapper
- [ ] Task 7: Add batch creation helper
- [ ] Task 8: Add integration test
- [ ] Task 9: Update documentation
- [ ] Task 10: Final testing and verification

## Next Steps

After implementation:
1. Run code review using @superpowers:requesting-code-review
2. Merge to main using @superpowers:finishing-a-development-branch
3. Consider adding CLI wrapper script in `scripts/` for easier usage
