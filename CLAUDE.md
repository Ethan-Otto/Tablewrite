# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

D&D module converter: transforms official D&D PDFs into structured XML assets for FoundryVTT. Uses Google's Gemini 2.5 Pro for AI-powered document analysis.

## Quick Start

```bash
# Install dependencies
uv venv && source .venv/bin/activate && uv pip sync

# Required .env configuration
GeminiImageAPI=<your_gemini_api_key>
FOUNDRY_URL=http://localhost:30000
FOUNDRY_API_KEY=<your_foundry_api_key>
FOUNDRY_CLIENT_ID=<your_client_id>

# Run full pipeline
uv run python scripts/full_pipeline.py --journal-name "Lost Mine of Phandelver"

# Start backend (for Foundry integration)
cd ui/backend && uvicorn app.main:app --reload --port 8000
```

## Architecture

```
src/
├── api.py                   # Public API (create_actor, extract_maps, create_scene, etc.)
├── config.py                # PROJECT_ROOT, SRC_DIR, get_env() - centralized config
├── exceptions.py            # DNDModuleError, ConversionError, FoundryError, etc.
├── caches/                  # SpellCache, IconCache
├── actor_pipeline/          # Actor creation: orchestrate.py, models.py, parse/extract
├── foundry_converters/      # Pure conversion (no network): actors/, journals/
├── foundry/                 # Network operations: client.py, journals.py, actors/
├── models/                  # XMLDocument, Journal (core data models)
├── pdf_processing/          # PDF extraction, xml conversion, map extraction
├── scenes/                  # Scene creation pipeline
├── scene_extraction/        # Scene artwork generation
├── wall_detection/          # Wall detection for battle maps
└── util/                    # Shared utilities

ui/backend/                  # FastAPI backend with WebSocket to Foundry
foundry-module/              # FoundryVTT module (Tablewrite Assistant)
```

### Key Patterns

**Centralized Config** (`src/config.py`):
```python
from config import PROJECT_ROOT, SRC_DIR, get_env
from caches import SpellCache
from exceptions import ConversionError, FoundryError
```

**Exception Hierarchy** (`src/exceptions.py`):
- `DNDModuleError` → base for all project errors
- `ConversionError` → PDF/XML conversion failures
- `FoundryError` → FoundryVTT communication errors
- `ConfigurationError` → missing config/environment
- `ValidationError` → data validation failures

### Data Flow

```
PDF → XML (Gemini) → XMLDocument → Journal → FoundryVTT
                                     ↓
                              Actors, Scenes, Maps
```

**Core Models:**
- `XMLDocument` (`src/models/xml_document.py`): Immutable, page-based structure from Gemini XML output
- `Journal` (`src/models/journal.py`): Mutable, semantic hierarchy (Chapter → Section → Subsection)

**Pydantic Patterns** (v2):
```python
from pydantic import BaseModel, ConfigDict

class ImmutableModel(BaseModel):
    model_config = ConfigDict(frozen=True)  # Immutable

class MutableModel(BaseModel):
    pass  # Default is mutable

# Serialization
json_str = model.model_dump_json(indent=2)
new_model = model.model_copy(update={"field": "new_value"})
```

## Public API

**Location:** `src/api.py`

```python
from api import create_actor, extract_maps, process_pdf_to_journal, create_scene, APIError

result = create_actor("A kobold scout", challenge_rating=0.5)  # → ActorCreationResult
maps = extract_maps("data/pdfs/module.pdf", chapter="Chapter 1")  # → MapExtractionResult
journal = process_pdf_to_journal("module.pdf", "Module Name")  # → JournalCreationResult
scene = create_scene("maps/castle.webp")  # → SceneCreationResult
# All raise APIError on failure
```

**Return Types:**
- `ActorCreationResult`: UUID, name, CR, output_dir, timestamp
- `MapExtractionResult`: maps list, output_dir, total_maps, timestamp
- `JournalCreationResult`: UUID, name, output_dir, chapter_count, timestamp
- `SceneCreationResult`: UUID, name, wall_count, grid_size, timestamp

## Backend & Foundry Integration

**Backend Location:** `ui/backend/`

**Key Endpoints:**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/foundry/status` | GET | Check WebSocket connection status |
| `/api/foundry/actor` | POST | Create actor from FoundryVTT JSON |
| `/api/foundry/actor/{uuid}` | GET | Fetch actor by UUID |
| `/api/foundry/actor/{uuid}` | DELETE | Delete actor by UUID |
| `/api/foundry/actor/{uuid}/items` | POST | Add compendium items to actor |
| `/api/foundry/scene` | POST | Create scene with walls and grid |
| `/api/foundry/journal` | POST | Create journal entry |
| `/api/foundry/search` | GET | Search compendiums |
| `/api/actors/create` | POST | Create actor from description (AI pipeline) |

**Foundry Module:** `foundry-module/tablewrite-assistant/`
- Connects to backend WebSocket on startup
- Executes Foundry API calls (Actor.create, Scene.create, JournalEntry.create)
- Shows notifications when content is created

### Actor Pipeline

**Module:** `src/actor_pipeline/`

**Workflow:**
```
Natural Language Description → Generate Stat Block (Gemini) → Parse to StatBlock
    → Parse to ParsedActorData → Convert to FoundryVTT Format → Upload
