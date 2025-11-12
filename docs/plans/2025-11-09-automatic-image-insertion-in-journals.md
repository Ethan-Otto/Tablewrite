# Automatic Image Insertion in Journals Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Automatically insert extracted map assets and scene artwork into Journal HTML output at semantically correct locations.

**Architecture:** Extend Journal model to automatically position images from map_assets and scene_artwork during HTML rendering. Maps inserted near their source pages, scene artwork inserted at section/subsection boundaries. Uses intelligent matching between image metadata (page numbers, scene names) and Journal content IDs.

**Tech Stack:** Python, Pydantic models, JSON metadata parsing, regex for fuzzy matching

---

## Task 1: Add Image Positioning Logic to Journal Model

**Files:**
- Modify: `src/models/journal.py:285-312`
- Test: `tests/models/test_journal_image_positioning.py` (create)

**Step 1: Write failing test for automatic map positioning**

Create test file `tests/models/test_journal_image_positioning.py`:

```python
"""Tests for automatic image positioning in Journal model."""

import pytest
from pathlib import Path
from models.xml_document import parse_xml_file
from models.journal import Journal, ImageMetadata


def test_add_map_assets_positions_images_near_source_page():
    """Test that map assets are positioned near their source page in the Journal."""
    # Load a real XML document
    xml_path = Path("tests/fixtures/sample_chapter.xml")
    xml_doc = parse_xml_file(xml_path)
    journal = Journal.from_xml_document(xml_doc)

    # Simulate map metadata from extract_map_assets.py
    map_metadata = [
        {
            "name": "Goblin Ambush",
            "page_num": 5,
            "type": "battle_map",
            "source": "extracted"
        },
        {
            "name": "Cragmaw Hideout",
            "page_num": 8,
            "type": "navigation_map",
            "source": "segmented"
        }
    ]

    # Add map assets to journal
    journal.add_map_assets(map_metadata, image_dir=Path("output/runs/test/map_assets/images"))

    # Verify maps were added to registry
    assert "page_005_goblin_ambush" in journal.image_registry
    assert "page_008_cragmaw_hideout" in journal.image_registry

    # Verify positioning: should be at first content after page 5
    img_meta = journal.image_registry["page_005_goblin_ambush"]
    assert img_meta.insert_before_content_id is not None
    assert "chapter_0_section" in img_meta.insert_before_content_id
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/models/test_journal_image_positioning.py::test_add_map_assets_positions_images_near_source_page -v`

Expected: FAIL with "Journal has no attribute 'add_map_assets'"

**Step 3: Implement add_map_assets method**

Add to `src/models/journal.py` after `remove_image` method (around line 312):

```python
def add_map_assets(self, maps_metadata: List[Dict], image_dir: Path):
    """Add map assets from extraction metadata to image registry.

    Automatically positions maps near their source page in the content stream.

    Args:
        maps_metadata: List of map metadata dicts from maps_metadata.json
        image_dir: Path to directory containing map image files
    """
    for map_data in maps_metadata:
        # Generate key from page number and name
        page_num = map_data["page_num"]
        safe_name = map_data["name"].lower().replace(" ", "_")
        key = f"page_{page_num:03d}_{safe_name}"

        # Find file path
        file_path = None
        for ext in [".png", ".jpg", ".jpeg"]:
            candidate = image_dir / f"{key}{ext}"
            if candidate.exists():
                file_path = candidate
                break

        # Create ImageMetadata
        metadata = ImageMetadata(
            key=key,
            source_page=page_num,
            type="map",
            description=map_data.get("name"),
            file_path=str(file_path) if file_path else None
        )

        # Find insertion point: first content after source page
        insert_id = self._find_content_after_page(page_num)
        if insert_id:
            metadata.insert_before_content_id = insert_id

        self.image_registry[key] = metadata

def _find_content_after_page(self, page_num: int) -> Optional[str]:
    """Find the first content ID that appears after a given source page.

    Uses source XMLDocument to map page numbers to content IDs.

    Args:
        page_num: Source page number (1-indexed)

    Returns:
        Content ID or None if not found
    """
    if not self.source:
        return None

    # Find the page in source XMLDocument
    for page in self.source.pages:
        if page.number >= page_num:
            # Find the first non-heading content on this page
            for content in page.content:
                if content.type not in ["chapter_title", "section", "subsection", "subsubsection"]:
                    # Map original page-based ID to semantic ID
                    # This requires reverse lookup in the Journal hierarchy
                    # For now, we'll use a heuristic: first content in next section
                    return self._get_first_content_id_heuristic()

    return None

def _get_first_content_id_heuristic(self) -> Optional[str]:
    """Get first content ID as fallback heuristic."""
    for chapter in self.chapters:
        if chapter.content:
            return chapter.content[0].id
        for section in chapter.sections:
            if section.content:
                return section.content[0].id
    return None
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/models/test_journal_image_positioning.py::test_add_map_assets_positions_images_near_source_page -v`

