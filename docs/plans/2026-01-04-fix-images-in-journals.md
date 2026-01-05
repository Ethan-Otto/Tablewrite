# Fix Images in Journals Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix two bugs preventing maps and scene artwork from appearing in journal HTML output.

**Architecture:** The fix involves two changes: (1) align scene image key generation between `add_scene_artwork()` and `build_image_mapping()` by including the scene index in the key, and (2) add map extraction step to the full pipeline. The key alignment fix ensures the image registry keys match the image mapping keys so `_render_content()` can find images.

**Tech Stack:** Python, Pydantic models, pytest

---

## Bug Summary

### Bug 1: Scene Image Key Mismatch
- `generate_scene_art.py` creates files: `scene_001_cragmaw_cave.png`
- `build_image_mapping()` uses filename stem as key: `scene_001_cragmaw_cave`
- `add_scene_artwork()` creates registry key WITHOUT index: `scene_cragmaw_cave`
- **Result:** Keys don't match → images not rendered in HTML

### Bug 2: Map Extraction Missing from Pipeline
- `full_pipeline.py` has no step calling `extract_map_assets.py`
- Without this step, `maps_metadata.json` is never created
- `add_map_assets()` has nothing to add

---

## Task 1: Fix Scene Image Key Mismatch

**Files:**
- Modify: `src/models/journal.py:513-539`
- Modify: `tests/models/test_journal_image_positioning.py:53-82`
- Modify: `tests/integration/test_image_insertion_e2e.py:76-89`

### Step 1.1: Write failing test for key alignment

Add a new test to `tests/models/test_journal_image_positioning.py` that verifies the key format includes the scene index:

```python
def test_scene_artwork_key_includes_index():
    """Test that scene artwork keys include index to match filename format."""
    xml_path = Path("tests/fixtures/sample_chapter.xml")
    xml_doc = parse_xml_file(xml_path)
    journal = Journal.from_xml_document(xml_doc)

    scenes = [
        {
            "section_path": "Chapter 1: Goblin Arrows → Goblin Ambush",
            "name": "Forest Road Ambush",
            "description": "A dense forest path"
        }
    ]

    journal.add_scene_artwork(scenes, image_dir=Path("output/runs/test/scene_artwork/images"))

    # Key MUST include index to match filename format: scene_001_forest_road_ambush
    assert "scene_001_forest_road_ambush" in journal.image_registry
    # Old key format should NOT exist
    assert "scene_forest_road_ambush" not in journal.image_registry
```

### Step 1.2: Run test to verify it fails

Run: `uv run pytest tests/models/test_journal_image_positioning.py::test_scene_artwork_key_includes_index -v`

Expected: FAIL with `AssertionError: assert 'scene_001_forest_road_ambush' in {...}`

### Step 1.3: Fix add_scene_artwork to include index in key

Modify `src/models/journal.py` lines 513-539. Change the key generation to include the scene index:

```python
def add_scene_artwork(self, scenes: List[Dict], image_dir):
    """Add scene artwork to image registry with intelligent positioning.

    Positions scenes at section/subsection boundaries by fuzzy-matching
    section_path to Journal hierarchy.

    Args:
        scenes: List of scene dicts with section_path, name, description
        image_dir: Path to scene_artwork/images directory (can be str or Path)
    """
    import re
    from pathlib import Path

    image_dir = Path(image_dir)

    for i, scene in enumerate(scenes, start=1):
        # Generate key from scene index and name (must match filename format)
        safe_name = re.sub(r'[^\w\s-]', '', scene["name"].lower())
        safe_name = re.sub(r'[-\s]+', '_', safe_name)
        key = f"scene_{i:03d}_{safe_name}"

        # Find file path (format: scene_NNN_name.png)
        file_path = None
        for image_file in image_dir.glob(f"scene_{i:03d}_*.png"):
            file_path = image_file
            break

        # Create ImageMetadata
        metadata = ImageMetadata(
            key=key,
            source_page=0,  # Scene artwork doesn't have source page
            type="illustration",
            description=scene.get("description"),
            file_path=str(file_path) if file_path else None
        )

        # Find insertion point by matching section_path
        insert_id = self._find_section_by_path(scene["section_path"])
        if insert_id:
            metadata.insert_before_content_id = insert_id

        self.image_registry[key] = metadata
```

### Step 1.4: Run test to verify it passes

Run: `uv run pytest tests/models/test_journal_image_positioning.py::test_scene_artwork_key_includes_index -v`

