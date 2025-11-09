# D&D Module Converter

Utilities for turning official Dungeons & Dragons PDFs into structured assets that can be post-processed into FoundryVTT content. The pipeline uses Google's Gemini 2.5 Pro for AI-powered document analysis, extracting chapters, stat blocks, NPCs, maps, and scenes into structured XML, then uploading complete journal entries and actors to FoundryVTT.

## Public API

The project provides a clean public API for external applications (chat UI, CLI tools) located in `src/api.py`:

```python
from api import create_actor, extract_maps, process_pdf_to_journal

# Create D&D actor from natural language description
result = create_actor(description="A cunning kobold scout with a poisoned dagger", challenge_rating=0.5)
print(f"Created: {result.name} - {result.foundry_uuid}")

# Extract maps from PDF
maps_result = extract_maps(pdf_path="data/pdfs/module.pdf", chapter="Chapter 1")
print(f"Extracted {maps_result.total_maps} maps")

# Process PDF to FoundryVTT journal
journal_result = process_pdf_to_journal(pdf_path="data/pdfs/module.pdf", journal_name="Lost Mine of Phandelver")
print(f"Created journal: {journal_result.journal_uuid}")
```

All functions raise `APIError` on failure and use environment variables from `.env` for configuration. See `tests/api/` for usage examples.

## Layout
- `src/pdf_processing/` – PDF processing scripts:
  - `split_pdf.py` – slices `data/pdfs/Lost_Mine_of_Phandelver.pdf` into chapter PDFs under `data/pdf_sections/`
  - `pdf_to_xml.py` – uploads each chapter page to Gemini (`GEMINI_MODEL_NAME`) and writes XML plus logs to `output/runs/<timestamp>/`
  - `get_toc.py` – extracts table of contents from PDF
  - `xml_to_html.py` – converts XML to browsable HTML (local previews and FoundryVTT uploads)
  - `valid_xml_tags.py` – XML tag validation utilities
  - `image_asset_processing/` – AI-powered map extraction from PDFs:
    - `models.py` – Pydantic models for MapDetectionResult and MapMetadata
    - `detect_maps.py` – Gemini Vision map detection and classification
    - `extract_maps.py` – PyMuPDF extraction with AI classification
    - `segment_maps.py` – Gemini Imagen segmentation with red perimeter technique
    - `preprocess_image.py` – Red pixel removal preprocessing
    - `extract_map_assets.py` – Main orchestration script
- `src/scene_extraction/` – AI-powered scene extraction and artwork generation:
  - `models.py` – Pydantic models for Scene and ChapterContext
  - `extract_context.py` – chapter environmental context extraction using Gemini
  - `identify_scenes.py` – scene location identification using Gemini
  - `generate_artwork.py` – AI image generation using Gemini Imagen
  - `create_gallery.py` – HTML gallery generation with collapsible prompts
- `src/actors/` – Actor/NPC extraction and creation:
  - `models.py` – Pydantic models (StatBlock, NPC)
  - `parse_stat_blocks.py` – parse stat blocks from XML using Gemini
  - `extract_npcs.py` – extract named NPCs from XML
  - `orchestrate.py` – complete actor creation pipeline from natural language
  - `process_actors.py` – batch processing for PDF workflows
- `src/foundry/` – FoundryVTT integration:
  - `client.py` – REST API client base class
  - `journals.py` – `JournalManager` class for journal CRUD operations
  - `actors/` – Actor management:
    - `models.py` – ParsedActorData and FoundryVTT-specific models
    - `spell_cache.py` – SpellCache for resolving spell UUIDs
    - `converter.py` – convert parsed actors to FoundryVTT JSON
    - `manager.py` – ActorManager for create/update/delete operations
  - `upload_to_foundry.py` – batch upload script for journals
  - `export_from_foundry.py` – export journals from FoundryVTT to HTML/JSON
- `src/models/` – Core data models:
  - `xml_document.py` – XMLDocument model (immutable, page-based XML representation)
  - `journal.py` – Journal model (mutable, semantic hierarchy with image registry)
