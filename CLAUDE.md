# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a D&D module converter that transforms official Dungeons & Dragons PDFs into structured XML assets for post-processing into FoundryVTT content. The pipeline uses Google's Gemini 2.5 Pro model for AI-powered document analysis and extraction.

## Public API

The project provides a clean public API for external applications (chat UI, CLI tools).

**Location:** `src/api.py`

**Key Functions:**

```python
from api import create_actor, extract_maps, process_pdf_to_journal, APIError

result = create_actor("A kobold scout", challenge_rating=0.5)  # → ActorCreationResult
maps = extract_maps("data/pdfs/module.pdf", chapter="Chapter 1")  # → MapExtractionResult
journal = process_pdf_to_journal("module.pdf", "Module Name")  # → JournalCreationResult
# All raise APIError on failure
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

## Environment Setup

1. **Install uv** (if not already installed):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   # Or: pip install uv
   ```
   - This also provides `uvx` for running tools without installing them (like `npx` for Node)

2. **Create Virtual Environment and Install Dependencies**:
   ```bash
   uv venv
   source .venv/bin/activate  # Unix/macOS
   # .venv\Scripts\activate   # Windows
   uv pip sync
   ```
   - Key packages: `google-generativeai`, `PyMuPDF` (fitz), `pytesseract`, `Pillow`, `python-dotenv`

3. **Required Configuration**: Create `.env` file at project root with:
   ```
   # Gemini API
   GeminiImageAPI=<your_gemini_api_key>

   # FoundryVTT Configuration (optional - for journal upload)
   FOUNDRY_URL=http://localhost:30000
   FOUNDRY_API_KEY=<your_foundry_api_key>
   FOUNDRY_CLIENT_ID=<your_client_id>
   FOUNDRY_AUTO_UPLOAD=false

   # DEPRECATED: Relay server is no longer needed
   # FOUNDRY_RELAY_URL=https://foundryvtt-rest-api-relay.fly.dev
   # FOUNDRY_TARGET=local
   ```

4. **Source PDFs**: Place D&D module PDFs in `data/pdfs/` (default expects `Lost_Mine_of_Phandelver.pdf`)

## Logging

All scripts use Python's standard `logging` module:
- **Log Levels**: DEBUG (detailed steps), INFO (workflow progress), WARNING (non-fatal issues), ERROR (failures)
- **Log Outputs**: Console (all levels), File (`pdf_to_xml.py` writes to `<run_dir>/pdf_to_xml.log`)
- **Configuration**: Centralized in `src/logging_config.py` - use `setup_logging(__name__)` or `get_run_logger(script_name, run_dir)`

## Common Commands

**Full Pipeline (recommended):**
```bash
# Complete workflow: split → XML → upload to FoundryVTT → export HTML
uv run python scripts/full_pipeline.py --journal-name "Lost Mine of Phandelver"

# Skip steps as needed
uv run python scripts/full_pipeline.py --skip-split --skip-xml  # Only upload + export
uv run python scripts/full_pipeline.py --skip-export             # Skip final export
```

**Individual Steps:**
```bash
# 1. Split source PDF into chapter PDFs
uv run src/pdf_processing/split_pdf.py

# 2. Generate XML from chapter PDFs using Gemini
uv run src/pdf_processing/pdf_to_xml.py

# 3. Upload to FoundryVTT
uv run src/foundry/upload_to_foundry.py                          # Upload latest run
uv run src/foundry/upload_to_foundry.py --run-dir output/runs/20241017_123456

# 4. Export from FoundryVTT
uv run src/foundry/export_from_foundry.py "Lost Mine of Phandelver"

# Scene Artwork Generation
uv run python scripts/generate_scene_art.py --run-dir output/runs/20241023_123456

# Map Asset Extraction
uv run python src/pdf_processing/image_asset_processing/extract_map_assets.py --pdf data/pdfs/module.pdf

# Utilities
uv run src/pdf_processing/pdf_to_xml.py --file "01_Introduction.pdf"  # Single chapter
uv run src/pdf_processing/get_toc.py                                   # Extract TOC
uv run python -m compileall src                                        # Syntax check

# Testing
uv run pytest                                    # All tests
uv run pytest -m "not integration and not slow"  # Unit tests only
uv run pytest -v                                 # Verbose output
```

