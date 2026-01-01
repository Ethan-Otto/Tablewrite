# ChatUI Actor Creator Tool Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add `create_actor` tool to ChatUI enabling users to create D&D actors via natural language

**Architecture:** New tool class (`ActorCreatorTool`) following existing tool system pattern. Imports `create_actor()` from `src/api.py`, runs in thread pool to avoid blocking, returns text-formatted response.

**Tech Stack:** FastAPI, Python asyncio, existing tool registry system, public API module

---

## Prerequisites

- Public API PR must be merged (contains `src/api.py` with `create_actor()`)
- Working in `.worktrees/public-api` directory
- ChatUI backend dependencies installed (`ui/backend/requirements.txt`)
- FoundryVTT server running (for integration testing)

---

## Task 1: Create ActorCreatorTool Skeleton

**Files:**
- Create: `ui/backend/app/tools/actor_creator.py`

**Step 1: Create the tool file with skeleton class**

Create `ui/backend/app/tools/actor_creator.py`:

```python
"""Actor creation tool using the public API."""
import sys
from pathlib import Path
from .base import BaseTool, ToolSchema, ToolResponse

# Add project src to path for api module
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))


class ActorCreatorTool(BaseTool):
    """Tool for creating D&D actors from descriptions."""

    @property
    def name(self) -> str:
        return "create_actor"

    def get_schema(self) -> ToolSchema:
        """Return tool schema for Gemini function calling."""
        pass  # TODO: implement

    async def execute(self, description: str, challenge_rating: float = None) -> ToolResponse:
        """Execute actor creation."""
        pass  # TODO: implement
```

**Step 2: Verify file structure**

Run: `ls -la ui/backend/app/tools/actor_creator.py`
Expected: File exists

**Step 3: Commit skeleton**

```bash
git add ui/backend/app/tools/actor_creator.py
git commit -m "feat(chatui): add ActorCreatorTool skeleton"
```

---

## Task 2: Implement Tool Schema

**Files:**
- Modify: `ui/backend/app/tools/actor_creator.py`

**Step 1: Implement get_schema() method**

Replace the `get_schema()` method:

```python
def get_schema(self) -> ToolSchema:
    """Return tool schema for Gemini function calling."""
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
```

**Step 2: Verify schema structure**

Check that the method returns a ToolSchema with name, description, and parameters.

**Step 3: Commit schema**

```bash
git add ui/backend/app/tools/actor_creator.py
git commit -m "feat(chatui): implement ActorCreatorTool schema"
```

---

## Task 3: Implement Execute Method

**Files:**
- Modify: `ui/backend/app/tools/actor_creator.py`

**Step 1: Add import for create_actor at top of file**

Add after the path manipulation:

```python
from api import create_actor, APIError  # noqa: E402
```

**Step 2: Implement execute() method**

Replace the `execute()` method:

```python
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

**Step 3: Verify imports**

Check that all imports are present at top of file:
- `sys`, `Path`, `BaseTool`, `ToolSchema`, `ToolResponse`
- `create_actor`, `APIError`

**Step 4: Commit implementation**

```bash
git add ui/backend/app/tools/actor_creator.py
git commit -m "feat(chatui): implement ActorCreatorTool execute method"
```

---

## Task 4: Register Tool with Registry

**Files:**
- Modify: `ui/backend/app/tools/__init__.py`

**Step 1: Check current registration pattern**

Read `ui/backend/app/tools/__init__.py` to see how `ImageGeneratorTool` is registered.

**Step 2: Add ActorCreatorTool registration**

Add import and registration after existing tools:

```python
from .actor_creator import ActorCreatorTool

# ... after existing registrations ...
registry.register(ActorCreatorTool())
```

**Step 3: Verify registry**

Check that `__init__.py` imports and registers both `ImageGeneratorTool` and `ActorCreatorTool`.

**Step 4: Commit registration**

```bash
git add ui/backend/app/tools/__init__.py
git commit -m "feat(chatui): register ActorCreatorTool in registry"
```

---

## Task 5: Manual Integration Testing

**Files:**
- None (testing only)

**Step 1: Start ChatUI backend**

```bash
cd ui/backend
source .venv/bin/activate  # if not already activated
uvicorn app.main:app --reload --port 8000
```

Expected: Server starts on http://localhost:8000

**Step 2: Check tool registration at /docs**

Open browser to http://localhost:8000/docs
Navigate to POST /chat endpoint
Expected: Tool schema includes `create_actor` function

**Step 3: Start ChatUI frontend**

In separate terminal:
```bash
cd ui/frontend
npm run dev
```

Expected: Frontend starts on http://localhost:5173

**Step 4: Test actor creation**

1. Open http://localhost:5173
2. Type: "Create a fierce goblin warrior with CR 1"
3. Send message
4. Wait 10-30 seconds
5. Expected: Response shows:
   - Actor name
   - Challenge rating
   - FoundryVTT UUID
   - Output directory path

**Step 5: Verify actor in FoundryVTT**

1. Open FoundryVTT (http://localhost:30000)
2. Open Actors directory
3. Search for UUID from chat response
4. Expected: Actor exists with correct name and CR

**Step 6: Document test results**

Create `ui/backend/TESTING.md` if it doesn't exist, add:

```markdown
## ActorCreatorTool Manual Testing

**Date:** 2025-11-05