- `scripts/full_pipeline.py` – complete pipeline: split → XML generation → actors → upload → export
- `scripts/generate_scene_art.py` – scene artwork generation orchestration script
- `src/logging_config.py` – centralized logging configuration
- `xml_examples/` – reference markup while refining the converters
- `data/pdf_sections/` – cache of manually curated chapter PDFs used as input for the XML step

## Setup
1. Install uv if not already installed: `curl -LsSf https://astral.sh/uv/install.sh | sh` (or `pip install uv`)
2. Create virtual environment and install dependencies: `uv venv && source .venv/bin/activate && uv pip sync`
3. Add a `.env` file at the project root with `GeminiImageAPI=<your key>` so the XML step can reach Gemini 2.5.
4. Drop source PDFs under `data/pdfs/`; the default workflow expects `Lost_Mine_of_Phandelver.pdf`.

## Workflow

**Full Pipeline (recommended):**
```bash
# Complete workflow: split → XML → actors → upload → export
uv run python scripts/full_pipeline.py --journal-name "Lost Mine of Phandelver"

# Skip steps as needed
uv run python scripts/full_pipeline.py --skip-split --skip-xml  # Only actors + upload + export
uv run python scripts/full_pipeline.py --skip-actors             # Skip actor/NPC extraction
uv run python scripts/full_pipeline.py --actors-only --run-dir output/runs/20241023_143022  # Process actors only
```

**Individual Steps:**
```bash
1. uv run src/pdf_processing/split_pdf.py           # Split PDF into chapters
2. uv run src/pdf_processing/pdf_to_xml.py          # Generate XML via Gemini
3. uv run src/foundry/upload_to_foundry.py          # Upload to FoundryVTT
4. uv run src/foundry/export_from_foundry.py "Lost Mine of Phandelver"  # Export HTML
```

Or activate the virtual environment first (`source .venv/bin/activate`) and use `python ...` directly.

Each run preserves logs, raw model responses, and word-count checks beneath `output/runs/<timestamp>/`; avoid editing outputs in place so history stays intact.

## Web UI

The project includes a chat-based web UI for interacting with the D&D Module Assistant. The UI features a wax seal aesthetic with parchment textures and provides a conversational interface for working with D&D module content.

### Architecture

- **Frontend**: React 19 + TypeScript + Vite with Tailwind CSS
- **Backend**: FastAPI (Python) with Google Gemini API
- **Design**: Wax seal aesthetic with medieval typography and parchment backgrounds

### Setup & Running

**1. Backend Setup:**
```bash
cd ui/backend

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
uv pip install -r requirements.txt

# Create .env file with your Gemini API key
echo "GEMINI_API_KEY=<your_api_key>" > .env
echo "CORS_ORIGINS=http://localhost:5173" >> .env

# Start the backend server
uvicorn app.main:app --reload --port 8000
```

Backend runs on http://localhost:8000 (Swagger docs at http://localhost:8000/docs)

**2. Frontend Setup:**
```bash
cd ui/frontend

# Install dependencies
npm install

# Start the development server
npm run dev
```

Frontend runs on http://localhost:5173

**3. Access the UI:**
Open your browser to http://localhost:5173

### Features

- **Chat Interface**: Conversational UI for working with D&D module content
- **Conversation History**: Full chat history maintained across messages
- **Markdown Support**: Rich text rendering for formatted responses
- **Wax Seal Aesthetic**: Medieval-themed design with parchment textures
- **Available Commands**:
  - `/generate-scene [description]` - Generate a new scene
  - `/list_scenes [chapter]` - List scenes in a chapter
  - `/list_actors` - List all actors/NPCs
  - `/help` - Show help

### Development

The UI uses hot module replacement for fast development:
- Frontend changes reload automatically via Vite HMR
- Backend changes reload automatically with `--reload` flag
- Hard refresh (Cmd+Shift+R or Ctrl+Shift+R) to clear browser cache if needed

See `ui/CLAUDE.md` for detailed architecture documentation, component breakdown, and development guidelines.

## Actor/NPC Extraction & Creation

The project automatically extracts and creates D&D 5e actors and NPCs from module PDFs or natural language descriptions.

### From Natural Language (API)

