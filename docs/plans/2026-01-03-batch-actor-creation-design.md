# Batch Actor Creation Design

## Overview

Allow users to create multiple D&D actors from a single natural language prompt, processed in parallel with live progress updates in the chat UI.

## Goals

- Natural language input: "Create a goblin, two bugbears, and a hobgoblin captain"
- AI extracts and expands actor requests (generates distinct names for duplicates)
- Parallel processing for speed
- Live progress updates in a single chat message
- All actors organized into `Actors/Tablewrite/` folder

## Already Implemented

The following infrastructure already exists and will be reused:

| Component | Location | Description |
|-----------|----------|-------------|
| Single actor creation | `ui/backend/app/tools/actor_creator.py` | `ActorCreatorTool` with full pipeline |
| Tablewrite folder creation | `foundry-module/.../handlers/folder.ts` | `handleGetOrCreateFolder()` |
| Actor image generation | `actor_creator.py:generate_actor_image()` | Gemini-based portrait generation |
| SpellCache loading | `actor_creator.py` | WebSocket-based spell fetching with retry |
| IconCache loading | `actor_creator.py` | WebSocket-based icon fetching with retry |
| Actor upload via WebSocket | `actor_creator.py:ws_actor_upload()` | Push actor with spells to Foundry |

## User Flow

### Input

User sends natural language in chat:
> "Create a goblin, two bugbears, and a hobgoblin captain for my ambush encounter"

### AI Parsing

Backend uses Gemini to extract actor requests:
```python
[
  {"description": "a goblin", "count": 1},
  {"description": "a bugbear", "count": 2},
  {"description": "a hobgoblin captain", "count": 1}
]
```

For duplicates (count > 1), AI generates distinct variants:
- "Bugbear Brute"
- "Bugbear Tracker"

### Processing

All 4 actors created in parallel using existing `create_actor_from_description()` pipeline.

### Chat Display

Single assistant message updates as actors complete:

**During processing:**
```
Creating 4 actors...
✓ Goblin
✓ Bugbear Brute
✓ Bugbear Tracker
⏳ Hobgoblin Captain
```

**Final state:**
```
Created 4 actors:
• @UUID[Actor.xxx]{Goblin}
• @UUID[Actor.xxx]{Bugbear Brute}
• @UUID[Actor.xxx]{Bugbear Tracker}
• @UUID[Actor.xxx]{Hobgoblin Captain}
```

## Backend Implementation

### New Tool: BatchActorCreatorTool

```python
# Schema
{
  "name": "create_actors",
  "description": "Create multiple D&D actors from a description",
  "parameters": {
    "prompt": "string - natural language description of actors to create"
  }
}
```

### Pipeline

1. **Parse prompt** - Gemini extracts actor list with counts *(NEW)*
2. **Expand duplicates** - Generate distinct names/variants for count > 1 *(NEW)*
3. **Create folder** - Ensure `Actors/Tablewrite/` exists *(DONE - reuse existing)*
4. **Load caches once** - SpellCache and IconCache shared across all actors *(DONE - refactor to share)*
5. **Parallel creation** - `asyncio.gather()` on all actors *(NEW)*
6. **Stream progress** - Send WebSocket updates as each completes *(NEW)*
7. **Return results** - List of UUIDs and names *(NEW)*

### Progress Streaming

New WebSocket message type `actor_batch_progress`:

```python
{
  "type": "actor_batch_progress",
  "request_id": "abc123",
  "completed": ["Goblin", "Bugbear Brute"],
  "pending": ["Bugbear Tracker", "Hobgoblin Captain"],
  "failed": []
}
```

UI updates the message in place when these arrive.

## Error Handling

### Partial Failures

Unlike module processing, batch actors continue on failure:

```
Created 3 of 4 actors:
• @UUID[Actor.xxx]{Goblin}
• @UUID[Actor.xxx]{Bugbear Brute}
• @UUID[Actor.xxx]{Bugbear Tracker}

Failed:
• Hobgoblin Captain - "Could not parse stat block"
```

