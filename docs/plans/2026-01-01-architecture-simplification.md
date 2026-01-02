# Architecture Simplification Design

> **Goal:** Separate concerns between pure library (`src/`) and web application (`ui/backend/`), eliminating the inverted dependency where `src/` makes HTTP calls back to the backend.

**Date:** 2026-01-01

---

## Decisions

| Decision | Choice |
|----------|--------|
| Primary use pattern | Web-first (backend owns Foundry connection) |
| Separation | Keep `src/` and `ui/backend/` separate |
| `src/foundry/` fate | Rename to `src/foundry_converters/`, keep only pure code |
| Network code location | All in `ui/backend/` |
| Relay server | Delete entirely |
| Plans location | Consolidate to `docs/plans/` |
| Virtual environments | Keep both, document clearly |
| Deep nesting | Keep `src/pdf_processing/image_asset_processing/` as-is |

---

## Current Architecture (Problem)

```
Script → FoundryClient → HTTP → FastAPI Backend → WebSocket → Foundry Module
         (src/foundry/)        (ui/backend/)       (tablewrite-assistant)
```

**Issues:**
- `src/foundry/` depends on `ui/backend/` being running (inverted dependency)
- Duplicated WebSocket logic between `src/` and `ui/backend/`
- Monolithic `main.py` (590 lines)
- Unclear which tests need backend running
- Orphaned relay server code

---

## New Architecture

```
src/                          # Pure Python library (no network calls)
  ├── Domain models
  ├── AI pipelines (Gemini)
  └── Format converters

ui/backend/                   # Web application (owns all Foundry I/O)
  ├── REST API
  ├── WebSocket to Foundry
  └── Imports from src/

CLI scripts                   # Call backend HTTP API or use src/ directly
```

---

## New Directory Structure

### `src/` (Pure Library)

```
src/
├── actors/                       # Actor generation pipeline (Gemini AI)
│   ├── __init__.py
│   ├── models.py                 # StatBlock, NPC models
│   ├── orchestrate.py            # AI pipeline orchestration
│   ├── extract_stat_blocks.py
│   ├── parse_stat_blocks.py
│   ├── extract_npcs.py
│   ├── generate_actor_file.py
│   ├── generate_actor_biography.py
│   ├── process_actors.py
│   └── statblock_parser.py
│
├── foundry_converters/           # Convert domain models → FoundryVTT format
│   ├── __init__.py               # Exports all converters
│   ├── actors/
│   │   ├── __init__.py
│   │   ├── converter.py          # ParsedActorData → FoundryVTT actor JSON
│   │   ├── models.py             # ParsedActorData, Attack, Trait, Spell, etc.
│   │   └── parser.py             # Raw stat block → ParsedActorData
│   ├── journals/
│   │   ├── __init__.py
│   │   └── converter.py          # Journal → FoundryVTT pages format
│   └── scenes/
│       ├── __init__.py
│       └── converter.py          # Scene → FoundryVTT scene format
│
├── models/                       # Core domain models
│   ├── __init__.py
│   ├── xml_document.py           # XMLDocument - immutable parsed XML
│   └── journal.py                # Journal - mutable semantic hierarchy
│
├── pdf_processing/               # PDF → XML pipeline
│   ├── __init__.py
│   ├── split_pdf.py
│   ├── pdf_to_xml.py
│   ├── pdf_to_html.py
│   ├── xml_to_html.py
│   ├── get_toc.py
│   ├── valid_xml_tags.py
│   └── image_asset_processing/   # Map extraction
│       ├── __init__.py
│       ├── models.py
│       ├── detect_maps.py
│       ├── extract_maps.py
│       ├── extract_map_assets.py
│       ├── segment_maps.py
│       ├── preprocess_image.py
│       └── validate_segmentation.py
│
├── scene_extraction/             # Scene artwork generation
│   ├── __init__.py
│   ├── models.py
│   ├── extract_context.py
│   ├── identify_scenes.py
│   ├── generate_artwork.py
│   └── create_gallery.py
│
├── wall_detection/               # Wall detection for maps
│   ├── polygonize.py
│   └── redline_walls.py
│
├── util/                         # Shared utilities
│   ├── __init__.py
│   ├── gemini.py
│   └── parallel_image_gen.py
│
├── api.py                        # Public API (thin HTTP client to backend)
└── logging_config.py
```

### `ui/backend/` (Web Application)