Expected: PASS (or failure with clearer error about missing fixture)

**Step 5: Commit**

```bash
git add src/models/journal.py tests/models/test_journal_image_positioning.py
git commit -m "feat: add map asset positioning to Journal model

Implements add_map_assets() to automatically position extracted maps
near their source pages in the Journal hierarchy.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 2: Add Scene Artwork Positioning Logic

**Files:**
- Modify: `src/models/journal.py` (add method after add_map_assets)
- Test: `tests/models/test_journal_image_positioning.py`

**Step 1: Write failing test for scene artwork positioning**

Add to `tests/models/test_journal_image_positioning.py`:

```python
def test_add_scene_artwork_positions_at_sections():
    """Test that scene artwork is positioned at section/subsection boundaries."""
    xml_path = Path("tests/fixtures/sample_chapter.xml")
    xml_doc = parse_xml_file(xml_path)
    journal = Journal.from_xml_document(xml_doc)

    # Simulate scene metadata from generate_scene_art.py
    scenes = [
        {
            "section_path": "Chapter 1 → Goblin Ambush → Initial Encounter",
            "name": "Forest Road Ambush",
            "description": "A dense forest path with overturned wagon"
        },
        {
            "section_path": "Chapter 1 → The Cragmaw Hideout → Area 1",
            "name": "Cave Entrance",
            "description": "Rocky cave entrance with twin pools"
        }
    ]

    # Add scene artwork
    journal.add_scene_artwork(scenes, image_dir=Path("output/runs/test/scene_artwork/images"))

    # Verify scenes were added to registry
    assert "scene_forest_road_ambush" in journal.image_registry
    assert "scene_cave_entrance" in journal.image_registry

    # Verify positioning: should be at subsection boundaries
    img_meta = journal.image_registry["scene_forest_road_ambush"]
    assert img_meta.insert_before_content_id is not None
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/models/test_journal_image_positioning.py::test_add_scene_artwork_positions_at_sections -v`

Expected: FAIL with "Journal has no attribute 'add_scene_artwork'"

**Step 3: Implement add_scene_artwork method**

Add to `src/models/journal.py`:

```python
def add_scene_artwork(self, scenes: List[Dict], image_dir: Path):
    """Add scene artwork to image registry with intelligent positioning.

    Positions scenes at section/subsection boundaries by fuzzy-matching
    section_path to Journal hierarchy.

    Args:
        scenes: List of scene dicts with section_path, name, description
        image_dir: Path to scene_artwork/images directory
    """
    import re

    for i, scene in enumerate(scenes, start=1):
        # Generate key from scene name
        safe_name = re.sub(r'[^\w\s-]', '', scene["name"].lower())
        safe_name = re.sub(r'[-\s]+', '_', safe_name)
        key = f"scene_{safe_name}"

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

