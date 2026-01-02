# Architecture Simplification Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Separate concerns between pure library (`src/`) and web application (`ui/backend/`), eliminating the inverted dependency where `src/` makes HTTP calls back to the backend.

**Architecture:** Create `src/foundry_converters/` containing only pure conversion logic (no network). Move all Foundry I/O to `ui/backend/`. Split monolithic `main.py` into focused routers.

**Tech Stack:** Python 3.11, FastAPI, Pydantic, pytest

---

## Phase 1: Create foundry_converters Module (Non-Breaking)

### Task 1.1: Create Directory Structure

**Files:**
- Create: `src/foundry_converters/__init__.py`
- Create: `src/foundry_converters/actors/__init__.py`
- Create: `src/foundry_converters/journals/__init__.py`
- Create: `src/foundry_converters/scenes/__init__.py`

**Step 1: Create the directory structure**

```bash
mkdir -p src/foundry_converters/actors
mkdir -p src/foundry_converters/journals
mkdir -p src/foundry_converters/scenes
```

**Step 2: Create empty __init__.py files**

Create `src/foundry_converters/__init__.py`:
```python
"""FoundryVTT format converters.

Pure conversion logic for transforming domain models to FoundryVTT format.
No network calls - all I/O is handled by ui/backend/.
"""

from .actors import convert_to_foundry, ParsedActorData, Attack, Trait
from .journals import convert_xml_to_journal_data

__all__ = [
    "convert_to_foundry",
    "ParsedActorData",
    "Attack",
    "Trait",
    "convert_xml_to_journal_data",
]
```

Create `src/foundry_converters/actors/__init__.py`:
```python
"""Actor conversion to FoundryVTT format."""

from .converter import convert_to_foundry
from .models import (
    ParsedActorData,
    Attack,
    Trait,
    Multiattack,
    Spell,
    DamageFormula,
    SavingThrow,
    AttackSave,
    InnateSpellcasting,
    InnateSpell,
    SkillProficiency,
    DamageModification,
)
from .parser import parse_stat_block_to_actor

__all__ = [
    "convert_to_foundry",
    "parse_stat_block_to_actor",
    "ParsedActorData",
    "Attack",
    "Trait",
    "Multiattack",
    "Spell",
    "DamageFormula",
    "SavingThrow",
    "AttackSave",
    "InnateSpellcasting",
    "InnateSpell",
    "SkillProficiency",
    "DamageModification",
]
```

Create `src/foundry_converters/journals/__init__.py`:
```python
"""Journal conversion to FoundryVTT format."""

from .converter import convert_xml_to_journal_data

__all__ = ["convert_xml_to_journal_data"]
```

Create `src/foundry_converters/scenes/__init__.py`:
```python
"""Scene conversion to FoundryVTT format."""

# Placeholder - scene converter to be added
__all__ = []
```

**Step 3: Verify structure exists**

Run: `ls -la src/foundry_converters/*/`
Expected: Three directories with __init__.py files

**Step 4: Commit**

```bash
git add src/foundry_converters/
git commit -m "feat: create foundry_converters directory structure"
```

---

### Task 1.2: Copy Actor Models

**Files:**
- Copy: `src/foundry/actors/models.py` → `src/foundry_converters/actors/models.py`
- Test: `tests/foundry_converters/actors/test_models.py`

**Step 1: Write the failing test**

Create `tests/foundry_converters/__init__.py`:
```python
"""Tests for foundry_converters module."""
```

Create `tests/foundry_converters/actors/__init__.py`:
```python
"""Tests for foundry_converters.actors module."""
```

