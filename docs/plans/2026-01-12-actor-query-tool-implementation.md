# Actor Query Tool Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create `ActorQueryTool` that fetches full actor data from Foundry and answers questions about abilities, attacks, and stats using Gemini.

**Architecture:** Tool fetches actor via existing `fetch_actor()` WebSocket function, extracts structured content (abilities, items, spells), formats for Gemini, and returns a natural language answer. Follows the same patterns as `JournalQueryTool`.

**Tech Stack:** Python, FastAPI, Pydantic, Gemini 2.0 Flash

---

### Task 1: Create Actor Query Tool Skeleton

**Files:**
- Create: `ui/backend/app/tools/actor_query.py`
- Modify: `ui/backend/app/tools/__init__.py`

**Step 1: Write the failing test**

Create file `ui/backend/tests/tools/test_actor_query.py`:

```python
"""Unit tests for ActorQueryTool."""
import pytest


class TestActorQueryToolSchema:
    """Test ActorQueryTool schema."""

    def test_tool_name(self):
        """Test tool has correct name."""
        from app.tools.actor_query import ActorQueryTool

        tool = ActorQueryTool()
        assert tool.name == "query_actor"

    def test_get_schema_returns_tool_schema(self):
        """Test get_schema returns valid ToolSchema."""
        from app.tools.actor_query import ActorQueryTool
        from app.tools.base import ToolSchema

        tool = ActorQueryTool()
        schema = tool.get_schema()

        assert isinstance(schema, ToolSchema)
        assert schema.name == "query_actor"
        assert "actor_uuid" in schema.parameters["properties"]
        assert "query" in schema.parameters["properties"]
        assert "query_type" in schema.parameters["properties"]

    def test_schema_query_type_enum(self):
        """Test query_type has correct enum values."""
        from app.tools.actor_query import ActorQueryTool

        tool = ActorQueryTool()
        schema = tool.get_schema()

        query_type = schema.parameters["properties"]["query_type"]
        assert query_type["enum"] == ["abilities", "combat", "general"]
```

**Step 2: Run test to verify it fails**

Run: `cd ui/backend && uv run pytest tests/tools/test_actor_query.py::TestActorQueryToolSchema -v`

Expected: FAIL with "No module named 'app.tools.actor_query'"

**Step 3: Write minimal implementation**

Create file `ui/backend/app/tools/actor_query.py`:

```python
"""Actor query tool for answering questions about actor abilities and stats."""
import logging
from typing import Optional

from .base import BaseTool, ToolSchema, ToolResponse

logger = logging.getLogger(__name__)


class ActorQueryTool(BaseTool):
    """Tool for querying actors to answer questions about abilities, attacks, and stats."""

    @property
    def name(self) -> str:
        return "query_actor"

    def get_schema(self) -> ToolSchema:
        """Return tool schema for Gemini function calling."""
        return ToolSchema(
            name="query_actor",
            description=(
                "Query a Foundry actor to answer questions about its abilities, attacks, "
                "spells, or stats. Use when user @mentions an actor and asks about what "
                "it can do, its combat abilities, or specific stats. The actor_uuid should "
                "come from the mentioned_entities context."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "actor_uuid": {
                        "type": "string",
                        "description": "The actor UUID from @mention (e.g., 'Actor.abc123')"
                    },
                    "query": {
                        "type": "string",
                        "description": "The user's question about the actor"
                    },
                    "query_type": {
                        "type": "string",
                        "enum": ["abilities", "combat", "general"],
                        "description": "Type of query: abilities for stats/skills, combat for attacks/spells, general for other info"
                    }
                },
                "required": ["actor_uuid", "query", "query_type"]
            }
        )

    async def execute(
        self,
        actor_uuid: str,
        query: str,
        query_type: str
    ) -> ToolResponse:
        """
        Execute actor query.

        Args:
            actor_uuid: Actor UUID from @mention
            query: User's question about the actor
            query_type: One of "abilities", "combat", "general"

        Returns:
            ToolResponse with answer about the actor
        """
        # Placeholder - will implement in next task
        return ToolResponse(
            type="error",
            message="Not implemented yet",
            data=None
        )
```

**Step 4: Run test to verify it passes**

Run: `cd ui/backend && uv run pytest tests/tools/test_actor_query.py::TestActorQueryToolSchema -v`

Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add ui/backend/app/tools/actor_query.py ui/backend/tests/tools/test_actor_query.py
git commit -m "$(cat <<'EOF'
feat(tools): add ActorQueryTool skeleton