### Edge Cases

| Case | Handling |
|------|----------|
| Empty/unclear prompt | AI asks for clarification before creating |
| Very large batch (20+) | Process anyway, parallel handles it |
| Duplicate of existing actor | Create new actor (no deduplication) |
| No actors extracted | "I couldn't identify any actors to create. Could you be more specific?" |

## Foundry Organization

All created actors go into `Actors/Tablewrite/` folder. *(Already implemented in single actor tool)*

## Implementation

### Files to Create

| File | Purpose |
|------|---------|
| `ui/backend/app/tools/batch_actor_creator.py` | New tool for batch creation |

### Files to Modify

| File | Changes |
|------|---------|
| `ui/backend/app/tools/actor_creator.py` | Extract shared cache loading to reusable function |
| `ui/backend/app/websocket/push.py` | Add `actor_batch_progress` message type |
| `foundry-module/tablewrite-assistant/src/ui/TablewriteTab.ts` | Handle progress messages, update in place |
| `ui/backend/app/tools/registry.py` | Register new BatchActorCreatorTool |

### No Changes Needed

| File | Reason |
|------|--------|
| `foundry-module/.../handlers/folder.ts` | Already complete with `handleGetOrCreateFolder()` |
| `foundry-module/.../handlers/actor.ts` | Already handles actor creation |

### Estimated Scope

- ~100 lines Python (batch tool - reduced since caches exist)
- ~30 lines Python (Gemini prompt for parsing)
- ~50 lines TypeScript (progress message handling)

## Fallback Plan

If live updates prove too complex to implement:
- Show "Creating N actors..." spinner
- Wait for all to complete
- Show final summary with links

Same end result, just no incremental progress visibility.

## Testing

### Playwright E2E Verification

Full end-to-end test using Playwright to verify batch actor creation works correctly.

**Test File:** `tests/ui/test_batch_actor_creation.py`

#### Test Flow

```python
@pytest.mark.integration
async def test_batch_actor_creation_e2e():
    """
    E2E test: Send batch request via chat UI, verify actors created with correct content.
    """
    # 1. Navigate to Tablewrite tab
    # 2. Send batch creation message
    # 3. Wait for completion (parse UUIDs from response)
    # 4. Fetch each actor via API and validate content
    # 5. Cleanup: delete test actors
```

#### Step 1: Send Batch Request via Chat UI

```python
async with FoundrySession() as session:
    session.goto_tablewrite()

    # Send batch creation request
    session.send_message("Create a goblin scout, a bugbear, and an orc war chief")

    # Wait for response with actor links (up to 120s for 3 actors)
    response = await session.wait_for_response(timeout=120)

    # Verify response contains expected actors
    assert "Created 3 actors" in response.text or "Created" in response.text
```

#### Step 2: Extract Actor UUIDs from Response

```python
    # Parse @UUID[Actor.xxx]{Name} links from response
    uuid_pattern = r'@UUID\[Actor\.([a-zA-Z0-9]+)\]\{([^}]+)\}'
    matches = re.findall(uuid_pattern, response.text)

    actor_uuids = [f"Actor.{m[0]}" for m in matches]
    actor_names = [m[1] for m in matches]

    assert len(actor_uuids) == 3, f"Expected 3 actors, got {len(actor_uuids)}"
```

#### Step 3: Fetch and Validate Each Actor