```python
from api import create_actor

# Create actor from description
result = create_actor(
    description="A fierce red dragon wyrmling with fire breath",
    challenge_rating=2.0
)
print(f"Created: {result.name} - {result.foundry_uuid}")
```

### From PDF (Pipeline)

```bash
# Full pipeline with actors
uv run python scripts/full_pipeline.py --journal-name "Lost Mine of Phandelver"

# Process actors only from existing run
uv run python scripts/full_pipeline.py --actors-only --run-dir output/runs/20241023_143022
```

### Processing Pipeline

```
PDF → XML (with <stat_block> tags)
    ↓
parse_stat_blocks.py (Gemini → StatBlock models)
    ↓
extract_npcs.py (Gemini → NPC models)
    ↓
ActorManager (creates FoundryVTT Actors)
```

### Actor Types

1. **Creature Actors**: Full stat blocks (AC, HP, abilities, actions, spells) - reuses compendium actors if name matches
2. **NPC Actors**: Named characters with bio (description, plot role, location) - links to creature stat block via @UUID

### Key Features

- **Two-Stage Parsing**: Basic extraction (StatBlock) → detailed parsing (ParsedActorData with attacks, traits, spells)
- **Spell Resolution**: SpellCache resolves spell names to compendium UUIDs for accurate spell data
- **FoundryVTT v10+ Activities**: Proper activity structure for attacks, saves, and damage
- **Batch Creation**: Process multiple actors in parallel with shared resources
- **Output Artifacts**: Saves raw text, JSON models, and FoundryVTT JSON for debugging

See `src/actors/` and `src/foundry/actors/` for implementation details.

## FoundryVTT Integration

The project includes full integration for uploading journal entries and actors directly to FoundryVTT via REST API.

### Setup

1. **Install FoundryVTT REST API Module:**
   - In FoundryVTT, go to Add-on Modules > Install Module
   - Paste manifest URL: `https://github.com/ThreeHats/foundryvtt-rest-api/releases/latest/download/module.json`
   - Enable the module in your world
   - Generate an API key in Module Settings

2. **Configure Environment:**
   Add to your `.env` file:
   ```bash
   FOUNDRY_RELAY_URL=https://foundryvtt-rest-api-relay.fly.dev
   FOUNDRY_LOCAL_URL=http://localhost:30000
   FOUNDRY_LOCAL_API_KEY=<your_api_key>
   FOUNDRY_LOCAL_CLIENT_ID=<your_client_id>
   FOUNDRY_AUTO_UPLOAD=false
   FOUNDRY_TARGET=local
   ```

3. **Upload and Export:**
   ```bash
   # Full pipeline (recommended)
   uv run python scripts/full_pipeline.py --journal-name "Lost Mine of Phandelver"

   # Manual upload of latest run
   uv run src/foundry/upload_to_foundry.py

   # Export journal from FoundryVTT
   uv run src/foundry/export_from_foundry.py "Lost Mine of Phandelver" --format html
   ```

### Features

- **Journals**: Create/replace journals with proper pages structure (FoundryVTT v10+)
- **Actors**: Create/update creatures and NPCs with stat blocks, spells, and traits
- **Export Support**: Download journals from FoundryVTT as HTML or JSON
- **UUID-based Operations**: Proper UUID handling for all operations
- **Self-Hosted Relay**: Uses local relay server (`relay-server/`) for development - see `docs/RELAY_SERVER_SETUP.md`
- **Dual Environment Support**: Works with both local FoundryVTT and The Forge

### Architecture

The integration uses the ThreeHats REST API module with a relay server:
- Script → HTTP → Relay Server → WebSocket → FoundryVTT Module → FoundryVTT

**JournalManager Pattern:**
- `src/foundry/journals.py` - `JournalManager` class handles all journal CRUD operations
- `src/foundry/client.py` - Base `FoundryClient` delegates to specialized managers

## Core Data Models: XMLDocument & Journal

The project uses two core Pydantic models representing different pipeline stages:

**XMLDocument** (`src/models/xml_document.py`):
- **Immutable** representation of raw XML output from Gemini
- **Page-based structure**: `XMLDocument → Page[] → Content[]`
- Direct parsing from XML strings/files
- Round-trip serialization to XML

