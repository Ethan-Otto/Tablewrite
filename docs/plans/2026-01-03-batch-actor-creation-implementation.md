# Batch Actor Creation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Allow users to create multiple D&D actors from a single natural language prompt (e.g., "Create a goblin, two bugbears, and a hobgoblin captain"), processed in parallel with progress updates.

**Architecture:** Extend existing `ActorCreatorTool` pattern with a new `BatchActorCreatorTool`. Use Gemini to parse natural language into structured actor requests, then create actors in parallel using `asyncio.gather()`. Reuse existing cache loading and actor creation infrastructure.

**Tech Stack:** Python (FastAPI backend), TypeScript (Foundry module), Playwright (E2E testing), Gemini API (prompt parsing)

---

## Task 1: Extract Shared Cache Loading Function

**Files:**
- Modify: `ui/backend/app/tools/actor_creator.py`
- Test: `tests/tools/test_actor_creator.py`

**Step 1: Write the failing test**

```python
# tests/tools/test_actor_creator.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

@pytest.mark.asyncio
async def test_load_caches_returns_spell_and_icon_cache():
    """Test that load_caches returns both SpellCache and IconCache."""
    from app.tools.actor_creator import load_caches

    # Mock the WebSocket calls
    mock_spells_result = MagicMock()
    mock_spells_result.success = True
    mock_spells_result.results = [
        MagicMock(name="Fire Bolt", uuid="Compendium.dnd5e.spells.Item.abc", type="spell", img="", pack="dnd5e.spells")
    ]

    mock_files_result = MagicMock()
    mock_files_result.success = True
    mock_files_result.files = ["icons/magic/fire.webp"]

    with patch('app.tools.actor_creator.list_compendium_items_with_retry', return_value=mock_spells_result), \
         patch('app.tools.actor_creator.list_files_with_retry', return_value=mock_files_result):
        spell_cache, icon_cache = await load_caches()

    assert spell_cache is not None
    assert icon_cache is not None
    assert spell_cache.spell_count > 0
    assert icon_cache.icon_count > 0
```

**Step 2: Run test to verify it fails**

Run: `cd ui/backend && PYTHONPATH=. pytest tests/tools/test_actor_creator.py::test_load_caches_returns_spell_and_icon_cache -v`
Expected: FAIL with "cannot import name 'load_caches'"

**Step 3: Write minimal implementation**

Extract lines 276-335 from `ActorCreatorTool.execute()` into a standalone async function:

```python
# ui/backend/app/tools/actor_creator.py

async def load_caches() -> tuple:
    """
    Load SpellCache and IconCache via WebSocket.

    Returns:
        Tuple of (SpellCache, IconCache)

    Raises:
        RuntimeError: If cache loading fails
    """
    # HARD FAIL: SpellCache MUST load successfully
    spell_cache = SpellCache()
    logger.info("Fetching spells from compendium via WebSocket (with retry)...")
    spells_result = await list_compendium_items_with_retry(
        document_type="Item",
        sub_type="spell",
        max_retries=3,
        initial_delay=1.0
    )

    if not spells_result.success:
        error_msg = f"❌ SpellCache FAILED to load: {spells_result.error}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    if not spells_result.results or len(spells_result.results) == 0:
        error_msg = "❌ SpellCache FAILED: No spells returned from compendium"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    # Convert SearchResultItem objects to dicts for load_from_data
    spell_dicts = [
        {
            "name": r.name,
            "uuid": r.uuid,
            "type": r.type,
            "img": r.img,
            "pack": r.pack,
        }
        for r in spells_result.results
    ]
    spell_cache.load_from_data(spell_dicts)
    logger.info(f"✓ SpellCache loaded with {spell_cache.spell_count} spells")

    # Verify critical spells exist
    test_uuid = spell_cache.get_spell_uuid("Fire Bolt")
    if not test_uuid:
        error_msg = "❌ SpellCache FAILED: 'Fire Bolt' not found - cache may be incomplete"
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    logger.info(f"✓ Test lookup 'Fire Bolt' -> {test_uuid}")

    # HARD FAIL: IconCache MUST load successfully
    icon_cache = IconCache()
    logger.info("Fetching icons via WebSocket (with retry)...")
    files_result = await list_files_with_retry(
        path="icons",
        source="public",
        recursive=True,
        extensions=[".webp", ".png", ".jpg", ".svg"],
        max_retries=3,
        initial_delay=1.0
    )

    if not files_result.success:
        error_msg = f"❌ IconCache FAILED to load: {files_result.error}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    icon_cache.load_from_data(files_result.files or [])
    logger.info(f"✓ IconCache loaded with {icon_cache.icon_count} icons")

    return spell_cache, icon_cache
```