Or activate the virtual environment manually first:
```bash
source .venv/bin/activate  # Unix/macOS
python src/pdf_processing/split_pdf.py
python src/pdf_processing/pdf_to_xml.py
```

## Architecture & Data Flow

### Core Data Models: XMLDocument and Journal

The project uses two core Pydantic models that represent different stages of the document processing pipeline:

**XMLDocument** (`src/models/xml_document.py`):
- Immutable representation of raw XML output from Gemini
- Page-based structure: `XMLDocument → Page[] → Content[]`
- Content types: paragraph, section, subsection, table, list, stat_block, image_ref, etc.
- Direct parsing from XML strings/files
- Can serialize back to XML with round-trip fidelity

**Journal** (`src/models/journal.py`):
- Mutable working representation with semantic hierarchy
- Chapter-based structure: `Journal → Chapter[] → Section[] → Subsection[] → Subsubsection[]`
- Owns the image registry for managing image references and metadata
- Transforms flat page structure into semantic hierarchy
- Reassigns content IDs from `page_X_content_Y` to `chapter_A_section_B_content_C`
- Exports to HTML, Markdown, or FoundryVTT-ready HTML

**Data Flow Pipeline:**
```
PDF → XML (Gemini)
    ↓
XMLDocument.from_xml(xml_string)
    ↓
Journal.from_xml_document(xml_doc)
    ↓
journal.to_foundry_html(image_mapping)
    ↓
FoundryVTT Journal Entry
```

**Quick Usage:**

```python
from models.xml_document import parse_xml_file
from models.journal import Journal, ImageMetadata

xml_doc = parse_xml_file(Path("output/runs/.../Chapter_1.xml"))
journal = Journal.from_xml_document(xml_doc)
journal.add_image(key="scene_art", metadata=ImageMetadata(key="scene_art", source_page=5, type="illustration"))
html = journal.to_foundry_html(image_mapping)
```

**Key Methods:**
- `XMLDocument.from_xml(str)` / `parse_xml_file(Path)` → Parse XML
- `xml_doc.to_journal_pages()` → FoundryVTT format
- `Journal.from_xml_document(xml_doc)` → Semantic hierarchy
- `journal.add_image()` / `reposition_image()` / `remove_image()` → Image management
- `journal.to_foundry_html(mapping)` → Export HTML

**Content Types:**
- `chapter_title`: Top-level chapter heading (h1)
- `section`: Major section heading (h2)
- `subsection`: Subsection heading (h3)
- `subsubsection`: Sub-subsection heading (h4)
- `paragraph`: Body text with markdown formatting
- `boxed_text`: Call-out boxes with decorative styling
- `table`: Tabular data with rows/cells
- `list`: Ordered or unordered lists
- `definition_list`: Term/description pairs (glossary)
- `stat_block`: Raw XML preserved for later actor parsing
- `image_ref`: Image placeholder with key for later resolution
- `footer`: Page footer text
- `page_number`: Page number metadata

**ImageMetadata Fields:**
- `key`: Unique identifier (e.g., "page_5_top_battle_map")
- `source_page`: Original page number from PDF
- `type`: "map", "illustration", "diagram", "unknown"
- `description`: Optional text description
- `file_path`: Optional local file path
- `insert_before_content_id`: Content ID to insert image before (for repositioning)

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

**Integration Points:**

1. **pdf_to_xml.py**: Generates XML files that become XMLDocument instances
2. **upload_to_foundry.py**: Uses XMLDocument or Journal to generate HTML for upload
3. **Scene Artwork Generation**: Adds scene images to Journal.image_registry
4. **Map Asset Extraction**: Registers map images in Journal.image_registry
5. **Actor/NPC Extraction**: Processes `stat_block` content from XMLDocument
6. **Web UI**: Can display Journal hierarchy for navigation