**Journal** (`src/models/journal.py`):
- **Mutable** working representation with semantic hierarchy
- **Chapter-based structure**: `Journal → Chapter[] → Section[] → Subsection[]`
- Transforms flat page structure into semantic hierarchy
- Manages image registry for all image references
- Reassigns content IDs from `page_X_content_Y` to `chapter_A_section_B_content_C`
- Exports to HTML, Markdown, or FoundryVTT-ready HTML

**Data Flow:**
```
PDF → XML (Gemini) → XMLDocument.from_xml() → Journal.from_xml_document() → journal.to_foundry_html() → FoundryVTT
```

**Usage Example:**
```python
from models.xml_document import parse_xml_file
from models.journal import Journal, ImageMetadata

# Parse XML to XMLDocument
xml_doc = parse_xml_file("output/runs/20241023_143022/documents/Chapter_1.xml")

# Convert to Journal with semantic hierarchy
journal = Journal.from_xml_document(xml_doc)

# Add custom scene artwork
journal.add_image(key="scene_goblin_ambush", metadata=ImageMetadata(...))
journal.reposition_image(key="scene_goblin_ambush", new_content_id="chapter_0_section_2_content_0")

# Export to FoundryVTT HTML
html = journal.to_foundry_html(image_mapping={"scene_goblin_ambush": "https://..."})
```

See `src/models/` for full API documentation.

## Scene Artwork Generation

The project includes AI-powered scene extraction and artwork generation for creating visual galleries of D&D module locations using Gemini AI.

### Features

- **Automatic Scene Identification**: Extracts physical locations from chapter XML while filtering out NPCs, monsters, and plot details
- **Context-Aware Generation**: Each scene tagged with location type (underground, outdoor, interior) for accurate image generation
- **Parallel Processing**: Generates multiple images concurrently for fast processing (5 workers)
- **Prompt Transparency**: HTML gallery includes collapsible boxes showing the exact Gemini prompt used for each image
- **No Text/Characters**: Automatically enforces constraints to exclude text and specific named creatures from images
- **Gemini Imagen**: Uses `imagen-3.0-generate-002` model for high-quality fantasy artwork

### Usage

```bash
# Generate artwork for all chapters in a run
uv run python scripts/generate_scene_art.py --run-dir output/runs/20241023_123456

# Generate artwork for single chapter
uv run python scripts/generate_scene_art.py --xml-file output/runs/latest/documents/02_Part_1_Goblin_Arrows.xml

# Custom style prompt
uv run python scripts/generate_scene_art.py --xml-file chapter.xml --style "dark fantasy, grimdark, oil painting"

# Custom output directory
uv run python scripts/generate_scene_art.py --xml-file chapter.xml --output-dir custom_output/
```

### Output

Scene artwork is saved to `output/runs/<timestamp>/scene_artwork/`:
- `images/` - Generated PNG images (~1-2 MB each)
- `scene_gallery.html` - Interactive HTML gallery with collapsible prompts

**Gallery Features:**
- Scene hierarchy breadcrumbs (Chapter → Location → Area)
- High-resolution AI-generated artwork
- Physical environment descriptions
- Collapsible "View Full Gemini Prompt" boxes for each image

### Performance

- **Processing Speed**: ~2-3 seconds per image with parallel generation
- **Typical Chapter**: 10-17 scenes in ~20-30 seconds
- **Model**: `imagen-3.0-generate-002` (no rate limit issues)

### Architecture

**Modules:**
- `src/scene_extraction/models.py` - Pydantic models (Scene, ChapterContext)
- `src/scene_extraction/extract_context.py` - Chapter environmental context extraction
- `src/scene_extraction/identify_scenes.py` - Scene location identification
- `src/scene_extraction/generate_artwork.py` - Gemini Imagen image generation
- `src/scene_extraction/create_gallery.py` - HTML gallery creation
- `scripts/generate_scene_art.py` - Main orchestration script

