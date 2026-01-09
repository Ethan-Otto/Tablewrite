# Chat Settings Panel Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a settings button to the chat tab that allows users to toggle Token Art Generation on/off and select art styles (Watercolor or Oil Painting).

**Architecture:** Foundry module settings store user preferences. A gear icon button opens an inline settings panel within the chat tab. Settings are passed to the backend via the chat service context, and the backend `actor_creator.py` uses them to control image generation behavior and style selection.

**Tech Stack:** TypeScript (Foundry module), Python/FastAPI (backend), Foundry's `game.settings` API

---

## Task 1: Register Foundry Settings

**Files:**
- Modify: `foundry-module/tablewrite-assistant/src/settings.ts`
- Modify: `foundry-module/tablewrite-assistant/lang/en.json`

**Step 1: Add settings registration**

Add to `settings.ts` after the existing `backendUrl` setting:

```typescript
  // Token art generation toggle
  game.settings.register(MODULE_ID, 'tokenArtEnabled', {
    name: 'TABLEWRITE_ASSISTANT.SettingsTokenArtEnabled',
    hint: 'TABLEWRITE_ASSISTANT.SettingsTokenArtEnabledHint',
    default: true,
    type: Boolean,
    config: false,  // Not in Foundry settings menu - use our custom UI
    scope: 'client',
  });

  // Art style selection
  game.settings.register(MODULE_ID, 'artStyle', {
    name: 'TABLEWRITE_ASSISTANT.SettingsArtStyle',
    hint: 'TABLEWRITE_ASSISTANT.SettingsArtStyleHint',
    default: 'watercolor',
    type: String,
    config: false,  // Not in Foundry settings menu - use our custom UI
    scope: 'client',
    choices: {
      'watercolor': 'TABLEWRITE_ASSISTANT.StyleWatercolor',
      'oil': 'TABLEWRITE_ASSISTANT.StyleOil',
    }
  });
```

**Step 2: Add getter functions**

Add to `settings.ts` after `getBackendUrl()`:

```typescript
/**
 * Get whether token art generation is enabled.
 */
export function isTokenArtEnabled(): boolean {
  return game.settings.get(MODULE_ID, 'tokenArtEnabled') as boolean;
}

/**
 * Set token art generation enabled state.
 */
export function setTokenArtEnabled(enabled: boolean): Promise<boolean> {
  return game.settings.set(MODULE_ID, 'tokenArtEnabled', enabled);
}

/**
 * Get the selected art style.
 */
export function getArtStyle(): string {
  return game.settings.get(MODULE_ID, 'artStyle') as string;
}

/**
 * Set the art style.
 */
export function setArtStyle(style: string): Promise<string> {
  return game.settings.set(MODULE_ID, 'artStyle', style);
}
```

**Step 3: Add localization strings**

Add to `lang/en.json`:

```json
{
  "TABLEWRITE_ASSISTANT.SettingsBackendUrl": "Backend URL",
  "TABLEWRITE_ASSISTANT.SettingsBackendUrlHint": "URL of your Tablewrite server (e.g., http://localhost:8000)",
  "TABLEWRITE_ASSISTANT.SettingsTokenArtEnabled": "Token Art Generation",
  "TABLEWRITE_ASSISTANT.SettingsTokenArtEnabledHint": "Generate AI artwork for created actors",
  "TABLEWRITE_ASSISTANT.SettingsArtStyle": "Art Style",
  "TABLEWRITE_ASSISTANT.SettingsArtStyleHint": "Visual style for generated actor portraits",
  "TABLEWRITE_ASSISTANT.StyleWatercolor": "Watercolor",
  "TABLEWRITE_ASSISTANT.StyleOil": "Oil Painting",
  "TABLEWRITE_ASSISTANT.Settings": "Settings",
  "TABLEWRITE_ASSISTANT.Connected": "Connected to Tablewrite",
  "TABLEWRITE_ASSISTANT.Disconnected": "Disconnected from Tablewrite",
  "TABLEWRITE_ASSISTANT.CreatedActor": "Created actor: {name}",
  "TABLEWRITE_ASSISTANT.CreatedJournal": "Created journal: {name}",
  "TABLEWRITE_ASSISTANT.CreatedScene": "Created scene: {name}",
  "TABLEWRITE_ASSISTANT.TabTooltip": "Tablewrite",
  "TABLEWRITE_ASSISTANT.Placeholder": "Ask me anything about D&D...",
  "TABLEWRITE_ASSISTANT.Loading": "Thinking...",
  "TABLEWRITE_ASSISTANT.ChatError": "Failed to send message",
  "TABLEWRITE_ASSISTANT.Send": "Send"
}
```