**Key Design Decisions:**

1. **Immutability**: XMLDocument is frozen (immutable) to prevent accidental modification of raw data
2. **Mutability**: Journal is mutable to support workflow operations (adding images, repositioning content)
3. **Separation of Concerns**: XMLDocument = raw data, Journal = working representation
4. **Content ID Reassignment**: Journal assigns semantic IDs for better addressing in workflows
5. **Image Registry**: Centralized management of all image references (from Gemini + custom additions)

### Processing Pipeline

The system follows a four-stage pipeline (orchestrated by `scripts/full_pipeline.py`):

1. **PDF Splitting** (`src/pdf_processing/split_pdf.py`):
   - Input: `data/pdfs/Lost_Mine_of_Phandelver.pdf`
   - Output: Chapter PDFs in `data/pdf_sections/Lost_Mine_of_Phandelver/`
   - Hardcoded chapter boundaries based on manual TOC analysis

2. **PDF to XML Conversion** (`src/pdf_processing/pdf_to_xml.py`):
   - Input: Chapter PDFs from `data/pdf_sections/`
   - Output: Timestamped run in `output/runs/<YYYYMMDD_HHMMSS>/documents/`
   - Core AI-powered extraction engine using Gemini 2.5 Pro

2.5. **Scene Artwork Generation** (`scripts/generate_scene_art.py`):
   - Input: Chapter XML from `output/runs/<timestamp>/documents/`
   - Output: Scene images and gallery HTML in `output/runs/<timestamp>/scene_artwork/`
   - Post-processing workflow using Gemini for context extraction and scene identification

3. **FoundryVTT Upload** (`src/foundry/upload_to_foundry.py`):
   - Input: XML files from run directory (converted to HTML on-the-fly)
   - Output: Journal entries in FoundryVTT
   - Uses `JournalManager` class for create/replace operations

4. **FoundryVTT Export** (`src/foundry/export_from_foundry.py`):
   - Input: Journal UUID from step 3 (or searches by name)
   - Output: HTML file in `output/runs/<timestamp>/foundry_export/`

### FoundryVTT Integration

The project includes full integration with FoundryVTT for uploading and exporting journal entries.

**Architecture:**
- Uses direct WebSocket connection via Tablewrite Foundry module (Backend → WebSocket → FoundryVTT)
- `src/foundry/client.py`: Base `FoundryClient` class with API configuration
- `src/foundry/journals.py`: `JournalManager` class with all journal CRUD operations
- `src/foundry/upload_to_foundry.py`: Batch upload script
- `src/foundry/export_from_foundry.py`: Export journals as HTML or JSON
- `scripts/full_pipeline.py`: Complete workflow orchestration

**Key Features:**
- **Create or Replace**: Automatically searches for existing journals and replaces them (no duplicates)
- **Export Support**: Download journals from FoundryVTT as HTML or JSON
- **UUID Optimization**: Returns journal UUID from upload to avoid extra API call during export
- **Pages Structure**: Compatible with FoundryVTT v10+ pages architecture
- **Environment-based Config**: Supports both local FoundryVTT and The Forge

**JournalManager API:**
```python
from foundry.client import FoundryClient
client = FoundryClient(target="local")  # or "forge"

uuid = client.journals.create_or_replace_journal(name="Chapter 1", pages=[...])
entry = client.journals.get_journal_entry(journal_name="Chapter 1")
results = client.journals.search_journals(name="Chapter 1")
client.journals.delete_journal(journal_uuid="JournalEntry.abc123")
```

**API Response Formats:**
- Create: `{'entity': {...}, 'uuid': 'JournalEntry.{id}'}`
- Update: `{'entity': [...], 'uuid': 'JournalEntry.{id}'}`  (entity is a list!)
- Delete: `{'success': True}`
- Search: `[{'id': '...', 'uuid': 'JournalEntry.{id}', 'name': '...'}]`
- Get: `{'_id': '...', 'uuid': 'JournalEntry.{id}', 'name': '...', 'pages': [...]}`

