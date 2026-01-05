# Quick Wins Bundle Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement four small improvements: UI rename, default folder, image model switch, and rules thinking mode.

**Architecture:** Each change is isolated - we tackle them in order of increasing complexity. UI rename is pure frontend, default folder requires new WebSocket handler, image model is config change, rules thinking adds AI classification.

**Tech Stack:** TypeScript (Foundry module), Python/FastAPI (backend), Playwright (verification)

---

## Task 1: UI Name Change

**Files:**
- Modify: `foundry-module/tablewrite-assistant/module.json:3`
- Modify: `foundry-module/tablewrite-assistant/lang/en.json:9`

**Step 1: Update module.json title**

```json
{
  "id": "tablewrite-assistant",
  "title": "Tablewrite",
  ...
}
```

Change line 3 from `"title": "Tablewrite Assistant"` to `"title": "Tablewrite"`.

**Step 2: Update lang/en.json tooltip**

```json
{
  ...
  "TABLEWRITE_ASSISTANT.TabTooltip": "Tablewrite",
  ...
}
```

Change line 9 from `"Tablewrite AI"` to `"Tablewrite"`.

**Step 3: Build the module**

Run: `cd foundry-module/tablewrite-assistant && npm run build`
Expected: Build completes with no errors

**Step 4: Verify with Playwright**

Create: `tests/ui/test_ui_name.py`

```python
"""Test UI name change from 'Tablewrite AI' to 'Tablewrite'."""
import pytest
import sys
from pathlib import Path

# Add helper to path
helper_path = Path(__file__).parent.parent.parent / "foundry-module/tablewrite-assistant/scripts/feedback"
sys.path.insert(0, str(helper_path))

from foundry_helper import FoundrySession


@pytest.mark.integration
def test_ui_name_is_tablewrite():
    """Verify the tab tooltip shows 'Tablewrite' not 'Tablewrite AI'."""
    with FoundrySession() as session:
        # Get the tab element
        tab = session.page.locator('a[data-tab="tablewrite"]')
        assert tab.count() > 0, "Tablewrite tab not found"

        # Check tooltip/title attribute
        title = tab.get_attribute('title') or tab.get_attribute('data-tooltip')
        assert title is not None, "Tab has no tooltip"
        assert "Tablewrite" in title, f"Expected 'Tablewrite' in tooltip, got: {title}"
        assert "AI" not in title, f"Tooltip should not contain 'AI', got: {title}"
```

**Step 5: Run verification**

Run: `cd foundry-module/tablewrite-assistant/scripts/feedback && python -c "from foundry_helper import FoundrySession; s = FoundrySession(headless=False).__enter__(); input('Check tooltip - press Enter')"`

Manually verify: Hover over Tablewrite tab, tooltip says "Tablewrite" not "Tablewrite AI"

**Step 6: Commit**

```bash
git add foundry-module/tablewrite-assistant/module.json foundry-module/tablewrite-assistant/lang/en.json
git commit -m "feat: rename UI from 'Tablewrite AI/Assistant' to 'Tablewrite'"
```

---

## Task 2: Default Tablewrite Folder

**Files:**
- Create: `foundry-module/tablewrite-assistant/src/handlers/folder.ts`
- Modify: `foundry-module/tablewrite-assistant/src/handlers/index.ts`
- Modify: `ui/backend/app/websocket/push.py`
- Modify: `ui/backend/app/tools/actor_creator.py`
- Test: `tests/ui/test_default_folder.py`

### Step 1: Create folder handler

Create: `foundry-module/tablewrite-assistant/src/handlers/folder.ts`