Create `tests/foundry_converters/actors/test_models.py`:
```python
"""Tests for foundry_converters.actors.models."""

import pytest
from foundry_converters.actors.models import (
    ParsedActorData,
    Attack,
    DamageFormula,
    Trait,
)


class TestParsedActorData:
    """Tests for ParsedActorData model."""

    def test_creates_minimal_actor(self):
        """Should create actor with minimal required fields."""
        actor = ParsedActorData(
            source_statblock_name="Goblin",
            name="Goblin",
            armor_class=15,
            hit_points=7,
            challenge_rating=0.25,
            abilities={
                "STR": 8, "DEX": 14, "CON": 10,
                "INT": 10, "WIS": 8, "CHA": 8
            }
        )

        assert actor.name == "Goblin"
        assert actor.armor_class == 15
        assert actor.abilities["DEX"] == 14


class TestAttack:
    """Tests for Attack model."""

    def test_creates_melee_attack(self):
        """Should create melee attack with damage."""
        attack = Attack(
            name="Scimitar",
            attack_type="melee",
            attack_bonus=4,
            reach=5,
            damage=[DamageFormula(number=1, denomination=6, bonus="+2", type="slashing")]
        )

        assert attack.name == "Scimitar"
        assert attack.attack_type == "melee"
        assert attack.damage[0].denomination == 6


class TestDamageFormula:
    """Tests for DamageFormula model."""

    def test_creates_damage_formula(self):
        """Should create damage formula."""
        formula = DamageFormula(number=2, denomination=6, bonus="+3", type="fire")

        assert formula.number == 2
        assert formula.denomination == 6
        assert formula.bonus == "+3"
        assert formula.type == "fire"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/foundry_converters/actors/test_models.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'foundry_converters'"

**Step 3: Copy the models file**

```bash
cp src/foundry/actors/models.py src/foundry_converters/actors/models.py
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/foundry_converters/actors/test_models.py -v`
Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add src/foundry_converters/actors/models.py tests/foundry_converters/
git commit -m "feat: add actor models to foundry_converters"
```

---

### Task 1.3: Copy Actor Converter

**Files:**
- Copy: `src/foundry/actors/converter.py` → `src/foundry_converters/actors/converter.py`
- Modify: Update imports in converter.py
- Test: `tests/foundry_converters/actors/test_converter.py`

**Step 1: Write the failing test**

Create `tests/foundry_converters/actors/test_converter.py`:
```python
"""Tests for foundry_converters.actors.converter."""

import pytest
from foundry_converters.actors.converter import convert_to_foundry
from foundry_converters.actors.models import ParsedActorData, Attack, DamageFormula


class TestConvertToFoundry:
    """Tests for convert_to_foundry function."""

    @pytest.mark.asyncio
    async def test_converts_basic_actor(self):
        """Should convert minimal actor to FoundryVTT format."""
        goblin = ParsedActorData(
            source_statblock_name="Goblin",
            name="Goblin",
            armor_class=15,
            hit_points=7,
            challenge_rating=0.25,
            abilities={
                "STR": 8, "DEX": 14, "CON": 10,
                "INT": 10, "WIS": 8, "CHA": 8
            }
        )

        result, spell_uuids = await convert_to_foundry(goblin)

        assert result["name"] == "Goblin"
        assert result["type"] == "npc"
        assert result["system"]["abilities"]["dex"]["value"] == 14
        assert result["system"]["attributes"]["ac"]["value"] == 15
        assert spell_uuids == []

    @pytest.mark.asyncio
    async def test_converts_actor_with_attack(self):
        """Should convert actor with attack to FoundryVTT format."""
        goblin = ParsedActorData(
            source_statblock_name="Goblin",
            name="Goblin",
            armor_class=15,
            hit_points=7,
            challenge_rating=0.25,
            abilities={"STR": 8, "DEX": 14, "CON": 10, "INT": 10, "WIS": 8, "CHA": 8},
            attacks=[
                Attack(
                    name="Scimitar",
                    attack_type="melee",
                    attack_bonus=4,
                    reach=5,
                    damage=[DamageFormula(number=1, denomination=6, bonus="+2", type="slashing")]
                )
            ]
        )

        result, spell_uuids = await convert_to_foundry(goblin)

        assert len(result["items"]) >= 1
        weapon = result["items"][0]
        assert weapon["name"] == "Scimitar"
        assert weapon["type"] == "weapon"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/foundry_converters/actors/test_converter.py -v`
Expected: FAIL with "ModuleNotFoundError" or import error

**Step 3: Copy and update the converter file**

```bash
cp src/foundry/actors/converter.py src/foundry_converters/actors/converter.py
```

Edit `src/foundry_converters/actors/converter.py` - update imports at top:

```python
"""Convert ParsedActorData to FoundryVTT actor JSON format."""

import asyncio
import logging
import secrets
from typing import Dict, Any, Optional, TYPE_CHECKING, List, Tuple
from .models import ParsedActorData, Attack, AttackSave

if TYPE_CHECKING:
    # These are only used for type hints, not at runtime
    pass

logger = logging.getLogger(__name__)
```