Add basic tool structure with schema for querying actors about
abilities, combat, and general information.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Register Tool and Add to Exports

**Files:**
- Modify: `ui/backend/app/tools/__init__.py`

**Step 1: Write the failing test**

Add to `ui/backend/tests/tools/test_actor_query.py`:

```python
class TestActorQueryToolRegistration:
    """Test ActorQueryTool is properly registered."""

    def test_tool_in_registry(self):
        """Test tool is registered in the tool registry."""
        from app.tools import registry

        tool = registry.get_tool("query_actor")
        assert tool is not None
        assert tool.name == "query_actor"

    def test_tool_in_exports(self):
        """Test tool is exported from package."""
        from app.tools import ActorQueryTool

        assert ActorQueryTool is not None
```

**Step 2: Run test to verify it fails**

Run: `cd ui/backend && uv run pytest tests/tools/test_actor_query.py::TestActorQueryToolRegistration -v`

Expected: FAIL with "cannot import name 'ActorQueryTool'"

**Step 3: Write minimal implementation**

Edit `ui/backend/app/tools/__init__.py` to add imports and registration:

After the existing imports (around line 14), add:
```python
from .actor_query import ActorQueryTool
```

After the existing registry.register calls (around line 29), add:
```python
registry.register(ActorQueryTool())
```

Add to `__all__` list:
```python
'ActorQueryTool',
```

**Step 4: Run test to verify it passes**

Run: `cd ui/backend && uv run pytest tests/tools/test_actor_query.py::TestActorQueryToolRegistration -v`

Expected: PASS (2 tests)

**Step 5: Commit**

```bash
git add ui/backend/app/tools/__init__.py ui/backend/tests/tools/test_actor_query.py
git commit -m "$(cat <<'EOF'
feat(tools): register ActorQueryTool in tool registry

Export and register the tool so it's available for Gemini
function calling.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Implement Actor Content Extraction

**Files:**
- Modify: `ui/backend/app/tools/actor_query.py`

**Step 1: Write the failing test**

Add to `ui/backend/tests/tools/test_actor_query.py`:

```python
class TestActorContentExtraction:
    """Test extracting structured content from actor data."""

    def test_extract_basic_info(self):
        """Test extracting basic actor info (name, CR, type, AC, HP)."""
        from app.tools.actor_query import ActorQueryTool

        tool = ActorQueryTool()

        actor = {
            "name": "Grolak the Quick",
            "system": {
                "details": {
                    "cr": 0.25,
                    "type": {"value": "humanoid", "subtype": "goblinoid"},
                    "alignment": "neutral evil"
                },
                "attributes": {
                    "ac": {"value": 15},
                    "hp": {"value": 7, "max": 7}
                }
            }
        }

        content = tool._extract_actor_content(actor)

        assert "Grolak the Quick" in content
        assert "CR: 0.25" in content
        assert "humanoid" in content
        assert "AC: 15" in content
        assert "HP: 7" in content

    def test_extract_abilities(self):
        """Test extracting ability scores."""
        from app.tools.actor_query import ActorQueryTool

        tool = ActorQueryTool()

        actor = {
            "name": "Test Actor",
            "system": {
                "abilities": {
                    "str": {"value": 8, "mod": -1},
                    "dex": {"value": 14, "mod": 2},
                    "con": {"value": 10, "mod": 0},
                    "int": {"value": 10, "mod": 0},
                    "wis": {"value": 8, "mod": -1},
                    "cha": {"value": 7, "mod": -2}
                },
                "details": {},
                "attributes": {}
            }
        }

        content = tool._extract_actor_content(actor)

        assert "STR: 8 (-1)" in content
        assert "DEX: 14 (+2)" in content
        assert "CHA: 7 (-2)" in content

    def test_extract_weapons(self):
        """Test extracting weapon items."""
        from app.tools.actor_query import ActorQueryTool

        tool = ActorQueryTool()

        actor = {
            "name": "Test Actor",
            "system": {"details": {}, "attributes": {}, "abilities": {}},
            "items": [
                {
                    "name": "Shortsword",
                    "type": "weapon",
                    "system": {
                        "attack": {"bonus": 4},
                        "damage": {"parts": [["1d6+2", "piercing"]]},
                        "range": {"value": 5, "units": "ft"},
                        "actionType": "mwak"
                    }
                }
            ]
        }

        content = tool._extract_actor_content(actor)

        assert "Shortsword" in content
        assert "+4 to hit" in content
        assert "1d6+2 piercing" in content

    def test_extract_special_abilities(self):
        """Test extracting feat/feature items."""
        from app.tools.actor_query import ActorQueryTool

        tool = ActorQueryTool()

        actor = {
            "name": "Test Actor",
            "system": {"details": {}, "attributes": {}, "abilities": {}},
            "items": [
                {
                    "name": "Nimble Escape",
                    "type": "feat",
                    "system": {
                        "activation": {"type": "bonus"},
                        "description": {"value": "Can take Disengage or Hide as bonus action"}
                    }
                }
            ]
        }

        content = tool._extract_actor_content(actor)

        assert "Nimble Escape" in content
        assert "Bonus Action" in content or "bonus" in content.lower()