```

**Usage:**
```python
from actor_pipeline.orchestrate import create_actor_from_description_sync

result = create_actor_from_description_sync("A red dragon wyrmling", challenge_rating=2.0)
# → ActorCreationResult with foundry_uuid, output_dir, stat_block, parsed_actor_data
```

**SpellCache** (`src/caches/spell_cache.py`):
```python
from caches import SpellCache

cache = SpellCache()
cache.load()  # Fetches all spells via REST API
uuid = cache.get_spell_uuid("Fireball")
```

### Async/Sync Pattern

All orchestration functions have both async and sync versions:
```python
# Async (for FastAPI/server usage)
result = await create_actor_from_description("A goblin", challenge_rating=0.25)

# Sync wrapper (for CLI/scripts)
result = create_actor_from_description_sync("A goblin", challenge_rating=0.25)

# Batch operations use asyncio.gather with return_exceptions=True
results = await create_actors_batch(descriptions, challenge_ratings)
```

### Output Directory Conventions

```
output/runs/<YYYYMMDD_HHMMSS>/
├── actors/                      # Actor creation outputs
│   ├── 01_raw_stat_block.txt
│   ├── 02_stat_block.json
│   ├── 03_parsed_actor_data.json
│   └── 04_foundry_actor.json
├── documents/                   # XML chapter files
├── scene_artwork/               # Generated scene images
├── map_assets/                  # Extracted maps + maps_metadata.json
└── intermediate_logs/           # Debug outputs
```

**Naming**: Prefix files with numbers (`01_`, `02_`) for processing order.

### Logging

```python
from logging_config import setup_logging, get_run_logger

# General logger
logger = setup_logging(__name__)

# Run-specific logger (writes to <run_dir>/<script_name>.log)
logger = get_run_logger("pdf_to_xml", run_dir)
```

## Testing

### Running Tests

```bash
pytest                                      # Smoke tests only (~1 min, 25 tests)
pytest --full                               # Full suite (~5 min parallel)
pytest --full -n auto --dist loadscope      # Parallel execution (fastest)
pytest -m "not integration and not slow"    # Unit tests only
pytest -m integration                       # Integration tests (cost money)
```

**Important:** Always use `--dist loadscope` with `-n auto`. This groups tests by fixture scope so session-scoped fixtures run once per group instead of once per worker.

### Test Structure

```
tests/
├── conftest.py              # Shared fixtures
├── actor_pipeline/          # Tests for src/actor_pipeline/
├── foundry_converters/      # Tests for src/foundry_converters/
├── foundry/                 # Tests for src/foundry/
├── models/                  # Tests for src/models/
├── pdf_processing/          # Tests for src/pdf_processing/
├── scenes/                  # Tests for src/scenes/
└── api/                     # Tests for src/api.py
```

### Test Markers

- `@pytest.mark.smoke` - Critical smoke tests (default run, ~25 tests)
- `@pytest.mark.integration` - Tests requiring real API calls AND/OR Foundry connections (consume quota, cost money)
- `@pytest.mark.slow` - Long-running tests
- `@pytest.mark.playwright` - Browser tests (cannot run in parallel)
- `@pytest.mark.requires_api` - Tests requiring Gemini API key
- `@pytest.mark.requires_foundry` - Tests requiring FoundryVTT running
- `@pytest.mark.map` - Map extraction tests
- `@pytest.mark.flaky` - May fail intermittently (auto-retries enabled)

### CI/Auto-Escalation Behavior

- **CI environment**: Sets `CI=true` → runs `not integration and not slow` (no Foundry available)
- **AUTO_ESCALATE**: Default `true` → shows full error details, waits 3s, then runs full suite
- **Disable escalation**: `AUTO_ESCALATE=false pytest` → stops after showing errors
- **Skip Foundry init**: `--skip-foundry-init` flag or `SKIP_FOUNDRY_INIT=true`

### REQUIRED: Full Test Suite Before PR

**The full test suite (`pytest --full`) MUST pass before creating a PR.**

```bash
# Before creating any PR, run:
uv run pytest --full -x  # -x stops on first failure