**Important Implementation Notes:**
- Update/delete operations require `uuid` as query parameter: `/update?clientId={id}&uuid={uuid}`
- Update payload is `{"data": {...}}`, NOT `{"entityType": "JournalEntry", "id": "...", "data": {...}}`
- FoundryVTT v10+ requires pages structure: `{"pages": [{"name": "...", "type": "text", "text": {"content": "..."}}]}`

**Search API Notes:**
- **Hard 200-result limit**: Hardcoded in QuickInsert module
- **Correct parameter is `filter`, NOT `type`**: Use `filter=Item` or `filter=documentType:Item,package:dnd5e.items`
- **World Actor Quirk**: Empty query returns only compendium actors; must search a-z to get all world actors
- **Bulk operations**: Build local cache by querying common terms, then perform lookups locally

**FoundryVTT Item Types:**
- **Physical Items**: `equipment`, `weapon`, `consumable`, `container`, `loot`
- **Character Options**: `spell`, `feat`, `subclass`, `background`, `race`
- **Magic Items**: Check `system.properties` for `'mgc'` flag (spans multiple subTypes)

### Actor/NPC Extraction

The project includes automatic extraction and creation of D&D 5e actors and NPCs from module PDFs.

**Processing Pipeline:**
```
PDF → XML (with <stat_block> tags)
    ↓
parse_stat_blocks.py (Gemini → StatBlock models)
    ↓
extract_npcs.py (Gemini → NPC models)
    ↓
ActorManager (creates/reuses FoundryVTT Actors)
```

**Actor Types:**
1. **Creature Actors**: Full stat blocks (AC, HP, abilities, actions) - reuses compendium actors if name matches
2. **NPC Actors**: Named characters with bio (description, plot role, location) - links to creature stat block via @UUID

**Usage:**
```bash
# Full pipeline with actors
uv run python scripts/full_pipeline.py --journal-name "Lost Mine of Phandelver"

# Skip actor processing
uv run python scripts/full_pipeline.py --skip-actors

# Process actors only
uv run python scripts/full_pipeline.py --actors-only --run-dir output/runs/20241023_143022
```

**Data Models** (see `src/actors/models.py` and `src/foundry/actors/models.py`):
```python
# Basic D&D stat block
class StatBlock(BaseModel):
    name: str
    raw_text: str
    armor_class: int
    hit_points: int
    challenge_rating: float
    # Optional: size, type, alignment, abilities, actions, traits, reactions, etc.

# Detailed parsed data for FoundryVTT
class ParsedActorData(BaseModel):
    name: str
    abilities: Dict[str, int]  # STR, DEX, CON, INT, WIS, CHA
    attacks: List[Attack]      # Weapon attacks with damage formulas
    traits: List[Trait]        # Special abilities
    spells: List[Spell]        # Spells with compendium UUIDs
    # Plus: skills, defenses, movement, senses, languages, etc.

class NPC(BaseModel):
    name: str
    creature_stat_block_name: str  # Links to creature
    description: str
    plot_relevance: str
```

**Parsing Pipeline:**
1. **Stage 1**: Basic extraction (`StatBlock`) - captures core stats, preserves raw text
2. **Stage 2**: Detailed parsing (`ParsedActorData`) - parses attacks, traits, multiattack, innate spellcasting, resolves spell UUIDs

**SpellCache** (see `src/foundry/actors/spell_cache.py`):
```python
cache = SpellCache()
cache.load()  # Fetches all spells via REST API
uuid = cache.get_spell_uuid("Fireball")
```

**FoundryVTT Actor Creation Workflow:**
1. **CREATE Actor**: Upload with weapons, feats, and traits embedded
2. **GIVE Spells**: Add compendium spells via `/give` endpoint (preserves full spell data)