```
ui/backend/
├── app/
│   ├── __init__.py
│   ├── main.py                   # ~50 lines: app setup, middleware, router imports
│   ├── config.py
│   │
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── chat.py               # Chat endpoints
│   │   ├── actors.py             # /api/foundry/actor/* and /api/actors/create
│   │   ├── journals.py           # /api/foundry/journal/*
│   │   ├── search.py             # /api/foundry/search, /api/foundry/compendium
│   │   ├── files.py              # /api/foundry/files
│   │   └── health.py             # /health, /, /api/foundry/status
│   │
│   ├── websocket/
│   │   ├── __init__.py           # Exports manager, operations
│   │   ├── manager.py            # ConnectionManager singleton
│   │   ├── endpoint.py           # /ws/foundry WebSocket route
│   │   ├── protocol.py           # Message types, response dataclasses
│   │   └── operations.py         # push_actor, fetch_actor, search_items, etc.
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── actor_service.py      # Orchestrates: src/ converters + WebSocket ops
│   │   ├── gemini_service.py     # Gemini chat logic
│   │   ├── spell_cache.py        # Spell lookup cache (moved from src/)
│   │   └── icon_cache.py         # Icon lookup cache (moved from src/)
│   │
│   ├── tools/                    # Gemini function calling tools
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── registry.py
│   │   ├── actor_creator.py
│   │   ├── image_generator.py
│   │   ├── journal_creator.py
│   │   └── scene_creator.py
│   │
│   └── models/                   # API request/response models
│       └── ...
│
├── tests/                        # All backend tests (need backend/Foundry)
│   ├── conftest.py
│   ├── routers/
│   ├── websocket/
│   ├── services/
│   └── integration/
│
├── requirements.txt
└── pytest.ini
```

---

## File Migration Plan

### Files to KEEP (move to `src/foundry_converters/`)

| Current Location | New Location |
|------------------|--------------|
| `src/foundry/actors/converter.py` | `src/foundry_converters/actors/converter.py` |
| `src/foundry/actors/parser.py` | `src/foundry_converters/actors/parser.py` |
| `src/foundry/actors/models.py` | `src/foundry_converters/actors/models.py` |
| `src/foundry/xml_to_journal_html.py` | `src/foundry_converters/journals/converter.py` |

### Files to DELETE (logic moves to backend)

| File | Reason |
|------|--------|
| `src/foundry/client.py` | HTTP calls → backend owns connection |
| `src/foundry/journals.py` | HTTP calls → `ui/backend/app/websocket/operations.py` |
| `src/foundry/folders.py` | HTTP calls → backend |
| `src/foundry/scenes.py` | HTTP calls → backend |
| `src/foundry/icon_cache.py` | HTTP calls → `ui/backend/app/services/icon_cache.py` |
| `src/foundry/actors/manager.py` | HTTP calls → backend |
| `src/foundry/actors/spell_cache.py` | HTTP calls → `ui/backend/app/services/spell_cache.py` |
| `src/foundry/items/manager.py` | HTTP calls → backend |
| `src/foundry/items/fetch.py` | HTTP calls → backend |
| `src/foundry/items/websocket_fetch.py` | Already duplicated in backend |
| `src/foundry/items/deduplicate.py` | Move to backend if needed |
| `src/foundry/actors/deduplicate.py` | Move to backend if needed |
| `src/foundry/upload_journal_to_foundry.py` | Script → use backend API |
| `src/foundry/export_from_foundry.py` | Script → use backend API |

### Directories to DELETE

| Directory | Reason |
|-----------|--------|
| `relay-server/` | Replaced by WebSocket, no longer needed |
| `plans/` | Consolidated to `docs/plans/` |

---

## Public API (`src/api.py`)

Simplified to thin HTTP client:

```python
"""Public API - requires backend running at BACKEND_URL."""

import os
import requests
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from pathlib import Path

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


class APIError(Exception):
    """Raised when API operations fail."""
    pass


@dataclass
class ActorCreationResult:
    foundry_uuid: str
    name: str
    challenge_rating: float
    output_dir: Optional[Path] = None


def create_actor(
    description: str,
    challenge_rating: Optional[float] = None
) -> ActorCreationResult:
    """Create a D&D actor from natural language description."""
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/actors/create",
            json={
                "description": description,
                "challenge_rating": challenge_rating
            },
            timeout=120
        )
        response.raise_for_status()
        data = response.json()

        return ActorCreationResult(
            foundry_uuid=data["foundry_uuid"],
            name=data["name"],
            challenge_rating=data["challenge_rating"],
            output_dir=Path(data["output_dir"]) if data.get("output_dir") else None
        )
    except requests.exceptions.RequestException as e:
        raise APIError(f"Failed to create actor: {e}") from e


# Similar pattern for extract_maps, process_pdf_to_journal, etc.
```

**For offline/standalone work (no Foundry needed):**

```python
# Direct library usage
from actors.orchestrate import create_actor_from_description
from foundry_converters.actors.converter import convert_to_foundry

result = create_actor_from_description("A goblin warrior")
foundry_json = convert_to_foundry(result.parsed_actor_data)
# User manually imports JSON into Foundry
```

