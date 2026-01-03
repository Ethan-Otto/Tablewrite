# Scene & Wall Integration Design

> Full orchestration pipeline: battle map image → wall detection → upload → FoundryVTT scene

## Overview

Create a single function `create_scene_from_map()` that takes a battle map image, detects walls using AI, uploads the image to FoundryVTT, and creates a scene with walls embedded.

## High-Level Architecture

```
create_scene_from_map("castle.webp")
    │
    ├─► Wall Detection Pipeline (existing)
    │   └─► redline_walls() → walls JSON + debug artifacts
    │
    ├─► Grid Detection (new)
    │   ├─► detect_gridlines() → {has_grid: bool, grid_size: int}
    │   └─► estimate_scene_size() → fallback dimensions (no AI)
    │
    ├─► File Upload (new)
    │   └─► Backend → WebSocket → Foundry module
    │       └─► Saves to worlds/<world>/uploaded-maps/<filename>
    │
    └─► Scene Creation (partially exists)
        └─► Backend → WebSocket → Foundry module
            └─► Scene.create() with walls + background image
    │
    ▼
SceneCreationResult
├── uuid: "Scene.abc123"
├── name: "Castle" (derived from filename)
├── foundry_image_path: "worlds/myworld/uploaded-maps/castle.webp"
├── grid_size: 70 (or null if gridless)
├── wall_count: 874
├── output_dir: Path("output/runs/.../scenes/castle/")
├── timestamp: "20241102_143022"
└── debug_artifacts: {grayscale, redlined, overlay, walls_json, ...}
```

## New Files & Modules

### New files to create:

```
src/scenes/
├── __init__.py
├── orchestrate.py          # Main pipeline: create_scene_from_map()
├── models.py               # SceneCreationResult, GridDetectionResult
├── detect_gridlines.py     # AI-powered grid detection (Gemini)
└── estimate_scene_size.py  # Simple math for gridless maps

src/foundry/
├── scenes.py               # (exists) Add create_scene(), delete_scene()
└── files.py                # (new) upload_file() for image transfer

ui/backend/app/routers/
└── foundry.py              # Add POST /api/foundry/scene
                            # Add POST /api/foundry/files/upload

foundry-module/tablewrite-assistant/src/handlers/
└── files.ts                # (exists) Add handleFileUpload()
```

### Modifications to existing files:

- `src/foundry/client.py` - Add `client.files.upload()` method
- `ui/backend/app/websocket/push.py` - Add `upload_file()` function
- `foundry-module/.../handlers/index.ts` - Register new `upload_file` message type

## Data Models

```python
# src/scenes/models.py

from pydantic import BaseModel
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime

class GridDetectionResult(BaseModel):
    """Result from detect_gridlines()"""
    has_grid: bool
    grid_size: Optional[int] = None  # Side length in pixels (e.g., 100 = 100x100px squares)
    confidence: float  # 0.0-1.0

class SceneCreationResult(BaseModel):
    """Result from create_scene_from_map()"""
    # Core identifiers (matches ActorCreationResult pattern)
    uuid: str                          # "Scene.abc123"
    name: str                          # "Castle" (derived from filename)
    output_dir: Path                   # output/runs/.../scenes/castle/
    timestamp: str                     # "20241102_143022"

    # Scene-specific details
    foundry_image_path: str            # "worlds/myworld/uploaded-maps/castle.webp"
    grid_size: Optional[int] = None    # Side length in pixels, None if gridless
    wall_count: int                    # 874
    image_dimensions: Dict[str, int]   # {"width": 1380, "height": 940}

    # Debug artifacts (paths to intermediate files)
    debug_artifacts: Dict[str, Path]   # {grayscale, redlined, overlay, walls_json, ...}
```

## Grid Detection Modules

### detect_gridlines.py - AI-powered grid detection

```python
async def detect_gridlines(image_path: Path) -> GridDetectionResult:
    """
    Analyze battle map image for grid lines using Gemini Vision.

    Returns:
        GridDetectionResult with has_grid, grid_size (side length), confidence

    Prompt strategy:
        1. Ask if visible grid lines exist (yes/no)
        2. If yes, estimate pixels between lines by analyzing spacing
        3. Return confidence based on grid clarity
    """
```

### estimate_scene_size.py - Simple math for gridless maps

```python
def estimate_scene_size(image_path: Path, target_grid_size: int = 100) -> int:
    """
    Calculate reasonable grid size for gridless maps.

    Strategy:
        - Load image dimensions
        - Target ~20-40 grid squares on longest edge (typical battle map)
        - Return grid_size that achieves this

    Example:
        2000px wide image → 2000/25 = 80px grid → ~25 squares across
    """
```

## File Upload Mechanism

### Backend endpoint

```python
# ui/backend/app/routers/foundry.py

@router.post("/files/upload")
async def upload_file(
    file: UploadFile,
    destination: str = "uploaded-maps"  # relative to world folder
):
    """
    Upload file to FoundryVTT via WebSocket.

    1. Read file bytes
    2. Base64 encode
    3. Send via WebSocket to Foundry module
    4. Module saves to worlds/<current-world>/<destination>/<filename>
    5. Return the Foundry-relative path
    """
    return {"path": "worlds/myworld/uploaded-maps/castle.webp"}
```

