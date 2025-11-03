# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a D&D module converter that transforms official Dungeons & Dragons PDFs into structured XML assets for post-processing into FoundryVTT content. The pipeline uses Google's Gemini 2.5 Pro model for AI-powered document analysis and extraction.

## Environment Setup

1. **Install uv** (if not already installed):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   # Or: pip install uv
   ```

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
   FOUNDRY_RELAY_URL=https://foundryvtt-rest-api-relay.fly.dev
   FOUNDRY_LOCAL_URL=http://localhost:30000
   FOUNDRY_LOCAL_API_KEY=<your_foundry_api_key>
   FOUNDRY_LOCAL_CLIENT_ID=<your_client_id>
   FOUNDRY_AUTO_UPLOAD=false
   FOUNDRY_TARGET=local
   ```

4. **Source PDFs**: Place D&D module PDFs in `data/pdfs/` (default expects `Lost_Mine_of_Phandelver.pdf`)

## Logging

All scripts use Python's standard `logging` module for structured output:

- **Log Levels**:
  - `DEBUG`: Detailed processing steps (page uploads, file creation, word frequency analysis)
  - `INFO`: Normal workflow progress (chapter/page processing, verification steps)
  - `WARNING`: Non-fatal issues (OCR fallback, retries, word count mismatches)
  - `ERROR`: Processing failures and unrecoverable errors

- **Log Outputs**:
  - Console: All log levels displayed with timestamps
  - File: `pdf_to_xml.py` writes logs to `<run_dir>/pdf_to_xml.log`

- **Configuration**: Centralized in `src/logging_config.py`
  - Use `setup_logging(__name__)` for simple console logging
  - Use `get_run_logger(script_name, run_dir)` for file + console logging

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
uv run src/foundry/export_from_foundry.py "Lost Mine of Phandelver" --format json

# Scene Artwork Generation
uv run python scripts/generate_scene_art.py --run-dir output/runs/20241023_123456
uv run python scripts/generate_scene_art.py --xml-file output/runs/latest/documents/chapter_01.xml --style "top-down battle map"

# Map Asset Extraction
uv run python src/pdf_processing/image_asset_processing/extract_map_assets.py --pdf data/pdfs/module.pdf
uv run python src/pdf_processing/image_asset_processing/extract_map_assets.py --pdf data/pdfs/module.pdf --chapter "Chapter 1"
uv run python src/pdf_processing/image_asset_processing/extract_map_assets.py --pdf data/pdfs/module.pdf --output custom/output/dir

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
# Then run scripts normally:
python src/pdf_processing/split_pdf.py
python src/pdf_processing/pdf_to_xml.py
python src/pdf_processing/xml_to_html.py
```

## Architecture & Data Flow

### Processing Pipeline

The system follows a four-stage pipeline (orchestrated by `scripts/full_pipeline.py`):

1. **PDF Splitting** (`src/pdf_processing/split_pdf.py`):
   - Input: `data/pdfs/Lost_Mine_of_Phandelver.pdf`
   - Output: Chapter PDFs in `pdf_sections/Lost_Mine_of_Phandelver/`
   - Hardcoded chapter boundaries based on manual TOC analysis

2. **PDF to XML Conversion** (`src/pdf_processing/pdf_to_xml.py`):
   - Input: Chapter PDFs from `pdf_sections/`
   - Output: Timestamped run in `output/runs/<YYYYMMDD_HHMMSS>/documents/`
   - Core AI-powered extraction engine using Gemini 2.5 Pro

2.5. **Scene Artwork Generation** (`scripts/generate_scene_art.py`):
   - Input: Chapter XML from `output/runs/<timestamp>/documents/`
   - Output: Scene images and gallery HTML in `output/runs/<timestamp>/scene_artwork/`
   - Post-processing workflow using Gemini for context extraction and scene identification
   - Gemini Imagen for artwork generation

3. **FoundryVTT Upload** (`src/foundry/upload_to_foundry.py`):
   - Input: XML files from run directory (converted to HTML on-the-fly)
   - Output: Journal entries in FoundryVTT
   - Uses `JournalManager` class for create/replace operations
   - Returns journal UUID for step 4

4. **FoundryVTT Export** (`src/foundry/export_from_foundry.py`):
   - Input: Journal UUID from step 3 (or searches by name)
   - Output: HTML file in `output/runs/<timestamp>/foundry_export/`
   - Exports final rendered journal for verification and archival

### FoundryVTT Integration

The project includes full integration with FoundryVTT for uploading and exporting journal entries.

**Architecture:**
- Uses ThreeHats REST API module (relay server → WebSocket → FoundryVTT)
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
- **Error Handling**: Graceful handling of search failures, network errors, and API issues

**JournalManager API:**
```python
from foundry.client import FoundryClient

client = FoundryClient(target="local")  # or "forge"