**Step 4: Update ActorCreatorTool.execute() to use load_caches()**

Replace lines 276-335 in `execute()` with:
```python
spell_cache, icon_cache = await load_caches()
```

**Step 5: Run test to verify it passes**

Run: `cd ui/backend && PYTHONPATH=. pytest tests/tools/test_actor_creator.py::test_load_caches_returns_spell_and_icon_cache -v`
Expected: PASS

**Step 6: Commit**

```bash
git add ui/backend/app/tools/actor_creator.py tests/tools/test_actor_creator.py
git commit -m "refactor: extract load_caches() for reuse in batch actor creation"
```

---

## Task 2: Create Prompt Parsing Function

**Files:**
- Create: `ui/backend/app/tools/batch_actor_creator.py`
- Test: `tests/tools/test_batch_actor_creator.py`

**Step 1: Write the failing test**

```python
# tests/tools/test_batch_actor_creator.py
import pytest
from unittest.mock import patch, MagicMock

@pytest.mark.asyncio
async def test_parse_actor_requests_extracts_creatures():
    """Test that parse_actor_requests extracts creatures from natural language."""
    from app.tools.batch_actor_creator import parse_actor_requests

    # Mock Gemini response
    mock_response = MagicMock()
    mock_response.text = '''[
        {"description": "a goblin scout", "count": 1},
        {"description": "a bugbear", "count": 2},
        {"description": "a hobgoblin captain", "count": 1}
    ]'''

    with patch('app.tools.batch_actor_creator.GeminiAPI') as MockGemini:
        mock_api = MagicMock()
        mock_api.generate_content.return_value = mock_response
        MockGemini.return_value = mock_api

        result = await parse_actor_requests("Create a goblin scout, two bugbears, and a hobgoblin captain")

    assert len(result) == 3
    assert result[0]["description"] == "a goblin scout"
    assert result[0]["count"] == 1
    assert result[1]["description"] == "a bugbear"
    assert result[1]["count"] == 2


@pytest.mark.asyncio
async def test_parse_actor_requests_empty_prompt():
    """Test that empty/unclear prompts return empty list."""
    from app.tools.batch_actor_creator import parse_actor_requests

    mock_response = MagicMock()
    mock_response.text = '[]'

    with patch('app.tools.batch_actor_creator.GeminiAPI') as MockGemini:
        mock_api = MagicMock()
        mock_api.generate_content.return_value = mock_response
        MockGemini.return_value = mock_api

        result = await parse_actor_requests("hello world")

    assert result == []
```

**Step 2: Run test to verify it fails**

Run: `cd ui/backend && PYTHONPATH=. pytest tests/tools/test_batch_actor_creator.py::test_parse_actor_requests_extracts_creatures -v`
Expected: FAIL with "No module named 'app.tools.batch_actor_creator'"

**Step 3: Write minimal implementation**