**Converter API:**
```python
from foundry.actors.converter import convert_to_foundry
from foundry.actors.spell_cache import SpellCache

spell_cache = SpellCache()
spell_cache.load()

actor_json, spell_uuids = convert_to_foundry(parsed_actor, spell_cache=spell_cache)
actor_uuid = client.actors.create_actor(actor_json, spell_uuids=spell_uuids)
```

**FoundryVTT v10+ Activities:**
- Single Activity: Simple weapon attack
- Two Activities: Attack + save
- Three Activities: Attack + save + ongoing damage
- Activity types: `attack`, `save`, `damage`
- Each activity has 16-character alphanumeric `_id`

**Key Modules:**
- `src/actors/`: models, parse/extract stat blocks/npcs, process_actors
- `src/foundry/actors/`: models, spell_cache, converter, manager

**Utility Scripts:**
```bash
# Delete all world actors (filters out compendiums)
uv run python scripts/delete_all_actors.py --yes
```

### Actor Creation Orchestration

**NEW**: Complete pipeline for creating D&D actors from natural language descriptions.

**Module**: `src/actors/orchestrate.py`

**Workflow**:
```
Natural Language Description
    ↓
Generate Stat Block Text (Gemini)
    ↓
Parse to StatBlock Model
    ↓
Parse to ParsedActorData
    ↓
Convert to FoundryVTT Format
    ↓
Upload to FoundryVTT Server
```

**Usage**:

```python
from actors.orchestrate import create_actor_from_description_sync, create_actors_batch_sync

# Single actor
result = create_actor_from_description_sync("A red dragon wyrmling", challenge_rating=2.0)
# → ActorCreationResult with foundry_uuid, output_dir, stat_block, parsed_actor_data

# Batch (pre-load SpellCache for efficiency)
results = create_actors_batch_sync(["dragon", "goblin"], challenge_ratings=[2.0, 0.5])
```

**Output**: `output/runs/<timestamp>/actors/` with `01_raw_stat_block.txt`, `02_stat_block.json`, `03_parsed_actor_data.json`, `04_foundry_actor.json`

### WebSocket Push Architecture

The backend includes a WebSocket endpoint for pushing content directly to connected Foundry clients, eliminating the need for the relay server.

**Endpoint:** `/ws/foundry`

**Protocol:**
- **Connect:** Client receives `{"type": "connected", "client_id": "..."}`
- **Ping/Pong:** Send `{"type": "ping"}` -> Receive `{"type": "pong"}`
- **Push Messages:** Server sends `{"type": "actor|journal|scene", "data": {...}}`

**Usage:**
```python
from app.websocket import push_actor, push_journal, push_scene

# Push actor to all connected Foundry clients
await push_actor({"name": "Goblin", "type": "npc", "uuid": "Actor.abc123"})

# Push journal entry
await push_journal({"name": "Chapter 1", "pages": [...]})

# Push scene
await push_scene({"name": "Cave Entrance", "walls": [...]})
```

**Foundry Module:**

The `foundry-module/tablewrite-assistant/` directory contains the FoundryVTT module that:
1. Connects to backend WebSocket on startup
2. Receives push notifications for new content
3. Automatically calls `Actor.create()`, `JournalEntry.create()`, `Scene.create()`
4. Shows notifications when content is created

**Quick Start:**
```bash
# Start backend with docker-compose
docker-compose -f docker-compose.tablewrite.yml up -d

# Or run directly
cd ui/backend && uvicorn app.main:app --reload --port 8000

# Install Foundry module:
# 1. Copy foundry-module/tablewrite-assistant/ to your Foundry Data/modules/ directory
# 2. Enable "Tablewrite Assistant" module in Foundry
# 3. Configure backend URL in module settings (default: http://localhost:8000)
```

**Testing:**
```bash
# Backend WebSocket tests
cd ui/backend && uv run pytest tests/websocket/ -v

# Module unit tests
cd foundry-module/tablewrite-assistant && npm test
```

### Self-Hosted Relay Server (DEPRECATED)