```

**Step 2: Run test to verify it fails**

Run: `cd ui/backend && uv run pytest tests/tools/test_actor_query.py::TestActorContentExtraction -v`

Expected: FAIL with "AttributeError: 'ActorQueryTool' object has no attribute '_extract_actor_content'"

**Step 3: Write minimal implementation**

Add to `ui/backend/app/tools/actor_query.py` (inside the class, after `execute`):

```python
    def _extract_actor_content(self, actor: dict) -> str:
        """
        Extract structured content from actor data for Gemini.

        Args:
            actor: Full actor dict from Foundry

        Returns:
            Formatted string with actor information
        """
        sections = []

        # Basic info
        name = actor.get("name", "Unknown")
        system = actor.get("system", {})
        details = system.get("details", {})
        attributes = system.get("attributes", {})

        # CR and type
        cr = details.get("cr", "?")
        actor_type = details.get("type", {})
        type_value = actor_type.get("value", "unknown") if isinstance(actor_type, dict) else str(actor_type)
        subtype = actor_type.get("subtype", "") if isinstance(actor_type, dict) else ""
        type_str = f"{type_value} ({subtype})" if subtype else type_value

        # AC and HP
        ac = attributes.get("ac", {}).get("value", "?")
        hp_data = attributes.get("hp", {})
        hp = hp_data.get("value", hp_data.get("max", "?"))

        sections.append(f"[ACTOR: {name}]")
        sections.append(f"CR: {cr} | Type: {type_str} | AC: {ac} | HP: {hp}")

        # Abilities
        abilities = system.get("abilities", {})
        if abilities:
            ability_strs = []
            for stat in ["str", "dex", "con", "int", "wis", "cha"]:
                if stat in abilities:
                    val = abilities[stat].get("value", 10)
                    mod = abilities[stat].get("mod", 0)
                    sign = "+" if mod >= 0 else ""
                    ability_strs.append(f"{stat.upper()}: {val} ({sign}{mod})")
            if ability_strs:
                sections.append("\n[ABILITIES]")
                sections.append(" | ".join(ability_strs))

        # Items (weapons, feats, spells)
        items = actor.get("items", [])
        weapons = []
        feats = []
        spells = []

        for item in items:
            item_type = item.get("type", "")
            item_name = item.get("name", "Unknown")
            item_system = item.get("system", {})

            if item_type == "weapon":
                attack_bonus = item_system.get("attack", {}).get("bonus", 0)
                damage_parts = item_system.get("damage", {}).get("parts", [])
                damage_str = ", ".join(f"{d[0]} {d[1]}" for d in damage_parts) if damage_parts else "?"
                range_val = item_system.get("range", {}).get("value", "")
                range_units = item_system.get("range", {}).get("units", "")
                range_str = f"{range_val} {range_units}" if range_val else ""

                weapons.append(f"- {item_name}: +{attack_bonus} to hit, {damage_str}" + (f" ({range_str})" if range_str else ""))

            elif item_type == "feat":
                activation = item_system.get("activation", {}).get("type", "")
                activation_str = activation.replace("bonus", "Bonus Action").replace("action", "Action") if activation else ""
                feats.append(f"- {item_name}" + (f" ({activation_str})" if activation_str else ""))

            elif item_type == "spell":
                level = item_system.get("level", 0)
                school = item_system.get("school", "")
                spells.append(f"- {item_name} (Level {level}, {school})")

        if weapons:
            sections.append("\n[COMBAT]")
            sections.extend(weapons)

        if feats:
            sections.append("\n[SPECIAL ABILITIES]")
            sections.extend(feats)

        if spells:
            sections.append("\n[SPELLS]")
            sections.extend(spells)

        return "\n".join(sections)