```python
# ui/backend/app/tools/batch_actor_creator.py
"""Batch actor creation tool - create multiple actors from natural language."""
import sys
import asyncio
import json
import logging
from pathlib import Path
from typing import List, Dict, Any

# Add project paths for module imports
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from util.gemini import GeminiAPI

logger = logging.getLogger(__name__)


async def parse_actor_requests(prompt: str) -> List[Dict[str, Any]]:
    """
    Parse natural language prompt into structured actor requests.

    Args:
        prompt: Natural language like "Create a goblin, two bugbears, and a hobgoblin"

    Returns:
        List of dicts with 'description' and 'count' keys
    """
    def _parse():
        api = GeminiAPI(model_name="gemini-2.0-flash")
        system_prompt = """You are a D&D creature parser. Extract creatures/actors from the user's request.

Return a JSON array where each element has:
- "description": brief creature description (e.g., "a goblin scout", "a bugbear brute")
- "count": number of this creature type requested (default 1)

Examples:
- "Create a goblin" -> [{"description": "a goblin", "count": 1}]
- "Make two bugbears and an orc" -> [{"description": "a bugbear", "count": 2}, {"description": "an orc", "count": 1}]
- "5 kobolds" -> [{"description": "a kobold", "count": 5}]

If no creatures are mentioned, return [].
Return ONLY the JSON array, no other text."""

        response = api.generate_content(f"{system_prompt}\n\nUser request: {prompt}")
        return response.text.strip()

    result_text = await asyncio.to_thread(_parse)

    # Parse JSON response
    try:
        # Handle potential markdown code blocks
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
        result = json.loads(result_text)
        return result if isinstance(result, list) else []
    except json.JSONDecodeError:
        logger.warning(f"Failed to parse actor requests: {result_text}")
        return []
```

**Step 4: Run test to verify it passes**

Run: `cd ui/backend && PYTHONPATH=. pytest tests/tools/test_batch_actor_creator.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add ui/backend/app/tools/batch_actor_creator.py tests/tools/test_batch_actor_creator.py
git commit -m "feat: add parse_actor_requests for batch actor creation"
```

---

## Task 3: Create Duplicate Expansion Function

**Files:**
- Modify: `ui/backend/app/tools/batch_actor_creator.py`
- Test: `tests/tools/test_batch_actor_creator.py`

**Step 1: Write the failing test**

```python
# tests/tools/test_batch_actor_creator.py (add to existing file)

@pytest.mark.asyncio
async def test_expand_duplicates_generates_unique_names():
    """Test that expand_duplicates generates distinct names for count > 1."""
    from app.tools.batch_actor_creator import expand_duplicates

    requests = [
        {"description": "a bugbear", "count": 2},
        {"description": "a goblin", "count": 1}
    ]

    # Mock Gemini response for name generation
    mock_response = MagicMock()
    mock_response.text = '["Bugbear Brute", "Bugbear Tracker"]'

    with patch('app.tools.batch_actor_creator.GeminiAPI') as MockGemini:
        mock_api = MagicMock()
        mock_api.generate_content.return_value = mock_response
        MockGemini.return_value = mock_api

        result = await expand_duplicates(requests)

    # Should have 3 actors total (2 bugbears + 1 goblin)
    assert len(result) == 3
    # Bugbears should have unique names
    bugbear_names = [r["description"] for r in result if "bugbear" in r["description"].lower() or "Bugbear" in r["description"]]
    assert len(set(bugbear_names)) == 2  # All unique
```

**Step 2: Run test to verify it fails**

Run: `cd ui/backend && PYTHONPATH=. pytest tests/tools/test_batch_actor_creator.py::test_expand_duplicates_generates_unique_names -v`
Expected: FAIL with "cannot import name 'expand_duplicates'"

**Step 3: Write minimal implementation**