> **DEPRECATED as of 2025-12-30:** The relay server has been fully replaced by the WebSocket Push Architecture above. All relay functionality (search, file listing, entity CRUD) is now available via WebSocket messages. See `relay-server/ARCHIVED.md` for the complete migration table.

**Migration Summary:**
| Old (Relay) | New (WebSocket) |
|-------------|-----------------|
| `GET /search` | `search_items` message |
| `GET /file-system` | `list_files` message |
| All entity CRUD | Direct WebSocket handlers |

**Preferred Method:** Use the WebSocket endpoint (`/ws/foundry`) with the Tablewrite Foundry module. No relay server configuration needed.

The relay server code is preserved in `relay-server/` for reference but is no longer actively maintained.

### Scene Extraction & Artwork Generation

AI-powered scene extraction and artwork generation for creating visual galleries.

**Processing Workflow:**
1. **Context Extraction**: Analyzes chapter XML to determine environment type, lighting, terrain
2. **Scene Identification**: Extracts physical locations, filters out NPCs/monsters
3. **Image Generation**: Creates AI artwork using `imagen-4.0-fast-generate-001` (parallel processing)
4. **Gallery Creation**: Generates HTML gallery with collapsible prompts

**Scene Model:**
```python
class Scene(BaseModel):
    section_path: str        # "Chapter 2 → The Cragmaw Hideout → Area 1"
    name: str               # "Twin Pools Cave"
    description: str        # Physical environment only
    location_type: str      # "underground", "outdoor", "interior", "underwater"
```

**Usage:**
```bash
# Generate artwork for all chapters
uv run python scripts/generate_scene_art.py --run-dir output/runs/20241023_123456

# Single chapter with custom style
uv run python scripts/generate_scene_art.py --xml-file chapter.xml --style "dark fantasy, oil painting"
```

**Output:** `output/runs/<timestamp>/scene_artwork/images/` + `scene_gallery.html`

### Image Asset Extraction

AI-powered map extraction for automatically extracting battle maps and navigation maps from PDFs.

**Processing Workflow:**
1. **Detection**: Gemini Vision identifies functional maps (filters decorative maps)
2. **Flattened PDF Detection**: Checks if page is single image (>80% page area)
3. **Extraction Attempt**: PyMuPDF extraction first (faster) with AI classification
4. **Fallback Segmentation**: Gemini Imagen with red perimeter technique if extraction fails
5. **Metadata Generation**: JSON with map names, types, page numbers, source method

**Key Features:**
- **Hybrid Approach**: PyMuPDF (fast) + Imagen segmentation (handles baked-in maps)
- **Fully Parallel Processing**: All pages processed concurrently with `asyncio`
- **Word Count Validation**: OCR quality check rejects extractions with >100 words (5 retries)
- **Models**: `gemini-2.0-flash` (detection), `gemini-2.5-flash-image` (segmentation)

**MapMetadata Model:**
```python
class MapMetadata(BaseModel):
    name: str              # "Example Keep"
    chapter: Optional[str] = None
    page_num: int
    type: str              # "navigation_map" or "battle_map"
    source: str            # "extracted" or "segmented"
```

**Usage:**
```bash
# Extract all maps from PDF
uv run python src/pdf_processing/image_asset_processing/extract_map_assets.py --pdf data/pdfs/module.pdf --chapter "Chapter 1"
```

**Output:** `output/runs/<timestamp>/map_assets/` with extracted PNG maps + `maps_metadata.json`

**Critical Implementation Details:**
1. **Functional Map Detection**: Distinguishes gameplay maps from decorative elements
2. **AI Classification**: Filters background textures and non-functional artwork
3. **Resolution Scaling**: Corrects for Gemini's image downscaling during segmentation
4. **Fully Parallel**: Uses `asyncio.to_thread()` for blocking PyMuPDF operations

### Wall Detection & FoundryVTT Export

AI-powered wall detection extracts walls from battle maps and exports to FoundryVTT format.

**Pipeline:** Image → PNG → Grayscale → AI Redlines → Polygonize → FoundryVTT JSON