# Create or replace journal (returns UUID)
uuid = client.journals.create_or_replace_journal(
    name="Chapter 1",
    pages=[{"name": "Page 1", "content": "<h1>...</h1>"}]
)

# Get journal by UUID or name
entry = client.journals.get_journal_entry(
    journal_name="Chapter 1",
    journal_uuid="JournalEntry.abc123"  # optional, avoids search
)

# Search for journals by name
results = client.journals.search_journals(name="Chapter 1")

# Delete journal
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
- Search results may return `id` OR `uuid` field; JournalManager normalizes to both `_id` and `uuid`
- FoundryVTT v10+ requires pages structure: `{"pages": [{"name": "...", "type": "text", "text": {"content": "..."}}]}`
- `create_or_replace_journal` returns the journal UUID for efficient subsequent operations

**Search API (via QuickInsert module):**

The `/search` endpoint uses the QuickInsert module on FoundryVTT and has specific behavior:

- **Hard 200-result limit**: Hardcoded in the FoundryVTT module (`src/ts/network/routers/search.ts:54`)
- **No pagination or bulk endpoints**: Cannot retrieve all compendium items in one call
- **Correct parameter is `filter`, NOT `type`**:
  - ❌ `type=Item` - ignored, just echoed back as metadata
  - ✅ `filter=Item` - filters to Items only (shorthand for `documentType:Item`)
  - ✅ `filter=documentType:Item,package:dnd5e.items` - multi-property filtering
  - ✅ `filter=documentType:Item,folder:abc123` - filter by folder

- **Filter syntax**:
  - Simple: `filter="Item"` → `{documentType: "Item"}`
  - Property-based: `filter="key:value,key2:value2"` → multiple filters
  - Supported properties: `documentType`, `package`, `folder`, `resultType`, or any item property

- **Request flow**: HTTP → Relay Server → WebSocket → FoundryVTT → QuickInsert → Response

- **Recommended approach for bulk operations**: Build a local cache by querying with common terms ("a", "of", "the") and specific compendium packs, then perform lookups locally

- **Critical Search API Quirk for World Actors**:
  - **Empty query returns ONLY compendium actors**: `query=""` with `filter="Actor"` returns 0 world actors
  - **Non-empty query returns world + compendium actors**: `query="a"` returns both world and compendium actors
  - **To get all world actors**: Must search with all 26 letters (a-z) and deduplicate by UUID
  - Example: `ActorManager.get_all_actors()` searches alphabet a-z and filters to `Actor.*` UUIDs
  - This quirk affects any bulk operations on world actors (deletion, export, migration)
  - Uses same comprehensive strategy as item caching (26 queries, one per letter)

**FoundryVTT Item Types:**

In FoundryVTT, "Item" is a broad document type that includes character options, spells, and physical items. Filter by `subType` to narrow down:

- **Physical Items** (treasure/loot):
  - `equipment` - armor, wondrous items, accessories, rings, cloaks
  - `weapon` - weapons (mundane and magical)
  - `consumable` - potions, scrolls, ammunition
  - `container` - bags of holding, chests, backpacks
  - `loot` - treasure, gems, art objects, trade goods

- **Character Options** (NOT physical items):
  - `spell` - spells (Aid, Fireball, etc.)
  - `feat` - feats and features (Alert, Action Surge, etc.)
  - `subclass` - subclass features
  - `background` - background features
  - `race` - racial traits

**Magic Item Identification:**
- Magic items span multiple subTypes: `equipment`, `weapon`, `consumable`, `container`
- No direct filter for "magic only" - must fetch full item data and check `system.properties` for `'mgc'`
- Example: Hat of Disguise has `system.properties: ['mgc']`, `system.rarity: 'uncommon'`, `system.attunement: 'required'`

**Caching Strategy for Physical Items:**
- Search alphabet (a-z) for each physical subType separately (API only supports AND filtering, not OR)
- 5 subTypes × 26 letters = 130 API calls for comprehensive coverage of all physical items
- Deduplicate by UUID (items appear in multiple compendiums like `dnd5e.items` and `dnd5e.equipment24`)

### Actor/NPC Extraction

The project includes automatic extraction and creation of D&D 5e actors and NPCs from module PDFs.

**Architecture:**
- **Stat Block Tagging**: During XML generation, Gemini tags stat blocks with `<stat_block name="...">raw text</stat_block>`
- **Stat Block Parsing**: Gemini parses raw stat blocks into structured Pydantic `StatBlock` models
- **NPC Extraction**: Post-processing analyzes XML to identify named NPCs and link them to stat blocks
- **Actor Creation**: Creates FoundryVTT Actor entities with compendium reuse

**Processing Pipeline:**
```
PDF → XML (with <stat_block> tags)
    ↓
parse_stat_blocks.py (Gemini parses → StatBlock models)
    ↓
extract_npcs.py (Gemini identifies NPCs → NPC models)
    ↓
ActorManager (creates/reuses FoundryVTT Actors)
```

