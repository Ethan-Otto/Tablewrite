# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Branch: document_cleanup

**Status:** Ready for public release

**Public repo:** https://github.com/Ethan-Otto/Tablewrite

**What was done:**
- Removed proprietary content from git history (PDFs, adventure XML fixtures, battlemaps)
- Created generic test fixtures (`tests/fixtures/xml/sample_adventure.xml`)
- Updated tests to use generic content
- Purged sensitive files (parallel.env, .env.swp) from history
- Released Tablewrite Assistant v0.1.2

**Remotes:**
- `origin` → private repo (full history, local use only)
- `public` → https://github.com/Ethan-Otto/Tablewrite (clean history)

**To push changes:** `git push public document_cleanup:main`

## Project Overview

Converts PDF modules into FoundryVTT modules. Generate and edit FoundryVTT objects using AI-powered document analysis (Google Gemini 2.5 Pro).

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
from api import create_actor, create_scene, APIError

result = create_actor("A kobold scout", challenge_rating=0.5)  # → ActorCreationResult
scene = create_scene("maps/castle.webp")  # → SceneCreationResult
# All raise APIError on failure
```

**Return Types:**
- `ActorCreationResult`: UUID, name, CR, output_dir, timestamp
- `SceneCreationResult`: UUID, name, wall_count, grid_size, timestamp

**For PDF Processing:** Use Module tab UI or `scripts/full_pipeline.py`
**For Map Extraction:** Import directly from `pdf_processing.image_asset_processing.extract_map_assets`

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

### Foundry Connection Management

**IMPORTANT:** When Foundry needs to be refreshed, reconnected, or logged in, Claude MUST run `python tests/foundry_init.py --force-refresh` automatically. Never ask the user to manually refresh Foundry - always use the foundry_init script.

```bash
# Refresh/reconnect Foundry connection (Claude should run this automatically)
python tests/foundry_init.py --force-refresh
```

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
./scripts/run_tests.sh                      # Full suite, parallel (recommended)
./scripts/run_tests.sh -k "test_name"       # Run specific test pattern

pytest                                      # Smoke tests only (~1 min, 25 tests)
pytest --full                               # Full suite (~7 min parallel)
pytest --full -n auto --dist loadscope      # Parallel execution (fastest)
pytest -m "not integration and not slow"    # Unit tests only
pytest -m integration                       # Integration tests (cost money)
```

### Test Logging

All pytest output is written to log files in real-time:

| File | Contents |
|------|----------|
| `test.log` | Symlink to most recent test log |
| `tests/logs/test_YYYYMMDD_HHMMSS.log` | Timestamped log files (one per run) |
| `test-results.xml` | JUnit XML report for CI integration |

**Log format:**
```
======================================================================
TEST SESSION START: 2026-01-28 10:30:45
======================================================================
platform darwin -- Python 3.13.5
rootdir: /path/to/project
RUNNING: tests/models/test_example.py::TestClass::test_method
  PASSED: tests/models/test_example.py::TestClass::test_method (0.02s)
...
======================================================================
TEST SESSION END: 2026-01-28 10:31:15
TOTAL DURATION: 30.0s
======================================================================
```

To tail logs in real-time during test runs:
```bash
tail -f test.log
```

To view previous test runs:
```bash
ls -la tests/logs/
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

## Foundry Module Versioning

- Use patch increments (0.0.1) for module releases: 0.2.0 → 0.2.1 → 0.2.2
- Update version in `foundry-module/tablewrite-assistant/module.json`
- Create GitHub release with tag matching version (e.g., `v0.2.1`)

## Playwright Testing for FoundryVTT

Use the `FoundrySession` helper for E2E testing. Located at:
`foundry-module/tablewrite-assistant/scripts/feedback/foundry_helper.py`

### Parallel Playwright Tests (User Pool)

Playwright tests can run in parallel using a pool of 5 FoundryVTT users (Testing1-Testing5). The `playwright_user` fixture manages this automatically:

```python
@pytest.mark.playwright
def test_something(playwright_user):
    with FoundrySession(headless=True, user=playwright_user) as session:
        session.goto_tablewrite()
        # ...
```

**How it works:**
- Up to 5 Playwright tests run concurrently (one per user)
- 6th+ tests wait (up to 5 min) for a user to become available
- Non-Playwright tests run freely in parallel with all workers
- Uses file locks in `tests/.playwright_locks/` for coordination

**Requirements:**
- 5 users in FoundryVTT: Testing1, Testing2, Testing3, Testing4, Testing5
- All users must have permission to join the game session

### Using FoundrySession Helper

```python
# Add helper to path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "foundry-module/tablewrite-assistant/scripts/feedback"))