Remove or comment out any imports from `..icon_cache` or `.spell_cache` - these will be passed as parameters instead.

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/foundry_converters/actors/test_converter.py -v`
Expected: PASS (2 tests)

**Step 5: Commit**

```bash
git add src/foundry_converters/actors/converter.py tests/foundry_converters/actors/test_converter.py
git commit -m "feat: add actor converter to foundry_converters"
```

---

### Task 1.4: Copy Actor Parser

**Files:**
- Copy: `src/foundry/actors/parser.py` → `src/foundry_converters/actors/parser.py`
- Modify: Update imports, remove SpellCache dependency from function signature
- Test: `tests/foundry_converters/actors/test_parser.py`

**Step 1: Write the failing test**

Create `tests/foundry_converters/actors/test_parser.py`:
```python
"""Tests for foundry_converters.actors.parser."""

import pytest
from foundry_converters.actors.parser import parse_senses


class TestParseSenses:
    """Tests for parse_senses helper function."""

    def test_parses_darkvision(self):
        """Should parse darkvision from senses string."""
        result = parse_senses("Darkvision 60 ft., Passive Perception 14")

        assert result["darkvision"] == 60

    def test_parses_passive_perception(self):
        """Should parse passive perception from senses string."""
        result = parse_senses("Darkvision 60 ft., Passive Perception 14")

        assert result.get("passive_perception") == 14 or "passive" in str(result).lower()

    def test_handles_none(self):
        """Should return empty dict for None input."""
        result = parse_senses(None)

        assert result == {}
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/foundry_converters/actors/test_parser.py -v`
Expected: FAIL with import error

**Step 3: Copy and update the parser file**

```bash
cp src/foundry/actors/parser.py src/foundry_converters/actors/parser.py
```

Edit `src/foundry_converters/actors/parser.py` - update imports at top:

```python
"""Parallel parser for converting StatBlock to ParsedActorData using Gemini."""

import asyncio
import json
import logging
from typing import Optional, Union, Callable
from pathlib import Path
import os

from google import genai
from dotenv import load_dotenv

from actors.models import StatBlock
from foundry_converters.actors.models import (
    ParsedActorData, Attack, Trait, Multiattack,
    InnateSpellcasting, InnateSpell, DamageFormula, AttackSave,
    SkillProficiency, DamageModification
)
from util.gemini import generate_content_async

# Load environment
PROJECT_ROOT = Path(__file__).parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

logger = logging.getLogger(__name__)
```

Note: The parser still uses Gemini API (allowed per design - only Foundry I/O moves to backend).

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/foundry_converters/actors/test_parser.py -v`
Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add src/foundry_converters/actors/parser.py tests/foundry_converters/actors/test_parser.py
git commit -m "feat: add actor parser to foundry_converters"
```

---

### Task 1.5: Copy Journal Converter

**Files:**
- Copy: `src/foundry/xml_to_journal_html.py` → `src/foundry_converters/journals/converter.py`
- Modify: Update imports
- Test: `tests/foundry_converters/journals/test_converter.py`

**Step 1: Write the failing test**

Create `tests/foundry_converters/journals/__init__.py`:
```python
"""Tests for foundry_converters.journals module."""
```

Create `tests/foundry_converters/journals/test_converter.py`:
```python
"""Tests for foundry_converters.journals.converter."""

import pytest
from pathlib import Path
from foundry_converters.journals.converter import convert_xml_to_journal_data


class TestConvertXmlToJournalData:
    """Tests for convert_xml_to_journal_data function."""

    def test_extracts_chapter_name_from_filename(self):
        """Should extract chapter name from XML filename."""
        # This test uses a fixture file that should exist
        xml_file = Path("tests/fixtures/xml/sample_chapter.xml")

        if not xml_file.exists():
            pytest.skip("Test fixture not available")

        result = convert_xml_to_journal_data(str(xml_file))

        assert "name" in result
        assert "html" in result
        assert isinstance(result["html"], str)
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/foundry_converters/journals/test_converter.py -v`
Expected: FAIL with import error

**Step 3: Copy and update the converter file**

```bash
cp src/foundry/xml_to_journal_html.py src/foundry_converters/journals/converter.py
```

Edit `src/foundry_converters/journals/converter.py` - update imports at top:

```python
"""Convert XML documents to FoundryVTT journal-ready HTML.

This module reuses the core XML to HTML conversion from pdf_processing/xml_to_html.py
and adds only FoundryVTT-specific modifications if needed.
"""