```python
# ui/backend/app/tools/batch_actor_creator.py (add to existing file)

async def expand_duplicates(requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Expand requests with count > 1 into individual actors with unique names.

    Args:
        requests: List of {"description": str, "count": int}

    Returns:
        Expanded list where each entry has count=1 and unique description
    """
    expanded = []

    for req in requests:
        count = req.get("count", 1)
        description = req.get("description", "")

        if count == 1:
            expanded.append({"description": description, "count": 1})
        else:
            # Generate unique names for duplicates
            unique_names = await _generate_unique_names(description, count)
            for name in unique_names:
                expanded.append({"description": name, "count": 1})

    return expanded


async def _generate_unique_names(base_description: str, count: int) -> List[str]:
    """Generate unique variant names for duplicate creatures."""
    def _generate():
        api = GeminiAPI(model_name="gemini-2.0-flash")
        prompt = f"""Generate {count} unique, distinct names/variants for this D&D creature:
"{base_description}"

Make each name descriptive and different (e.g., "Bugbear Brute", "Bugbear Tracker", "Bugbear Shaman").
Return ONLY a JSON array of strings, no other text.

Example: ["Bugbear Brute", "Bugbear Tracker"]"""

        response = api.generate_content(prompt)
        return response.text.strip()

    result_text = await asyncio.to_thread(_generate)

    try:
        # Handle potential markdown code blocks
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
        names = json.loads(result_text)
        if isinstance(names, list) and len(names) >= count:
            return names[:count]
    except json.JSONDecodeError:
        logger.warning(f"Failed to parse unique names: {result_text}")

    # Fallback: append numbers
    return [f"{base_description} #{i+1}" for i in range(count)]
```

**Step 4: Run test to verify it passes**

Run: `cd ui/backend && PYTHONPATH=. pytest tests/tools/test_batch_actor_creator.py::test_expand_duplicates_generates_unique_names -v`
Expected: PASS

**Step 5: Commit**

```bash
git add ui/backend/app/tools/batch_actor_creator.py tests/tools/test_batch_actor_creator.py
git commit -m "feat: add expand_duplicates for unique actor names"
```

---

## Task 4: Create BatchActorCreatorTool Class

**Files:**
- Modify: `ui/backend/app/tools/batch_actor_creator.py`
- Test: `tests/tools/test_batch_actor_creator.py`

**Step 1: Write the failing test**

```python
# tests/tools/test_batch_actor_creator.py (add to existing file)

@pytest.mark.asyncio
async def test_batch_actor_creator_tool_schema():
    """Test BatchActorCreatorTool has correct schema."""
    from app.tools.batch_actor_creator import BatchActorCreatorTool

    tool = BatchActorCreatorTool()
    schema = tool.get_schema()

    assert schema.name == "create_actors"
    assert "prompt" in schema.parameters["properties"]
    assert schema.parameters["required"] == ["prompt"]


@pytest.mark.asyncio
async def test_batch_actor_creator_executes_parallel():
    """Test that BatchActorCreatorTool creates actors in parallel."""
    from app.tools.batch_actor_creator import BatchActorCreatorTool

    tool = BatchActorCreatorTool()

    # Mock all dependencies
    with patch('app.tools.batch_actor_creator.parse_actor_requests') as mock_parse, \
         patch('app.tools.batch_actor_creator.expand_duplicates') as mock_expand, \
         patch('app.tools.batch_actor_creator.load_caches') as mock_caches, \
         patch('app.tools.batch_actor_creator.create_single_actor') as mock_create:

        mock_parse.return_value = [{"description": "a goblin", "count": 1}]
        mock_expand.return_value = [{"description": "a goblin", "count": 1}]
        mock_caches.return_value = (MagicMock(), MagicMock())
        mock_create.return_value = {"uuid": "Actor.abc123", "name": "Goblin"}

        response = await tool.execute(prompt="Create a goblin")

    assert response.type == "text"
    assert "Actor.abc123" in response.message or "Goblin" in response.message
```

**Step 2: Run test to verify it fails**

Run: `cd ui/backend && PYTHONPATH=. pytest tests/tools/test_batch_actor_creator.py::test_batch_actor_creator_tool_schema -v`
Expected: FAIL with "cannot import name 'BatchActorCreatorTool'"

**Step 3: Write minimal implementation**