```typescript
/**
 * Handle folder operations - get or create folders by name and type.
 */

export interface FolderResult {
  success: boolean;
  folder_id?: string;
  folder_uuid?: string;
  name?: string;
  error?: string;
}

/**
 * Get or create a folder by name and document type.
 *
 * @param data.name - Folder name (e.g., "Tablewrite")
 * @param data.type - Document type: "Actor", "Scene", "JournalEntry", "Item"
 */
export async function handleGetOrCreateFolder(data: {
  name: string;
  type: string;
}): Promise<FolderResult> {
  try {
    const { name, type } = data;

    if (!name || !type) {
      return {
        success: false,
        error: 'Missing name or type'
      };
    }

    // Check if folder already exists
    const existingFolder = game.folders?.find(
      (f: FoundryDocument) => f.name === name && f.type === type
    );

    if (existingFolder) {
      console.log(`[Tablewrite] Found existing folder: ${name} (${type})`);
      return {
        success: true,
        folder_id: existingFolder.id,
        folder_uuid: `Folder.${existingFolder.id}`,
        name: existingFolder.name
      };
    }

    // Create new folder
    const folder = await Folder.create({
      name: name,
      type: type,
      parent: null
    });

    if (folder) {
      console.log(`[Tablewrite] Created folder: ${name} (${type})`);
      return {
        success: true,
        folder_id: folder.id,
        folder_uuid: `Folder.${folder.id}`,
        name: folder.name
      };
    }

    return {
      success: false,
      error: 'Folder.create returned null'
    };
  } catch (error) {
    console.error('[Tablewrite] Failed to get/create folder:', error);
    return {
      success: false,
      error: String(error)
    };
  }
}
```

### Step 2: Add folder handler to index.ts exports

Modify: `foundry-module/tablewrite-assistant/src/handlers/index.ts`

Add to imports at top:
```typescript
import { handleGetOrCreateFolder } from './folder.js';
```

Add to exports:
```typescript
export { handleGetOrCreateFolder } from './folder.js';
```

Add to MessageType union (line 17):
```typescript
export type MessageType = 'actor' | 'journal' | ... | 'get_or_create_folder' | 'connected' | 'pong';
```

Add to FolderResult interface after FileUploadResult:
```typescript
export interface FolderResult {
  success: boolean;
  folder_id?: string;
  folder_uuid?: string;
  name?: string;
  error?: string;
}
```

Update MessageResult data type to include FolderResult:
```typescript
data?: CreateResult | GetResult | DeleteResult | ListResult | GiveResult | SearchResult | FileListResult | FileUploadResult | FolderResult;
```

Add case to handleMessage switch (before 'connected'):
```typescript
    case 'get_or_create_folder':
      if (message.data) {
        const result = await handleGetOrCreateFolder(message.data as {
          name: string;
          type: string;
        });
        return {
          responseType: result.success ? 'folder_result' : 'folder_error',
          request_id: message.request_id,
          data: result,
          error: result.error
        };
      }
      return {
        responseType: 'folder_error',
        request_id: message.request_id,
        error: 'Missing data for get_or_create_folder'
      };
```

### Step 3: Add backend push function for folder

Modify: `ui/backend/app/websocket/push.py`

Add new function (after other push functions):

```python
async def get_or_create_folder(name: str, folder_type: str) -> dict:
    """
    Get or create a folder in Foundry.

    Args:
        name: Folder name (e.g., "Tablewrite")
        folder_type: Document type ("Actor", "Scene", "JournalEntry", "Item")

    Returns:
        Dict with folder_id on success
    """
    result = await send_and_wait({
        "type": "get_or_create_folder",
        "data": {
            "name": name,
            "type": folder_type
        }
    })
    return result
```

### Step 4: Update actor_creator to use Tablewrite folder

Modify: `ui/backend/app/tools/actor_creator.py`

Add import at top with other websocket imports:
```python
from app.websocket import push_actor, list_files, list_compendium_items, upload_file, get_or_create_folder  # noqa: E402
```

In the `execute` method, before calling `push_actor`, add folder handling:

Find the section where actor_data is prepared for push (around line 395-400) and add:

```python
            # Ensure Tablewrite folder exists and set it on the actor
            try:
                folder_result = await get_or_create_folder("Tablewrite", "Actor")
                if folder_result.get("success") and folder_result.get("folder_id"):
                    actor_data["folder"] = folder_result["folder_id"]
                    logger.info(f"Set actor folder to Tablewrite: {folder_result['folder_id']}")
            except Exception as e:
                logger.warning(f"Failed to get/create Tablewrite folder: {e}")
                # Continue without folder - actor will be created at root
```

### Step 5: Build the module

Run: `cd foundry-module/tablewrite-assistant && npm run build`
Expected: Build completes with no errors

### Step 6: Write integration test

Create: `tests/ui/test_default_folder.py`