import os
import sys
import re
from pathlib import Path
from typing import Dict, Any, List

# Import the shared XML to HTML conversion function
from pdf_processing.xml_to_html import xml_to_html_content
```

Remove the sys.path manipulation - use proper imports.

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/foundry_converters/journals/test_converter.py -v`
Expected: PASS (1 test, may skip if fixture missing)

**Step 5: Commit**

```bash
git add src/foundry_converters/journals/converter.py tests/foundry_converters/journals/
git commit -m "feat: add journal converter to foundry_converters"
```

---

### Task 1.6: Update foundry_converters __init__.py Exports

**Files:**
- Modify: `src/foundry_converters/__init__.py`
- Modify: `src/foundry_converters/actors/__init__.py`

**Step 1: Write the failing test**

Create `tests/foundry_converters/test_imports.py`:
```python
"""Tests for foundry_converters module imports."""

import pytest


class TestModuleImports:
    """Tests that all exports are accessible."""

    def test_imports_from_root(self):
        """Should import key items from foundry_converters."""
        from foundry_converters import (
            convert_to_foundry,
            ParsedActorData,
            Attack,
            convert_xml_to_journal_data,
        )

        assert callable(convert_to_foundry)
        assert ParsedActorData is not None

    def test_imports_from_actors(self):
        """Should import from foundry_converters.actors."""
        from foundry_converters.actors import (
            convert_to_foundry,
            ParsedActorData,
            Attack,
            Trait,
            DamageFormula,
        )

        assert callable(convert_to_foundry)

    def test_imports_from_journals(self):
        """Should import from foundry_converters.journals."""
        from foundry_converters.journals import convert_xml_to_journal_data

        assert callable(convert_xml_to_journal_data)
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/foundry_converters/test_imports.py -v`
Expected: FAIL with import error

**Step 3: Update the __init__.py files**

Already created in Task 1.1 - verify they match and update if needed.

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/foundry_converters/test_imports.py -v`
Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add src/foundry_converters/ tests/foundry_converters/test_imports.py
git commit -m "feat: finalize foundry_converters module exports"
```

---

### Task 1.7: Run All foundry_converters Tests

**Step 1: Run all new tests**

Run: `uv run pytest tests/foundry_converters/ -v`
Expected: All tests PASS

**Step 2: Run original foundry tests (should still pass)**

Run: `uv run pytest tests/foundry/actors/ -v -m "not integration"`
Expected: All non-integration tests PASS (both old and new modules work)

**Step 3: Commit checkpoint**

```bash
git add -A
git commit -m "checkpoint: Phase 1 complete - foundry_converters module created"
```

---

## Phase 2: Reorganize Backend

### Task 2.1: Create Health Router

**Files:**
- Create: `ui/backend/app/routers/health.py`
- Modify: `ui/backend/app/main.py`

**Step 1: Create health router**

Create `ui/backend/app/routers/health.py`:
```python
"""Health and status endpoints."""

from fastapi import APIRouter
from app.websocket import foundry_manager

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "module-assistant-api"}


@router.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "D&D Module Assistant API",
        "docs": "/docs",
        "health": "/health"
    }


@router.get("/api/foundry/status")
async def foundry_status():
    """Check Foundry WebSocket connection status."""
    return {
        "connected_clients": foundry_manager.connection_count,
        "status": "connected" if foundry_manager.connection_count > 0 else "disconnected"
    }
```

**Step 2: Update main.py to use router**

In `ui/backend/app/main.py`, add import and include router:
```python
from app.routers import chat, health

# ... after app creation ...

app.include_router(chat.router)
app.include_router(health.router)
```

Remove the health/root/status endpoints from main.py.

**Step 3: Test health endpoint**

Run: `cd ui/backend && uv run pytest tests/ -v -k "health or status" --ignore=tests/integration`
Expected: PASS

**Step 4: Commit**