```

**Step 4: Run test to verify it passes**

Run: `cd ui/backend && uv run pytest tests/tools/test_actor_query.py::TestActorContentExtraction -v`

Expected: PASS (4 tests)

**Step 5: Commit**

```bash
git add ui/backend/app/tools/actor_query.py ui/backend/tests/tools/test_actor_query.py
git commit -m "$(cat <<'EOF'
feat(tools): implement actor content extraction

Extract structured data from Foundry actor format:
- Basic info (name, CR, type, AC, HP)
- Ability scores with modifiers
- Weapons with attack bonus and damage
- Special abilities with activation type

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Implement Prompt Building

**Files:**
- Modify: `ui/backend/app/tools/actor_query.py`

**Step 1: Write the failing test**

Add to `ui/backend/tests/tools/test_actor_query.py`:

```python
class TestPromptBuilding:
    """Test prompt building for different query types."""

    def test_build_abilities_prompt(self):
        """Test building prompt for abilities query type."""
        from app.tools.actor_query import ActorQueryTool

        tool = ActorQueryTool()

        prompt = tool._build_prompt(
            query="What are this creature's stats?",
            query_type="abilities",
            content="[ACTOR: Goblin]\nSTR: 8 (-1) | DEX: 14 (+2)"
        )

        assert "What are this creature's stats?" in prompt
        assert "Goblin" in prompt
        assert "ability scores" in prompt.lower() or "abilities" in prompt.lower()

    def test_build_combat_prompt(self):
        """Test building prompt for combat query type."""
        from app.tools.actor_query import ActorQueryTool

        tool = ActorQueryTool()

        prompt = tool._build_prompt(
            query="What attacks can this monster make?",
            query_type="combat",
            content="[ACTOR: Goblin]\n[COMBAT]\n- Shortsword: +4 to hit"
        )

        assert "attacks" in prompt.lower() or "combat" in prompt.lower()
        assert "Shortsword" in prompt

    def test_build_general_prompt(self):
        """Test building prompt for general query type."""
        from app.tools.actor_query import ActorQueryTool

        tool = ActorQueryTool()

        prompt = tool._build_prompt(
            query="Tell me about this creature",
            query_type="general",
            content="[ACTOR: Goblin]\nCR: 0.25"
        )

        assert "Tell me about this creature" in prompt
        assert "Goblin" in prompt
```

**Step 2: Run test to verify it fails**

Run: `cd ui/backend && uv run pytest tests/tools/test_actor_query.py::TestPromptBuilding -v`

Expected: FAIL with "AttributeError: 'ActorQueryTool' object has no attribute '_build_prompt'"

**Step 3: Write minimal implementation**

Add to `ui/backend/app/tools/actor_query.py` (inside the class):

```python
    def _build_prompt(self, query: str, query_type: str, content: str) -> str:
        """
        Build a prompt for Gemini based on query type.

        Args:
            query: User's question
            query_type: One of "abilities", "combat", "general"
            content: Extracted actor content

        Returns:
            Formatted prompt string
        """
        base_instructions = """You are a D&D assistant answering questions about a specific actor/creature.
Answer based ONLY on the provided actor data. Be concise and helpful.

Actor Data:
"""

        if query_type == "abilities":
            task = """

Focus on the creature's ability scores, skills, saving throws, and any passive abilities.
Explain what these stats mean for the creature's capabilities.

Question: """

        elif query_type == "combat":
            task = """

Focus on the creature's attacks, weapons, spells, and combat-related abilities.
Explain damage, attack bonuses, and tactical capabilities.

Question: """

        else:  # general
            task = """

Provide a helpful overview based on the question.

Question: """

        return base_instructions + content + task + query + "\n\nAnswer:"
```

**Step 4: Run test to verify it passes**

Run: `cd ui/backend && uv run pytest tests/tools/test_actor_query.py::TestPromptBuilding -v`

Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add ui/backend/app/tools/actor_query.py ui/backend/tests/tools/test_actor_query.py
git commit -m "$(cat <<'EOF'
feat(tools): implement actor query prompt building

Build context-aware prompts for abilities, combat, and general
query types.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Implement Full Execute Method

**Files:**
- Modify: `ui/backend/app/tools/actor_query.py`

**Step 1: Write the failing test**