# Requirements:
# 1. Backend running: cd ui/backend && uvicorn app.main:app --reload
# 2. FoundryVTT running with Tablewrite module connected
# 3. Valid .env with API keys
```

### Integration Test Requirements

**Integration tests MUST FAIL (not skip) if Foundry is not connected:**

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_actor():
    from foundry import FoundryClient

    client = FoundryClient()

    # FAIL with actionable message - never skip silently
    assert client.is_connected, "Foundry not connected - start backend and connect Foundry module"

    result = await client.actors.create({"name": "Test", "type": "npc"})
    assert result.success, f"Failed to create actor: {result.error}"
```

### Round-Trip Integration Tests

**REQUIRED:** All features that create Foundry resources MUST have round-trip tests:

1. **Create** the resource in Foundry (in a `/tests` folder)
2. **Fetch** the resource back from Foundry
3. **Verify** the fetched data matches what was sent

### MANDATORY: Test Resources Use /tests Folder

**All integration tests that create Foundry resources MUST store them in a `/tests` folder.**

**Backend provides helpers in `ui/backend/tests/conftest.py`:**
```python
# Session-scoped fixture - creates /tests folders for Actor, Scene, JournalEntry
@pytest.fixture(scope="session")
def test_folders(ensure_foundry_connected):
    # Returns: {"Actor": "folder_id", "Scene": "folder_id", "JournalEntry": "folder_id"}

# Helper function for async tests
async def get_or_create_test_folder(folder_type: str) -> str:
    # folder_type: "Actor", "Scene", or "JournalEntry"
    # Returns folder ID
```

**Example round-trip test:**
```python
from tests.conftest import get_or_create_test_folder

@pytest.mark.integration
@pytest.mark.asyncio
async def test_actor_roundtrip():
    """Create actor in /tests folder, fetch it back, verify data."""
    folder_id = await get_or_create_test_folder("Actor")

    # Create in /tests folder
    result = await create_actor({
        "name": "Test Goblin",
        "type": "npc",
        "folder": folder_id,  # REQUIRED: Put in /tests folder
        ...
    })
    assert result.success, f"Create failed: {result.error}"
    actor_uuid = result.uuid

    # Fetch back
    fetched = await get_actor(actor_uuid)
    assert fetched.success, f"Fetch failed: {fetched.error}"

    # Verify critical fields match
    assert fetched.entity["name"] == "Test Goblin"
    assert fetched.entity["type"] == "npc"
```

### Key Fixtures (from `conftest.py`)

- `test_pdf_path`: `Lost_Mine_of_Phandelver_test.pdf` (7 pages)
- `full_pdf_path`: Full PDF (for TOC tests only)
- `test_output_dir`: Temporary directory (auto-cleaned)
- `sample_xml_content`: Valid XML for testing
- `check_api_key`: Ensures Gemini API key is available

### Writing New Tests

1. **Mirror src/ structure**: Tests for `src/foo/bar.py` go in `tests/foo/test_bar.py`
2. **Use fixtures**: Import from `conftest.py`
3. **Mark appropriately**: Use `@pytest.mark.integration` for API calls
4. **Test real behavior**: Integration tests make REAL Gemini API calls (not mocked)
5. **REQUIRED**: Every new feature MUST have an integration test with real data

### Fixture Scope Guidelines

- **Session-scoped**: API keys, PDF paths, Foundry connection, test folders
- **Module-scoped**: Expensive Gemini API results (share across test file)
- **Function-scoped**: Temp directories, test-specific outputs

```python
# Share expensive API calls at module level
@pytest.fixture(scope="module")
def shared_stat_blocks(check_api_key, sample_chapter_path):
    """Parse stat blocks once, share across all tests in module."""
    return extract_and_parse_stat_blocks(str(sample_chapter_path))
```

## Common Commands

```bash
# Pipeline steps
uv run src/pdf_processing/split_pdf.py              # Split PDF into chapters
uv run src/pdf_processing/pdf_to_xml.py             # Convert to XML
uv run src/foundry/upload_to_foundry.py             # Upload to Foundry
uv run python scripts/generate_scene_art.py         # Generate scene artwork

# Map extraction
uv run python src/pdf_processing/image_asset_processing/extract_map_assets.py --pdf data/pdfs/module.pdf

# Utilities
uv run python scripts/delete_all_actors.py --yes   # Clean up actors
python tests/foundry_init.py --force-refresh        # Reconnect Foundry

# Restart backend
lsof -ti :8000 | xargs kill -9; cd ui/backend && uvicorn app.main:app --reload --port 8000 &
```

## Coding Conventions

- PEP 8, 4-space indent, snake_case, f-strings
- Use `config.PROJECT_ROOT` not `os.path.dirname` chains
- Use `from exceptions import ...` for error handling
- Use `from caches import SpellCache` for caches
- Clear > compact, simple > clever

## Commit Style

- Short, imperative mood summaries
- Group related changes
- Copy `.env` when creating new worktree