**Actor Types:**
1. **Creature Actors**: Full stat blocks from the module (e.g., "Goblin", "Bugbear")
   - Contains complete D&D 5e stats (AC, HP, abilities, actions)
   - Created from `StatBlock` models
   - Reuses compendium actors if name matches

2. **NPC Actors**: Named characters with plot context (e.g., "Klarg", "Sildar Hallwinter")
   - Bio-only actors (no stats directly)
   - Biography includes description, plot role, location
   - Links to creature stat block via @UUID syntax
   - Example: "Klarg" (NPC) → links to → "Bugbear" (creature actor)

**Usage:**
```bash
# Full pipeline with actors
uv run python scripts/full_pipeline.py --journal-name "Lost Mine of Phandelver"

# Skip actor processing
uv run python scripts/full_pipeline.py --skip-actors

# Process actors only (from existing run)
uv run python scripts/full_pipeline.py --actors-only

# Process actors for specific run
uv run python scripts/full_pipeline.py --actors-only --run-dir output/runs/20241023_143022
```

**Compendium Reuse:**
- Before creating creature actors, searches ALL user compendiums by name
- If match found, uses existing actor UUID (avoids duplicates)
- NPCs link to existing compendium entries when possible
- Example: "Goblin" found in dnd5e.monsters → reuse instead of creating new

**Data Models** (see `src/actors/models.py` and `src/foundry/actors/models.py`):
```python
# Basic D&D stat block (src/actors/models.py)
class StatBlock(BaseModel):
    name: str
    raw_text: str  # Original stat block text preserved
    armor_class: int
    hit_points: int
    challenge_rating: float
    reactions: Optional[str] = None  # REACTIONS section
    # Optional: size, type, alignment, abilities, actions, traits, etc.

# Detailed parsed data for FoundryVTT conversion (src/foundry/actors/models.py)
class ParsedActorData(BaseModel):
    """Fully parsed stat block ready for FoundryVTT conversion."""
    source_statblock_name: str
    name: str
    armor_class: int
    hit_points: int
    challenge_rating: float
    abilities: Dict[str, int]  # STR, DEX, CON, INT, WIS, CHA
    attacks: List[Attack]  # Weapon attacks with damage formulas
    traits: List[Trait]  # Special abilities and features
    spells: List[Spell]  # Spells with compendium UUIDs
    # Plus: skills, defenses, movement, senses, languages, etc.

class NPC(BaseModel):
    name: str
    creature_stat_block_name: str  # Links to creature (e.g., "Bugbear")
    description: str
    plot_relevance: str
    location: Optional[str]
    first_appearance_section: Optional[str]
```

**Detailed Parsing Infrastructure**:
The project includes a two-stage parsing pipeline for converting stat blocks into FoundryVTT actors:

1. **Stage 1**: Basic extraction (`StatBlock` model)
   - Captures core stats: AC, HP, CR
   - Preserves raw text for all fields (actions, traits, reactions)

2. **Stage 2**: Detailed parsing (`ParsedActorData` model)
   - Parses attacks into structured `Attack` objects with damage formulas
   - Parses traits into structured `Trait` objects with activation types
   - Parses multiattack actions into feat items
   - Parses innate spellcasting with usage frequency (at will, 3/day, 1/day)
   - Resolves spell names to compendium UUIDs using `SpellCache`
   - Breaks down abilities, skills, senses, and defenses into FoundryVTT-ready format

**Actor Parsing Features:**
- **Basic Stats**: Abilities (STR-CHA), AC, HP, CR, saves, movement, senses, languages
- **Attacks**: Weapon items with damage formulas and attack bonuses
- **Traits**: Feat items for special abilities (passive or activated)
- **Multiattack**: Feat item for creatures that make multiple attacks per action
- **Innate Spellcasting**: Feat + spell items with usage limits (at will, X/day)
- **SpellCache Integration**: Automatic spell UUID lookup from FoundryVTT compendiums
- **Full Round-Trip**: ParsedActorData → Upload → Download → Verify (26+ tests passing)

For detailed usage and examples, see `docs/actor-parsing-guide.md`

**SpellCache** (see `src/foundry/actors/spell_cache.py`):
```python
# Load all spells from FoundryVTT compendiums
cache = SpellCache()
cache.load()  # Fetches all spells via REST API

# Resolve spell names to UUIDs
uuid = cache.get_spell_uuid("Fireball")
# Returns: "Compendium.dnd5e.spells.Item.ztgcdrWPshKRpFd0"
```

**FoundryVTT Actor Creation Workflow:**

The system uses a **two-step workflow** for creating actors with compendium spells:

1. **CREATE Actor**: Upload actor with weapons, feats, and traits embedded in payload
2. **GIVE Spells**: Add compendium spells via `/give` endpoint to preserve full spell data