Add to `ui/backend/tests/tools/test_actor_query.py`:

```python
class TestExecuteMethod:
    """Test the execute method with mocked dependencies."""

    @pytest.mark.asyncio
    async def test_execute_returns_error_for_missing_actor(self):
        """Test execute returns error when actor not found."""
        from app.tools.actor_query import ActorQueryTool
        from unittest.mock import AsyncMock, patch

        tool = ActorQueryTool()

        # Mock fetch_actor to return failure
        mock_result = AsyncMock()
        mock_result.success = False
        mock_result.error = "Actor not found"

        with patch("app.tools.actor_query.fetch_actor", return_value=mock_result):
            response = await tool.execute(
                actor_uuid="Actor.nonexistent",
                query="What can this do?",
                query_type="general"
            )

        assert response.type == "error"
        assert "not found" in response.message.lower() or "failed" in response.message.lower()

    @pytest.mark.asyncio
    async def test_execute_returns_answer_for_valid_actor(self):
        """Test execute returns answer for valid actor."""
        from app.tools.actor_query import ActorQueryTool
        from unittest.mock import AsyncMock, patch, MagicMock

        tool = ActorQueryTool()

        # Mock fetch_actor to return success
        mock_fetch_result = AsyncMock()
        mock_fetch_result.success = True
        mock_fetch_result.entity = {
            "name": "Goblin",
            "system": {
                "details": {"cr": 0.25, "type": {"value": "humanoid"}},
                "attributes": {"ac": {"value": 15}, "hp": {"value": 7}},
                "abilities": {
                    "str": {"value": 8, "mod": -1},
                    "dex": {"value": 14, "mod": 2},
                    "con": {"value": 10, "mod": 0},
                    "int": {"value": 10, "mod": 0},
                    "wis": {"value": 8, "mod": -1},
                    "cha": {"value": 8, "mod": -1}
                }
            },
            "items": []
        }

        # Mock Gemini response
        mock_gemini = MagicMock()
        mock_gemini.generate_content.return_value.text = "The goblin is a small humanoid with decent dexterity."

        with patch("app.tools.actor_query.fetch_actor", return_value=mock_fetch_result):
            with patch("app.tools.actor_query.GeminiAPI", return_value=mock_gemini):
                response = await tool.execute(
                    actor_uuid="Actor.abc123",
                    query="What is this creature?",
                    query_type="general"
                )

        assert response.type == "text"
        assert "goblin" in response.message.lower()
```

**Step 2: Run test to verify it fails**

Run: `cd ui/backend && uv run pytest tests/tools/test_actor_query.py::TestExecuteMethod -v`

Expected: FAIL (current execute returns "Not implemented yet")

**Step 3: Write minimal implementation**

Update the `execute` method in `ui/backend/app/tools/actor_query.py`:

First, add the imports at the top of the file:
```python
import asyncio
from app.websocket import fetch_actor
```

Then add GeminiAPI import after the project path setup (we need to follow the pattern from journal_query.py):
```python
import sys
from pathlib import Path

# Add project src to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from util.gemini import GeminiAPI  # noqa: E402
```

Replace the `execute` method:

```python
    async def execute(
        self,
        actor_uuid: str,
        query: str,
        query_type: str
    ) -> ToolResponse:
        """
        Execute actor query.

        Args:
            actor_uuid: Actor UUID from @mention
            query: User's question about the actor
            query_type: One of "abilities", "combat", "general"

        Returns:
            ToolResponse with answer about the actor
        """
        try:
            # 1. Fetch the actor from Foundry
            result = await fetch_actor(actor_uuid)

            if not result.success:
                return ToolResponse(
                    type="error",
                    message=f"Failed to fetch actor: {result.error or 'Actor not found'}",
                    data=None
                )

            actor = result.entity

            # 2. Extract structured content
            content = self._extract_actor_content(actor)

            # 3. Build prompt and query Gemini
            prompt = self._build_prompt(query, query_type, content)
            answer = await self._query_gemini(prompt)

            # 4. Return formatted response
            return ToolResponse(
                type="text",
                message=answer,
                data={
                    "actor_name": actor.get("name"),
                    "actor_uuid": actor_uuid,
                    "query_type": query_type
                }
            )

        except Exception as e:
            logger.error(f"Actor query failed: {e}")
            return ToolResponse(
                type="error",
                message=f"Failed to query actor: {str(e)}",
                data=None
            )

    async def _query_gemini(self, prompt: str) -> str:
        """Send prompt to Gemini and get response."""
        def _generate():
            api = GeminiAPI(model_name="gemini-2.0-flash")
            return api.generate_content(prompt).text

        return await asyncio.to_thread(_generate)
```