**Usage:**
```bash
PYTHONPATH=src uv run python scripts/test_redline_walls.py
```

**6 Composable Functions:**
1. `convert_to_png()` - Format conversion
2. `create_grayscale()` - Grayscale for AI processing
3. `generate_redlines()` - AI wall detection (gemini-2.5-flash-image)
4. `polygonize_redlines()` - Vector extraction
5. `create_overlay()` - Visual verification (red lines, alpha=0.8)
6. `convert_to_foundry_format()` - FoundryVTT JSON export

**Output Files:**
- `01_original.png` - Original map
- `02_grayscale.png` - Grayscale version
- `03_redlined.png` - AI red lines
- `04_polygonized/` - Vector data (7 files)
- `05_final_overlay.png` - Red line overlay for verification
- `06_foundry_walls.json` - FoundryVTT walls (coordinates, blocking settings)

**FoundryVTT Format:**
```json
{
  "walls": [{"c": [x1, y1, x2, y2], "move": 0, "sense": 0, "door": 0, "ds": 0}],
  "image_dimensions": {"width": 1380, "height": 940},
  "total_walls": 874
}
```

**Modules:**
- `src/wall_detection/redline_walls.py` - Complete pipeline
- `src/wall_detection/polygonize.py` - Vector extraction
- `src/util/parallel_image_gen.py` - Parallel image generation utility

## Web UI

Chat-based web UI with wax seal aesthetic for D&D Module Assistant.

**For detailed UI documentation, see [`ui/CLAUDE.md`](ui/CLAUDE.md).**

**Key Features:**
- React 19 + TypeScript + Vite frontend with Tailwind CSS
- FastAPI backend with Google Gemini API integration
- Fixed 96vh layout with ChatWindow-only scrolling
- Conversation history maintained across messages

**Quick Start:**
```bash
# Backend (in ui/backend/)
uv venv && source .venv/bin/activate && uv pip install -r requirements.txt
echo "GEMINI_API_KEY=<your_key>" > .env
uvicorn app.main:app --reload --port 8000

# Frontend (in ui/frontend/)
npm install && npm run dev
```

Access at http://localhost:5173

### Key Architecture Patterns

**pdf_to_xml.py** (main conversion engine):
- **Parallel Processing**: `ThreadPoolExecutor` (max 5 workers) for page/chapter processing
- **Text Extraction**: Two-tier fallback (embedded text → Tesseract OCR if corrupted)
- **AI-Powered XML**: Each page uploaded to Gemini 2.5 Pro with structured prompt
- **Retry Logic**: 3 attempts per page with exponential backoff
- **Self-Healing XML**: Malformed XML sent back to Gemini for correction
- **Quality Validation**: Word count comparison (15% tolerance), page-level and chapter-level

**Output Directory Structure:**
```
output/runs/<timestamp>/
├── documents/<chapter>.xml
├── intermediate_logs/<chapter>/pages/  # Per-page PDFs, text, XML attempts
└── error_report.txt
```

### Critical Implementation Details

1. **PROJECT_ROOT Pattern**:
   - `src/pdf_processing/`: `os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))`
   - `src/`: `os.path.dirname(os.path.dirname(os.path.abspath(__file__)))`

2. **Import Pattern**: Scripts in `src/pdf_processing/` add parent to sys.path:
   ```python
   import sys
   sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
   from logging_config import setup_logging
   ```

3. **Gemini Model**: Hardcoded to `gemini-2.5-pro` (`GEMINI_MODEL_NAME` constant)

4. **XML Generation**: Uses Markdown syntax (`*italic*`, `**bold**`) with D&D tags like `<monster>`

5. **Error Handling**: Page errors mark entire chapter as failed; preserves partial outputs; never edits in place

## Testing

### Test Structure