**Why Two Steps?**
- Including spell UUIDs in CREATE payload results in FoundryVTT stripping the UUIDs and creating minimal stubs
- The `/give` endpoint properly hydrates full compendium data (descriptions, activities, damage formulas)
- Weapons and feats MUST be in CREATE payload (cannot use /give for custom items)

**Converter API:**
```python
from foundry.actors.converter import convert_to_foundry
from foundry.actors.spell_cache import SpellCache

# Load spell cache for UUID resolution
spell_cache = SpellCache()
spell_cache.load()

# Convert ParsedActorData to FoundryVTT format
actor_json, spell_uuids = convert_to_foundry(parsed_actor, spell_cache=spell_cache)

# actor_json contains: weapons, feats, traits, multiattack, innate spellcasting feat
# spell_uuids contains: list of compendium spell UUIDs to add via /give

# Create actor (automatically adds spells via /give)
actor_uuid = client.actors.create_actor(actor_json, spell_uuids=spell_uuids)
```

**FoundryVTT v10+ Activities Structure:**

The converter generates proper v10+ activities for weapon attacks:

- **Single Activity**: Simple weapon attack (e.g., Scimitar)
- **Two Activities**: Attack + save (e.g., Poison Bite with CON save)
- **Three Activities**: Attack + save + ongoing damage (e.g., Pit Fiend Bite with poison damage)

Each activity has a unique 16-character alphanumeric `_id` field (format: `[a-zA-Z0-9]{16}`).

**Activity Types:**
- `attack`: Weapon attack with attack bonus and damage
- `save`: Saving throw (DC, ability, damage, onSave behavior)
- `damage`: Ongoing damage effects (e.g., poison damage at start of turn)

**Key Modules:**
- `src/actors/models.py`: Pydantic models for StatBlock and NPC
- `src/actors/parse_stat_blocks.py`: Gemini-powered stat block parser
- `src/actors/extract_stat_blocks.py`: Extract stat blocks from XML
- `src/actors/extract_npcs.py`: Gemini-powered NPC identification
- `src/actors/process_actors.py`: Orchestration workflow
- `src/foundry/actors/models.py`: Detailed ParsedActorData models for FoundryVTT (Attack, Trait, Spell, etc.)
- `src/foundry/actors/spell_cache.py`: Spell UUID resolution cache
- `src/foundry/actors/converter.py`: Convert ParsedActorData to FoundryVTT JSON with v10+ activities
- `src/foundry/actors/manager.py`: FoundryVTT Actor CRUD operations (create, get, delete, search)

**Utility Scripts:**
- `scripts/delete_all_actors.py`: Delete all world actors (filters out compendiums)
  ```bash
  # Interactive mode (asks for confirmation)
  uv run python scripts/delete_all_actors.py

  # Auto-confirm (useful for cleanup during development)
  uv run python scripts/delete_all_actors.py --yes
  ```

### Self-Hosted Relay Server

The project uses a **self-hosted local relay server** instead of the public hosted service for local development.

**Quick Setup:**
1. Start relay: `cd relay-server && docker-compose -f docker-compose.local.yml up -d`
2. Configure FoundryVTT module: Change relay URL to `http://localhost:3010`
3. Verify: `curl http://localhost:3010/health`
4. Test: `uv run python scripts/test_relay_connection.py`

**Configuration:**
- Relay URL: `http://localhost:3010` (set in `.env` as `FOUNDRY_RELAY_URL`)
- Database: In-memory (bypasses authentication for local development)
- Logs: `docker-compose -f relay-server/docker-compose.local.yml logs -f relay`
- Location: `relay-server/` directory

**Key Features:**
- Built from source for Apple Silicon (ARM64) compatibility
- Uses memory database to bypass API key authentication
- WebSocket connection to FoundryVTT for real-time communication
- Compatible with all existing FoundryVTT integration code

**See:** `docs/RELAY_SERVER_SETUP.md` for complete documentation.

### Scene Extraction & Artwork Generation

The project includes AI-powered scene extraction and artwork generation for creating visual galleries of D&D module locations.

**Architecture:**
- `src/scene_extraction/models.py`: Pydantic models for Scene and ChapterContext
- `src/scene_extraction/extract_context.py`: Chapter-level environmental context extraction using Gemini
- `src/scene_extraction/identify_scenes.py`: Scene location identification using Gemini 2.0 Flash
- `src/scene_extraction/generate_artwork.py`: AI image generation using Gemini Imagen
- `src/scene_extraction/create_gallery.py`: HTML gallery generation with collapsible prompts
- `scripts/generate_scene_art.py`: Main orchestration script with parallel image generation