**Step 4: Run test to verify it passes**

Run: `cd ui/backend && uv run pytest tests/tools/test_actor_query.py::TestExecuteMethod -v`

Expected: PASS (2 tests)

**Step 5: Commit**

```bash
git add ui/backend/app/tools/actor_query.py ui/backend/tests/tools/test_actor_query.py
git commit -m "$(cat <<'EOF'
feat(tools): implement ActorQueryTool execute method

Full implementation that:
- Fetches actor via WebSocket
- Extracts structured content
- Queries Gemini with context-aware prompt
- Returns formatted answer

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: Add API Router Endpoint

**Files:**
- Modify: `ui/backend/app/routers/tools.py`

**Step 1: Write the failing test**

Add to `ui/backend/tests/tools/test_actor_query.py`:

```python
import httpx


class TestActorQueryRouter:
    """Test the /api/tools/query_actor endpoint."""

    @pytest.fixture
    def backend_client(self):
        """HTTP client for backend API calls."""
        return httpx.Client(base_url="http://localhost:8000", timeout=60.0)

    @pytest.mark.integration
    def test_query_actor_endpoint_exists(self, backend_client):
        """Test that the endpoint exists and accepts POST."""
        # This will fail if endpoint doesn't exist (404) or wrong method (405)
        response = backend_client.post(
            "/api/tools/query_actor",
            json={
                "actor_uuid": "Actor.test123",
                "query": "What can this do?",
                "query_type": "general"
            }
        )
        # 200 = success, 400 = bad request (validation), anything else is a problem
        assert response.status_code in [200, 400, 500], f"Unexpected status: {response.status_code}"
```

**Step 2: Run test to verify it fails**

Run: `cd ui/backend && uv run pytest tests/tools/test_actor_query.py::TestActorQueryRouter::test_query_actor_endpoint_exists -v`

Expected: FAIL with 404 (endpoint not found)

**Step 3: Write minimal implementation**

Add to `ui/backend/app/routers/tools.py`:

After `JournalQueryRequest` class (around line 32), add:

```python
class ActorQueryRequest(BaseModel):
    """Request model for query_actor tool."""
    actor_uuid: str
    query: str
    query_type: str  # "abilities", "combat", "general"