```python
# ui/backend/app/tools/batch_actor_creator.py (add to existing file)

from dotenv import load_dotenv
from .base import BaseTool, ToolSchema, ToolResponse
from .actor_creator import (
    load_caches,
    generate_actor_description,
    generate_actor_image,
    _image_generation_enabled,
)
from actors.orchestrate import create_actor_from_description
from app.websocket import push_actor, get_or_create_folder

# Load environment variables
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path)


async def create_single_actor(
    description: str,
    spell_cache,
    icon_cache,
    folder_id: str = None
) -> Dict[str, Any]:
    """
    Create a single actor with shared caches.

    Returns:
        Dict with 'uuid', 'name', 'cr', and optionally 'image_url'
    """
    # Generate image if enabled
    image_url = None
    foundry_image_path = None
    if _image_generation_enabled:
        try:
            visual_desc = await generate_actor_description(description)
            image_url, foundry_image_path = await generate_actor_image(visual_desc)
        except Exception as e:
            logger.warning(f"Image generation failed (non-fatal): {e}")

    # Actor upload function
    async def ws_actor_upload(actor_data: dict, spell_uuids: list) -> str:
        if folder_id:
            actor_data["folder"] = folder_id
        if foundry_image_path:
            actor_data["img"] = foundry_image_path

        result = await push_actor({
            "actor": actor_data,
            "spell_uuids": spell_uuids
        }, timeout=30.0)

        if result.success:
            return result.uuid
        raise RuntimeError(f"Failed to create actor: {result.error}")

    # Create the actor
    result = await create_actor_from_description(
        description=description,
        spell_cache=spell_cache,
        icon_cache=icon_cache,
        actor_upload_fn=ws_actor_upload,
    )

    return {
        "uuid": result.foundry_uuid,
        "name": result.stat_block.name if result.stat_block else "Unknown",
        "cr": result.challenge_rating,
        "image_url": image_url
    }


class BatchActorCreatorTool(BaseTool):
    """Tool for creating multiple D&D actors from a single prompt."""

    @property
    def name(self) -> str:
        return "create_actors"

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name="create_actors",
            description=(
                "Create multiple D&D actors/creatures from a natural language description. "
                "Use when user asks to create several actors at once, like 'create a goblin, "
                "two bugbears, and a hobgoblin captain'."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Natural language description of actors to create"
                    }
                },
                "required": ["prompt"]
            }
        )

    async def execute(self, prompt: str) -> ToolResponse:
        """Execute batch actor creation."""
        try:
            # Step 1: Parse prompt into actor requests
            requests = await parse_actor_requests(prompt)
            if not requests:
                return ToolResponse(
                    type="text",
                    message="I couldn't identify any actors to create. Could you be more specific?",
                    data=None
                )

            # Step 2: Expand duplicates into unique actors
            expanded = await expand_duplicates(requests)
            total = len(expanded)

            # Step 3: Load caches once (shared across all actors)
            spell_cache, icon_cache = await load_caches()

            # Step 4: Get or create Tablewrite folder
            folder_id = None
            try:
                folder_result = await get_or_create_folder("Tablewrite", "Actor")
                if folder_result.success:
                    folder_id = folder_result.folder_id
            except Exception as e:
                logger.warning(f"Failed to get Tablewrite folder: {e}")

            # Step 5: Create actors in parallel
            tasks = [
                create_single_actor(
                    req["description"],
                    spell_cache,
                    icon_cache,
                    folder_id
                )
                for req in expanded
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Step 6: Collect successes and failures
            successes = []
            failures = []
            image_urls = []

            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    failures.append({
                        "description": expanded[i]["description"],
                        "error": str(result)
                    })
                else:
                    successes.append(result)
                    if result.get("image_url"):
                        image_urls.append(result["image_url"])

            # Step 7: Build response message
            if successes:
                lines = [f"Created {len(successes)} of {total} actors:"]
                for s in successes:
                    link = f"@UUID[{s['uuid']}]{{{s['name']}}}"
                    lines.append(f"• {link} (CR {s['cr']})")

                if failures:
                    lines.append("\nFailed:")
                    for f in failures:
                        lines.append(f"• {f['description']} - {f['error']}")

                message = "\n".join(lines)
            else:
                message = f"Failed to create any actors:\n" + "\n".join(
                    f"• {f['description']} - {f['error']}" for f in failures
                )

            # Return with images if available
            response_data = {
                "created": [{"uuid": s["uuid"], "name": s["name"], "cr": s["cr"]} for s in successes],
                "failed": failures
            }

            if image_urls:
                return ToolResponse(
                    type="image",
                    message=message,
                    data={**response_data, "image_urls": image_urls}
                )

            return ToolResponse(
                type="text",
                message=message,
                data=response_data
            )

        except Exception as e:
            logger.error(f"Batch actor creation failed: {e}")
            return ToolResponse(
                type="error",
                message=f"Failed to create actors: {str(e)}",
                data=None
            )
```