```python
    import requests

    for uuid, expected_name in zip(actor_uuids, actor_names):
        # Fetch actor data via backend API
        response = requests.get(f"http://localhost:8000/api/foundry/actor/{uuid}")
        assert response.status_code == 200

        result = response.json()
        assert result["success"], f"Failed to fetch {uuid}: {result.get('error')}"

        actor = result["entity"]

        # Validate basic structure
        assert actor["name"] == expected_name
        assert actor["type"] == "npc"

        # Validate has stats (not empty/default)
        abilities = actor.get("system", {}).get("abilities", {})
        assert abilities.get("str", {}).get("value", 10) != 10 or \
               abilities.get("dex", {}).get("value", 10) != 10, \
               f"Actor {expected_name} has default stats - stat block not applied"

        # Validate HP is set
        hp = actor.get("system", {}).get("attributes", {}).get("hp", {})
        assert hp.get("max", 0) > 4, f"Actor {expected_name} has minimal HP ({hp.get('max')})"

        # Validate has items (attacks, traits, etc.)
        items = actor.get("items", [])
        assert len(items) > 0, f"Actor {expected_name} has no items"

        # Validate at least one attack or action
        attack_types = ["weapon", "feat", "spell"]
        has_attack = any(item.get("type") in attack_types for item in items)
        assert has_attack, f"Actor {expected_name} has no attacks/actions"

        print(f"✓ {expected_name}: {len(items)} items, HP {hp.get('max')}")
```

#### Step 4: Validate Actor Content Details

```python
def validate_actor_content(actor: dict, expected_type: str) -> list[str]:
    """
    Validate actor has appropriate content for its type.
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

    # Check AC is set
    ac = system.get("attributes", {}).get("ac", {}).get("value", 0)
    if ac < 5:
        errors.append(f"{name}: AC too low ({ac})")

    # Check CR is set
    cr = system.get("details", {}).get("cr")
    if cr is None:
        errors.append(f"{name}: No CR set")

    # Check items have proper types
    items = actor.get("items", [])
    for item in items:
        item_type = item.get("type")
        if item_type not in ["weapon", "feat", "spell", "equipment", "consumable", "loot"]:
            errors.append(f"{name}: Invalid item type '{item_type}' on {item.get('name')}")

    return errors
```

#### Step 5: Cleanup Test Actors

```python
    # Delete test actors from Tablewrite folder
    for uuid in actor_uuids:
        response = requests.delete(f"http://localhost:8000/api/foundry/actor/{uuid}")
        assert response.status_code == 200, f"Failed to delete {uuid}"

    print(f"✓ Cleaned up {len(actor_uuids)} test actors")
```

### Actor Content Validation Matrix

| Actor Type | Required Stats | Required Items | HP Range |
|------------|----------------|----------------|----------|
| Goblin | DEX > STR | At least 1 weapon | 5-15 |
| Bugbear | STR > 14 | At least 1 weapon | 20-40 |
| Orc War Chief | STR > 16, CHA > 12 | Weapon + leadership feat | 80-120 |
| Spellcaster | INT or WIS or CHA > 14 | At least 1 spell | Varies |

### Test Scenarios

| Scenario | Input | Expected Actors | Validation |
|----------|-------|-----------------|------------|
| Basic batch | "goblin, bugbear, orc" | 3 distinct actors | Each has unique stats |
| Duplicates | "two goblins" | 2 goblins with different names | Names differ |
| Mixed CR | "a CR 1/4 goblin and a CR 5 troll" | Goblin ~7HP, Troll ~84HP | HP matches CR |
| With context | "guards for a castle" | Multiple guard-type actors | All have weapons |
| Large batch | "5 kobolds" | 5 kobolds | All created, unique names |

### Integration Test File Structure

```
tests/
├── ui/
│   └── test_batch_actor_creation.py   # Playwright E2E tests
└── tools/
    └── test_batch_actor_creator.py    # Unit tests for batch tool
```

### Prerequisites for Tests

1. Backend running: `cd ui/backend && uvicorn app.main:app --reload`
2. FoundryVTT running with Tablewrite module connected
3. Chrome with debug port: `--remote-debugging-port=9222`
4. Playwright installed: `pip install playwright && playwright install`

## Out of Scope

- Challenge rating specification per actor (use natural language: "a CR 5 hobgoblin captain")
- Actor customization/editing in batch (use ActorEditorTool after creation)
- Deduplication with existing world actors