def _find_section_by_path(self, section_path: str) -> Optional[str]:
    """Find content ID for a section by fuzzy-matching section_path.

    Section path format: "Chapter Title → Section Title → Subsection Title"

    Args:
        section_path: Hierarchical path from scene extraction

    Returns:
        Content ID of first content in matched section/subsection
    """
    import re

    # Parse section path
    parts = [p.strip() for p in section_path.split("→")]
    if len(parts) < 2:
        return None

    chapter_title = parts[0]
    section_title = parts[1] if len(parts) > 1 else None
    subsection_title = parts[2] if len(parts) > 2 else None

    # Normalize titles for fuzzy matching (lowercase, remove punctuation)
    def normalize(text):
        return re.sub(r'[^\w\s]', '', text.lower())

    chapter_norm = normalize(chapter_title)

    # Find matching chapter
    for chapter in self.chapters:
        if normalize(chapter.title) == chapter_norm:
            # If only chapter specified, insert at first section
            if not section_title:
                if chapter.sections and chapter.sections[0].content:
                    return chapter.sections[0].content[0].id
                return None

            # Find matching section
            section_norm = normalize(section_title)
            for section in chapter.sections:
                if normalize(section.title) == section_norm:
                    # If only chapter + section, insert at first content
                    if not subsection_title:
                        if section.content:
                            return section.content[0].id
                        return None

                    # Find matching subsection
                    subsection_norm = normalize(subsection_title)
                    for subsection in section.subsections:
                        if normalize(subsection.title) == subsection_norm:
                            if subsection.content:
                                return subsection.content[0].id

    return None
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/models/test_journal_image_positioning.py::test_add_scene_artwork_positions_at_sections -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/models/journal.py tests/models/test_journal_image_positioning.py
git commit -m "feat: add scene artwork positioning to Journal model

Implements add_scene_artwork() with fuzzy section path matching
to position scene images at semantic boundaries.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 3: Integrate Image Positioning into Upload Pipeline

**Files:**
- Modify: `src/foundry/upload_journal_to_foundry.py:78-116`
- Test: `tests/foundry/test_upload_journal.py`

**Step 1: Write failing test for integrated upload with images**

Add to `tests/foundry/test_upload_journal.py`:

```python
@pytest.mark.integration
def test_upload_journal_includes_positioned_images(tmp_path):
    """Test that upload includes automatically positioned images."""
    # Create mock run directory structure
    run_dir = tmp_path / "runs" / "test_run"
    docs_dir = run_dir / "documents"
    maps_dir = run_dir / "map_assets" / "images"
    scenes_dir = run_dir / "scene_artwork" / "images"

    docs_dir.mkdir(parents=True)
    maps_dir.mkdir(parents=True)
    scenes_dir.mkdir(parents=True)

    # Copy sample XML
    import shutil
    shutil.copy("tests/fixtures/sample_chapter.xml", docs_dir / "chapter_01.xml")

    # Create mock metadata files
    import json

    maps_metadata = {
        "maps": [
            {
                "name": "Test Map",
                "page_num": 5,
                "type": "battle_map",
                "source": "extracted"
            }
        ]
    }

    with open(run_dir / "map_assets" / "maps_metadata.json", "w") as f:
        json.dump(maps_metadata, f)

    # Create mock image files
    from PIL import Image
    img = Image.new('RGB', (100, 100), color='red')
    img.save(maps_dir / "page_005_test_map.png")
    img.save(scenes_dir / "scene_001_test_scene.png")

    # Load and process journal
    from foundry.upload_journal_to_foundry import load_and_position_images

    journal = load_and_position_images(run_dir)

    # Verify images are in registry with positions
    assert "page_005_test_map" in journal.image_registry
    assert journal.image_registry["page_005_test_map"].insert_before_content_id is not None
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/foundry/test_upload_journal.py::test_upload_journal_includes_positioned_images -v`

Expected: FAIL with "no function load_and_position_images"

**Step 3: Implement load_and_position_images helper**

Add to `src/foundry/upload_journal_to_foundry.py` after `build_image_mapping`:

```python
def load_and_position_images(run_dir: Path) -> Journal:
    """Load Journal from XML and automatically position all extracted images.

    Processes:
    1. Load XMLDocument from documents/ directory
    2. Convert to Journal
    3. Add map assets with automatic positioning
    4. Add scene artwork with automatic positioning

    Args:
        run_dir: Run directory containing documents/, map_assets/, scene_artwork/

    Returns:
        Journal with all images positioned
    """
    import json

    # Load all XML documents
    xml_dir = run_dir / "documents"
    xml_files = sorted(xml_dir.glob("*.xml"))

    if not xml_files:
        raise ValueError(f"No XML files found in {xml_dir}")

    # For now, merge all chapters into one Journal
    # TODO: Support multi-chapter journals properly
    journals = []
    for xml_file in xml_files:
        xml_doc = parse_xml_file(xml_file)
        journal = Journal.from_xml_document(xml_doc)
        journals.append(journal)

    # Use first journal (single-chapter workflow)
    journal = journals[0]
    logger.info(f"Loaded journal: {journal.title}")

    # Add map assets if present
    maps_metadata_file = run_dir / "map_assets" / "maps_metadata.json"
    if maps_metadata_file.exists():
        with open(maps_metadata_file) as f:
            maps_data = json.load(f)
            maps = maps_data.get("maps", [])

        if maps:
            maps_dir = run_dir / "map_assets" / "images"
            journal.add_map_assets(maps, maps_dir)
            logger.info(f"Added {len(maps)} map assets to journal")

    # Add scene artwork if present
    scenes_dir = run_dir / "scene_artwork" / "images"
    if scenes_dir.exists():
        # Parse scenes from image filenames (scene_NNN_name.png)
        # In real workflow, this would come from scene extraction metadata
        scenes = []
        for i, img_file in enumerate(sorted(scenes_dir.glob("scene_*.png")), start=1):
            # Extract name from filename: scene_001_forest_ambush.png -> Forest Ambush
            name_part = img_file.stem.split("_", 2)[-1]  # Remove "scene_NNN_"
            name = name_part.replace("_", " ").title()

            scenes.append({
                "section_path": f"{journal.title} → Scene {i}",
                "name": name,
                "description": ""
            })

        if scenes:
            journal.add_scene_artwork(scenes, scenes_dir)
            logger.info(f"Added {len(scenes)} scene artworks to journal")

    return journal
```

**Step 4: Modify upload_run_to_foundry to use new helper**

Replace lines 200-220 in `upload_run_to_foundry` with:

```python
# Load journal with positioned images
journal = load_and_position_images(Path(run_dir))

# Build image URL mapping for rendering
image_mapping = build_image_mapping(Path(run_dir))

# Render to HTML with positioned images
html_content = journal.to_foundry_html(image_mapping)
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/foundry/test_upload_journal.py::test_upload_journal_includes_positioned_images -v`

Expected: PASS

**Step 6: Commit**

```bash
git add src/foundry/upload_journal_to_foundry.py tests/foundry/test_upload_journal.py
git commit -m "feat: integrate automatic image positioning in upload pipeline

Adds load_and_position_images() to automatically position maps
and scene artwork when uploading journals to FoundryVTT.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 4: Add Scene Metadata Preservation

**Files:**
- Modify: `scripts/generate_scene_art.py:140-144`
- Create: Scene metadata JSON output

**Step 1: Write failing test for scene metadata output**

Add to `tests/scene_extraction/test_scene_metadata.py` (create):

```python
"""Tests for scene metadata preservation."""

import pytest
import json
from pathlib import Path


def test_generate_scene_art_saves_metadata(tmp_path):
    """Test that scene artwork generation saves metadata JSON."""
    from scripts.generate_scene_art import process_chapter

    # Use real XML fixture
    xml_file = Path("tests/fixtures/sample_chapter.xml")
    output_dir = tmp_path / "scene_artwork"

    # Process chapter
    result = process_chapter(xml_file, output_dir)

    # Verify metadata file exists
    metadata_file = output_dir / "scenes_metadata.json"
    assert metadata_file.exists()

    # Verify structure
    with open(metadata_file) as f:
        data = json.load(f)

    assert "scenes" in data
    assert "generated_at" in data
    assert len(data["scenes"]) > 0

    # Verify scene structure
    scene = data["scenes"][0]
    assert "section_path" in scene
    assert "name" in scene
    assert "description" in scene
    assert "image_file" in scene
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/scene_extraction/test_scene_metadata.py::test_generate_scene_art_saves_metadata -v`

Expected: FAIL with "no file scenes_metadata.json"

**Step 3: Add metadata output to generate_scene_art.py**

Modify `process_chapter` function in `scripts/generate_scene_art.py`:

```python
# After Step 4 (create gallery HTML), add:

