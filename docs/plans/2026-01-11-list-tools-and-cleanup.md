# List Tools and Cleanup Plan

**Goal:** Add basic listing tools for actors/scenes, add help tool, and clean up dead code.

---

## Task 1: Create ListActorsTool

**Files:**
- Create: `ui/backend/app/tools/list_actors.py`

**Implementation:**
```python
"""List actors tool."""
from .base import BaseTool, ToolSchema, ToolResponse
from app.websocket import list_actors

class ListActorsTool(BaseTool):
    @property
    def name(self) -> str:
        return "list_actors"

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name="list_actors",
            description="List all actors in the world with clickable links",
            parameters={"type": "object", "properties": {}, "required": []}
        )

    async def execute(self) -> ToolResponse:
        result = await list_actors()
        if not result.success:
            return ToolResponse(type="error", message=result.error, data=None)

        if not result.actors:
            return ToolResponse(type="text", message="No actors found.", data=None)

        lines = [f"**Actors ({len(result.actors)}):**\n"]
        for actor in result.actors:
            lines.append(f"- @UUID[{actor.uuid}]{{{actor.name}}}")

        return ToolResponse(
            type="text",
            message="\n".join(lines),
            data={"actors": [{"uuid": a.uuid, "name": a.name} for a in result.actors]}
        )
```

---

## Task 2: Create ListScenesTool

**Files:**
- Create: `ui/backend/app/tools/list_scenes.py`

**Implementation:**
Same pattern as ListActorsTool, calling `list_scenes()` instead.

---

## Task 3: Create HelpTool

**Files:**
- Create: `ui/backend/app/tools/help.py`

**Implementation:**
```python
"""Help tool - lists all available tools."""
from .base import BaseTool, ToolSchema, ToolResponse
from .registry import registry

class HelpTool(BaseTool):
    @property
    def name(self) -> str:
        return "help"

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name="help",
            description="List all available tools and commands",
            parameters={"type": "object", "properties": {}, "required": []}
        )

    async def execute(self) -> ToolResponse:
        schemas = registry.get_schemas()
        lines = ["**Available Tools:**\n"]
        for schema in schemas:
            lines.append(f"- **{schema.name}**: {schema.description}")

        return ToolResponse(type="text", message="\n".join(lines), data=None)
```

---

## Task 4: Register New Tools

**Files:**
- Modify: `ui/backend/app/tools/__init__.py`

Add imports and register:
```python
from .list_actors import ListActorsTool
from .list_scenes import ListScenesTool
from .help import HelpTool

registry.register(ListActorsTool())
registry.register(ListScenesTool())
registry.register(HelpTool())
```

---

## Task 5: Remove Placeholder Chat Commands

**Files:**
- Modify: `ui/backend/app/routers/chat.py`

Remove:
- `_handle_list_scenes()` function (lines 179-191)
- `_handle_list_actors()` function (lines 194-206)
- `CommandType.LIST_SCENES` and `CommandType.LIST_ACTORS` handlers in `chat()`

The tools will handle these now via natural language ("list actors", "show scenes").

---

## Task 6: Clean Up src/api.py Stubs

**Files:**
- Modify: `src/api.py`

Remove stub functions that just raise errors:
- `extract_maps()` - tells users to use library directly
- `process_pdf_to_journal()` - tells users to use CLI

These are misleading since the functionality exists elsewhere. Either implement them properly or remove them from the public API.

**Decision:** Remove them. The Module tab UI handles PDF processing, and direct library imports work for scripts.

---

## Verification

After implementation:
1. Run smoke tests: `pytest`
2. Test in Foundry chat:
   - "list actors" → should show actor links
   - "list scenes" → should show scene links
   - "help" → should show all tools
