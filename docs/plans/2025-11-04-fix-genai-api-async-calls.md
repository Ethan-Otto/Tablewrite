# Fix Google Genai API Async Calls Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix incorrect usage of non-existent `generate_content_async()` method by creating a centralized async wrapper using `asyncio.to_thread()`.

**Architecture:** Create a single async wrapper function in `src/util/gemini.py` that wraps the synchronous `generate_content()` call. All code uses this wrapper instead of duplicating `asyncio.to_thread()` logic everywhere (DRY principle).

**Tech Stack:** Python 3.11, google-genai library, asyncio

---

## Background

During the migration from `google.generativeai` to `google.genai`, we incorrectly assumed the API had an async method `generate_content_async()`. It doesn't exist. The API only provides the synchronous `generate_content()` method.

**Current failures:** 24 tests failing with `AttributeError: 'Models' object has no attribute 'generate_content_async'`

**Solution:** Create ONE async wrapper function, use it everywhere (not 7 copies of `asyncio.to_thread()`)

**Files affected:**
- `src/util/gemini.py` - ADD async wrapper
- `src/actors/statblock_parser.py` - USE wrapper
- `src/actors/generate_actor_file.py` - USE wrapper
- `src/actors/generate_actor_biography.py` - USE wrapper
- `src/foundry/actors/parser.py` - USE wrapper (3 calls)
- `src/foundry/icon_cache.py` - USE wrapper

---

### Task 1: Create async wrapper in util/gemini.py

**Files:**
- Modify: `src/util/gemini.py`
- Test: `tests/util/test_gemini.py`

**Step 1: Read current GeminiAPI implementation**

Run: `cat src/util/gemini.py | grep -A 20 "class GeminiAPI"`

Expected: See the sync `generate_content()` method

**Step 2: Add async wrapper function**

Add this function after the `GeminiAPI` class (around line 170):

```python
async def generate_content_async(
    client: genai.Client,
    model: str,
    contents: Any,
    config: Optional[dict] = None
) -> Any:
    """
    Async wrapper for generate_content using asyncio.to_thread.

    The google.genai library only provides synchronous generate_content().
    This wrapper allows async code to call it without blocking the event loop.

    Args:
        client: genai.Client instance
        model: Model name (e.g., "gemini-2.5-pro")
        contents: Content to send to the model
        config: Optional generation config dict

    Returns:
        Response object with .text attribute

    Example:
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        response = await generate_content_async(
            client=client,
            model="gemini-2.5-pro",
            contents="Hello",
            config={'temperature': 0.7}
        )
    """
    return await asyncio.to_thread(
        client.models.generate_content,
        model=model,
        contents=contents,
        config=config
    )
```

**Step 3: Update imports**

Ensure `asyncio` is imported at the top:

```python
import asyncio
```

And ensure `Any` and `Optional` are imported from `typing`.

**Step 4: Write test for async wrapper**

Add to `tests/util/test_gemini.py`:

```python
@pytest.mark.asyncio
async def test_generate_content_async_wrapper():
    """Test async wrapper for generate_content."""
    from util.gemini import generate_content_async
    from google import genai
    import os

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GeminiImageAPI")
    if not api_key:
        pytest.skip("No API key available")

    client = genai.Client(api_key=api_key)

    response = await generate_content_async(
        client=client,
        model="gemini-2.0-flash",
        contents="Say 'test' in one word",
        config={'temperature': 0.0}
    )

    assert response.text
    assert isinstance(response.text, str)
```

**Step 5: Run test**

Run: `uv run pytest tests/util/test_gemini.py::test_generate_content_async_wrapper -v`

Expected: Test passes

**Step 6: Commit**

```bash
git add src/util/gemini.py tests/util/test_gemini.py
git commit -m "feat(util): add async wrapper for generate_content

Provides generate_content_async() function that wraps the synchronous
genai API call with asyncio.to_thread() to avoid blocking event loop.

This centralizes the async pattern in one place (DRY) instead of
duplicating asyncio.to_thread() in 7 different locations."
```

---

### Task 2: Update all call sites to use wrapper