**Processing Flow:**
1. Extract chapter context (environment, lighting, terrain)
2. Identify physical locations (rooms, areas, outdoor locations)
3. Generate artwork in parallel (5 concurrent workers)
4. Create HTML gallery with collapsible prompts

**Scene Model:**
```python
class Scene(BaseModel):
    section_path: str      # "Chapter 2 → The Cragmaw Hideout → Area 1"
    name: str             # "Twin Pools Cave"
    description: str      # Physical environment only
    location_type: str    # "underground", "outdoor", "interior", "underwater"
```

## Map Asset Extraction

The project includes AI-powered map extraction for automatically extracting battle maps and navigation maps from D&D module PDFs using Gemini AI.

### Features

- **Automatic Map Detection**: Scans all pages to identify functional gameplay maps (navigation and battle maps)
- **Hybrid Extraction**: Combines fast PyMuPDF extraction with AI-powered Imagen segmentation for baked-in maps
- **Smart Filtering**: Distinguishes functional maps from decorative elements (maps as props in artwork, scene illustrations)
- **Word Count Validation**: OCR-based quality check rejects extractions with excessive text (>100 words, 5 retries)
- **Fully Parallel Processing**: All pages processed concurrently for maximum speed
- **Debug Files**: Preprocessed and red-perimeter images saved to `temp/` subdirectory for troubleshooting
- **Models**: Uses `gemini-2.0-flash` for detection/classification, `gemini-2.5-flash-image` for segmentation

### Usage

```bash
# Extract all maps from PDF
uv run python src/pdf_processing/image_asset_processing/extract_map_assets.py --pdf data/pdfs/module.pdf

# Specify chapter name for metadata
uv run python src/pdf_processing/image_asset_processing/extract_map_assets.py --pdf data/pdfs/module.pdf --chapter "Chapter 1"

# Custom output directory
uv run python src/pdf_processing/image_asset_processing/extract_map_assets.py --pdf data/pdfs/module.pdf --output custom/output/dir
```

### Output

Map assets are saved to `output/runs/<timestamp>/map_assets/`:
- `page_XXX_map_name.png` - Final extracted maps
- `maps_metadata.json` - JSON metadata with map names, types, page numbers, and extraction method
- `temp/` - Debug files (only created if Imagen segmentation used):
  - `*_preprocessed.png` - Page with existing red pixels removed
  - `*_with_red_perimeter.png` - Imagen-generated image with red border

**Example Metadata:**
```json
{
  "extracted_at": "2025-10-26T19:14:02.722375",
  "total_maps": 6,
  "maps": [
    {
      "name": "Cragmaw Hideout",
      "chapter": "Lost Mine of Phandelver",
      "page_num": 9,
      "type": "navigation_map",
      "source": "segmented"
    }
  ]
}
```

### Performance

- **Detection**: ~2.5 minutes for 60-page PDF (parallel page processing)
- **PyMuPDF Extraction**: ~13-15 seconds per page (with AI classification, run in parallel)
- **Imagen Segmentation**: ~15-20 seconds per page (with 5 retries, run in parallel)
- **Total Time**: ~3-4 minutes for typical module PDF with 10 maps
- **Success Rate**: 85-100% depending on text-to-map ratio in PDF pages

**Example**: Lost Mine of Phandelver (7 maps) extracted in 3:42 with 85.7% success rate

### Architecture

**Modules:**
- `src/pdf_processing/image_asset_processing/models.py` - Pydantic models (MapDetectionResult, MapMetadata)
- `src/pdf_processing/image_asset_processing/detect_maps.py` - Gemini Vision map detection and classification
- `src/pdf_processing/image_asset_processing/extract_maps.py` - PyMuPDF extraction with AI classification
- `src/pdf_processing/image_asset_processing/segment_maps.py` - Gemini Imagen segmentation with red perimeter
- `src/pdf_processing/image_asset_processing/preprocess_image.py` - Red pixel removal preprocessing
- `src/pdf_processing/image_asset_processing/extract_map_assets.py` - Main orchestration script