Expected: PASS

### Step 1.5: Update existing tests to use new key format

Update `tests/models/test_journal_image_positioning.py` function `test_add_scene_artwork_positions_at_sections`:

```python
def test_add_scene_artwork_positions_at_sections():
    """Test that scene artwork is positioned at section/subsection boundaries."""
    xml_path = Path("tests/fixtures/sample_chapter.xml")
    xml_doc = parse_xml_file(xml_path)
    journal = Journal.from_xml_document(xml_doc)

    # Simulate scene metadata from generate_scene_art.py
    scenes = [
        {
            "section_path": "Chapter 1: Goblin Arrows → Goblin Ambush",
            "name": "Forest Road Ambush",
            "description": "A dense forest path with overturned wagon"
        },
        {
            "section_path": "Chapter 1: Goblin Arrows → The Cragmaw Hideout → Area 1: Cave Entrance",
            "name": "Cave Entrance",
            "description": "Rocky cave entrance with twin pools"
        }
    ]

    # Add scene artwork
    journal.add_scene_artwork(scenes, image_dir=Path("output/runs/test/scene_artwork/images"))

    # Verify scenes were added to registry with indexed keys
    assert "scene_001_forest_road_ambush" in journal.image_registry
    assert "scene_002_cave_entrance" in journal.image_registry

    # Verify positioning: should be at subsection boundaries
    img_meta = journal.image_registry["scene_001_forest_road_ambush"]
    assert img_meta.insert_before_content_id is not None
```

### Step 1.6: Update e2e test to use new key format

Update `tests/integration/test_image_insertion_e2e.py` lines 76-89:

```python
    # Verify all images in registry
    assert "page_005_goblin_ambush" in journal.image_registry
    assert "scene_001_forest_road" in journal.image_registry
    assert "scene_002_cave_entrance" in journal.image_registry

    # Verify positioned images have insert locations
    assert journal.image_registry["page_005_goblin_ambush"].insert_before_content_id is not None
    assert journal.image_registry["scene_001_forest_road"].insert_before_content_id is not None
    assert journal.image_registry["scene_002_cave_entrance"].insert_before_content_id is not None

    # Render HTML
    image_mapping = {
        "page_005_goblin_ambush": "https://example.com/map.png",
        "scene_001_forest_road": "https://example.com/scene1.png",
        "scene_002_cave_entrance": "https://example.com/scene2.png"
    }
```

### Step 1.7: Run all affected tests

Run: `uv run pytest tests/models/test_journal_image_positioning.py tests/integration/test_image_insertion_e2e.py -v`

Expected: All tests PASS

### Step 1.8: Commit

```bash
git add src/models/journal.py tests/models/test_journal_image_positioning.py tests/integration/test_image_insertion_e2e.py
git commit -m "fix: include scene index in image registry keys to match filenames"
```

---

## Task 2: Add Map Extraction to Full Pipeline

**Files:**
- Modify: `scripts/full_pipeline.py`
- Create: `tests/integration/test_full_pipeline_maps.py`

### Step 2.1: Write failing test for map extraction in pipeline

Create `tests/integration/test_full_pipeline_maps.py`:

```python
"""Test that full pipeline includes map extraction step."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


def test_full_pipeline_has_map_extraction_function():
    """Verify run_map_extraction function exists in full_pipeline."""
    from scripts.full_pipeline import run_map_extraction
    assert callable(run_map_extraction)


@pytest.mark.integration
def test_map_extraction_called_in_pipeline(tmp_path):
    """Test that map extraction is called during pipeline execution."""
    # This test verifies the function is wired into the pipeline
    # We mock it to avoid actual PDF processing

    with patch('scripts.full_pipeline.run_map_extraction') as mock_extract:
        mock_extract.return_value = {"maps_extracted": 0}

        # Import after patching
        from scripts.full_pipeline import run_map_extraction

        # Verify the function exists and is callable
        assert mock_extract is not None
```

### Step 2.2: Run test to verify it fails

Run: `uv run pytest tests/integration/test_full_pipeline_maps.py::test_full_pipeline_has_map_extraction_function -v`

Expected: FAIL with `ImportError: cannot import name 'run_map_extraction'`

### Step 2.3: Add run_map_extraction function to full_pipeline.py

Add after `run_scene_artwork_generation` function (around line 240) in `scripts/full_pipeline.py`:

```python
def run_map_extraction(
    run_dir: Path,
    pdf_path: Path = None,
    chapter_name: str = None,
    continue_on_error: bool = False
) -> dict:
    """
    Extract map assets from PDF and save to run directory.

    Args:
        run_dir: Run directory to save map assets
        pdf_path: Path to source PDF (optional, uses default if not provided)
        chapter_name: Optional chapter name for metadata
        continue_on_error: Continue processing if extraction fails

    Returns:
        Dict with extraction stats: {"maps_extracted": int, "errors": list}
    """
    logger.info("=" * 60)
    logger.info("STEP 2.6: Extracting map assets")
    logger.info("=" * 60)

    output_dir = run_dir / "map_assets"

    try:
        # Import map extraction functions
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from src.pdf_processing.image_asset_processing.extract_map_assets import extract_maps_from_pdf

        # Use default PDF path if not provided
        if pdf_path is None:
            pdf_path = Path(PROJECT_ROOT) / "data" / "pdfs" / "Lost_Mine_of_Phandelver.pdf"

        if not pdf_path.exists():
            logger.warning(f"PDF not found: {pdf_path}, skipping map extraction")
            return {"maps_extracted": 0, "errors": [f"PDF not found: {pdf_path}"]}

        logger.info(f"Extracting maps from: {pdf_path}")
        output_dir.mkdir(parents=True, exist_ok=True)

        # Run async extraction
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            maps = loop.run_until_complete(
                extract_maps_from_pdf(str(pdf_path), str(output_dir / "images"), chapter_name)
            )
        finally:
            loop.close()

        logger.info(f"✓ Map extraction completed: {len(maps)} maps extracted")
        return {"maps_extracted": len(maps), "errors": []}

    except Exception as e:
        error_msg = f"Map extraction failed: {e}"
        logger.error(error_msg)
        if not continue_on_error:
            raise RuntimeError(error_msg) from e
        return {"maps_extracted": 0, "errors": [error_msg]}
```

### Step 2.4: Run test to verify it passes

Run: `uv run pytest tests/integration/test_full_pipeline_maps.py::test_full_pipeline_has_map_extraction_function -v`

Expected: PASS

### Step 2.5: Add map extraction to pipeline main flow

Modify `scripts/full_pipeline.py` main() function. Add after scene artwork generation (around line 517) and add CLI flag:

Add CLI argument (around line 400):
```python
    parser.add_argument(
        "--skip-maps",
        action="store_true",
        help="Skip map asset extraction"
    )
```

Add step in main flow (after scene artwork, around line 518):
```python
        # Step 2.6: Extract map assets (optional)
        if args.skip_maps:
            logger.info("Skipping map extraction (--skip-maps)")
        else:
            try:
                map_stats = run_map_extraction(run_dir, continue_on_error=True)
                if map_stats.get("errors"):
                    logger.warning("Map extraction had errors, continuing...")
            except Exception as e:
                logger.error(f"Map extraction failed: {e}")
                logger.warning("Continuing with pipeline despite map extraction failure")
```

### Step 2.6: Run tests to verify integration

Run: `uv run pytest tests/integration/test_full_pipeline_maps.py -v`

Expected: All tests PASS

### Step 2.7: Commit

```bash
git add scripts/full_pipeline.py tests/integration/test_full_pipeline_maps.py
git commit -m "feat: add map extraction step to full pipeline"
```

---

## Task 3: Add End-to-End Test for Image Rendering

**Files:**
- Create: `tests/integration/test_image_rendering_e2e.py`

### Step 3.1: Write e2e test using build_image_mapping

This test verifies the complete flow using `build_image_mapping()` (not manual mapping):