**Processing Workflow:**
1. **Context Extraction**: Analyzes chapter XML to determine environment type (underground/outdoor/interior), lighting, terrain, atmosphere
2. **Scene Identification**: Extracts physical locations from XML, filtering out NPCs, monsters, and plot details
3. **Image Generation**: Creates AI artwork for each scene using Gemini Imagen (parallel processing with 5 workers)
4. **Gallery Creation**: Generates HTML gallery with images, descriptions, and collapsible Gemini prompts

**Key Features:**
- **Location-Specific Context**: Each scene tagged with location_type (underground, outdoor, interior) for accurate image generation
- **Parallel Generation**: Uses ThreadPoolExecutor with 5 concurrent workers for fast processing
- **Prompt Transparency**: Collapsible boxes in gallery show full Gemini prompt used for each image
- **Image Constraints**: Automatically enforces no text in images, no specific named creatures
- **Model**: Uses `imagen-3.0-generate-002` (no rate limit issues with parallel generation)

**Scene Model:**
```python
class Scene(BaseModel):
    section_path: str        # e.g., "Chapter 2 → The Cragmaw Hideout → Area 1"
    name: str               # "Twin Pools Cave"
    description: str        # Physical environment only (no NPCs/monsters)
    location_type: str      # "underground", "outdoor", "interior", "underwater"
    xml_section_id: Optional[str] = None
```

**Usage:**
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

**Output Structure:**
```
output/runs/<timestamp>/scene_artwork/
├── images/
│   ├── scene_001_cave_mouth.png
│   ├── scene_002_goblin_blind.png
│   └── ...
└── scene_gallery.html  # Gallery with collapsible prompts
```

**Performance:**
- Typical chapter: 10-17 scenes
- Generation speed: ~2-3 seconds per image with parallel processing
- Total time: ~20-30 seconds for full chapter
- Image size: ~1-2 MB per PNG

**Integration with Full Pipeline:**
- Can be integrated into `scripts/full_pipeline.py` as optional step
- Scene gallery HTML can be uploaded to FoundryVTT as journal page

### Image Asset Extraction

The project includes AI-powered map extraction for automatically extracting battle maps and navigation maps from D&D module PDFs.

**Architecture:**
- `src/pdf_processing/image_asset_processing/models.py`: Pydantic models for MapDetectionResult and MapMetadata
- `src/pdf_processing/image_asset_processing/detect_maps.py`: Async Gemini Vision map detection and image classification
- `src/pdf_processing/image_asset_processing/extract_maps.py`: PyMuPDF extraction with AI classification
- `src/pdf_processing/image_asset_processing/segment_maps.py`: Gemini Imagen segmentation with red perimeter technique
- `src/pdf_processing/image_asset_processing/preprocess_image.py`: Red pixel removal preprocessing
- `src/pdf_processing/image_asset_processing/extract_map_assets.py`: Main orchestration script

**Processing Workflow:**
1. **Detection**: Scans all pages in parallel using Gemini Vision to identify functional maps
   - Filters out decorative maps (maps as props in artwork, scene illustrations)
   - Uses "FUNCTIONAL MAP" prompt to distinguish gameplay maps from decorative elements
2. **Flattened PDF Detection**: Checks if page is flattened (single image covering >80% of page area)
   - Skips PyMuPDF extraction for flattened pages (would extract entire page)
   - Proceeds directly to Imagen segmentation
3. **Extraction Attempt**: Tries PyMuPDF extraction first (faster for embedded images)
   - Size filtering: Images must be ≥200x200px and occupy ≥10% of page area
   - AI classification: All candidates sent to Gemini Vision in parallel to verify they're actually maps
   - Returns first image classified as a map (avoids background textures)
4. **Fallback Segmentation**: If PyMuPDF fails, uses Gemini Imagen segmentation
   - Preprocesses image to remove existing red pixels
   - Generates image with tight RGB(255,0,0) red border around map
   - Detects red pixels and calculates bounding box
   - Scales coordinates back to original resolution (critical for correct extraction)
   - Crops original image to segmented region
   - Word count validation: Rejects extractions with >100 words (5 retry attempts)
5. **Metadata Generation**: Creates JSON metadata with map names, types, page numbers, and source method

**Key Features:**
- **Hybrid Approach**: Combines PyMuPDF extraction (fast) with Imagen segmentation (handles baked-in maps)
- **Fully Parallel Processing**: All pages processed concurrently using `asyncio.gather()` and `asyncio.to_thread()` for blocking operations
- **AI Classification**: Filters out background textures, decorative maps, and non-functional map artwork
- **Word Count Validation**: OCR-based quality check rejects extractions with excessive text (>100 words, 5 retries)
- **Resolution Scaling Fix**: Corrects for Gemini's image downscaling during segmentation
- **Temp Directory Organization**: Debug files (preprocessed, red perimeter images) stored in `temp/` subdirectory
- **Comprehensive Metadata**: Tracks extraction method (extracted vs segmented) for quality analysis
- **Models**: Uses `gemini-2.0-flash` for detection/classification, `gemini-2.5-flash-image` for segmentation
- **High Reliability**: 100% success rate on clean test cases with 5 retry attempts and temperature 0.5