**Step 4: Run test to verify it passes**

Run: `cd ui/backend && PYTHONPATH=. pytest tests/tools/test_batch_actor_creator.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add ui/backend/app/tools/batch_actor_creator.py tests/tools/test_batch_actor_creator.py
git commit -m "feat: add BatchActorCreatorTool for parallel actor creation"
```

---

## Task 5: Register BatchActorCreatorTool

**Files:**
- Modify: `ui/backend/app/tools/__init__.py`
- Test: Manual verification

**Step 1: Check current __init__.py**

```bash
cat ui/backend/app/tools/__init__.py
```

**Step 2: Add import and registration**

```python
# ui/backend/app/tools/__init__.py
"""Tool registry initialization."""
from .registry import registry, ToolRegistry
from .base import BaseTool, ToolSchema, ToolResponse
from .actor_creator import ActorCreatorTool
from .batch_actor_creator import BatchActorCreatorTool
from .scene_creator import SceneCreatorTool
from .journal_creator import JournalCreatorTool
from .actor_editor import ActorEditorTool
from .image_generator import ImageGeneratorTool

# Register all tools
registry.register(ActorCreatorTool())
registry.register(BatchActorCreatorTool())
registry.register(SceneCreatorTool())
registry.register(JournalCreatorTool())
registry.register(ActorEditorTool())
registry.register(ImageGeneratorTool())

__all__ = [
    "registry",
    "ToolRegistry",
    "BaseTool",
    "ToolSchema",
    "ToolResponse",
]
```

**Step 3: Verify registration works**

Run: `cd ui/backend && python -c "from app.tools import registry; print([s.name for s in registry.get_schemas()])"`
Expected: Output includes "create_actors"

**Step 4: Commit**

```bash
git add ui/backend/app/tools/__init__.py
git commit -m "feat: register BatchActorCreatorTool in tool registry"
```

---

## Task 6: Create Playwright E2E Test

**Files:**
- Create: `tests/ui/test_batch_actor_creation.py`

**Step 1: Create test file**

