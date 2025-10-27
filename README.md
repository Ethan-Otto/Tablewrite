# D&D Module Converter

Utilities for turning official Dungeons & Dragons PDFs into structured assets that can be post-processed into FoundryVTT content. The current pipeline extracts chapter PDFs, feeds them through Gemini for XML generation, and renders quick HTML previews for review.

## Layout
- `src/pdf_processing/` – PDF processing scripts:
  - `split_pdf.py` – slices `data/pdfs/Lost_Mine_of_Phandelver.pdf` into chapter PDFs under `pdf_sections/`
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
- `src/foundry/` – FoundryVTT integration:
  - `client.py` – REST API client base class
  - `journals.py` – `JournalManager` class for journal CRUD operations
  - `upload_to_foundry.py` – batch upload script for journals
  - `export_from_foundry.py` – export journals from FoundryVTT to HTML/JSON
- `scripts/full_pipeline.py` – complete pipeline: split → XML generation → upload → export
- `scripts/generate_scene_art.py` – scene artwork generation orchestration script
- `src/logging_config.py` – centralized logging configuration
- `xml_examples/` – reference markup while refining the converters
- `pdf_sections/` – cache of manually curated chapter PDFs used as input for the XML step

## Setup
1. Install uv if not already installed: `curl -LsSf https://astral.sh/uv/install.sh | sh` (or `pip install uv`)
2. Create virtual environment and install dependencies: `uv venv && source .venv/bin/activate && uv pip sync`
3. Add a `.env` file at the project root with `GeminiImageAPI=<your key>` so the XML step can reach Gemini 2.5.
4. Drop source PDFs under `data/pdfs/`; the default workflow expects `Lost_Mine_of_Phandelver.pdf`.

## Workflow

**Full Pipeline (recommended):**
```bash
# Complete workflow: split → XML → upload → export
uv run python scripts/full_pipeline.py --journal-name "Lost Mine of Phandelver"

# Skip steps as needed
uv run python scripts/full_pipeline.py --skip-split --skip-xml  # Only upload + export
uv run python scripts/full_pipeline.py --skip-export             # Skip final export
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

## FoundryVTT Integration

The project includes optional integration for uploading generated HTML content directly to FoundryVTT as journal entries.

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

- **Create or Replace**: Automatically searches for existing journals by name and replaces them (no duplicates)
- **Export Support**: Download journals from FoundryVTT as HTML or JSON
- **UUID-based Operations**: Proper UUID handling for all journal operations
- **Pages Structure**: Compatible with FoundryVTT v10+ pages architecture
- **Dual Environment Support**: Works with both local FoundryVTT and The Forge

### Architecture

The integration uses the ThreeHats REST API module with a relay server:
- Script → HTTP → Relay Server → WebSocket → FoundryVTT Module → FoundryVTT

**JournalManager Pattern:**
- `src/foundry/journals.py` - `JournalManager` class handles all journal CRUD operations
- `src/foundry/client.py` - Base `FoundryClient` delegates to specialized managers

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

The project includes a comprehensive pytest test suite that mirrors the `src/` directory structure:

```
tests/
├── conftest.py              # Shared fixtures and configuration
├── test_main.py             # End-to-end pipeline tests (PDF → XML → HTML)
├── pdf_processing/          # Tests for PDF processing scripts
│   ├── test_split_pdf.py   # PDF splitting tests
│   ├── test_pdf_to_xml.py  # XML generation tests
│   ├── test_get_toc.py     # TOC extraction tests
│   └── test_xml_to_html.py # HTML conversion tests
├── scene_extraction/        # Tests for scene extraction and artwork
│   ├── test_extract_context.py    # Context extraction tests
│   ├── test_identify_scenes.py    # Scene identification tests
│   ├── test_generate_artwork.py   # Image generation tests
│   ├── test_create_gallery.py     # Gallery HTML generation tests
│   └── test_real_api.py            # Real API integration tests (Gemini & Imagen)
└── foundry/                 # Tests for FoundryVTT integration
    ├── test_client.py       # FoundryClient API tests
    ├── test_upload_script.py # Upload script tests
    └── test_xml_to_journal_html.py # XML to journal converter tests
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
✅ **Full Pipeline**: Complete workflow from PDF → XML → FoundryVTT → HTML export
✅ **FoundryVTT Integration**: Upload, export, create/replace journals with UUID-based operations
✅ **Scene Artwork Generation**: AI-powered scene extraction and image generation with Gemini Imagen
✅ **Bug Fixes**: Mixed XML content handling, improved heading hierarchy detection

### Recent Updates
- **Scene Artwork Generation** (`scripts/generate_scene_art.py`): AI-powered scene extraction, image generation with Gemini Imagen, and HTML gallery creation with collapsible prompts
- **Location-Aware Context**: Each scene tagged with location type (underground/outdoor/interior) for accurate image generation
- **Parallel Image Processing**: ThreadPoolExecutor with 5 workers for fast concurrent generation
- **Full Pipeline Script** (`scripts/full_pipeline.py`): Orchestrates all 4 stages with skip flags
- **Journal Export**: Download journals from FoundryVTT as HTML or JSON
- **JournalManager Refactor**: Specialized manager class for journal operations
- **XML Mixed Content Fix**: Properly handles bare text + child elements in definitions
- **Improved Prompts**: Better heading hierarchy detection (context over font size)

### Future Work
- Normalize XML schema for consistent journal structure
- Attach media assets (images, maps) to journal entries
- Build complete FoundryVTT module manifest exporter
- Add folder organization for journal entries