```bash
git add ui/backend/app/routers/health.py ui/backend/app/main.py
git commit -m "refactor: extract health endpoints to router"
```

---

### Task 2.2: Create Actors Router

**Files:**
- Create: `ui/backend/app/routers/actors.py`
- Modify: `ui/backend/app/main.py`

**Step 1: Create actors router**

Create `ui/backend/app/routers/actors.py`:
```python
"""Actor CRUD endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.websocket import push_actor, fetch_actor, delete_actor, list_actors

router = APIRouter(prefix="/api", tags=["actors"])


class CreateActorRequest(BaseModel):
    """Request body for actor creation."""
    description: str
    challenge_rating: float = 1.0
    output_dir_base: Optional[str] = None


class GiveItemsRequest(BaseModel):
    """Request body for giving items to an actor."""
    item_uuids: list[str]


@router.get("/foundry/actor/{uuid}")
async def get_actor_by_uuid(uuid: str):
    """Fetch an actor from Foundry by UUID via WebSocket."""
    result = await fetch_actor(uuid, timeout=10.0)

    if result.success:
        return {
            "success": True,
            "name": result.entity.get("name") if result.entity else None,
            "entity": result.entity
        }
    else:
        raise HTTPException(status_code=404, detail=result.error)


@router.delete("/foundry/actor/{uuid}")
async def delete_actor_by_uuid(uuid: str):
    """Delete an actor from Foundry by UUID via WebSocket."""
    result = await delete_actor(uuid, timeout=10.0)

    if result.success:
        return {
            "success": True,
            "uuid": result.uuid,
            "name": result.name,
            "message": f"Deleted actor: {result.name}"
        }
    else:
        raise HTTPException(status_code=404, detail=result.error)


@router.post("/foundry/actor")
async def create_actor_raw(request: dict):
    """Create a raw actor in Foundry via WebSocket."""
    actor_data = request.get("actor")
    if not actor_data:
        raise HTTPException(status_code=400, detail="Missing 'actor' field in request")

    result = await push_actor(actor_data, timeout=30.0)

    if result.success:
        return {
            "success": True,
            "uuid": result.uuid,
            "id": result.id,
            "name": result.name
        }
    else:
        raise HTTPException(status_code=500, detail=result.error)


@router.get("/foundry/actors")
async def get_all_actors():
    """List all world actors from Foundry (not compendium)."""
    result = await list_actors(timeout=10.0)

    if result.success:
        return {
            "success": True,
            "count": len(result.actors) if result.actors else 0,
            "actors": [
                {"uuid": a.uuid, "id": a.id, "name": a.name}
                for a in (result.actors or [])
            ]
        }
    else:
        raise HTTPException(status_code=500, detail=result.error)


@router.post("/foundry/actor/{uuid}/items")
async def give_items_to_actor(uuid: str, request: GiveItemsRequest):
    """Add compendium items to an actor via WebSocket."""
    from app.websocket import give_items

    result = await give_items(
        actor_uuid=uuid,
        item_uuids=request.item_uuids,
        timeout=30.0
    )

    if result.success:
        return {
            "success": True,
            "actor_uuid": result.actor_uuid,
            "items_added": result.items_added,
            "errors": result.errors
        }
    else:
        raise HTTPException(status_code=500, detail=result.error)
```

**Step 2: Update main.py**

Add import and include router:
```python
from app.routers import chat, health, actors

app.include_router(actors.router)
```

Remove actor endpoints from main.py.

**Step 3: Test actor endpoints**

Run: `cd ui/backend && uv run pytest tests/ -v -k "actor" --ignore=tests/integration`
Expected: PASS

**Step 4: Commit**

```bash
git add ui/backend/app/routers/actors.py ui/backend/app/main.py
git commit -m "refactor: extract actor endpoints to router"
```

---

### Task 2.3: Create Journals Router

**Files:**
- Create: `ui/backend/app/routers/journals.py`
- Modify: `ui/backend/app/main.py`

**Step 1: Create journals router**