**Files:**
- Modify: `src/actors/statblock_parser.py`
- Modify: `src/actors/generate_actor_file.py`
- Modify: `src/actors/generate_actor_biography.py`
- Modify: `src/foundry/actors/parser.py`
- Modify: `src/foundry/icon_cache.py`

**Step 1: Fix statblock_parser.py**

Replace (around line 144):

```python
    response = await client.models.generate_content_async(
        model=model_name,
        contents=prompt,
        config={
            'temperature': PARSE_TEMPERATURE,
            'response_mime_type': 'application/json'
        }
    )
```

With:

```python
    from util.gemini import generate_content_async

    response = await generate_content_async(
        client=client,
        model=model_name,
        contents=prompt,
        config={
            'temperature': PARSE_TEMPERATURE,
            'response_mime_type': 'application/json'
        }
    )
```

Add import at top of file:

```python
from util.gemini import generate_content_async
```

**Step 2: Fix generate_actor_file.py**

Same pattern - replace `client.models.generate_content_async()` with `generate_content_async()` around line 253.

Add import at top.

**Step 3: Fix generate_actor_biography.py**

Same pattern - replace around line 105.

Add import at top.

**Step 4: Fix parser.py (3 occurrences)**

Replace all 3 occurrences (around lines 220, 313, 383):
- First: in `parse_action_or_multiattack_async()`
- Second: in `parse_trait_async()`
- Third: in `parse_innate_spellcasting_async()`

All follow same pattern. Add import at top once.

**Step 5: Fix icon_cache.py**

Replace around line 265.

Add import at top.

**Step 6: Run tests for each file**

Run: `uv run pytest tests/actors/test_parse_stat_blocks.py -v`
Run: `uv run pytest tests/actors/test_orchestrate.py -v`
Run: `uv run pytest tests/foundry/actors/test_parser.py -v`

Expected: Tests pass

**Step 7: Commit**

```bash
git add src/actors/statblock_parser.py src/actors/generate_actor_file.py src/actors/generate_actor_biography.py src/foundry/actors/parser.py src/foundry/icon_cache.py
git commit -m "fix: use centralized async wrapper for all genai API calls

Replace all incorrect calls to generate_content_async() (which doesn't
exist) with calls to our new generate_content_async() wrapper.

Fixes 24 failing tests with AttributeError.

Files updated:
- actors/statblock_parser.py
- actors/generate_actor_file.py
- actors/generate_actor_biography.py
- foundry/actors/parser.py (3 calls)
- foundry/icon_cache.py"
```

---

### Task 3: Run full test suite

**Step 1: Run fast unit tests**

Run: `uv run pytest -m "not integration and not slow" -v`

Expected: All 244 unit tests pass

**Step 2: Run integration tests**

Run: `uv run pytest -m "integration" -v --tb=short`

Expected: Integration tests pass (will take several minutes)

**Step 3: Run complete test suite**

Run: `uv run pytest -v --tb=short`

Expected: 317 tests pass (or close to it)

**Step 4: Verify no AttributeError**

Check output for: `AttributeError.*generate_content_async`

Expected: No such errors

---

### Task 4: Final verification

**Step 1: Check all imports are correct**

Run: `grep -rn "from util.gemini import generate_content_async" src/`

Expected: See 5 files importing it

**Step 2: Check no direct async calls remain**

Run: `grep -rn "\.generate_content_async" src/`

Expected: No results (we're not calling the non-existent method anymore)

**Step 3: Check git log**

Run: `git log --oneline -3`

Expected: See the 2 commits

**Step 4: Push changes**

Run: `git push origin main`

Expected: Push successful

---

## Success Criteria

- ✅ Created ONE async wrapper function (DRY principle)
- ✅ All 5 files use the wrapper
- ✅ No more `asyncio.to_thread()` scattered everywhere
- ✅ Unit tests pass (244 tests)
- ✅ Integration tests pass
- ✅ No `AttributeError` about `generate_content_async`
- ✅ Code committed with clear messages

## Testing Notes

- Integration tests make real Gemini API calls (slow but necessary)
- Full test suite takes ~15 minutes to complete
- The async wrapper is tested directly and indirectly through all the callers