---

## Testing Strategy

### Test Organization

```
tests/                            # Tests for src/ (pure library)
├── actors/                       # Gemini API needed, NO backend needed
├── foundry_converters/           # Pure unit tests, NO network
├── models/                       # Pure unit tests
├── pdf_processing/               # Gemini API needed, NO backend needed
├── scene_extraction/             # Gemini API needed, NO backend needed
└── api/                          # Needs backend running

ui/backend/tests/                 # Tests for backend (need backend + maybe Foundry)
├── routers/                      # HTTP endpoint tests
├── websocket/                    # WebSocket tests (need Foundry)
├── services/                     # Service layer tests
└── integration/                  # Full E2E (need Foundry)
```

### Testing Integrity Rule

**CRITICAL: Integration tests MUST use live connections. No mocking in integration tests.**

| Test Type | What's Real | What's Mocked |
|-----------|-------------|---------------|
| Unit tests (`foundry_converters/`) | N/A - pure functions | Nothing |
| Unit tests (`actors/`) | Gemini (optional mock for speed) | Nothing required |
| Integration tests | **Everything** | **Nothing** |

### Enforcement

1. **Integration tests fail loudly** if connection missing:

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_actor_in_foundry():
    from foundry import FoundryClient

    client = FoundryClient()

    # FAIL with actionable message - never skip silently
    assert client.is_connected, \
        "Foundry not connected - start backend and connect Foundry module"

    result = await client.actors.create({"name": "Test", "type": "npc"})
    assert result.success, f"Failed to create actor: {result.error}"

    # Cleanup
    await client.actors.delete(result.uuid)
```

2. **No `@pytest.mark.skipif` for missing connections** - tests must fail

3. **Audit during migration**: Every test that moves gets reviewed:
   - Integration markers preserved
   - No new mocks added
   - Live assertions remain

### Test Workflow

```bash
# Development (no Foundry needed)
pytest tests/ -m "not integration"     # Pure library tests

# With backend running
pytest tests/api/                       # API client tests

# Full integration (backend + Foundry)
cd ui/backend && pytest                 # All backend tests
pytest --full                           # Everything
```

---

## Cleanup Tasks

### Delete

| Item | Action |
|------|--------|
| `relay-server/` | Delete entire directory |
| `plans/` | Move contents to `docs/plans/archive/`, delete directory |

### Add to `.gitignore`

```gitignore
# Root clutter
repomix-output.xml
tree.txt
parallel.env
test_output.log
```

### Document

Add to `CLAUDE.md` or `README.md`:

```markdown
## Virtual Environments

This project uses two virtual environments:

- **Root `.venv/`**: For `src/` library development and scripts
  ```bash
  source .venv/bin/activate
  uv run pytest tests/
  ```

- **`ui/backend/.venv/`**: For FastAPI backend
  ```bash
  cd ui/backend
  source .venv/bin/activate
  uvicorn app.main:app --reload
  ```
```

---

## Implementation Order

### Phase 1: Create New Structure (non-breaking)

1. [ ] Create `src/foundry_converters/` directory
2. [ ] Copy pure files from `src/foundry/` to `src/foundry_converters/`
3. [ ] Update imports in copied files
4. [ ] Add `__init__.py` exports
5. [ ] Write tests for `src/foundry_converters/`

### Phase 2: Reorganize Backend

6. [ ] Split `ui/backend/app/main.py` into routers
7. [ ] Create `ui/backend/app/services/` layer
8. [ ] Move caches (spell_cache, icon_cache) to services
9. [ ] Update imports throughout backend
10. [ ] Verify all backend tests pass

### Phase 3: Update src/ Consumers

11. [ ] Update `src/actors/orchestrate.py` to use `foundry_converters`
12. [ ] Update `src/api.py` to be thin HTTP client
13. [ ] Update scripts to use new imports
14. [ ] Verify all src tests pass

### Phase 4: Delete Old Code

15. [ ] Delete `src/foundry/` (now replaced by `foundry_converters`)
16. [ ] Delete `relay-server/`
17. [ ] Move `plans/` to `docs/plans/archive/`
18. [ ] Update `.gitignore`

### Phase 5: Test Migration

19. [ ] Move Foundry integration tests to `ui/backend/tests/`
20. [ ] Audit all moved tests for mocking violations
21. [ ] Verify `pytest --full` passes
22. [ ] Update CLAUDE.md with new structure

---

## Success Criteria

1. **Clean separation**: `src/` has zero network calls (except Gemini API)
2. **Single connection owner**: Only `ui/backend/` talks to Foundry
3. **Tests pass**: `pytest --full` passes with live Foundry
4. **No mocking in integration tests**: All integration tests use real connections
5. **Documentation updated**: CLAUDE.md reflects new structure