from foundry_helper import FoundrySession

# Basic usage - headless=False for debugging, use playwright_user fixture in tests
with FoundrySession(headless=False, user="Testing1") as session:
    # Navigate to Tablewrite tab
    session.goto_tablewrite()

    # Send a message and wait for response
    session.send_message("Create a goblin", wait=30)

    # Get response
    response_text = session.get_message_text()
    response_html = session.get_message_html()

    # Take screenshot
    session.screenshot("/tmp/result.png")

    # Check tab switching works
    results = session.check_tab_switching()
    print(f"Tab switching: {results}")
```

### Quick One-Liners

```python
from foundry_helper import quick_screenshot, test_message

# Take screenshot of current state
quick_screenshot("/tmp/foundry.png")

# Send message and get response
result = test_message("Create a goblin scout")
print(result['text'])
```

### FoundrySession Methods

| Method | Description |
|--------|-------------|
| `goto_tablewrite()` | Click Tablewrite tab |
| `goto_chat()` | Click native Chat tab |
| `send_message(text, wait=3)` | Send message, wait for response |
| `screenshot(path, selector="#sidebar")` | Take screenshot |
| `get_message_text()` | Get latest assistant message text |
| `get_message_html()` | Get latest assistant message HTML |
| `get_all_messages()` | Get all messages as list |
| `check_tab_switching()` | Verify tab visibility |

### Raw Playwright (for debugging)

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page(viewport={'width': 1920, 'height': 1080})

    # Capture console
    page.on("console", lambda msg: print(f"[{msg.type}] {msg.text}"))

    page.goto("http://localhost:30000")
    page.wait_for_load_state('networkidle')

    # Check module status
    module_info = page.evaluate('''() => {
        const mod = game.modules.get('tablewrite-assistant');
        return mod ? { id: mod.id, active: mod.active } : null;
    }''')
    print(f"Module: {module_info}")

    browser.close()
```

### Key Selectors for FoundryVTT

| Element | Selector |
|---------|----------|
| Join form | `#join-game` |
| User dropdown | `select[name="userid"]` |
| Join button | `button[name="join"]` |
| Sidebar | `#sidebar` |
| Sidebar tabs | `#sidebar-tabs` |
| Tab by name | `[data-tab="tablewrite"]` |
| Chat tab | `[data-tab="chat"]` |

### Checking Module Status via JS

```python
# Check if module is loaded and active
module_info = page.evaluate('''() => {
    const mod = game.modules.get('tablewrite-assistant');
    return mod ? { id: mod.id, active: mod.active, title: mod.title } : null;
}''')

# Check registered hooks
hooks = page.evaluate('''() => {
    return Object.keys(Hooks.events || {}).filter(k => k.includes('Sidebar'));
}''')
```

### Symlink for Development

The module must be symlinked to Foundry's modules directory:

```bash
# Check current symlink
ls -la "/Users/ethanotto/Library/Application Support/FoundryVTT/Data/modules/tablewrite-assistant"

# Update symlink for worktree development
rm "/Users/ethanotto/Library/Application Support/FoundryVTT/Data/modules/tablewrite-assistant"
ln -s "$(pwd)/foundry-module/tablewrite-assistant" "/Users/ethanotto/Library/Application Support/FoundryVTT/Data/modules/tablewrite-assistant"

# Restart Foundry or refresh world after symlink change
```

## Context Management

> *"One Task, One Chat"*

| Scenario | Action |
|----------|--------|
| New feature | New chat |
| Bug fix (unrelated) | `/clear` then new task |
| Research vs implementation | Separate chats |
| 20+ turns elapsed | Start fresh |

## Claude Code Plugins

### Context7 - Live Documentation

Gives Claude access to up-to-date library documentation, solving the training cutoff problem.

```bash
claude mcp add context7 -- npx -y @upstash/context7-mcp@latest
```

**Usage:** Ask Claude to use Context7 for current docs:
```
Using context7, show me the Next.js 15 cache API
```

### Code-Simplifier - Clean Code Agent

Official Anthropic plugin that simplifies and refines code for clarity without changing functionality. Reduces token usage 20-30%.

```bash
claude plugin install code-simplifier
```

**Usage:** Run after implementing features to clean up code:
```
/code-simplifier
```

## References

- [Claude Code Mastery Guide](https://thedecipherist.github.io/claude-code-mastery/) - Comprehensive guide for Claude Code best practices