**Test:** Actor creation via chat
**Input:** "Create a fierce goblin warrior with CR 1"
**Result:** ✅ PASS
- Actor created successfully
- UUID: Actor.abc123
- Response time: ~15 seconds
- Actor visible in FoundryVTT

**Test:** Actor creation without CR
**Input:** "Create a cunning kobold assassin"
**Result:** ✅ PASS
- CR inferred correctly (CR 0.5)
- UUID: Actor.def456

**Test:** Error handling (missing API key)
**Setup:** Temporarily remove GEMINI_API_KEY from .env
**Result:** ✅ PASS
- Clear error message returned
- No server crash
```

---

## Task 6: Error Handling Testing

**Files:**
- None (testing only)

**Step 1: Test missing API key**

1. Edit `ui/backend/.env`, comment out `GEMINI_API_KEY`
2. Restart backend server
3. Try creating an actor
4. Expected: Error message "Failed to create actor: Missing Gemini API key"

**Step 2: Restore API key**

Uncomment `GEMINI_API_KEY` in `.env`

**Step 3: Test invalid CR**

1. Modify tool schema temporarily to allow CR outside range
2. Try creating actor with CR 100
3. Expected: Error from API validation

**Step 4: Restore original schema**

Revert schema changes.

**Step 5: Test FoundryVTT connection failure**

1. Stop FoundryVTT server
2. Try creating an actor
3. Expected: Error message about FoundryVTT connection
4. Restart FoundryVTT

**Step 6: Document error tests**

Add to `ui/backend/TESTING.md`:

```markdown
## Error Handling Tests

**Missing API Key:** ✅ PASS - Clear error message
**Invalid CR:** ✅ PASS - Validation error caught
**FoundryVTT Down:** ✅ PASS - Connection error reported
```

---

## Task 7: Update ChatUI Documentation

**Files:**
- Modify: `ui/CLAUDE.md`

**Step 1: Add actor creator section to tool system docs**

Find the "Tool System" section in `ui/CLAUDE.md`, add after image generation:

```markdown
**Actor Creation:**
- Tool: `create_actor`
- Parameters: `description` (required), `challenge_rating` (optional)
- Execution time: 10-30 seconds
- Returns: Text summary with name, CR, UUID
- Example: "Create a fierce goblin warrior with CR 1"
```

**Step 2: Add usage examples**

Add to "Common Tasks" section:

```markdown
### Create Actor via Chat

1. User types natural language: "Create a cunning kobold assassin"
2. Gemini calls `create_actor` tool
3. Backend executes in thread pool (non-blocking)
4. Response shows actor details after 10-30 seconds
5. User can find actor in FoundryVTT using UUID
```

**Step 3: Commit documentation**

```bash
git add ui/CLAUDE.md
git commit -m "docs(chatui): document ActorCreatorTool usage"
```

---

## Task 8: Final Verification

**Files:**
- None (verification only)

**Step 1: Run backend tests (if they exist)**

```bash
cd ui/backend
pytest -v
```

Expected: All tests pass (or note if no tests exist yet)

**Step 2: Test complete workflow**

1. Start backend and frontend
2. Create 3 different actors:
   - With explicit CR
   - Without CR (inferred)
   - Complex description with multiple abilities
3. Verify all created successfully
4. Check FoundryVTT for all 3 actors

**Step 3: Test loading behavior**

1. Create actor with long description
2. Observe Gemini's "thinking" message while tool executes
3. Confirm user sees feedback during 10-30 second wait

**Step 4: Review all commits**

```bash
git log --oneline
```

Expected commits:
1. Add ActorCreatorTool skeleton
2. Implement ActorCreatorTool schema
3. Implement ActorCreatorTool execute method
4. Register ActorCreatorTool in registry
5. Document ActorCreatorTool usage

**Step 5: Push to remote (if applicable)**

```bash
git push origin feature/public-api
```

**Step 6: Update PR description**

Add to existing PR #11:

```markdown
## Update: ChatUI Integration

Added ActorCreatorTool to enable actor creation via chat:
- Natural language interface ("create a goblin warrior")
- Optional challenge rating parameter
- Text response with name, CR, UUID
- Follows existing tool system pattern
- No frontend changes required

**Testing:** Manual testing complete, all workflows verified.
```

---

## Success Criteria Checklist

- [ ] ActorCreatorTool class created and implements BaseTool
- [ ] Tool schema includes description and challenge_rating parameters
- [ ] execute() method calls create_actor via thread pool
- [ ] Tool registered in registry
- [ ] Manual testing: Actor creation works via chat
- [ ] Manual testing: CR inference works (optional parameter)
- [ ] Manual testing: Error handling works (missing key, etc.)
- [ ] Manual testing: Actors visible in FoundryVTT
- [ ] Documentation updated in ui/CLAUDE.md
- [ ] All commits pushed to remote

---

## Notes

**Integration Points:**
- Depends on `src/api.py` being available (from public-api PR)
- Uses existing tool registry pattern (no router changes)
- Frontend Message component already handles markdown (no changes needed)

**Testing Strategy:**
- Manual testing only (no unit tests for this task)
- Verify via ChatUI interface
- Check FoundryVTT directly for created actors

**Future Improvements:**
- Add unit tests for ActorCreatorTool
- Add progress streaming during execution
- Add rich stat block UI component
- Support batch actor creation