```python
# tests/ui/test_batch_actor_creation.py
"""
Playwright E2E tests for batch actor creation.

Prerequisites:
1. Backend running: cd ui/backend && uvicorn app.main:app --reload
2. FoundryVTT running with Tablewrite module connected
3. Chrome with debug port: open -a "Google Chrome" --args --remote-debugging-port=9222
"""
import pytest
import re
import requests
import time

# Add foundry_helper to path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "foundry-module/tablewrite-assistant/scripts/feedback"))

from foundry_helper import FoundrySession

BACKEND_URL = "http://localhost:8000"


def validate_actor_content(actor: dict) -> list[str]:
    """
    Validate actor has appropriate D&D content.
    Returns list of validation errors (empty if valid).
    """
    errors = []
    name = actor.get("name", "Unknown")
    system = actor.get("system", {})

    # Check abilities exist and are reasonable
    abilities = system.get("abilities", {})
    for ability in ["str", "dex", "con", "int", "wis", "cha"]:
        value = abilities.get(ability, {}).get("value", 0)
        if value < 1 or value > 30:
            errors.append(f"{name}: {ability} value {value} out of range")

    # Check HP is set (not default 4)
    hp = system.get("attributes", {}).get("hp", {})
    if hp.get("max", 0) <= 4:
        errors.append(f"{name}: HP too low ({hp.get('max', 0)})")

    # Check has items
    items = actor.get("items", [])
    if len(items) == 0:
        errors.append(f"{name}: No items (attacks, traits)")

    return errors


@pytest.mark.integration
@pytest.mark.slow
def test_batch_actor_creation_e2e():
    """
    E2E test: Send batch request via chat UI, verify actors created with correct content.
    """
    created_uuids = []

    try:
        with FoundrySession(headless=True) as session:
            # Step 1: Navigate to Tablewrite tab
            session.goto_tablewrite()
            time.sleep(1)

            # Step 2: Send batch creation request
            session.send_message(
                "Create a goblin scout and a bugbear",
                wait=60  # Actor creation takes time
            )

            # Step 3: Get response and extract UUIDs
            response_text = session.get_message_text()
            print(f"Response: {response_text[:500]}...")

            # Check for success indicators
            assert "Created" in response_text or "@UUID" in response_text, \
                f"Expected success message, got: {response_text[:200]}"

            # Parse @UUID[Actor.xxx]{Name} links
            uuid_pattern = r'@UUID\[Actor\.([a-zA-Z0-9]+)\]\{([^}]+)\}'
            matches = re.findall(uuid_pattern, response_text)

            assert len(matches) >= 2, f"Expected at least 2 actors, found {len(matches)}"

            created_uuids = [f"Actor.{m[0]}" for m in matches]
            actor_names = [m[1] for m in matches]
            print(f"Created actors: {list(zip(actor_names, created_uuids))}")

            # Step 4: Fetch and validate each actor
            for uuid, expected_name in zip(created_uuids, actor_names):
                response = requests.get(f"{BACKEND_URL}/api/foundry/actor/{uuid}")
                assert response.status_code == 200, f"Failed to fetch {uuid}"

                result = response.json()
                assert result["success"], f"Fetch failed: {result.get('error')}"

                actor = result["entity"]

                # Validate basic structure
                assert actor["name"] == expected_name, f"Name mismatch: {actor['name']} != {expected_name}"
                assert actor["type"] == "npc", f"Wrong type: {actor['type']}"

                # Validate content
                errors = validate_actor_content(actor)
                assert not errors, f"Validation errors for {expected_name}: {errors}"

                print(f"✓ {expected_name}: Validated successfully")

    finally:
        # Step 5: Cleanup - delete test actors
        for uuid in created_uuids:
            try:
                response = requests.delete(f"{BACKEND_URL}/api/foundry/actor/{uuid}")
                if response.status_code == 200:
                    print(f"✓ Deleted {uuid}")
            except Exception as e:
                print(f"Warning: Failed to delete {uuid}: {e}")


@pytest.mark.integration
@pytest.mark.slow
def test_batch_actor_duplicates_have_unique_names():
    """Test that requesting multiple of same creature creates unique names."""
    created_uuids = []

    try:
        with FoundrySession(headless=True) as session:
            session.goto_tablewrite()
            time.sleep(1)

            # Request two of the same creature
            session.send_message("Create two goblins", wait=90)

            response_text = session.get_message_text()

            # Parse UUIDs
            uuid_pattern = r'@UUID\[Actor\.([a-zA-Z0-9]+)\]\{([^}]+)\}'
            matches = re.findall(uuid_pattern, response_text)

            assert len(matches) >= 2, f"Expected 2 goblins, found {len(matches)}"

            created_uuids = [f"Actor.{m[0]}" for m in matches]
            actor_names = [m[1] for m in matches]

            # Verify names are unique
            assert len(set(actor_names)) == len(actor_names), \
                f"Names not unique: {actor_names}"

            print(f"✓ Created {len(actor_names)} goblins with unique names: {actor_names}")

    finally:
        for uuid in created_uuids:
            try:
                requests.delete(f"{BACKEND_URL}/api/foundry/actor/{uuid}")
            except:
                pass
```

**Step 2: Run test (requires running backend and Foundry)**

Run: `cd ui/backend && PYTHONPATH=. pytest tests/ui/test_batch_actor_creation.py -v -s`
Expected: PASS (if backend and Foundry are running)

**Step 3: Commit**