Create `ui/backend/app/routers/journals.py`:
```python
"""Journal CRUD endpoints."""

from fastapi import APIRouter, HTTPException
from app.websocket import push_journal, delete_journal

router = APIRouter(prefix="/api/foundry", tags=["journals"])


@router.post("/journal")
async def create_journal_entry(request: dict):
    """Create a journal entry in Foundry via WebSocket."""
    journal_data = {
        "journal": {
            "name": request.get("name", "Untitled Journal"),
            "pages": request.get("pages", [
                {
                    "name": "Content",
                    "type": "text",
                    "text": {"content": request.get("content", "")}
                }
            ])
        }
    }

    result = await push_journal(journal_data, timeout=30.0)

    if result.success:
        return {
            "success": True,
            "uuid": result.uuid,
            "id": result.id,
            "name": result.name
        }
    else:
        raise HTTPException(status_code=500, detail=result.error)


@router.delete("/journal/{uuid}")
async def delete_journal_by_uuid(uuid: str):
    """Delete a journal entry from Foundry by UUID via WebSocket."""
    result = await delete_journal(uuid, timeout=10.0)

    if result.success:
        return {
            "success": True,
            "uuid": result.uuid,
            "name": result.name,
            "message": f"Deleted journal: {result.name}"
        }
    else:
        raise HTTPException(status_code=404, detail=result.error)
```

**Step 2: Update main.py**

Add import and include router:
```python
from app.routers import chat, health, actors, journals

app.include_router(journals.router)
```

Remove journal endpoints from main.py.

**Step 3: Commit**

```bash
git add ui/backend/app/routers/journals.py ui/backend/app/main.py
git commit -m "refactor: extract journal endpoints to router"
```

---

### Task 2.4: Create Search Router

**Files:**
- Create: `ui/backend/app/routers/search.py`
- Modify: `ui/backend/app/main.py`

**Step 1: Create search router**

Create `ui/backend/app/routers/search.py`:
```python
"""Search and compendium endpoints."""

from fastapi import APIRouter, HTTPException
from app.websocket import search_items, list_compendium_items, list_files

router = APIRouter(prefix="/api/foundry", tags=["search"])


@router.get("/search")
async def search_foundry_items(
    query: str = "",
    document_type: str = "Item",
    sub_type: str = None
):
    """Search Foundry compendiums for items."""
    result = await search_items(
        query=query,
        document_type=document_type,
        sub_type=sub_type,
        timeout=30.0
    )

    if result.success:
        return {
            "success": True,
            "count": len(result.results) if result.results else 0,
            "results": [
                {
                    "uuid": r.uuid,
                    "id": r.id,
                    "name": r.name,
                    "type": r.type,
                    "img": r.img,
                    "pack": r.pack
                }
                for r in (result.results or [])
            ]
        }
    else:
        raise HTTPException(status_code=500, detail=result.error)


@router.get("/compendium")
async def list_compendium_items_endpoint(
    document_type: str = "Item",
    sub_type: str = None
):
    """List ALL items of a specific type from Foundry compendiums."""
    result = await list_compendium_items(
        document_type=document_type,
        sub_type=sub_type,
        timeout=60.0
    )

    if result.success:
        return {
            "success": True,
            "count": len(result.results) if result.results else 0,
            "results": [
                {
                    "uuid": r.uuid,
                    "id": r.id,
                    "name": r.name,
                    "type": r.type,
                    "img": r.img,
                    "pack": r.pack,
                    "system": r.system if hasattr(r, 'system') and r.system else None
                }
                for r in (result.results or [])
            ]
        }
    else:
        raise HTTPException(status_code=500, detail=result.error)


@router.get("/files")
async def list_foundry_files(
    path: str = "icons",
    source: str = "public",
    recursive: bool = True,
    extensions: str = None
):
    """List files in Foundry file system."""
    ext_list = extensions.split(",") if extensions else None

    result = await list_files(
        path=path,
        source=source,
        recursive=recursive,
        extensions=ext_list,
        timeout=60.0
    )

    if result.success:
        return {
            "success": True,
            "count": len(result.files) if result.files else 0,
            "files": result.files or []
        }
    else:
        raise HTTPException(status_code=500, detail=result.error)
```

**Step 2: Update main.py**

Add import and include router:
```python
from app.routers import chat, health, actors, journals, search

app.include_router(search.router)
```

Remove search/compendium/files endpoints from main.py.

**Step 3: Commit**

```bash
git add ui/backend/app/routers/search.py ui/backend/app/main.py
git commit -m "refactor: extract search endpoints to router"
```

---

### Task 2.5: Slim Down main.py

