# Module Processing Tab Design

## Overview

Add a new "Module" tab to the Tablewrite sidebar that allows users to upload a D&D module PDF and import it into FoundryVTT as a complete package: journals, actors, scenes, and generated artwork.

## Goals

- Expose the existing `full_pipeline.py` functionality through the UI
- Simple toggle options for what to extract
- Stage-based progress feedback
- Detailed results with clickable links to created items
- All outputs organized into folders by module name

## UI Design

### Tab Structure

New "Module" tab alongside existing Chat and Battle Map tabs.

### Form Section

| Element | Description |
|---------|-------------|
| File Upload | Drag-and-drop or click to select PDF (same pattern as Battle Map tab) |
| Module Name | Text input, auto-populated from PDF filename, editable. Used for folder names. |
| Options | Four checkboxes, all checked by default |
| Process Button | "Import Module" (disabled until PDF selected) |

**Options (checkboxes):**
- Extract Journal (module text → journal pages)
- Extract Actors (stat blocks → NPC actors)
- Extract Battle Maps (maps → playable Scenes with walls)
- Generate Scene Artwork (AI images → gallery Journal)

### Progress Section

Shown during processing:
- Stage indicator: "Splitting PDF..." → "Converting to XML..." → "Extracting Actors..." → "Creating Scenes..." → "Uploading to Foundry..."
- Cancel button to abort

### Results Section

Shown after completion:
- Summary line: "Import complete" or "Import failed at: [stage]"
- Expandable sections for each type:
  - **Journal** (1) - clickable item
  - **Actors** (24) - expandable list of clickable items
  - **Scenes** (8) - expandable list of clickable items
  - **Scene Artwork** (1) - clickable gallery journal
- All items use `@UUID[...]` pattern for click-to-open

## Foundry Organization

Each sidebar tab gets its own folder with the module name:

```
Actors Tab:
  📁 Lost Mine of Phandelver/
     - Goblin
     - Bugbear
     - Nezznar the Black Spider

Scenes Tab:
  📁 Lost Mine of Phandelver/
     - Cragmaw Hideout
     - Wave Echo Cave

Journal Tab:
  📁 Lost Mine of Phandelver/
     - Lost Mine of Phandelver (main journal)
     - Scene Artwork Gallery
```

## Backend API

### Endpoint

`POST /api/modules/process`

### Request

Multipart form-data with PDF file and JSON options:

```python
{
  "module_name": "Lost Mine of Phandelver",
  "options": {
    "extract_journal": true,
    "extract_actors": true,
    "extract_battle_maps": true,
    "generate_scene_artwork": true
  }
}
```

### Response

```python
{
  "success": true,
  "error": null,  # or {"stage": "extract_actors", "message": "..."}
  "folders": {
    "actors": "Folder.abc123",
    "scenes": "Folder.def456",
    "journals": "Folder.ghi789"
  },
  "created": {
    "journal": {
      "uuid": "JournalEntry.xyz",
      "name": "Lost Mine of Phandelver",
      "page_count": 12
    },
    "actors": [
      {"uuid": "Actor.a1", "name": "Goblin"},
      {"uuid": "Actor.a2", "name": "Bugbear"}
    ],
    "scenes": [
      {"uuid": "Scene.s1", "name": "Cragmaw Hideout", "wall_count": 45}
    ],
    "artwork_journal": {
      "uuid": "JournalEntry.art",
      "name": "Scene Artwork Gallery",
      "image_count": 8
    }
  }
}
```

### Pipeline Stages

1. Split PDF into chapters
2. Convert chapters to XML
3. Extract actors from stat blocks (if enabled)
4. Extract battle maps as Scenes (if enabled)
5. Generate scene artwork gallery (if enabled)
6. Upload journal to Foundry (if enabled)

### Error Handling

Stop on first error. Return partial results with error details:

```python
{
  "success": false,
  "error": {
    "stage": "extract_actors",
    "message": "Failed to parse stat block for 'Venomfang'"
  },
  "created": {
    "journal": {"uuid": "...", "name": "...", "page_count": 12},
    "actors": [...]  # actors created before failure
  }
}
```

## Implementation

### Files to Create

| File | Purpose |
|------|---------|
| `foundry-module/tablewrite-assistant/src/ui/ModuleUpload.ts` | New UI component |
| `foundry-module/tablewrite-assistant/src/handlers/folder.ts` | Folder create/find handler |
| `ui/backend/app/routers/modules.py` | New API router |

### Files to Modify

| File | Changes |
|------|---------|
| `foundry-module/tablewrite-assistant/src/ui/TablewriteTab.ts` | Add third tab, wire up switching |
| `foundry-module/tablewrite-assistant/styles/module.css` | Styles for new tab, expandable results |
| `ui/backend/app/main.py` | Register modules router |

### Key Dependencies

- `scripts/full_pipeline.py` - Existing pipeline orchestration
- `src/pdf_processing/split_pdf.py` - PDF splitting
- `src/pdf_processing/pdf_to_xml.py` - XML conversion
- `src/actors/process_actors.py` - Actor extraction
- `src/pdf_processing/image_asset_processing/extract_map_assets.py` - Map extraction
- `scripts/generate_scene_art.py` - Scene artwork generation

### Estimated Scope

- ~300 lines TypeScript (UI component + tab integration)
- ~150 lines Python (new router, wrapping existing pipeline)
- ~50 lines TypeScript (folder handler)

## Out of Scope

- Batch actor creation from single prompt (separate feature)
- Progress streaming via WebSocket (stage-based polling sufficient for v1)
- Resume/retry failed imports (user re-uploads and unchecks completed stages)