**Step 4: Build to verify compilation**

Run: `cd foundry-module/tablewrite-assistant && npm run build`
Expected: No TypeScript errors

**Step 5: Commit**

```bash
git add foundry-module/tablewrite-assistant/src/settings.ts foundry-module/tablewrite-assistant/lang/en.json
git commit -m "feat(foundry): add token art settings registration"
```

---

## Task 2: Add Settings Button and Panel to Chat Tab

**Files:**
- Modify: `foundry-module/tablewrite-assistant/src/ui/TablewriteTab.ts`

**Step 1: Add imports for settings functions**

Update the imports at top of `TablewriteTab.ts`:

```typescript
import { getBackendUrl, isTokenArtEnabled, setTokenArtEnabled, getArtStyle, setArtStyle } from '../settings.js';
```

**Step 2: Add settings panel state**

Add to the `TablewriteTab` class properties (after `moduleUpload`):

```typescript
  private settingsOpen: boolean = false;
```

**Step 3: Update render() to include settings button**

Replace the tabs HTML in `render()` with:

```typescript
        <div class="tablewrite-tabs">
          <button class="tab-btn active" data-tab="chat">Chat</button>
          <button class="tab-btn" data-tab="battlemap">Battle Map</button>
          <button class="tab-btn" data-tab="module">Module</button>
          <button class="settings-btn" title="${game.i18n.localize('TABLEWRITE_ASSISTANT.Settings')}">
            <i class="fas fa-cog"></i>
          </button>
        </div>
```

**Step 4: Add settings panel HTML after tabs**

Add after the `tablewrite-tabs` div and before the first `tab-content`:

```typescript
        <div class="tablewrite-settings-panel" style="display: none;">
          <div class="settings-row">
            <label>
              <input type="checkbox" id="token-art-toggle" ${isTokenArtEnabled() ? 'checked' : ''} />
              ${game.i18n.localize('TABLEWRITE_ASSISTANT.SettingsTokenArtEnabled')}
            </label>
          </div>
          <div class="settings-row">
            <label for="art-style-select">${game.i18n.localize('TABLEWRITE_ASSISTANT.SettingsArtStyle')}</label>
            <select id="art-style-select">
              <option value="watercolor" ${getArtStyle() === 'watercolor' ? 'selected' : ''}>
                ${game.i18n.localize('TABLEWRITE_ASSISTANT.StyleWatercolor')}
              </option>
              <option value="oil" ${getArtStyle() === 'oil' ? 'selected' : ''}>
                ${game.i18n.localize('TABLEWRITE_ASSISTANT.StyleOil')}
              </option>
            </select>
          </div>
        </div>
```

**Step 5: Add settings listeners method**

Add new method to the class:

```typescript
  private attachSettingsListeners(): void {
    const settingsBtn = this.container.querySelector('.settings-btn');
    const settingsPanel = this.container.querySelector('.tablewrite-settings-panel') as HTMLElement;
    const tokenArtToggle = this.container.querySelector('#token-art-toggle') as HTMLInputElement;
    const artStyleSelect = this.container.querySelector('#art-style-select') as HTMLSelectElement;

    // Toggle settings panel
    settingsBtn?.addEventListener('click', () => {
      this.settingsOpen = !this.settingsOpen;
      settingsPanel.style.display = this.settingsOpen ? 'block' : 'none';
      settingsBtn.classList.toggle('active', this.settingsOpen);
    });

    // Handle token art toggle
    tokenArtToggle?.addEventListener('change', async () => {
      await setTokenArtEnabled(tokenArtToggle.checked);
      // Disable style select when art is disabled
      artStyleSelect.disabled = !tokenArtToggle.checked;
    });

    // Handle art style change
    artStyleSelect?.addEventListener('change', async () => {
      await setArtStyle(artStyleSelect.value);
    });

    // Set initial disabled state
    if (artStyleSelect && tokenArtToggle) {
      artStyleSelect.disabled = !tokenArtToggle.checked;
    }
  }
```

**Step 6: Call settings listeners in render()**

Add after `this.activateListeners();` in render():