```
tests/
├── conftest.py              # Shared fixtures
├── test_main.py             # End-to-end pipeline tests
├── pdf_processing/          # Tests for src/pdf_processing/
│   ├── test_split_pdf.py
│   ├── test_pdf_to_xml.py
│   ├── test_get_toc.py
│   └── test_xml_to_html.py
├── foundry/                 # Tests for src/foundry/
│   ├── test_client.py
│   ├── test_upload_script.py
│   └── actors/              # Tests for src/foundry/actors/
│       ├── test_models.py
│       ├── test_spell_cache.py
│       └── fixtures/        # Test data (goblin_parsed.json, mage_parsed.json)
└── output/test_runs/        # Persistent test output (NOT auto-cleaned)
```

### Running Tests

```bash
pytest                                      # Smoke tests only (<2 min) - DEFAULT
pytest --full                               # Full suite (~35 min)
pytest -m "not integration and not slow"    # Unit tests only
pytest -m integration                       # Integration tests (cost money)
AUTO_ESCALATE=false pytest                  # Disable auto-escalation on failure
```

**Smoke tests** cover: PDF Processing, Actor Creation, FoundryVTT Integration, XMLDocument Parsing, Image Asset Processing, Public API

### Test Markers

- `@pytest.mark.smoke`: Critical smoke tests (one per major feature)
- `@pytest.mark.unit`: Fast unit tests (no external dependencies)
- `@pytest.mark.integration`: Real Gemini API calls (consume quota, cost money)
- `@pytest.mark.slow`: Slow tests (API calls, large file processing)
- `@pytest.mark.requires_api`: Tests requiring Gemini API key

### Key Fixtures (from `conftest.py`)

- `test_pdf_path`: `Lost_Mine_of_Phandelver_test.pdf` (7 pages)
- `full_pdf_path`: Full PDF (for TOC tests only)
- `test_output_dir`: Temporary directory (auto-cleaned)
- `sample_xml_content`: Valid XML for testing

### Writing New Tests

1. **Mirror src/ structure**: Tests for `src/foo/bar.py` go in `tests/foo/test_bar.py`
2. **Use fixtures**: Import from `conftest.py`
3. **Mark appropriately**: Use `@pytest.mark.integration` for API calls
4. **Test real behavior**: Integration tests make REAL Gemini API calls (not mocked)

**Integration Test Warning:** Tests marked `@pytest.mark.integration` consume API quota and cost money. Run unit tests only for fast feedback: `uv run pytest -m "not integration and not slow"`

## Claude Code Workflow

- **Test Output**: When running tests, write output to a log file (e.g., `uv run pytest 2>&1 | tee test_output.log`) instead of truncating with `head`/`tail`. This preserves full warnings, errors, and test summaries for review.
- **Running Tests**: Run non-slow tests normally. Run full test suite (`pytest --full`) in the background since it takes ~40 minutes.

## Coding Conventions

**General Principles:**
- Write clean, concise code - prioritize readability and simplicity
- Keep functions focused - each function should do one thing well
- Avoid unnecessary complexity - use straightforward solutions
- Clear is better than compact - favor explicit, readable code

**From AGENTS.md:**
- **Style**: PEP 8 with 4-space indentation, snake_case names, UPPER_SNAKE_CASE for constants
- **Module Naming**: `verb_noun.py` pattern (e.g., `split_pdf.py`, `get_toc.py`)
- **Strings**: Prefer f-strings
- **Validation**: Early validation of external resources
- **Helpers**: Keep helpers near call sites, confine I/O to small adapters
- **Docstrings**: Concise module-level docstrings for entry points

## Commit Style

Based on git history:
- Short, imperative mood summaries ("added requirements.txt", "updated", "fixes")
- Group related changes
- Mention impacted scripts

## Future Development Notes

- README mentions long-term goal: map XML to FoundryVTT module manifests
- Need to normalize XML schema before building Foundry exporter
- Consider adding pytest suites under `tests/` directory
- Mock Gemini calls for offline testing
- Use fixtures from `xml_examples/` or trimmed pages
- "whenever creating a new worktree cp the .env file
- If there is a failure, report with big red X, especially if you plan on showing greencheck marks