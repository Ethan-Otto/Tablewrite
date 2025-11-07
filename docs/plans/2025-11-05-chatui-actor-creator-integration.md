# ChatUI Actor Creator Integration - Design Document

**Date:** 2025-11-05
**Status:** Design Complete
**Context:** Integrate `create_actor()` from public API into ChatUI tool system

## Problem Statement

The new public API (`src/api.py`) provides a `create_actor()` function that creates D&D actors from natural language descriptions and uploads them to FoundryVTT. The ChatUI needs access to this functionality so users can create actors through conversational interface.

**Goal:** Enable ChatUI users to create FoundryVTT actors using natural language (e.g., "create a fierce goblin warrior") via Gemini tool calling.

## Requirements (from Brainstorming)

### Decided Approach
- **Interaction method:** Natural language + Gemini tool calling (no slash commands)
- **UI response:** Text summary with name, CR, UUID (no special UI components)
- **Challenge rating:** Optional parameter - user can specify or let AI infer
- **Loading UX:** Simple loading message (matches existing image generation pattern)
- **Architecture:** New tool following existing pattern (ActorCreatorTool)

### Design Constraints
- Must follow existing tool system pattern (`BaseTool`, `ToolSchema`, `ToolResponse`)
- No frontend changes required
- Must handle 10-30 second execution time gracefully
- Error messages must be clear and actionable

## Architecture

### Component Structure

**New File:** `ui/backend/app/tools/actor_creator.py`

```python
"""Actor creation tool using the public API."""
import sys
from pathlib import Path
from .base import BaseTool, ToolSchema, ToolResponse

# Add project src to path for api module
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))
from api import create_actor, APIError  # noqa: E402


class ActorCreatorTool(BaseTool):
    """Tool for creating D&D actors from descriptions."""

    @property
    def name(self) -> str:
        return "create_actor"

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name="create_actor",
            description=(
                "Create a D&D actor/creature in FoundryVTT from a natural "
                "language description. Use when user asks to create, make, "
                "or generate an actor, monster, NPC, or creature."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "Detailed description of the creature"
                    },
                    "challenge_rating": {
                        "type": "number",
                        "description": "Optional CR (0.125 to 30). Omit to infer from description.",
                        "minimum": 0.125,
                        "maximum": 30
                    }
                },
                "required": ["description"]
            }
        )

    async def execute(self, description: str, challenge_rating: float = None) -> ToolResponse:
        """Execute actor creation."""
        try:
            # Call synchronous API in thread pool (non-blocking)
            import asyncio
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                create_actor,
                description,
                challenge_rating
            )

            # Format text response
            cr_text = f"CR {result.challenge_rating}"
            message = (
                f"Created **{result.name}** ({cr_text})!\n\n"
                f"- **FoundryVTT UUID**: `{result.foundry_uuid}`\n"
                f"- **Output Directory**: `{result.output_dir}`"
            )

            return ToolResponse(
                type="text",
                message=message,
                data=None
            )

        except APIError as e:
            return ToolResponse(
                type="error",
                message=f"Failed to create actor: {str(e)}",
                data=None
            )
```

**Registration:** Add to `ui/backend/app/tools/__init__.py`:
```python
from .actor_creator import ActorCreatorTool
registry.register(ActorCreatorTool())
```

### Data Flow

1. **User Input:** "Create a fierce goblin warrior with CR 1"
2. **Gemini Tool Calling:** Gemini detects intent, calls `create_actor` tool with:
   ```json
   {
     "name": "create_actor",
     "args": {
       "description": "A fierce goblin warrior",
       "challenge_rating": 1.0
     }
   }
   ```
3. **Tool Execution** (10-30 seconds):
   - Calls `create_actor()` from `src/api.py`
   - Runs in thread pool via `run_in_executor()` (non-blocking)
   - Generates stat block using Gemini
   - Parses abilities, attacks, spells
   - Uploads to FoundryVTT
4. **Tool Response:**
   ```python
   ToolResponse(
     type="text",
     message="Created **Goblin Warrior** (CR 1.0)!\n\n- **FoundryVTT UUID**: `Actor.abc123`\n- **Output Directory**: `output/runs/20251105_120000/actors`",
     data=None
   )
   ```
5. **ChatUI Display:** Markdown-formatted text message in chat window

### Integration Points

**No changes needed to:**
- Frontend components (Message.tsx already renders markdown)
- Backend router (tool auto-registers)
- Chat service (tools passed to Gemini automatically)

**Path handling:**
- Uses same `sys.path.insert()` pattern as `ImageGeneratorTool`
- Imports `create_actor()` from `src/api.py`

## Error Handling

### Error Scenarios

1. **Missing API Key:**
   - `APIError("Missing Gemini API key")`
   - User sees: "Failed to create actor: Missing Gemini API key"

2. **FoundryVTT Connection Failed:**
   - `APIError("Failed to upload to FoundryVTT")`
   - Partial results still saved to output directory
   - User gets clear error message with cause

3. **Invalid Challenge Rating:**
   - Gemini schema enforces `0.125 <= CR <= 30`
   - Backend validation catches edge cases
   - Clear error returned

4. **Timeout (30+ seconds):**
   - FastAPI timeout (configurable)
   - User sees timeout error
   - Actor may still complete in background

5. **Gemini Parsing Failure:**
   - Wrapped as `APIError` with `__cause__` preserved
   - User gets actionable message
   - Logs contain full stack trace for debugging

### Loading State

- Gemini streams "Creating actor..." while tool executes
- No special loading UI needed (matches image generation)
- User sees assistant is working

## Example Usage

**User:** "Create a cunning kobold assassin with poisoned daggers, CR 1"

**Gemini calls:**
```json
{
  "tool": "create_actor",
  "args": {
    "description": "A cunning kobold assassin with poisoned daggers",
    "challenge_rating": 1.0
  }
}
```

**ChatUI displays:**
```
Created **Kobold Assassin** (CR 1.0)!

- **FoundryVTT UUID**: `Actor.def456`
- **Output Directory**: `output/runs/20251105_143022/actors`
```

**User can then find actor in FoundryVTT by searching for UUID.**

## Success Criteria

- [ ] User can create actors via natural language
- [ ] Challenge rating can be specified or inferred
- [ ] Tool executes without blocking chat
- [ ] Success message shows name, CR, UUID
- [ ] Errors are clear and actionable
- [ ] No frontend changes needed
- [ ] Follows existing tool system pattern

## Implementation Notes

**Dependencies:**
- Requires `src/api.py` from public-api PR to be merged
- No new backend dependencies
- No new frontend dependencies

**Testing:**
- Manual testing: Start ChatUI, type "create a goblin warrior"
- Verify tool is registered: Check `/docs` endpoint for `create_actor` schema
- Error testing: Remove API key, verify error message
- Load testing: Create multiple actors, ensure no blocking

## Future Enhancements

Possible future improvements (out of scope for initial implementation):
- Rich stat block cards instead of text summary
- Progress streaming ("Generating stat block...", "Uploading...")
- Batch actor creation from lists
- Actor editing/updating via chat
- Preview before uploading to FoundryVTT