```typescript
    // Attach settings panel listeners
    this.attachSettingsListeners();
```

**Step 7: Build to verify compilation**

Run: `cd foundry-module/tablewrite-assistant && npm run build`
Expected: No TypeScript errors

**Step 8: Commit**

```bash
git add foundry-module/tablewrite-assistant/src/ui/TablewriteTab.ts
git commit -m "feat(foundry): add settings button and panel to chat tab"
```

---

## Task 3: Add CSS Styles for Settings Panel

**Files:**
- Modify: `foundry-module/tablewrite-assistant/styles/module.css`

**Step 1: Add settings button styles**

Add at end of `module.css`:

```css
/* ========================================
   Settings Panel Styles
   ======================================== */

/* Settings gear button in tab bar */
.settings-btn {
  margin-left: auto;
  padding: 8px 12px;
  background: none;
  border: none;
  cursor: pointer;
  color: #888;
  font-size: 14px;
  transition: color 0.2s ease;
}

.settings-btn:hover {
  color: #fff;
}

.settings-btn.active {
  color: #7a4;
}

/* Settings panel */
.tablewrite-settings-panel {
  padding: 10px 12px;
  background: rgba(0, 0, 0, 0.3);
  border-bottom: 1px solid #444;
  margin-bottom: 10px;
}

.settings-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.settings-row:last-child {
  margin-bottom: 0;
}

.settings-row label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #ccc;
  cursor: pointer;
}

.settings-row input[type="checkbox"] {
  accent-color: #7a4;
  width: 16px;
  height: 16px;
}

.settings-row select {
  padding: 4px 8px;
  border: 1px solid #555;
  border-radius: 4px;
  background: #333;
  color: #fff;
  font-size: 12px;
  min-width: 120px;
}

.settings-row select:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.settings-row select:focus {
  border-color: #7a4;
  outline: none;
}
```

**Step 2: Commit**

```bash
git add foundry-module/tablewrite-assistant/styles/module.css
git commit -m "feat(foundry): add settings panel CSS styles"
```

---

## Task 4: Pass Settings to Backend via Chat Service

**Files:**
- Modify: `foundry-module/tablewrite-assistant/src/ui/chat-service.ts`

**Step 1: Update imports**

Update imports in `chat-service.ts`:

```typescript
import { getBackendUrl, isTokenArtEnabled, getArtStyle } from '../settings.js';
```

**Step 2: Add settings to request context**

Update the `send` method body to include settings:

```typescript
  async send(message: string, history: ChatMessage[]): Promise<ChatResponse> {
    const url = `${getBackendUrl()}/api/chat`;

    const conversationHistory = history.map(msg => ({
      role: msg.role,
      content: msg.content,
      timestamp: msg.timestamp?.toISOString() ?? new Date().toISOString()
    }));

    // Include user settings in context
    const context = {
      settings: {
        tokenArtEnabled: isTokenArtEnabled(),
        artStyle: getArtStyle()
      }
    };

    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message,
        context,
        conversation_history: conversationHistory
      })
    });

    if (!response.ok) {
      throw new Error(`Chat request failed: ${response.status}`);
    }

    return await response.json();
  }
```

**Step 3: Build to verify compilation**

Run: `cd foundry-module/tablewrite-assistant && npm run build`
Expected: No TypeScript errors

**Step 4: Commit**

```bash
git add foundry-module/tablewrite-assistant/src/ui/chat-service.ts
git commit -m "feat(foundry): pass settings to backend in chat context"
```

---

## Task 5: Update Backend to Use Settings

**Files:**
- Modify: `ui/backend/app/tools/image_styles.py`
- Modify: `ui/backend/app/tools/actor_creator.py`

**Step 1: Add style getter function**

Add to `image_styles.py`:

```python
def get_actor_style(style_name: str = "watercolor") -> str:
    """Get actor style prompt by name.

    Args:
        style_name: Either "watercolor" or "oil"

    Returns:
        The style prompt string
    """
    if style_name == "oil":
        return ACTOR_STYLE_OIL
    return ACTOR_STYLE  # Default to watercolor
```

**Step 2: Update actor_creator to accept style parameter**

Update `generate_actor_image` function signature and body in `actor_creator.py`:

```python
async def generate_actor_image(
    visual_description: str,
    upload_to_foundry: bool = True,
    style: str = "watercolor"
) -> tuple[Optional[str], Optional[str]]:
    """
    Generate an image of the actor using Imagen.

    Args:
        visual_description: Visual description of the actor
        upload_to_foundry: Whether to upload the image to Foundry
        style: Art style to use ("watercolor" or "oil")

    Returns:
        Tuple of (local_url, foundry_path)
    """
    import base64
    from .image_styles import get_actor_style

    try:
        # Get style prompt based on setting
        style_prompt = get_actor_style(style)
        styled_prompt = f"{visual_description}, {style_prompt}"
        logger.info(f"[IMAGE PROMPT] style={style}, prompt={styled_prompt[:100]}...")
```

**Step 3: Update ActorCreatorTool.execute to use context settings**

Update the schema to include optional settings parameter:

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

**Step 4: Store context settings for tool execution**

The context needs to be passed through. Add a module-level variable and setter:

```python
# Context settings from frontend (set per-request)
_request_context: dict = {}

def set_request_context(context: dict):
    """Set the request context for the current request."""
    global _request_context
    _request_context = context or {}

def get_request_context() -> dict:
    """Get the current request context."""
    return _request_context
```

**Step 5: Update execute() to use context settings**

In the `execute` method, replace the image generation section:

```python
            # Get settings from request context
            context = get_request_context()
            settings = context.get('settings', {})
            art_enabled = settings.get('tokenArtEnabled', True)
            art_style = settings.get('artStyle', 'watercolor')

            # Generate actor image BEFORE actor creation (if enabled)
            image_url = None
            foundry_image_path = None
            if _image_generation_enabled and art_enabled:
                logger.info(f"Generating actor image (style={art_style}) for: {description[:50]}...")
                try:
                    visual_desc = await generate_actor_description(description)
                    logger.info(f"Generated visual description: {visual_desc[:100]}...")
                    image_url, foundry_image_path = await generate_actor_image(
                        visual_desc,
                        style=art_style
                    )
```

**Step 6: Commit**

```bash
git add ui/backend/app/tools/image_styles.py ui/backend/app/tools/actor_creator.py
git commit -m "feat(backend): use frontend settings for actor image generation"
```

---

## Task 6: Wire Context Through Chat Router

**Files:**
- Modify: `ui/backend/app/routers/chat.py`

**Step 1: Import context setter**

Add import at top:

```python
from app.tools.actor_creator import set_request_context
```

**Step 2: Set context before tool execution**

In the `chat` function, add context setting before calling Gemini with tools:

```python
            # Set request context for tool execution
            set_request_context(request.context)

            # Get all available tool schemas
            tool_schemas = registry.get_schemas()
```

**Step 3: Commit**

```bash
git add ui/backend/app/routers/chat.py
git commit -m "feat(backend): wire request context to tool execution"
```

---

## Task 7: Build and Manual Test

**Step 1: Build Foundry module**

Run: `cd foundry-module/tablewrite-assistant && npm run build`
Expected: No TypeScript errors, `dist/` files updated

**Step 2: Restart backend**

Run: `cd ui/backend && uvicorn app.main:app --reload --port 8000`

**Step 3: Manual test in Foundry**

1. Refresh FoundryVTT to load updated module
2. Open Tablewrite sidebar tab
3. Click gear icon - settings panel should appear/disappear
4. Toggle "Token Art Generation" checkbox
5. Select different art style from dropdown
6. Create an actor with "Create a goblin warrior"
7. Verify: If art enabled, image generates with selected style
8. Verify: If art disabled, no image generates

**Step 4: Final commit**

```bash
git add -A
git commit -m "feat: add chat settings panel for token art generation

- Add settings button (gear icon) to chat tab header
- Add inline settings panel with:
  - Token Art Generation toggle (on/off)
  - Art Style selector (Watercolor/Oil Painting)
- Pass settings to backend via chat context
- Backend respects tokenArtEnabled and artStyle settings
- Settings persist per-client via Foundry game.settings"
```

---

## Summary

| Task | Files Modified | Purpose |
|------|---------------|---------|
| 1 | settings.ts, en.json | Register Foundry settings |
| 2 | TablewriteTab.ts | Add settings button and panel UI |
| 3 | module.css | Style the settings panel |
| 4 | chat-service.ts | Pass settings to backend |
| 5 | image_styles.py, actor_creator.py | Backend style selection |
| 6 | chat.py | Wire context to tools |
| 7 | (manual test) | Verify end-to-end |