**Processing Flow:**
1. Detect functional maps on all pages in parallel (filters out decorative elements)
2. Check if page is flattened (single image covering >80% of page)
3. Try PyMuPDF extraction first for embedded images (with AI classification to filter background textures)
4. Fallback to Imagen segmentation for baked-in maps (red perimeter technique)
5. Validate extraction quality using OCR word count (<100 words, 5 retries)
6. Generate JSON metadata with map names, types, page numbers, and source method

**Map Metadata Model:**
```python
class MapMetadata(BaseModel):
    name: str              # "Cragmaw Hideout"
    chapter: Optional[str] # "Lost Mine of Phandelver"
    page_num: int          # 9
    type: str              # "navigation_map" or "battle_map"
    source: str            # "extracted" (PyMuPDF) or "segmented" (Imagen)
```

### Key Features

- **Flattened PDF Detection**: Automatically detects when pages are rasterized as single images and skips PyMuPDF extraction
- **Functional Map Filtering**: Uses detailed prompt to distinguish gameplay maps from decorative elements
- **OCR Quality Validation**: Rejects extractions containing >100 words using pytesseract (prevents capturing text-heavy pages)
- **Red Pixel Preprocessing**: Removes existing red pixels before Imagen processing to avoid confusion with generated borders
- **Resolution Scaling**: Corrects for Gemini's image downscaling (e.g., 3523x4644 → 896x1152) before cropping
- **True Parallel Processing**: Uses `asyncio.to_thread()` for blocking PyMuPDF operations to achieve concurrency
- **Temp Directory Organization**: Debug files automatically stored in `temp/` subdirectory (avoids nested directories)

## Logging
All scripts use Python's standard `logging` module for structured output:
- **DEBUG**: Detailed processing steps (page uploads, file creation)
- **INFO**: Normal workflow progress (chapter/page processing)
- **WARNING**: Non-fatal issues (OCR fallback, retries, word count mismatches)
- **ERROR**: Processing failures

Logs are written to both console and `<run_dir>/pdf_to_xml.log` for the main conversion script.

## Testing

The project includes a comprehensive test suite with 417 tests.

**Quick Start:**

```bash
# Default: Smoke tests only (~6 tests, <2 min)
pytest

# Full test suite (~417 tests, ~35 min)
pytest --full

# Disable auto-escalation on failure
AUTO_ESCALATE=false pytest
```

**Test Organization:**

- **Smoke tests** (`@pytest.mark.smoke`): 6 critical tests covering major features
- **Integration tests** (`@pytest.mark.integration`): Real API calls (Gemini, FoundryVTT)
- **Unit tests** (`@pytest.mark.unit`): Fast, no external dependencies
- **Slow tests** (`@pytest.mark.slow`): Long-running operations

**Auto-escalation:** If smoke tests fail, the full suite runs automatically (disable with `AUTO_ESCALATE=false`)

### Test Structure

The pytest test suite mirrors the `src/` directory structure:

```
tests/
├── conftest.py              # Shared fixtures and configuration
├── test_main.py             # End-to-end pipeline tests (PDF → XML → HTML)
├── api/                     # Tests for public API
│   ├── test_api.py         # Unit tests for api.py
│   └── test_api_integration.py # Integration tests with real Gemini calls
├── pdf_processing/          # Tests for PDF processing scripts
│   ├── test_split_pdf.py   # PDF splitting tests
│   ├── test_pdf_to_xml.py  # XML generation tests
│   └── test_get_toc.py     # TOC extraction tests
├── actors/                  # Tests for actor extraction and creation
│   ├── test_models.py      # StatBlock and NPC model tests
│   ├── test_parse_stat_blocks.py # Stat block parsing tests
│   └── test_orchestrate.py # Actor creation orchestration tests
├── scene_extraction/        # Tests for scene extraction and artwork
│   ├── test_extract_context.py    # Context extraction tests
│   ├── test_identify_scenes.py    # Scene identification tests
│   └── test_generate_artwork.py   # Image generation tests
└── foundry/                 # Tests for FoundryVTT integration
    ├── test_client.py       # FoundryClient API tests
    ├── actors/              # Tests for actor management
    │   ├── test_models.py  # ParsedActorData model tests
    │   ├── test_spell_cache.py # SpellCache tests
    │   └── test_converter.py # Actor converter tests
    └── test_upload_script.py # Upload script tests
```