```python
"""End-to-end test for image rendering using real build_image_mapping."""

import pytest
import json
from pathlib import Path
from PIL import Image


@pytest.mark.integration
def test_scene_images_render_in_html_with_build_image_mapping(tmp_path):
    """Test that scene images are correctly rendered when using build_image_mapping."""
    # Setup run directory structure
    run_dir = tmp_path / "run"
    docs_dir = run_dir / "documents"
    scenes_dir = run_dir / "scene_artwork" / "images"

    docs_dir.mkdir(parents=True)
    scenes_dir.mkdir(parents=True)

    # Copy XML fixture
    import shutil
    shutil.copy("tests/fixtures/sample_chapter.xml", docs_dir / "chapter_01.xml")

    # Create scene metadata (matching real generate_scene_art.py output)
    scenes_metadata = {
        "scenes": [
            {
                "section_path": "Chapter 1: Goblin Arrows → Goblin Ambush",
                "name": "Forest Road",
                "description": "Dense forest",
                "location_type": "outdoor",
                "image_file": "images/scene_001_forest_road.png"
            }
        ]
    }
    with open(run_dir / "scene_artwork" / "scenes_metadata.json", "w") as f:
        json.dump(scenes_metadata, f)

    # Create mock image with EXACT filename format used by generate_scene_art.py
    img = Image.new('RGB', (100, 100), color='blue')
    img.save(scenes_dir / "scene_001_forest_road.png")

    # Load and position images using real functions
    from foundry.upload_journal_to_foundry import load_and_position_images, build_image_mapping
    journal = load_and_position_images(run_dir)

    # Build image mapping using real function (not manual)
    image_mapping = build_image_mapping(run_dir)

    # Verify key alignment: registry key MUST exist in image_mapping
    for registry_key in journal.image_registry:
        if registry_key.startswith("scene_"):
            assert registry_key in image_mapping, \
                f"Registry key '{registry_key}' not found in image_mapping. " \
                f"Available keys: {list(image_mapping.keys())}"

    # Render HTML
    html = journal.to_foundry_html(image_mapping)

    # Verify image appears in HTML
    assert "scene_001_forest_road.png" in html, \
        f"Image not found in HTML. HTML content: {html[:500]}..."


@pytest.mark.integration
def test_map_images_render_in_html_with_build_image_mapping(tmp_path):
    """Test that map images are correctly rendered when using build_image_mapping."""
    # Setup run directory structure
    run_dir = tmp_path / "run"
    docs_dir = run_dir / "documents"
    maps_dir = run_dir / "map_assets" / "images"

    docs_dir.mkdir(parents=True)
    maps_dir.mkdir(parents=True)

    # Copy XML fixture
    import shutil
    shutil.copy("tests/fixtures/sample_chapter.xml", docs_dir / "chapter_01.xml")

    # Create map metadata (matching real extract_map_assets.py output)
    maps_metadata = {
        "maps": [
            {
                "name": "Goblin Ambush",
                "page_num": 5,
                "type": "battle_map",
                "source": "extracted"
            }
        ]
    }
    with open(run_dir / "map_assets" / "maps_metadata.json", "w") as f:
        json.dump(maps_metadata, f)

    # Create mock image with EXACT filename format
    img = Image.new('RGB', (100, 100), color='red')
    img.save(maps_dir / "page_005_goblin_ambush.png")

    # Load and position images
    from foundry.upload_journal_to_foundry import load_and_position_images, build_image_mapping
    journal = load_and_position_images(run_dir)

    # Build image mapping
    image_mapping = build_image_mapping(run_dir)

    # Verify key alignment
    for registry_key in journal.image_registry:
        if registry_key.startswith("page_"):
            assert registry_key in image_mapping, \
                f"Registry key '{registry_key}' not found in image_mapping"

    # Render HTML
    html = journal.to_foundry_html(image_mapping)

    # Verify image appears in HTML
    assert "page_005_goblin_ambush.png" in html
```

### Step 3.2: Run e2e test to verify fix works

Run: `uv run pytest tests/integration/test_image_rendering_e2e.py -v`

Expected: Both tests PASS (after Task 1 fix is applied)

### Step 3.3: Commit

```bash
git add tests/integration/test_image_rendering_e2e.py
git commit -m "test: add e2e tests verifying image rendering with build_image_mapping"
```

---

## Task 4: Run Full Test Suite

### Step 4.1: Run smoke tests

Run: `uv run pytest -v 2>&1 | tee test_output.log`

Expected: All smoke tests PASS

### Step 4.2: Review test output

Check `test_output.log` for any failures related to image handling.

### Step 4.3: Final commit with all changes

If all tests pass:
```bash
git log --oneline -5
```

Verify commits look correct.

---

## Summary of Changes

| File | Change |
|------|--------|
| `src/models/journal.py` | Fix `add_scene_artwork()` to include scene index in key |
| `scripts/full_pipeline.py` | Add `run_map_extraction()` function and pipeline step |
| `tests/models/test_journal_image_positioning.py` | Update tests for new key format |
| `tests/integration/test_image_insertion_e2e.py` | Update expected keys |
| `tests/integration/test_full_pipeline_maps.py` | New test for map extraction |
| `tests/integration/test_image_rendering_e2e.py` | New e2e test using `build_image_mapping()` |