**MapMetadata Model:**
```python
class MapMetadata(BaseModel):
    name: str              # "Example Keep"
    chapter: Optional[str] = None  # "Chapter 1"
    page_num: int          # 1
    type: str              # "navigation_map" or "battle_map"
    source: str            # "extracted" (PyMuPDF) or "segmented" (Imagen)
```

**Usage:**
```bash
# Extract all maps from PDF
uv run python src/pdf_processing/image_asset_processing/extract_map_assets.py --pdf data/pdfs/module.pdf

# Specify chapter name for metadata
uv run python src/pdf_processing/image_asset_processing/extract_map_assets.py --pdf data/pdfs/module.pdf --chapter "Chapter 1"

# Custom output directory
uv run python src/pdf_processing/image_asset_processing/extract_map_assets.py --pdf data/pdfs/module.pdf --output custom/output/dir
```

**Output Structure:**
```
output/runs/<timestamp>/map_assets/
├── page_001_example_keep.png         # Final extracted maps
├── page_002_goblin_cave.png
├── page_005_battle_grid.png
├── maps_metadata.json
└── temp/                              # Debug files (only created if Imagen segmentation used)
    ├── page_001_example_keep_preprocessed.png
    ├── page_001_example_keep_with_red_perimeter.png
    ├── page_002_goblin_cave_preprocessed.png
    └── page_002_goblin_cave_with_red_perimeter.png
```

**Example Metadata:**
```json
{
  "extracted_at": "2025-10-26T14:52:30.869016",
  "total_maps": 4,
  "maps": [
    {
      "name": "Example Keep Small",
      "chapter": "Strongholds & Followers Test",
      "page_num": 1,
      "type": "navigation_map",
      "source": "extracted"
    }
  ]
}
```

**Performance:**
- Detection: ~2.5 minutes for 60-page PDF (parallel page processing)
- PyMuPDF extraction: ~13-15 seconds per page (with AI classification, run in parallel)
- Imagen segmentation: ~15-20 seconds per page (with 5 retries, run in parallel)
- Total: ~3-4 minutes for typical module PDF with 10 maps
- Example: Lost Mine of Phandelver (7 maps) extracted in 3:42 with 85.7% success rate

**Critical Implementation Details:**
1. **Functional Map Detection**: Uses detailed prompt to distinguish functional gameplay maps from decorative elements:
   - FUNCTIONAL MAP: Primary content is usable for gameplay (floor plans, terrain, tactical grids)
   - NOT A MAP: Maps as props in artwork, decorative elements in scene illustrations, character portraits
   - Significantly reduces false positives (10 → 7 detected pages on Lost Mine test)

2. **Background Texture Problem**: Many D&D PDFs have large background textures (e.g., 3107x4132) that are larger than actual maps. Size-based heuristics fail 100% of the time. AI classification solves this by identifying semantic content.

3. **Word Count Validation**: OCR-based quality check using pytesseract:
   - Rejects extractions with >100 words (likely included text paragraphs)
   - 5 retry attempts with temperature 0.5
   - Achieves 100% success rate on clean test cases

4. **Red Pixel Preprocessing**: Removes existing red pixels from page before sending to Imagen to avoid confusion with generated border (uses same threshold: R>200, G<50, B<50)

5. **Resolution Scaling Bug Fix**: Gemini downscales input images (e.g., 3523x4644 → 896x1152, 3.93x smaller). Red pixel detection works on downscaled image, but must scale bounding box coordinates back up before cropping original image. Without scaling, extracts wrong region.

6. **Lenient Red Pixel Detection**: Uses R>200, G<50, B<50 instead of exact RGB(255,0,0) to account for compression artifacts.

7. **Fully Parallel Processing**: Uses `asyncio.to_thread()` for blocking PyMuPDF operations to achieve true concurrency. All pages process simultaneously instead of sequentially.

8. **Temp Directory Organization**: Debug files automatically stored in `temp/` subdirectory. Detects if already in temp directory to avoid nested `temp/temp/` structure.

### Key Architecture Patterns

**pdf_to_xml.py** (main conversion engine):

- **Parallel Processing**: Uses `ThreadPoolExecutor` (max 5 workers) for both page-level and chapter-level processing
- **Text Extraction Strategy**: Two-tier fallback system
  1. First attempts embedded text extraction from PDF
  2. Falls back to local Tesseract OCR if embedded text is corrupted (checks legibility via word length heuristics)
- **AI-Powered XML Generation**: Each page uploaded to Gemini 2.5 Pro with structured prompt requesting semantic XML
- **Retry Logic**: 3 attempts per page with exponential backoff (2^attempt seconds)
- **Self-Healing XML**: If Gemini produces malformed XML, automatically sends it back to Gemini for correction with original text as reference
- **Quality Validation**:
  - Word count comparison between source PDF and generated XML (15% tolerance threshold)
  - Validates at both page-level and final chapter-level
  - Stores word frequency analysis as JSON when validation fails