### Running Tests

```bash
# Run all unit tests (excludes slow API tests)
uv run pytest -m "not integration and not slow"

# Run all tests including integration tests with Gemini API
uv run pytest

# Run tests with verbose output
uv run pytest -v

# Run specific test file
uv run pytest tests/pdf_processing/test_split_pdf.py

# Run tests matching a pattern
uv run pytest -k "test_word_count"
```

### Test Categories

- **Unit tests**: Fast tests that don't require API calls (default)
- **Integration tests**: Tests that make real Gemini API calls (marked with `@pytest.mark.integration` and `@pytest.mark.slow`)
- **PDF tests**: Tests requiring PDF files (marked with `@pytest.mark.requires_pdf`)
- **End-to-end tests**: Full pipeline tests in `test_main.py` that run PDF → XML → HTML conversion with timestamped test runs

### Test Configuration

- Configuration: `pytest.ini`
- Fixtures: `tests/conftest.py`
- Test PDF: `data/pdfs/Lost_Mine_of_Phandelver_test.pdf` (7 pages)
- Full PDF: `data/pdfs/Lost_Mine_of_Phandelver.pdf` (for TOC tests)
- Output: `tests/output/` (persistent, not cleaned automatically)
- Test runs: `tests/output/test_runs/<timestamp>/` (created by end-to-end tests)

## Continuous Integration

GitHub Actions automatically runs the full test suite on all pull requests. See [GitHub Actions Setup Guide](.github/SETUP.md) for configuration details.

**Required**: Add your Gemini API key as a GitHub Secret named `GEMINI_API_KEY` for integration tests to run.

## Validation & Next Steps
- Use `uv run python -m compileall src` after edits to catch syntax errors
- Run `uv run pytest` to verify changes don't break functionality
- GitHub Actions runs all tests automatically on pull requests

### Current Status
✅ **Full Pipeline**: PDF → XML → Actors → Maps → Scenes → FoundryVTT upload → Export
✅ **Public API**: Clean Python API for external applications (`api.py`)
✅ **Actor/NPC Extraction**: Automatic extraction and creation of creatures and NPCs from PDFs
✅ **Actor Creation**: Create D&D 5e actors from natural language descriptions
✅ **XMLDocument & Journal Models**: Immutable and mutable data models for document processing
✅ **FoundryVTT Integration**: Full journal and actor CRUD operations via REST API
✅ **Scene Artwork Generation**: AI-powered scene extraction and image generation
✅ **Map Asset Extraction**: Hybrid PyMuPDF + Imagen segmentation for battle maps
✅ **Web UI**: Chat interface with Gemini integration
✅ **Self-Hosted Relay**: Local relay server for development
✅ **Comprehensive Testing**: 50+ tests with unit and integration coverage

### Recent Updates
- **Public API** (`src/api.py`): Clean API for `create_actor()`, `extract_maps()`, `process_pdf_to_journal()`
- **Actor Creation Orchestration** (`src/actors/orchestrate.py`): Complete pipeline from natural language → FoundryVTT actors
- **Two-Stage Actor Parsing**: Basic StatBlock extraction → detailed ParsedActorData with attacks, traits, spells
- **SpellCache** (`src/foundry/actors/spell_cache.py`): Resolve spell names to compendium UUIDs
- **XMLDocument & Journal Models** (`src/models/`): Immutable page-based and mutable semantic hierarchy models
- **Map Asset Extraction** (`src/pdf_processing/image_asset_processing/`): Hybrid extraction with AI classification
- **Scene Artwork Generation** (`scripts/generate_scene_art.py`): Parallel image generation with Gemini Imagen
- **Self-Hosted Relay Server** (`relay-server/`): Docker-based local development relay
- **Actor Manager** (`src/foundry/actors/manager.py`): Create/update actors with spell integration

### Future Work
- Attach scene artwork and maps to journal entries automatically
- Build complete FoundryVTT module manifest exporter
- Add folder organization for journal entries and actors
- Item extraction and creation (weapons, armor, magic items)
- Spell extraction from module custom spells