**Files:**
- Modify: `ui/backend/app/main.py`

**Step 1: Verify main.py is now minimal**

After all extractions, `main.py` should be approximately:

```python
"""D&D Module Assistant API."""

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pathlib import Path
from dotenv import load_dotenv

from app.routers import chat, health, actors, journals, search
from app.config import settings
from app.websocket import foundry_websocket_endpoint

# Load environment variables from project root .env
project_root = Path(__file__).parent.parent.parent.parent
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

app = FastAPI(
    title="D&D Module Assistant API",
    description="Backend API for D&D module generation and management",
    version="0.1.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(chat.router)
app.include_router(health.router)
app.include_router(actors.router)
app.include_router(journals.router)
app.include_router(search.router)


@app.websocket("/ws/foundry")
async def websocket_foundry(websocket: WebSocket):
    """WebSocket endpoint for Foundry module connections."""
    await foundry_websocket_endpoint(websocket)


@app.get("/api/images/{filename}")
async def serve_image(filename: str):
    """Serve generated images from chat_images directory."""
    from fastapi import HTTPException

    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    if not filename.endswith(".png"):
        raise HTTPException(status_code=400, detail="Only PNG files supported")

    file_path = settings.IMAGE_OUTPUT_DIR / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")

    return FileResponse(file_path, media_type="image/png")
```

**Step 2: Count lines**

Run: `wc -l ui/backend/app/main.py`
Expected: ~60-80 lines (down from 590)

**Step 3: Run all backend tests**

Run: `cd ui/backend && uv run pytest tests/ -v --ignore=tests/integration`
Expected: All tests PASS

**Step 4: Commit**

```bash
git add ui/backend/app/main.py
git commit -m "refactor: slim main.py to ~60 lines"
```

---

### Task 2.6: Phase 2 Checkpoint

**Step 1: Run smoke tests**

Run: `uv run pytest -m smoke -v`
Expected: All smoke tests PASS

**Step 2: Commit checkpoint**

```bash
git add -A
git commit -m "checkpoint: Phase 2 complete - backend reorganized into routers"
```

---

## Phase 3: Update src/ Consumers

### Task 3.1: Update orchestrate.py Imports

**Files:**
- Modify: `src/actors/orchestrate.py`

**Step 1: Read current imports in orchestrate.py**

Check what imports from `foundry.actors` and update to `foundry_converters.actors`.

**Step 2: Update imports**

Change:
```python
from foundry.actors.models import ParsedActorData
from foundry.actors.converter import convert_to_foundry
from foundry.actors.parser import parse_stat_block_to_actor
```

To:
```python
from foundry_converters.actors.models import ParsedActorData
from foundry_converters.actors.converter import convert_to_foundry
from foundry_converters.actors.parser import parse_stat_block_to_actor
```

**Step 3: Run orchestrate tests**

Run: `uv run pytest tests/actors/test_orchestrate.py -v -m "not integration"`
Expected: PASS

**Step 4: Commit**

```bash
git add src/actors/orchestrate.py
git commit -m "refactor: update orchestrate.py to use foundry_converters"
```

---

### Task 3.2: Update api.py to Thin HTTP Client

**Files:**
- Modify: `src/api.py`

**Step 1: Rewrite api.py**

Replace contents with thin HTTP client (see design doc for full code).

**Step 2: Run API tests**

Run: `uv run pytest tests/api/test_api.py -v`
Expected: PASS (unit tests should still work)

**Step 3: Commit**

```bash
git add src/api.py
git commit -m "refactor: simplify api.py to thin HTTP client"
```

---

## Phase 4: Delete Old Code

### Task 4.1: Delete src/foundry/

**Step 1: Verify no remaining imports**

Run: `grep -r "from foundry\." src/ --include="*.py" | grep -v foundry_converters | grep -v "^Binary"`
Expected: No matches (or only in files to be deleted)

**Step 2: Delete the directory**

```bash
rm -rf src/foundry/
```

**Step 3: Run tests**

Run: `uv run pytest tests/ -v -m "not integration" --ignore=tests/foundry`
Expected: PASS

**Step 4: Commit**

```bash
git add -A
git commit -m "chore: delete src/foundry/ (replaced by foundry_converters)"
```

---

### Task 4.2: Delete relay-server/

