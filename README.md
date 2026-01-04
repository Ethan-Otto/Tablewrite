# D&D Module Converter

Convert official D&D PDFs into FoundryVTT content. Uses Google Gemini AI to extract chapters, stat blocks, NPCs, maps, and scenes into structured data, then uploads complete journal entries, actors, and scenes to FoundryVTT.

## Features

- **PDF to Journal** - Extract chapter text, formatting, tables, and boxed text into FoundryVTT journal entries
- **Actor Extraction** - Parse stat blocks into complete FoundryVTT actors with attacks, spells, and abilities
- **Map Extraction** - Automatically detect and extract battle maps from PDF pages
- **Wall Detection** - AI-powered wall detection for battle maps, exports to FoundryVTT scene format
- **Scene Creation** - Create FoundryVTT scenes with walls and grid detection
- **Scene Artwork** - Generate AI artwork for locations described in the module
- **Chat Interface** - Natural language actor creation via Tablewrite module in FoundryVTT

## Quick Start

### 1. Install Dependencies

```bash
# Install uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv sync
```

### 2. Configure Environment

Create a `.env` file in the project root:

```bash
# Required: Gemini API key
GeminiImageAPI=your_gemini_api_key

# Required for FoundryVTT integration
FOUNDRY_URL=http://localhost:30000
```

### 3. Install FoundryVTT Module

Copy `foundry-module/tablewrite-assistant/` to your FoundryVTT `Data/modules/` directory, then enable "Tablewrite Assistant" in your world.

### 4. Start the Backend

```bash
cd ui/backend
uv run uvicorn app.main:app --reload --port 8000
```

### 5. Run the Pipeline

```bash
# Place your PDF in data/pdfs/, then run:
uv run python scripts/full_pipeline.py --journal-name "Your Module Name"
```

## Example Output

### Map Extraction
Battle maps are automatically detected and extracted from PDF pages:

![Extracted Map](docs/screenshots/map-extraction/page_004_cragmaw_hideout.png)

### Wall Detection
AI detects walls in battle maps and exports them for FoundryVTT scenes:

| Original | AI Wall Detection |
|----------|-------------------|
| ![Original](docs/screenshots/wall-detection/01_original.png) | ![Walls](docs/screenshots/wall-detection/05_final_overlay.png) |

### Scene Artwork
AI-generated artwork for locations in the module:

![Scene Artwork](docs/screenshots/scene-artwork/scene_001.png)

## Usage

### Full Pipeline

```bash
# Complete workflow
uv run python scripts/full_pipeline.py --journal-name "Lost Mine of Phandelver"

# Skip steps as needed
uv run python scripts/full_pipeline.py --skip-split --skip-xml   # Reuse existing XML
uv run python scripts/full_pipeline.py --skip-actors             # Skip actor extraction
```

### Individual Steps

```bash
# Split PDF into chapters
uv run python src/pdf_processing/split_pdf.py

# Generate XML from chapters
uv run python src/pdf_processing/pdf_to_xml.py

# Extract maps from PDF
uv run python src/pdf_processing/image_asset_processing/extract_map_assets.py --pdf data/pdfs/module.pdf

# Generate scene artwork
uv run python scripts/generate_scene_art.py --run-dir output/runs/latest

# Upload to FoundryVTT
uv run python src/foundry/upload_journal_to_foundry.py
```

### Python API

```python
from api import create_actor, extract_maps, process_pdf_to_journal, create_scene

# Create actor from natural language description
result = create_actor("A cunning kobold scout with a poisoned dagger", challenge_rating=0.5)
print(f"Created: {result.name} - {result.foundry_uuid}")

# Extract maps from PDF
maps = extract_maps("data/pdfs/module.pdf", chapter="Chapter 1")
print(f"Extracted {maps.total_maps} maps")

# Create scene from battle map with automatic wall detection
scene = create_scene("maps/castle.webp")
print(f"Created scene with {scene.wall_count} walls, grid size {scene.grid_size}px")
```

### Chat Interface

The Tablewrite module provides a chat interface directly in FoundryVTT:

```
You: Create a goblin shaman with CR 1
Assistant: Created "Goblin Shaman" (Actor.abc123) with 2 spells and 3 abilities.

You: Generate an image of a dark forest clearing
Assistant: [Generated image displayed in chat]
```

## Project Structure

```
src/
├── api.py                    # Public API for external tools
├── pdf_processing/           # PDF splitting, XML generation, map extraction
├── actors/                   # Actor/NPC extraction and creation
├── scenes/                   # Scene creation with wall/grid detection
├── foundry/                  # FoundryVTT client and managers
├── foundry_converters/       # Data conversion (actors, journals, scenes)
├── models/                   # Core data models (XMLDocument, Journal)
└── wall_detection/           # AI wall detection for battle maps

ui/backend/                   # FastAPI backend for Foundry WebSocket
foundry-module/               # FoundryVTT Tablewrite Assistant module
scripts/                      # Pipeline orchestration scripts
output/runs/                  # Timestamped output directories
```

## Configuration

Full `.env` options:

```bash
# Gemini API (required)
GeminiImageAPI=your_api_key

# FoundryVTT Connection (required for upload)
FOUNDRY_URL=http://localhost:30000

# Optional: The Forge hosting
FOUNDRY_FORGE_URL=https://your-game.forge-vtt.com
FOUNDRY_FORGE_API_KEY=your_forge_key
FOUNDRY_TARGET=local  # or "forge"

# Optional: Scene artwork settings
ENABLE_SCENE_ARTWORK=true
IMAGE_STYLE_PROMPT=fantasy illustration, D&D 5e art style
```

## Architecture

```
PDF → Gemini AI → XML → FoundryVTT Entities
                    ↓
    Backend (FastAPI) ←WebSocket→ Foundry Module → FoundryVTT
```

The system uses two integration paths:
1. **Batch Pipeline** - Process entire PDFs via command line scripts
2. **Real-time Chat** - Create individual entities via Tablewrite chat interface

Both paths communicate with FoundryVTT through the backend's WebSocket connection to the Tablewrite module.

## Testing

```bash
# Smoke tests (fast, <2 min)
uv run pytest

# Full test suite (~450 tests, requires backend + Foundry running)
uv run pytest --full

# Unit tests only (no API calls)
uv run pytest -m "not integration and not slow"
```

## Troubleshooting

**Backend won't start**
```bash
# Check if port 8000 is in use
lsof -i :8000
# Kill existing process if needed
lsof -ti :8000 | xargs kill -9
```

**Foundry module not connecting**
1. Ensure backend is running on port 8000
2. Check Foundry console (F12) for WebSocket errors
3. Verify module is enabled in your world

**Map extraction fails**
- Ensure PDF has embedded images (not scanned/flattened)
- Check `output/runs/<timestamp>/map_assets/temp/` for debug images

**Actor creation times out**
- Actor creation takes 10-30 seconds (Gemini API calls)
- Check backend logs for detailed error messages

## Requirements

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) package manager
- Google Gemini API key
- FoundryVTT v10+ with Tablewrite Assistant module

## License

MIT