### Foundry module handler

```typescript
// foundry-module/.../handlers/files.ts

async function handleFileUpload(data: {
    filename: string,
    content: string,      // base64 encoded
    destination: string   // "uploaded-maps"
}): Promise<UploadResult> {
    // 1. Decode base64 to binary
    // 2. Get current world folder path
    // 3. Ensure destination folder exists
    // 4. Write file using FilePicker.upload() or fs
    // 5. Return Foundry-relative path
}
```

**Size consideration:** Base64 adds ~33% overhead. A 5MB image becomes ~6.7MB over WebSocket. Should be fine for typical battle maps.

## Scene Creation

### Backend endpoint (general-purpose)

```python
# ui/backend/app/routers/foundry.py

@router.post("/scene")
async def create_scene(request: SceneCreateRequest):
    """
    Create FoundryVTT scene.

    Supports:
        - Battle maps with walls and grid
        - Art scenes (splash images, chapter headers)
        - Gridless theater-of-mind scenes

    Request body:
        name: str
        background_src: str              # Foundry-relative path
        width: int
        height: int
        grid_size: Optional[int] = None  # None = gridless
        walls: Optional[List[WallData]] = None  # None = no walls
    """
```

### FoundryVTT scene data structure

```python
scene_data = {
    "name": "Castle",
    "background": {
        "src": "worlds/myworld/uploaded-maps/castle.webp"
    },
    "width": 1380,
    "height": 940,
    "grid": {
        "size": 70,           # or null/omit for gridless
        "type": 1             # 1 = square grid
    },
    "walls": [                # Optional - omit for art scenes
        {"c": [x1, y1, x2, y2], "move": 0, "sense": 0, "door": 0, "ds": 0},
        # ... more walls
    ]
}
```

### Example usage

```python
# Battle map with walls
create_scene(name="Castle", background_src="...", grid_size=70, walls=[...])

# Art scene (chapter splash)
create_scene(name="Chapter 1 - Phandalin", background_src="...", grid_size=None, walls=None)

# Gridless encounter
create_scene(name="Tavern Brawl", background_src="...", grid_size=100, walls=None)
```

## Main Orchestration Function

```python
# src/scenes/orchestrate.py

async def create_scene_from_map(
    image_path: Union[str, Path],
    name: Optional[str] = None,  # Derived from filename if not provided
) -> SceneCreationResult:
    """
    Complete pipeline: image → walls → upload → scene.

    Steps:
        1. Derive scene name from filename (if not provided)
        2. Create timestamped output directory
        3. Run wall detection pipeline (redline_walls)
        4. Detect grid lines (detect_gridlines)
           - If no grid: use estimate_scene_size() as fallback
        5. Upload image to Foundry (POST /files/upload)
        6. Create scene with walls (POST /scene)
        7. Return SceneCreationResult with all details
    """

def create_scene_from_map_sync(
    image_path: Union[str, Path],
    name: Optional[str] = None,
) -> SceneCreationResult:
    """Synchronous wrapper for create_scene_from_map()."""
    return asyncio.run(create_scene_from_map(image_path, name))
```

### Output directory structure

```
output/runs/<timestamp>/scenes/<scene-name>/
├── 01_original.png
├── 02_grayscale.png
├── 03_redlined.png
├── 04_polygonized/
│   ├── polylines.json
│   └── ... (debug images)
├── 05_final_overlay.png
├── 06_foundry_walls.json
└── 07_scene_result.json      # Final SceneCreationResult
```

## Testing Requirements

### Test structure

```
tests/scenes/
├── test_orchestrate.py           # Unit tests (mocked)
├── test_orchestrate_integration.py  # Real API calls
├── test_detect_gridlines.py      # Grid detection tests
├── test_estimate_scene_size.py   # Simple math tests
└── fixtures/
    ├── gridded_map.webp          # Map with visible grid
    └── gridless_map.webp         # Art scene / no grid
```

### Required integration test (round-trip)

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_scene_creation_roundtrip():
    """Create scene in Foundry, fetch it back, verify walls exist."""

    result = await create_scene_from_map("tests/scenes/fixtures/gridded_map.webp")

    assert result.uuid.startswith("Scene.")
    assert result.wall_count > 0

    # Fetch back from Foundry
    scene = await client.scenes.get_scene(result.uuid)

    assert scene["name"] == result.name
    assert len(scene["walls"]) == result.wall_count
    assert scene["background"]["src"] == result.foundry_image_path
```

## Implementation Order

1. **File upload** (backend → module → client)
2. **Scene creation endpoint** (backend → complete SceneManager)
3. **Grid detection modules**
4. **Orchestration pipeline**
5. **Integration tests**

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Input format | Single image path | Simple API, derive name from filename |
| Image storage | Fixed folder `uploaded-maps/` | Predictable, easy to manage |
| Grid detection | AI with simple fallback | Accurate when grids exist, sensible defaults otherwise |
| Walls in scene | Embedded in create call | No separate import step needed |
| Scene endpoint | General-purpose | Supports battle maps, art scenes, gridless encounters |