- **Comprehensive Logging**: Each run preserves:
  - `intermediate_logs/<chapter>/pages/` - per-page PDFs, embedded text, OCR text, raw Gemini responses, XML attempts
  - `documents/<chapter>.xml` - final merged XML
  - `error_report.txt` - summary of all failures

**Output Directory Structure**:
```
output/runs/<timestamp>/
├── documents/
│   └── <chapter>.xml          # Final merged XML files
├── intermediate_logs/
│   └── <chapter>/
│       ├── pages/
│       │   ├── page_N.pdf
│       │   ├── page_N_embedded.txt
│       │   ├── page_N_ocr.txt (if fallback triggered)
│       │   ├── page_N_attempt_1_raw.xml
│       │   ├── page_N_corrected.xml (if malformed)
│       │   └── page_N.xml (final)
│       ├── final_unverified.xml
│       └── <chapter>_corrected.xml (if needed)
└── error_report.txt
```

### Critical Implementation Details

1. **PROJECT_ROOT Pattern**:
   - Scripts in `src/pdf_processing/` calculate project root as `os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))` (pdf_processing/ → src/ → root)
   - Scripts in `src/` calculate project root as `os.path.dirname(os.path.dirname(os.path.abspath(__file__)))` (src/ → root)

2. **Import Pattern**: Scripts in `src/pdf_processing/` add parent directory to sys.path before importing from src/:
   ```python
   import sys
   sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
   from logging_config import setup_logging
   ```

3. **Gemini Model**: Hardcoded to `gemini-2.5-pro` (see `GEMINI_MODEL_NAME` constant)

4. **XML Generation Prompt**: Instructs Gemini to use Markdown syntax for styling (`*italic*`, `**bold**`) instead of HTML tags, with specialized tags for D&D elements like `<monster>` stat blocks

5. **HTML Tag Replacement**: Post-processes Gemini output to convert any `<i>`, `<b>`, `<italic>` tags to Markdown equivalents before validation

6. **Error Handling Philosophy**:
   - Page errors mark entire chapter as failed
   - Preserves partial outputs for debugging
   - Never edits generated outputs in place—regenerate instead

7. **Chapter Boundaries**: Hardcoded in `src/pdf_processing/split_pdf.py` sections array (0-indexed page ranges with display names)

8. **XML Mixed Content Handling**: `xml_to_html.py` properly processes XML elements with both text content and child elements (e.g., `<definition>text<p>child</p></definition>`) by extracting `elem.text`, processing children, and capturing `child.tail`

9. **Heading Hierarchy Prompt**: Updated in `pdf_to_xml.py` to emphasize semantic context over font size when determining section/subsection levels

## Testing

### Test Structure

The test suite mirrors the `src/` directory structure:

```
tests/
├── conftest.py              # Shared fixtures and test configuration
├── test_main.py             # End-to-end pipeline tests (PDF → XML → HTML)
├── pdf_processing/          # Tests for src/pdf_processing/
│   ├── __init__.py
│   ├── test_split_pdf.py   # Tests for split_pdf.py
│   ├── test_pdf_to_xml.py  # Tests for pdf_to_xml.py
│   ├── test_get_toc.py     # Tests for get_toc.py (uses FULL PDF)
│   └── test_xml_to_html.py # Tests for xml_to_html.py
├── foundry/                 # Tests for src/foundry/
│   ├── __init__.py
│   ├── test_client.py       # Tests for FoundryClient API
│   ├── test_upload_script.py # Tests for upload_to_foundry.py
│   ├── test_xml_to_journal_html.py # Tests for XML to journal HTML converter
│   └── actors/              # Tests for src/foundry/actors/
│       ├── __init__.py
│       ├── test_models.py   # Tests for ParsedActorData models
│       ├── test_spell_cache.py # Tests for SpellCache
│       ├── test_converter.py # Tests for converter stub
│       ├── test_fixtures.py # Fixture validation tests
│       └── fixtures/        # Test data for actor parsing
│           ├── goblin_parsed.json  # Example Goblin ParsedActorData
│           └── mage_parsed.json    # Example Mage ParsedActorData
└── output/                  # Persistent test output (not auto-cleaned)
    └── test_runs/           # Timestamped test runs from end-to-end tests
```

### Running Tests

```bash
# Unit tests only (fast, no API calls)
uv run pytest -m "not integration and not slow"

# All tests including Gemini API integration tests
uv run pytest

# Specific test file
uv run pytest tests/pdf_processing/test_split_pdf.py

# Verbose output
uv run pytest -v

# Tests matching pattern
uv run pytest -k "test_word_count"
```

### Test Markers