```

After the `execute_query_journal` endpoint (at the end of the file), add:

```python
@router.post("/query_actor", response_model=ToolResponse)
async def execute_query_actor(request: ActorQueryRequest) -> ToolResponse:
    """
    Execute the query_actor tool directly.

    This endpoint is used when the AI calls the query_actor tool
    to answer questions about an @mentioned actor.
    """
    try:
        result = await registry.execute_tool(
            "query_actor",
            actor_uuid=request.actor_uuid,
            query=request.query,
            query_type=request.query_type
        )

        return ToolResponse(
            type=result.type,
            message=result.message,
            data=result.data
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

**Step 4: Run test to verify it passes**

Run: `cd ui/backend && uv run pytest tests/tools/test_actor_query.py::TestActorQueryRouter::test_query_actor_endpoint_exists -v`

Expected: PASS (endpoint returns 200 or 500, not 404)

**Step 5: Commit**

```bash
git add ui/backend/app/routers/tools.py ui/backend/tests/tools/test_actor_query.py
git commit -m "$(cat <<'EOF'
feat(api): add /api/tools/query_actor endpoint

Expose ActorQueryTool via REST API for direct invocation
and Gemini function calling.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: Create Integration Test with Real Actor

**Files:**
- Create: `ui/backend/tests/tools/test_actor_query_integration.py`

**Step 1: Write the failing test**

Create file `ui/backend/tests/tools/test_actor_query_integration.py`:

```python
"""Integration tests for ActorQueryTool with real Foundry data."""
import pytest
import httpx
import os

from tests.conftest import check_backend_and_foundry, get_or_create_test_folder

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_query_actor_roundtrip():
    """
    Integration test: Create a test actor, query it, verify answer contains expected info.

    1. Create a test actor with known stats
    2. Query the actor's abilities
    3. Verify the answer mentions the expected stats
    4. Delete the test actor
    """
    await check_backend_and_foundry()

    folder_id = await get_or_create_test_folder("Actor")

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Create test actor with known stats
        actor_data = {
            "name": "Test Query Goblin",
            "type": "npc",
            "folder": folder_id,
            "system": {
                "details": {
                    "cr": 0.25,
                    "type": {"value": "humanoid", "subtype": "goblinoid"}
                },
                "attributes": {
                    "ac": {"value": 15},
                    "hp": {"value": 7, "max": 7}
                },
                "abilities": {
                    "str": {"value": 8, "mod": -1},
                    "dex": {"value": 14, "mod": 2},
                    "con": {"value": 10, "mod": 0},
                    "int": {"value": 10, "mod": 0},
                    "wis": {"value": 8, "mod": -1},
                    "cha": {"value": 8, "mod": -1}
                }
            }
        }

        create_response = await client.post(
            f"{BACKEND_URL}/api/foundry/actor",
            json=actor_data
        )
        assert create_response.status_code == 200, f"Failed to create actor: {create_response.text}"
        actor_uuid = create_response.json()["uuid"]

        try:
            # Query the actor's abilities
            query_response = await client.post(
                f"{BACKEND_URL}/api/tools/query_actor",
                json={
                    "actor_uuid": actor_uuid,
                    "query": "What are this creature's ability scores?",
                    "query_type": "abilities"
                }
            )
            assert query_response.status_code == 200, f"Query failed: {query_response.text}"

            data = query_response.json()
            assert data["type"] == "text", f"Expected text response, got: {data['type']}"

            message = data["message"].lower()
            # Verify the answer mentions key stats
            assert "dex" in message or "dexterity" in message or "14" in message, \
                f"Expected DEX info in response: {data['message']}"

        finally:
            # Clean up: delete the test actor
            delete_response = await client.delete(
                f"{BACKEND_URL}/api/foundry/actor/{actor_uuid}"
            )
            assert delete_response.status_code == 200, f"Failed to delete actor: {delete_response.text}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_query_actor_combat_info():
    """Test querying actor's combat abilities."""
    await check_backend_and_foundry()

    folder_id = await get_or_create_test_folder("Actor")

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Create actor with weapon
        actor_data = {
            "name": "Test Combat Goblin",
            "type": "npc",
            "folder": folder_id,
            "system": {
                "details": {"cr": 0.25},
                "attributes": {"ac": {"value": 15}, "hp": {"value": 7}}
            },
            "items": [
                {
                    "name": "Scimitar",
                    "type": "weapon",
                    "system": {
                        "attack": {"bonus": 4},
                        "damage": {"parts": [["1d6+2", "slashing"]]},
                        "actionType": "mwak"
                    }
                }
            ]
        }

        create_response = await client.post(
            f"{BACKEND_URL}/api/foundry/actor",
            json=actor_data
        )
        assert create_response.status_code == 200, f"Failed to create actor: {create_response.text}"
        actor_uuid = create_response.json()["uuid"]

        try:
            # Query combat abilities
            query_response = await client.post(
                f"{BACKEND_URL}/api/tools/query_actor",
                json={
                    "actor_uuid": actor_uuid,
                    "query": "What attacks can this creature make?",
                    "query_type": "combat"
                }
            )
            assert query_response.status_code == 200

            data = query_response.json()
            assert data["type"] == "text"

            message = data["message"].lower()
            # Should mention the weapon
            assert "scimitar" in message or "slashing" in message or "attack" in message, \
                f"Expected combat info in response: {data['message']}"

        finally:
            await client.delete(f"{BACKEND_URL}/api/foundry/actor/{actor_uuid}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_query_nonexistent_actor():
    """Test querying a non-existent actor returns error."""
    await check_backend_and_foundry()

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{BACKEND_URL}/api/tools/query_actor",
            json={
                "actor_uuid": "Actor.nonexistent123",
                "query": "What can this do?",
                "query_type": "general"
            }
        )

        assert response.status_code == 200  # Tool returns error in response, not HTTP error
        data = response.json()
        assert data["type"] == "error", f"Expected error response for nonexistent actor: {data}"
```

**Step 2: Run test to verify it fails (or passes if implementation is complete)**

Run: `cd ui/backend && uv run pytest tests/tools/test_actor_query_integration.py -v`

Expected: Tests should pass if Foundry is connected, otherwise FAIL with connection error

**Step 3: Commit**

```bash
git add ui/backend/tests/tools/test_actor_query_integration.py
git commit -m "$(cat <<'EOF'
test(tools): add ActorQueryTool integration tests

Round-trip tests that:
- Create actor in /tests folder
- Query abilities and combat info
- Verify responses contain expected data
- Clean up test actors

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 8: Update Gemini Service System Prompt

**Files:**
- Modify: `ui/backend/app/services/gemini_service.py`

**Step 1: Write the failing test**

Add to `ui/backend/tests/tools/test_actor_query.py`:

```python
class TestGeminiSystemPrompt:
    """Test that system prompt includes actor query instructions."""

    def test_system_prompt_mentions_actor_query(self):
        """Test that the system prompt instructs AI to use query_actor tool."""
        from app.services.gemini_service import GeminiService

        service = GeminiService()
        prompt = service._build_chat_prompt("test", {}, [])

        # Should mention the query_actor tool
        assert "query_actor" in prompt or "@mention" in prompt.lower(), \
            "System prompt should mention actor querying"
```

**Step 2: Run test to verify it fails**

Run: `cd ui/backend && uv run pytest tests/tools/test_actor_query.py::TestGeminiSystemPrompt -v`

Expected: FAIL (prompt doesn't mention query_actor yet)

**Step 3: Write minimal implementation**

Edit `ui/backend/app/services/gemini_service.py`, in the `_build_chat_prompt` method.

Find the section with "CRITICAL TOOL USAGE" (around line 264) and add after the journal queries section:

```python
5. **ACTOR QUERIES**: When the user @mentions an actor and asks about its abilities, attacks, stats, or what it can do - you MUST call the query_actor tool. The actor_uuid will be provided in the mentioned_entities context.
   - "@[Dire Wolf](Actor.xyz) What can this creature do" → call query_actor
   - "@[Goblin](Actor.abc) What attacks does it have" → call query_actor
   - "Tell me about @[Dragon](Actor.123)'s abilities" → call query_actor
```

**Step 4: Run test to verify it passes**

Run: `cd ui/backend && uv run pytest tests/tools/test_actor_query.py::TestGeminiSystemPrompt -v`

Expected: PASS

**Step 5: Commit**

```bash
git add ui/backend/app/services/gemini_service.py ui/backend/tests/tools/test_actor_query.py
git commit -m "$(cat <<'EOF'
feat(ai): add query_actor to Gemini system prompt

Instruct AI to use query_actor tool when users @mention an actor
and ask about abilities, attacks, or stats.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 9: Run Full Test Suite

**Files:**
- None (verification only)

**Step 1: Run all actor query tests**

Run: `cd ui/backend && uv run pytest tests/tools/test_actor_query.py tests/tools/test_actor_query_integration.py -v`

Expected: All tests pass

**Step 2: Run smoke tests**

Run: `cd ui/backend && uv run pytest -m smoke -v`

Expected: All smoke tests pass

**Step 3: Run full test suite**

Run: `cd ui/backend && uv run pytest --full -x`

Expected: All tests pass

**Step 4: Commit (if any fixes were needed)**

Only if fixes were made during this step.

---

### Task 10: Final Verification and Cleanup

**Step 1: Verify tool appears in registry**

Run: `cd ui/backend && python -c "from app.tools import registry; print([t.name for t in registry.list_tools()])"`

Expected: Output includes "query_actor"

**Step 2: Test manually via API**

Run:
```bash
curl -X POST http://localhost:8000/api/tools/query_actor \
  -H "Content-Type: application/json" \
  -d '{"actor_uuid": "Actor.SOME_REAL_UUID", "query": "What can this creature do?", "query_type": "general"}'
```

Expected: Returns JSON with actor information

**Step 3: Final commit with complete implementation**

```bash
git log --oneline -10  # Review commits
git status  # Ensure clean working directory
```

---

## Summary

This plan implements the ActorQueryTool in 10 tasks:

1. **Skeleton** - Basic tool class with schema
2. **Registration** - Add to registry and exports
3. **Content Extraction** - Parse Foundry actor structure
4. **Prompt Building** - Context-aware prompts for query types
5. **Execute Method** - Full implementation with Gemini
6. **API Router** - REST endpoint for direct invocation
7. **Integration Tests** - Round-trip tests with real actors
8. **System Prompt** - Instruct AI to use the tool
9. **Test Suite** - Verify all tests pass
10. **Final Verification** - Manual testing and cleanup

Each task follows TDD: write failing test, implement, verify, commit.