```bash
git add tests/ui/test_batch_actor_creation.py
git commit -m "test: add Playwright E2E tests for batch actor creation"
```

---

## Task 7: Integration Test - Full Round-Trip

**Files:**
- Create: `tests/integration/test_batch_actor_roundtrip.py`

**Step 1: Create integration test**

```python
# tests/integration/test_batch_actor_roundtrip.py
"""
Integration tests for batch actor creation.
Tests the full pipeline without UI, using the tool directly.
"""
import pytest
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "ui/backend"))


@pytest.mark.integration
@pytest.mark.asyncio
async def test_batch_actor_creation_roundtrip():
    """
    Test batch actor creation end-to-end:
    1. Call BatchActorCreatorTool.execute()
    2. Fetch created actors via API
    3. Validate actor content
    4. Cleanup
    """
    from app.tools.batch_actor_creator import BatchActorCreatorTool
    from app.websocket import fetch_actor, delete_actor
    import re

    tool = BatchActorCreatorTool()

    # Create actors
    response = await tool.execute(prompt="Create a goblin and a bugbear")

    assert response.type in ["text", "image"], f"Unexpected response type: {response.type}"
    assert response.data is not None, "No data in response"

    created = response.data.get("created", [])
    assert len(created) >= 2, f"Expected 2 actors, got {len(created)}"

    # Fetch and validate each actor
    try:
        for actor_info in created:
            uuid = actor_info["uuid"]

            # Fetch from Foundry
            result = await fetch_actor(uuid)
            assert result.success, f"Failed to fetch {uuid}: {result.error}"

            actor = result.entity
            assert actor["type"] == "npc"

            # Validate has stats
            abilities = actor.get("system", {}).get("abilities", {})
            assert any(
                abilities.get(a, {}).get("value", 10) != 10
                for a in ["str", "dex", "con"]
            ), f"Actor {actor['name']} has default stats"

            # Validate has items
            items = actor.get("items", [])
            assert len(items) > 0, f"Actor {actor['name']} has no items"

            print(f"✓ {actor['name']}: {len(items)} items, validated")

    finally:
        # Cleanup
        for actor_info in created:
            await delete_actor(actor_info["uuid"])


@pytest.mark.integration
@pytest.mark.asyncio
async def test_batch_actor_partial_failure():
    """Test that batch continues even if one actor fails."""
    from app.tools.batch_actor_creator import BatchActorCreatorTool
    from app.websocket import delete_actor

    tool = BatchActorCreatorTool()

    # Request includes one very unusual creature that might fail
    response = await tool.execute(
        prompt="Create a goblin and a creature made entirely of pure abstract mathematics"
    )

    # Should still create at least the goblin
    created = response.data.get("created", [])
    assert len(created) >= 1, "Should create at least one actor"

    # Cleanup
    for actor_info in created:
        await delete_actor(actor_info["uuid"])
```

**Step 2: Run integration test**

Run: `cd ui/backend && PYTHONPATH=. pytest tests/integration/test_batch_actor_roundtrip.py -v -s -m integration`
Expected: PASS

**Step 3: Commit**

```bash
git add tests/integration/test_batch_actor_roundtrip.py
git commit -m "test: add integration tests for batch actor roundtrip"
```

---

## Summary

| Task | Files | Purpose |
|------|-------|---------|
| 1 | actor_creator.py | Extract `load_caches()` for reuse |
| 2 | batch_actor_creator.py | Add `parse_actor_requests()` |
| 3 | batch_actor_creator.py | Add `expand_duplicates()` |
| 4 | batch_actor_creator.py | Add `BatchActorCreatorTool` class |
| 5 | __init__.py | Register tool in registry |
| 6 | test_batch_actor_creation.py | Playwright E2E tests |
| 7 | test_batch_actor_roundtrip.py | Integration roundtrip tests |

**Total estimated lines:** ~350 Python

**Note:** Progress streaming (live updates in UI) is intentionally deferred to the fallback plan. This implementation waits for all actors to complete, then shows the final summary. Live updates can be added later if needed.