- `@pytest.mark.unit`: Fast unit tests (no external dependencies)
- `@pytest.mark.integration`: Tests that make real Gemini API calls
- `@pytest.mark.slow`: Slow tests (API calls, large file processing)
- `@pytest.mark.requires_api`: Tests requiring Gemini API key
- `@pytest.mark.requires_pdf`: Tests requiring PDF files

### Key Fixtures (from `conftest.py`)

- `test_pdf_path`: Path to `Lost_Mine_of_Phandelver_test.pdf` (7 pages, for most tests)
- `full_pdf_path`: Path to full PDF (for TOC tests only)
- `test_output_dir`: Temporary directory (auto-cleaned)
- `clean_test_output`: Persistent `tests/output/` (NOT auto-cleaned)
- `check_api_key`: Verifies Gemini API key is configured
- `sample_xml_content`: Valid XML for testing
- `sample_malformed_xml`: Invalid XML for error handling tests

### Test Coverage

**PDF Processing** (`test_split_pdf.py`):
- Chapter boundary detection
- PDF page extraction and validation
- Output file creation
- Edge cases (empty PDFs, single page)
- XML element name sanitization

**XML Generation** (`test_pdf_to_xml.py`):
- XML element name sanitization (numeric prefixes)
- Word counting and frequency analysis
- Text legibility detection
- Text extraction (embedded and OCR fallback)
- XML structure validation
- Error handling and retry logic
- **Gemini API integration** (real API calls in `@pytest.mark.integration` tests)

**TOC Extraction** (`test_get_toc.py`):
- TOC structure validation (level, title, page tuples)
- Level hierarchy correctness
- Page number validity and ordering
- Expected section detection
- Page mapping and content verification
- **Note**: Uses FULL PDF (`Lost_Mine_of_Phandelver.pdf`), not test PDF

**HTML Conversion** (`test_xml_to_html.py`):
- XML to HTML content conversion
- HTML structure generation (headings, paragraphs, lists)
- Navigation link creation
- CSS styling inclusion
- Malformed XML error handling
- Multiple file conversion
- Output validation (valid HTML structure, UTF-8, viewport)

**End-to-End Pipeline** (`test_main.py`):
- Complete PDF → XML → HTML workflow
- Single-page and multi-page pipeline tests
- Timestamped test run directory creation
- Output directory structure validation
- Run isolation (separate timestamped runs don't interfere)
- Error handling throughout pipeline
- **Integration tests**: Make REAL Gemini API calls for full workflow testing

**FoundryVTT Integration** (`tests/foundry/`):
- **Journal Manager Tests** (`test_journals.py`): `JournalManager` class tests
  - Create, search, get, delete journal operations
  - `create_or_replace_journal` flow (searches, then creates/replaces)
  - UUID-based operations and normalization
  - Error handling for API failures
- **Client Tests** (`test_client.py`): `FoundryClient` delegation tests
  - Environment-based initialization (local and forge)
  - Delegation to `JournalManager`
- **Upload Script Tests** (`test_upload_script.py`): Upload workflow tests
  - XML to HTML conversion and batching
  - Upload statistics tracking
  - Error handling for failed uploads
- **Export Script Tests**: Export workflow validation
- All tests use mocked HTTP requests (no real API calls to FoundryVTT)

### Writing New Tests

Follow these patterns when adding tests:

1. **Mirror src/ structure**: Tests for `src/foo/bar.py` go in `tests/foo/test_bar.py`
2. **Use fixtures**: Import from `conftest.py` rather than creating test data
3. **Mark appropriately**: Use `@pytest.mark.integration` for API calls, `@pytest.mark.slow` for long tests
4. **Test real behavior**: Integration tests make REAL Gemini API calls (not mocked)
5. **Organize by class**: Group related tests in classes (e.g., `TestWordCounting`, `TestXMLValidation`)
6. **End-to-end tests**: Use `test_main.py` for full pipeline tests that save to timestamped `tests/output/test_runs/` directories

### Integration Test Warning

Tests marked with `@pytest.mark.integration` make **real Gemini API calls** and will:
- Consume API quota
- Cost money
- Be slow (API latency)
- Require valid API key in `.env`

Run unit tests only for fast feedback: `uv run pytest -m "not integration and not slow"`

## Coding Conventions

**General Principles:**
- **Write clean, concise code**: Prioritize readability and simplicity over cleverness
- **Keep functions focused**: Each function should do one thing well
- **Avoid unnecessary complexity**: Use straightforward solutions unless performance requires otherwise
- **Clear is better than compact**: Favor explicit, readable code over terse one-liners

From AGENTS.md:

- **Style**: PEP 8 with 4-space indentation, snake_case names, UPPER_SNAKE_CASE for constants
- **Module Naming**: Follow `verb_noun.py` pattern (e.g., `split_pdf.py`, `get_toc.py`)
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