**Step 1: Delete the directory**

```bash
rm -rf relay-server/
```

**Step 2: Commit**

```bash
git add -A
git commit -m "chore: delete relay-server/ (replaced by WebSocket)"
```

---

### Task 4.3: Consolidate plans/

**Step 1: Create archive directory**

```bash
mkdir -p docs/plans/archive
```

**Step 2: Move old plans**

```bash
mv plans/* docs/plans/archive/
rmdir plans
```

**Step 3: Commit**

```bash
git add -A
git commit -m "chore: consolidate plans/ to docs/plans/archive/"
```

---

### Task 4.4: Update .gitignore

**Step 1: Add entries**

Append to `.gitignore`:
```
# Root clutter
repomix-output.xml
tree.txt
parallel.env
test_output.log
```

**Step 2: Commit**

```bash
git add .gitignore
git commit -m "chore: update .gitignore for root clutter"
```

---

## Phase 5: Test Migration and Verification

### Task 5.1: Move Foundry Integration Tests

**Files:**
- Move: `tests/foundry/` integration tests → `ui/backend/tests/integration/`

**Step 1: Identify integration tests to move**

Run: `grep -l "@pytest.mark.integration" tests/foundry/**/*.py`

**Step 2: Move tests that require Foundry connection**

Tests that make HTTP calls to backend should move to `ui/backend/tests/`.
Tests that only test pure converters stay in `tests/foundry_converters/`.

**Step 3: Update imports in moved tests**

**Step 4: Run moved tests**

Run: `cd ui/backend && uv run pytest tests/integration/ -v`
Expected: PASS (with Foundry connected)

**Step 5: Commit**

```bash
git add -A
git commit -m "test: migrate Foundry integration tests to backend"
```

---

### Task 5.2: Rename tests/foundry to tests/foundry_converters

**Step 1: Move remaining pure tests**

```bash
mv tests/foundry/actors/test_converter.py tests/foundry_converters/actors/ 2>/dev/null || true
mv tests/foundry/actors/test_parser.py tests/foundry_converters/actors/ 2>/dev/null || true
```

**Step 2: Delete old tests/foundry if empty**

```bash
rm -rf tests/foundry/
```

**Step 3: Run all tests**

Run: `uv run pytest tests/foundry_converters/ -v`
Expected: PASS

**Step 4: Commit**

```bash
git add -A
git commit -m "test: consolidate tests under tests/foundry_converters"
```

---

### Task 5.3: Full Test Suite Verification

**Step 1: Run smoke tests**

Run: `uv run pytest -m smoke -v`
Expected: All PASS

**Step 2: Run full test suite**

Run: `uv run pytest --full -v 2>&1 | tee test_full_output.log`
Expected: All tests PASS with live Foundry

**Step 3: Verify no mocking in integration tests**

Run: `grep -r "Mock\|patch\|MagicMock" ui/backend/tests/integration/`
Expected: No matches (or only in non-integration test files)

**Step 4: Commit**

```bash
git add -A
git commit -m "test: verify full test suite passes"
```

---

### Task 5.4: Update CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Update architecture section**

Update the FoundryVTT Integration section to reflect new structure:
- `src/foundry_converters/` for pure conversion
- `ui/backend/` for all Foundry I/O
- Remove references to relay server

**Step 2: Update testing section**

Update test workflow to reflect new organization.

**Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md for new architecture"
```

---

### Task 5.5: Final Commit

**Step 1: Create summary commit**

```bash
git add -A
git commit -m "feat: complete architecture simplification

- Created src/foundry_converters/ with pure conversion logic
- Reorganized ui/backend/ into focused routers
- Deleted src/foundry/ (network code moved to backend)
- Deleted relay-server/ (replaced by WebSocket)
- Consolidated plans/ to docs/plans/archive/
- Updated all tests and documentation

Breaking changes:
- Import from foundry_converters instead of foundry
- src/api.py now requires backend running"
```

---

## Success Criteria Checklist

- [ ] `src/` has zero network calls (except Gemini API)
- [ ] Only `ui/backend/` talks to Foundry
- [ ] `pytest --full` passes with live Foundry
- [ ] No mocking in integration tests
- [ ] `ui/backend/app/main.py` is ~60 lines
- [ ] CLAUDE.md reflects new structure