```python
"""Test that created actors go into Tablewrite folder."""
import pytest
import sys
from pathlib import Path

helper_path = Path(__file__).parent.parent.parent / "foundry-module/tablewrite-assistant/scripts/feedback"
sys.path.insert(0, str(helper_path))

from foundry_helper import FoundrySession


@pytest.mark.integration
def test_actor_created_in_tablewrite_folder():
    """Verify created actor appears in Actors/Tablewrite folder."""
    with FoundrySession(headless=False) as session:
        session.goto_tablewrite()

        # Create a simple actor
        session.send_message("Create a goblin scout", wait=15.0)

        # Check for success message
        response = session.get_message_text()
        assert "Created" in response or "actor" in response.lower(), f"Actor creation may have failed: {response}"

        # Navigate to Actors tab and check for Tablewrite folder
        session.page.locator('a[data-tab="actors"]').click()
        session.page.wait_for_timeout(1000)

        # Look for Tablewrite folder
        folder = session.page.locator('.folder-header:has-text("Tablewrite")')
        assert folder.count() > 0, "Tablewrite folder not found in Actors tab"
```

### Step 7: Run verification

Run: `uv run pytest tests/ui/test_default_folder.py -v -s`
Expected: Test passes, actor is in Tablewrite folder

### Step 8: Commit

```bash
git add foundry-module/tablewrite-assistant/src/handlers/folder.ts \
        foundry-module/tablewrite-assistant/src/handlers/index.ts \
        ui/backend/app/websocket/push.py \
        ui/backend/app/tools/actor_creator.py \
        tests/ui/test_default_folder.py
git commit -m "feat: default Tablewrite folder for created actors"
```

---

## Task 3: Image Model Switch

**Files:**
- Modify: `ui/backend/app/tools/image_generator.py:24`
- Modify: `ui/backend/app/tools/actor_creator.py:91`
- Modify: `src/scene_extraction/generate_artwork.py:17`
- Test: `tests/ui/test_image_generation.py`

### Step 1: Update image_generator.py

Modify: `ui/backend/app/tools/image_generator.py`

Change line 24 from:
```python
    MODEL_NAME = "imagen-4.0-fast-generate-001"
```

To:
```python
    # Image generation model - can switch back to "imagen-4.0-fast-generate-001" if needed
    MODEL_NAME = "gemini-2.5-flash-preview-05-20"
```

Also update the `_generate_and_save_image` method to use Gemini's image generation API format.
Replace the method (lines 134-164):

```python
    def _generate_and_save_image(self, prompt: str, filepath: Path):
        """
        Blocking call to generate and save image.

        Args:
            prompt: Image description
            filepath: Where to save the image
        """
        from google.genai import types

        # Enhance prompt with default D&D fantasy style
        styled_prompt = f"{prompt}, {self.DEFAULT_STYLE}"

        # Generate image using Gemini
        response = self.api.client.models.generate_content(
            model=self.MODEL_NAME,
            contents=styled_prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
            )
        )

        # Extract and save the generated image
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    image_data = part.inline_data.data
                    with open(filepath, 'wb') as f:
                        f.write(image_data)
                    return

        raise RuntimeError("No image generated in response")
```

### Step 2: Update actor_creator.py

Modify: `ui/backend/app/tools/actor_creator.py`

Find the `generate_actor_image` function (around line 69) and update the image generation section (around line 90-96):

Change:
```python
        def _generate_image():
            api = GeminiAPI(model_name="imagen-4.0-fast-generate-001")
            return api.client.models.generate_images(
                model="imagen-4.0-fast-generate-001",
                prompt=styled_prompt,
                config=types.GenerateImagesConfig(number_of_images=1)
            )
```

To:
```python
        def _generate_image():
            # Using Gemini for image generation (can switch back to imagen-4.0-fast-generate-001)
            api = GeminiAPI(model_name="gemini-2.5-flash-preview-05-20")
            return api.client.models.generate_content(
                model="gemini-2.5-flash-preview-05-20",
                contents=styled_prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                )
            )
```

Also update the response handling (around line 100-112):

Change:
```python
        if response.generated_images:
            # Save image locally
            output_dir = settings.IMAGE_OUTPUT_DIR
            output_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = uuid.uuid4().hex[:8]
            filename = f"actor_{timestamp}_{unique_id}.png"
            filepath = output_dir / filename

            generated_image = response.generated_images[0]
            # Use public image_bytes API instead of private _pil_image
            image_data = generated_image.image.image_bytes
```

To:
```python
        # Extract image from Gemini response
        image_data = None
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    image_data = part.inline_data.data
                    break

        if image_data:
            # Save image locally
            output_dir = settings.IMAGE_OUTPUT_DIR
            output_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = uuid.uuid4().hex[:8]
            filename = f"actor_{timestamp}_{unique_id}.png"
            filepath = output_dir / filename
```

