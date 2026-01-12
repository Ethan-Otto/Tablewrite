# Actor Query Tool Design

**Date:** 2026-01-12
**Status:** Approved

## Problem

When users @mention an actor and ask questions about it, the AI has no tool to query the actor's full data. It falls back to searching journals, which don't contain actor stat blocks.

Example:
- User: `@[Dire Wolf](Actor.xyz) What can this creature do`
- Current: AI searches journals, finds nothing useful
- Expected: AI queries actor data, returns abilities/attacks

## Solution

Create `ActorQueryTool` that fetches full actor data from Foundry and answers questions about it using Gemini.

## Tool Interface

```python
class ActorQueryTool(BaseTool):
    name = "query_actor"

    # Parameters:
    # - actor_uuid: str (required) - Actor UUID from @mention
    # - query: str (required) - User's question
    # - query_type: enum ["abilities", "combat", "general"]
```

**Tool description:**
```
Query a Foundry actor to answer questions about its abilities, attacks,
spells, or stats. Use when user @mentions an actor and asks about what
it can do, its combat abilities, or specific stats. The actor_uuid should
come from the mentioned_entities context.
```

## Content Extraction

Extract from Foundry actor structure:

**From `system`:**
- Abilities (STR, DEX, CON, INT, WIS, CHA)
- Attributes (AC, HP, movement, senses)
- Details (CR, type, alignment, biography)
- Skills (with proficiency)
- Traits (resistances, immunities, languages)

**From `items`:**
- Weapons: name, attack bonus, damage dice, range, damage type
- Feats: name, description, activation type
- Spells: name, level, school

**Output format for Gemini:**
```
[ACTOR: Grolak the Quick]
CR: 0.25 | Type: humanoid (goblinoid) | AC: 15 | HP: 7

[ABILITIES]
STR: 8 (-1) | DEX: 14 (+2) | CON: 10 (+0) | INT: 10 (+0) | WIS: 8 (-1) | CHA: 7 (-2)

[COMBAT]
- Shortsword: +4 to hit, 1d6+2 piercing (melee, 5 ft reach)
- Shortbow: +4 to hit, 1d6+2 piercing (ranged, 80/320 ft)

[SPECIAL ABILITIES]
- Nimble Escape (Bonus Action): Can take Disengage or Hide as bonus action
```

## Integration Flow

1. User sends: `@[Dire Wolf](Actor.xyz) What can this creature do`
2. `parse_and_resolve_mentions()` extracts basic stats as context
3. AI sees mention context, recognizes question about actor
4. AI calls `query_actor(actor_uuid="Actor.xyz", query="...", query_type="combat")`
5. Tool fetches full actor via `fetch_actor()`
6. Tool extracts structured content
7. Tool sends to Gemini with query
8. Returns detailed answer

## Implementation

**Files to create/modify:**

| File | Action |
|------|--------|
| `ui/backend/app/tools/actor_query.py` | New - ActorQueryTool class |
| `ui/backend/app/tools/__init__.py` | Add ActorQueryTool to exports |
| `ui/backend/app/services/gemini_service.py` | Add tool to AVAILABLE_TOOLS |
| `ui/backend/tests/tools/test_actor_query.py` | Unit tests |
| `ui/backend/tests/tools/test_actor_query_integration.py` | Integration test |

## Testing

**Unit tests:**
1. Content extraction from actor dict
2. Prompt building for different query types
3. Response formatting

**Integration tests (in /tests folder):**
1. Create test actor in /tests folder
2. Query actor abilities → returns stat breakdown
3. Query actor combat → returns attacks and damage
4. Query actor with spells → returns spell list
5. Query non-existent actor → returns error
6. Query without Foundry connection → fails with clear message