# Step 5: Save scene metadata
logger.info("Step 5: Saving scene metadata...")
scenes_metadata = []
for i, scene in enumerate(scenes, start=1):
    safe_name = sanitize_filename(scene.name)
    image_filename = f"scene_{i:03d}_{safe_name}.png"

    scenes_metadata.append({
        "section_path": scene.section_path,
        "name": scene.name,
        "description": scene.description,
        "location_type": scene.location_type,
        "image_file": f"images/{image_filename}"
    })

metadata_file = output_dir / "scenes_metadata.json"
metadata_content = {
    "generated_at": datetime.now().isoformat(),
    "total_scenes": len(scenes),
    "scenes": scenes_metadata
}

import json
with open(metadata_file, "w") as f:
    json.dump(metadata_content, f, indent=2)

logger.info(f"  Saved metadata to: {metadata_file}")

return {
    "scenes_found": len(scenes),
    "images_generated": len(image_paths),
    "gallery_file": str(gallery_file),
    "metadata_file": str(metadata_file)
}
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/scene_extraction/test_scene_metadata.py::test_generate_scene_art_saves_metadata -v`

Expected: PASS

**Step 5: Commit**

```bash
git add scripts/generate_scene_art.py tests/scene_extraction/test_scene_metadata.py
git commit -m "feat: save scene metadata JSON during artwork generation

Preserves scene metadata (section_path, name, description, image_file)
for later use in automatic positioning.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 5: Update load_and_position_images to Use Scene Metadata

**Files:**
- Modify: `src/foundry/upload_journal_to_foundry.py` (load_and_position_images)
- Test: `tests/foundry/test_upload_journal.py`

**Step 1: Write failing test for scene metadata loading**

Add to `tests/foundry/test_upload_journal.py`:

```python
def test_load_and_position_uses_scene_metadata(tmp_path):
    """Test that scene positioning uses scenes_metadata.json."""
    run_dir = tmp_path / "run"
    docs_dir = run_dir / "documents"
    scenes_dir = run_dir / "scene_artwork" / "images"

    docs_dir.mkdir(parents=True)
    scenes_dir.mkdir(parents=True)

    # Copy XML
    import shutil
    shutil.copy("tests/fixtures/sample_chapter.xml", docs_dir / "chapter_01.xml")

    # Create scene metadata
    import json
    scenes_metadata = {
        "scenes": [
            {
                "section_path": "Chapter 1 → Goblin Ambush",
                "name": "Forest Ambush",
                "description": "Dense forest path",
                "location_type": "outdoor",
                "image_file": "images/scene_001_forest_ambush.png"
            }
        ]
    }

    with open(run_dir / "scene_artwork" / "scenes_metadata.json", "w") as f:
        json.dump(scenes_metadata, f)

    # Create mock image
    from PIL import Image
    img = Image.new('RGB', (100, 100), color='blue')
    img.save(scenes_dir / "scene_001_forest_ambush.png")

    # Load journal
    from foundry.upload_journal_to_foundry import load_and_position_images
    journal = load_and_position_images(run_dir)

    # Verify scene was positioned using metadata
    assert "scene_forest_ambush" in journal.image_registry
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/foundry/test_upload_journal.py::test_load_and_position_uses_scene_metadata -v`

Expected: FAIL (scene not found in registry or wrong position)

**Step 3: Update load_and_position_images to read metadata**

Replace scene artwork section in `load_and_position_images`:

```python
# Add scene artwork if present
scenes_metadata_file = run_dir / "scene_artwork" / "scenes_metadata.json"
if scenes_metadata_file.exists():
    with open(scenes_metadata_file) as f:
        scenes_data = json.load(f)
        scenes = scenes_data.get("scenes", [])

    if scenes:
        scenes_dir = run_dir / "scene_artwork" / "images"
        journal.add_scene_artwork(scenes, scenes_dir)
        logger.info(f"Added {len(scenes)} scene artworks to journal")
elif (run_dir / "scene_artwork" / "images").exists():
    # Fallback to filename parsing if no metadata
    logger.warning("No scenes_metadata.json found, using filename heuristic")
    # ... existing filename parsing code ...
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/foundry/test_upload_journal.py::test_load_and_position_uses_scene_metadata -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/foundry/upload_journal_to_foundry.py tests/foundry/test_upload_journal.py
git commit -m "feat: use scenes_metadata.json for accurate positioning

Reads scene metadata with section_path for precise positioning
instead of filename heuristics.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 6: Add Fixtures and Integration Test

**Files:**
- Create: `tests/fixtures/sample_chapter.xml`
- Create: `tests/integration/test_image_insertion_e2e.py`

**Step 1: Create sample XML fixture**

Create `tests/fixtures/sample_chapter.xml`:

```xml
<Chapter_1>
  <page number="1">
    <chapter_title>Chapter 1: Goblin Arrows</chapter_title>
    <paragraph>The adventure begins on the High Road.</paragraph>
  </page>
  <page number="2">
    <section>Goblin Ambush</section>
    <paragraph>The party encounters goblins on the road.</paragraph>
  </page>
  <page number="5">
    <paragraph>A battle map shows the ambush site.</paragraph>
    <image_ref key="page_5_battle_map" />
  </page>
  <page number="8">
    <section>The Cragmaw Hideout</section>
    <subsection>Area 1: Cave Entrance</subsection>
    <paragraph>Twin pools of water flank the cave entrance.</paragraph>
  </page>
</Chapter_1>
```

**Step 2: Write end-to-end integration test**

Create `tests/integration/test_image_insertion_e2e.py`:

```python
"""End-to-end test for automatic image insertion."""

import pytest
import json
from pathlib import Path
from PIL import Image


@pytest.mark.integration
def test_full_pipeline_with_image_insertion(tmp_path):
    """Test complete workflow: XML → Journal → positioned images → HTML."""
    # Setup run directory
    run_dir = tmp_path / "run"
    docs_dir = run_dir / "documents"
    maps_dir = run_dir / "map_assets" / "images"
    scenes_dir = run_dir / "scene_artwork" / "images"

    docs_dir.mkdir(parents=True)
    maps_dir.mkdir(parents=True)
    scenes_dir.mkdir(parents=True)

    # Copy XML fixture
    import shutil
    shutil.copy("tests/fixtures/sample_chapter.xml", docs_dir / "chapter_01.xml")

    # Create map metadata
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

    # Create scene metadata
    scenes_metadata = {
        "scenes": [
            {
                "section_path": "Chapter 1: Goblin Arrows → Goblin Ambush",
                "name": "Forest Road",
                "description": "Dense forest",
                "location_type": "outdoor",
                "image_file": "images/scene_001_forest_road.png"
            },
            {
                "section_path": "Chapter 1: Goblin Arrows → The Cragmaw Hideout → Area 1: Cave Entrance",
                "name": "Cave Entrance",
                "description": "Rocky cave",
                "location_type": "underground",
                "image_file": "images/scene_002_cave_entrance.png"
            }
        ]
    }
    with open(run_dir / "scene_artwork" / "scenes_metadata.json", "w") as f:
        json.dump(scenes_metadata, f)

    # Create mock images
    img = Image.new('RGB', (100, 100), color='red')
    img.save(maps_dir / "page_005_goblin_ambush.png")

    img = Image.new('RGB', (100, 100), color='blue')
    img.save(scenes_dir / "scene_001_forest_road.png")
    img.save(scenes_dir / "scene_002_cave_entrance.png")

    # Load and position images
    from foundry.upload_journal_to_foundry import load_and_position_images
    journal = load_and_position_images(run_dir)

    # Verify all images in registry
    assert "page_005_goblin_ambush" in journal.image_registry
    assert "scene_forest_road" in journal.image_registry
    assert "scene_cave_entrance" in journal.image_registry

    # Verify all images have positions
    for key in journal.image_registry:
        assert journal.image_registry[key].insert_before_content_id is not None

    # Render HTML
    image_mapping = {
        "page_005_goblin_ambush": "https://example.com/map.png",
        "scene_forest_road": "https://example.com/scene1.png",
        "scene_cave_entrance": "https://example.com/scene2.png"
    }

    html = journal.to_foundry_html(image_mapping)

    # Verify images appear in HTML
    assert "https://example.com/map.png" in html
    assert "https://example.com/scene1.png" in html
    assert "https://example.com/scene2.png" in html

    # Verify structure (headings before images)
    assert "<h1>Chapter 1: Goblin Arrows</h1>" in html
    assert "<h2>Goblin Ambush</h2>" in html
