# Quick Wins Bundle Design

## Overview

Four small improvements bundled together for efficient implementation.

## Changes

### 1. Image Model Switch

**Change:** Replace `imagen-4.0-fast-generate-001` with `gemini-2.5-flash` for all image generation.

**Files to modify:**
| File | Change |
|------|--------|
| `ui/backend/app/tools/actor_creator.py` | Use new model for actor portraits |
| `ui/backend/app/tools/image_generator.py` | Use new model for general images |
| `scripts/generate_scene_art.py` | Use new model for scene artwork |

**Approach:**
- Add `IMAGE_MODEL` config variable (default: `gemini-2.5-flash`)
- Keep Imagen code path available (commented or flag-gated) for future switch-back

**Playwright Verification:**
- Create actor via chat
- Verify image file created in `actor-portraits/`
- Visual screenshot check

---

### 2. Default Tablewrite Folder

**Change:** All created actors, scenes, journals go into a `Tablewrite/` folder by default.

**Foundry folder structure:**
```
Actors Tab:
  📁 Tablewrite/
     - Created actors...

Scenes Tab:
  📁 Tablewrite/
     - Created scenes...

Journal Tab:
  📁 Tablewrite/
     - Created journals...
```

**Files to modify:**
| File | Change |
|------|--------|
| `ui/backend/app/tools/actor_creator.py` | Set folder on actor creation |
| `ui/backend/app/tools/scene_creator.py` | Set folder on scene creation |
| `ui/backend/app/tools/journal_creator.py` | Set folder on journal creation |
| `foundry-module/tablewrite-assistant/src/handlers/folder.ts` | New handler: create/find folder by name and type |

**Approach:**
- New WebSocket message type: `get_or_create_folder`
- Request: `{"type": "get_or_create_folder", "name": "Tablewrite", "folder_type": "Actor"}`
- Response: `{"folder_id": "abc123"}`
- Tools call this before creating documents, pass folder ID to create call

**Playwright Verification:**
- Create actor via chat
- Navigate to Actors sidebar
- Verify actor appears under `Tablewrite/` folder

---

### 3. UI Name Change

**Change:** "Tablewrite AI" → "Tablewrite"

**Files to modify:**
| File | Change |
|------|--------|
| `foundry-module/tablewrite-assistant/module.json` | Update `title` field |
| `foundry-module/tablewrite-assistant/lang/en.json` | Update any localized strings |
| `foundry-module/tablewrite-assistant/src/ui/TablewriteTab.ts` | Update header text if hardcoded |

**Playwright Verification:**
- Open Tablewrite sidebar
- Screenshot header area
- Verify text shows "Tablewrite" (not "Tablewrite AI")

---

### 4. Rules Lookup (Thinking Mode)

**Change:** When user asks a D&D rules question, use Gemini's thinking mode for more thorough answers.

**Files to modify:**
| File | Change |
|------|--------|
| `ui/backend/app/services/gemini_service.py` | Add `thinking_mode` parameter to chat calls |
| `ui/backend/app/routers/chat.py` | Detect rules questions, enable thinking mode |

**Approach:**
1. Before main Gemini call, quick classification: "Is this a D&D rules question?"
2. If yes, set `thinking_mode=True` on the main call
3. Gemini uses extended reasoning before answering

**Rules Detection Prompt:**
```
Is this message asking about D&D 5e rules, mechanics, or how something works in the game?
Answer only: YES or NO

Message: "{user_message}"
```

**Playwright Verification:**
- Send message: "How does grappling work in D&D 5e?"
- Verify response contains thorough explanation (check for key terms: "Athletics", "contested check", "restrained")
- Compare response length to non-rules question (should be more detailed)

---

## Implementation Order

1. UI name change (simplest, no backend)
2. Default folder (needed by other features)
3. Image model switch (isolated change)
4. Rules lookup (requires Gemini service changes)

## Estimated Scope

| Change | Lines |
|--------|-------|
| Image model switch | ~30 |
| Default folder | ~80 |
| UI name change | ~10 |
| Rules lookup | ~60 |
| Playwright tests | ~100 |
| **Total** | ~280 |

## Out of Scope

- Configurable image model in UI settings
- User-selectable default folder
- Rules source lookup (SRD database)