### Step 3: Update scene artwork generator

Modify: `src/scene_extraction/generate_artwork.py`

Change line 17 from:
```python
MODEL_NAME = "imagen-4.0-fast-generate-001"
```

To:
```python
# Image generation model - can switch back to "imagen-4.0-fast-generate-001" if needed
MODEL_NAME = "gemini-2.5-flash-preview-05-20"
```

Note: This file uses `generate_images_parallel` utility which may need separate updates. Check if `src/util/parallel_image_gen.py` needs updating too - it may need to support both Imagen and Gemini formats.

### Step 4: Write test

Create: `tests/ui/test_image_generation.py`

```python
"""Test image generation with new model."""
import pytest
import sys
from pathlib import Path

helper_path = Path(__file__).parent.parent.parent / "foundry-module/tablewrite-assistant/scripts/feedback"
sys.path.insert(0, str(helper_path))

from foundry_helper import FoundrySession


@pytest.mark.integration
def test_actor_image_generated():
    """Verify actor creation generates an image."""
    with FoundrySession(headless=False) as session:
        session.goto_tablewrite()

        # Create actor and wait for completion
        session.send_message("Create a fire elemental", wait=20.0)

        # Check response includes image
        response_html = session.get_message_html()

        # Should have an image tag or image reference
        has_image = '<img' in response_html or 'actor-portraits' in response_html
        assert has_image, f"Expected image in response, got: {response_html[:500]}"
```

### Step 5: Run verification

Run: `uv run pytest tests/ui/test_image_generation.py -v -s`
Expected: Test passes, image is generated

### Step 6: Commit

```bash
git add ui/backend/app/tools/image_generator.py \
        ui/backend/app/tools/actor_creator.py \
        src/scene_extraction/generate_artwork.py \
        tests/ui/test_image_generation.py
git commit -m "feat: switch image generation to gemini-2.5-flash"
```

---

## Task 4: Rules Lookup (Thinking Mode)

**Files:**
- Modify: `ui/backend/app/services/gemini_service.py`
- Modify: `ui/backend/app/routers/chat.py`
- Test: `tests/ui/test_rules_lookup.py`

### Step 1: Add thinking mode to GeminiService

Modify: `ui/backend/app/services/gemini_service.py`

Add new method after `generate_chat_response` (around line 123):

```python
    def is_rules_question(self, message: str) -> bool:
        """
        Detect if message is asking about D&D rules.

        Args:
            message: User message

        Returns:
            True if this appears to be a rules question
        """
        prompt = f"""Is this message asking about D&D 5e rules, mechanics, or how something works in the game?
Answer only: YES or NO

Message: "{message}"

Answer:"""

        response = self.api.generate_content(prompt)
        answer = response.text.strip().upper()
        return answer.startswith("YES")

    def generate_with_thinking(
        self,
        message: str,
        conversation_history: Optional[list] = None
    ) -> str:
        """
        Generate a response using extended thinking for thorough reasoning.

        Args:
            message: User message
            conversation_history: Previous messages

        Returns:
            Generated response with thorough reasoning
        """
        # Build prompt optimized for rules explanation
        prompt = f"""You are an expert D&D 5e rules advisor. Answer the following question thoroughly and accurately.

Include:
- The core rule mechanics
- Relevant page references if known (PHB, DMG, etc.)
- Common edge cases or clarifications
- Practical examples when helpful

Think through this step by step before answering.

"""

        if conversation_history:
            prompt += "\n**Conversation History:**\n"
            for msg in conversation_history:
                role = msg.get("role", "").upper()
                content = msg.get("content", "")
                if role == "SYSTEM":
                    continue
                prompt += f"{role}: {content}\n"
            prompt += "\n"

        prompt += f"Question: {message}\n\nAnswer:"

        # Use thinking model configuration
        response = self.api.client.models.generate_content(
            model="gemini-2.0-flash-thinking-exp",
            contents=prompt
        )

        return response.text
```

### Step 2: Update chat router to use thinking mode

Modify: `ui/backend/app/routers/chat.py`

In the `chat` function, add rules detection before the tool calling section (around line 46, inside the `else:` for regular chat):

Replace the entire `else:` block (lines 46-90) with:

```python
        else:  # Regular chat
            # Convert conversation history to dict format
            history_dicts = [
                {
                    "role": msg.role.value,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat()
                }
                for msg in request.conversation_history
            ]

            # Check if this is a rules question
            if gemini_service.is_rules_question(request.message):
                print(f"[DEBUG] Detected rules question, using thinking mode")
                response_text = gemini_service.generate_with_thinking(
                    message=request.message,
                    conversation_history=history_dicts
                )
                return ChatResponse(
                    message=response_text,
                    type="text",
                    data={"thinking_mode": True}
                )

            # Get all available tool schemas
            tool_schemas = registry.get_schemas()
            print(f"[DEBUG] Available tools: {[t.name for t in tool_schemas]}")

            # Call Gemini with function calling enabled
            response = await gemini_service.generate_with_tools(
                message=request.message,
                conversation_history=history_dicts,
                tools=tool_schemas
            )
            print(f"[DEBUG] Gemini response type: {response.get('type')}")
            print(f"[DEBUG] Gemini response: {response}")

            # Check if Gemini wants to call a tool
            if response.get("type") == "tool_call":
                tool_name = response["tool_call"]["name"]
                tool_params = response["tool_call"]["parameters"]

                # Execute the tool
                tool_response = await registry.execute_tool(tool_name, **tool_params)

                # Return tool response
                return ChatResponse(
                    message=tool_response.message,
                    type=tool_response.type,
                    data=tool_response.data
                )

            # No tool call - return text response
            return ChatResponse(
                message=response["text"],
                type="text",
                data=None
            )
```

### Step 3: Write test

Create: `tests/ui/test_rules_lookup.py`

```python
"""Test rules lookup with thinking mode."""
import pytest
import sys
from pathlib import Path

helper_path = Path(__file__).parent.parent.parent / "foundry-module/tablewrite-assistant/scripts/feedback"
sys.path.insert(0, str(helper_path))

from foundry_helper import FoundrySession


@pytest.mark.integration
def test_rules_question_gets_thorough_answer():
    """Verify rules questions get detailed answers with thinking mode."""
    with FoundrySession(headless=False) as session:
        session.goto_tablewrite()

        # Ask a rules question
        session.send_message("How does grappling work in D&D 5e?", wait=10.0)

        response = session.get_message_text()

        # Check for key grappling terms that indicate a thorough answer
        key_terms = ["athletics", "acrobatics", "contested", "grappled"]
        found_terms = [term for term in key_terms if term.lower() in response.lower()]

        assert len(found_terms) >= 2, f"Expected thorough rules answer with terms like {key_terms}, got: {response[:500]}"


@pytest.mark.integration
def test_non_rules_question_uses_normal_mode():
    """Verify non-rules questions don't trigger thinking mode."""
    with FoundrySession(headless=False) as session:
        session.goto_tablewrite()

        # Ask a non-rules question (should use normal chat)
        session.send_message("Hello, how are you?", wait=5.0)

        response = session.get_message_text()

        # Should get a conversational response, not a rules explanation
        assert len(response) < 1000, f"Response seems too long for a greeting: {len(response)} chars"
```

### Step 4: Run verification

Run: `uv run pytest tests/ui/test_rules_lookup.py -v -s`
Expected: Both tests pass

### Step 5: Commit

```bash
git add ui/backend/app/services/gemini_service.py \
        ui/backend/app/routers/chat.py \
        tests/ui/test_rules_lookup.py
git commit -m "feat: add thinking mode for D&D rules questions"
```

---

## Final Verification

### Step 1: Run all new tests together

Run: `uv run pytest tests/ui/ -v`
Expected: All tests pass

### Step 2: Manual smoke test

1. Open Foundry, go to Tablewrite tab
2. Hover over tab - tooltip should say "Tablewrite"
3. Ask "Create a goblin" - should appear in Actors/Tablewrite folder
4. Ask "How does advantage work?" - should get detailed rules answer
5. Check actor has portrait image

### Step 3: Final commit (if any cleanup needed)

```bash
git add -A
git commit -m "test: add comprehensive UI verification tests"
```

---

## Summary

| Task | Files Changed | Est. Lines |
|------|---------------|------------|
| UI Name | 2 | ~5 |
| Default Folder | 5 | ~100 |
| Image Model | 3 | ~50 |
| Rules Thinking | 2 | ~80 |
| Tests | 4 | ~120 |
| **Total** | **16** | **~355** |