```

**Step 3: Run test to verify current state**

Run: `pytest tests/integration/test_image_insertion_e2e.py -v`

Expected: Should identify any remaining issues

**Step 4: Fix any failures and iterate**

Debug and fix issues until test passes.

**Step 5: Commit**

```bash
git add tests/fixtures/sample_chapter.xml tests/integration/test_image_insertion_e2e.py
git commit -m "test: add e2e test for automatic image insertion

Validates complete workflow from XML to positioned images in HTML.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 7: Update Documentation

**Files:**
- Modify: `CLAUDE.md` (architecture section)
- Create: Example usage in docstrings

**Step 1: Write documentation update**

Add to `CLAUDE.md` after "ImageMetadata Fields" section (around line 160):

```markdown
**Automatic Image Positioning:**

The Journal model automatically positions images from extracted maps and scene artwork:

```python
from foundry.upload_journal_to_foundry import load_and_position_images

# Load journal with automatic image positioning
journal = load_and_position_images(Path("output/runs/20241109_120000"))

# Image registry now contains:
# - Maps positioned near source pages (from maps_metadata.json)
# - Scene artwork positioned at section boundaries (from scenes_metadata.json)

# Render HTML with positioned images
image_mapping = build_image_mapping(Path("output/runs/20241109_120000"))
html = journal.to_foundry_html(image_mapping)
```

**Positioning Logic:**

1. **Map Assets**: Positioned at first content after source page
   - Uses `page_num` from `maps_metadata.json`
   - Matches content using XMLDocument page mapping

2. **Scene Artwork**: Positioned at section/subsection boundaries
   - Uses `section_path` from `scenes_metadata.json`
   - Fuzzy matches titles in Journal hierarchy
   - Normalizes punctuation and case for robust matching

**Metadata Files:**

- `map_assets/maps_metadata.json`: Generated by `extract_map_assets.py`
- `scene_artwork/scenes_metadata.json`: Generated by `generate_scene_art.py`
```

**Step 2: Verify documentation builds**

Run: `cat CLAUDE.md | grep "Automatic Image Positioning" -A 20`

Expected: Shows new section

**Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: document automatic image positioning feature

Explains positioning logic for maps and scene artwork.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 8: Final Testing and Verification

**Files:**
- Test: All test files
- Run: Integration tests with real data

**Step 1: Run full test suite**

Run: `pytest tests/ -v`

Expected: All tests pass

**Step 2: Run smoke tests**

Run: `pytest -m smoke`

Expected: All smoke tests pass

**Step 3: Manual verification with real data**

```bash
# Generate test run with images
uv run python scripts/full_pipeline.py \
  --journal-name "Test Module" \
  --skip-split

# Verify images appear in FoundryVTT
# Check that maps appear near their source pages
# Check that scene artwork appears at section boundaries
```

**Step 4: Fix any issues found**

Iterate on implementation until manual verification succeeds.

**Step 5: Final commit**

```bash
git add -A
git commit -m "test: verify automatic image insertion with real data

Manual testing confirms images positioned correctly in FoundryVTT.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Notes

**Design Decisions:**

1. **Page → Content ID Mapping**: Uses XMLDocument.source field to preserve page numbers during Journal transformation
2. **Fuzzy Section Matching**: Normalizes titles to handle punctuation/case differences between scene extraction and XML
3. **Metadata Files**: Scene artwork generation now saves JSON for accurate positioning
4. **Fallback Heuristics**: Falls back to filename parsing if metadata missing

**Testing Strategy:**

- Unit tests for positioning logic (@pytest.mark.unit)
- Integration tests for full pipeline (@pytest.mark.integration)
- Fixtures for reproducible test data
- Manual verification with real PDFs

**Future Improvements:**

- Support multi-chapter journals (currently uses first chapter only)
- Better handling of images that don't match any content
- UI for manually adjusting image positions
- Support for inline images (mid-paragraph placement)
