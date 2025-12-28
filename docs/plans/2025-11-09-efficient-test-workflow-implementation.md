# Efficient Test Workflow Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add smoke test markers with auto-escalation to reduce local test time from 35 minutes to <2 minutes

**Architecture:** Pytest hooks in conftest.py detect smoke test failures and auto-rerun full suite. Smoke marker applied to ~10 critical tests.

**Tech Stack:** pytest, pytest hooks (pytest_addoption, pytest_configure, pytest_sessionfinish)

---

## Task 1: Add Smoke Marker Definition to pytest.ini

**Files:**
- Modify: `pytest.ini`

**Step 1: Read current pytest.ini**

Run: `cat pytest.ini`

**Step 2: Add smoke marker definition**

Edit `pytest.ini` to add smoke marker (keep existing markers):

```ini
[pytest]
markers =
    smoke: Critical smoke tests (one per major feature)
    integration: Tests with real API calls
    slow: Long-running tests
    unit: Fast unit tests
    requires_api: Tests requiring API keys
    requires_foundry: Tests requiring FoundryVTT
    requires_pdf: Tests requiring PDF files
    map: Map-related tests
```

**Step 3: Test marker is recognized**

Run: `pytest --markers | grep smoke`
Expected: Output showing "smoke: Critical smoke tests (one per major feature)"

**Step 4: Commit**

```bash
git add pytest.ini
git commit -m "feat(testing): add smoke marker definition to pytest.ini"
```

---

## Task 2: Add Pytest Hooks to conftest.py

**Files:**
- Modify: `tests/conftest.py`

**Step 1: Read current conftest.py structure**

Run: `head -50 tests/conftest.py`

**Step 2: Add pytest hooks at the top of conftest.py**

Add these imports and functions at the top of `tests/conftest.py` (after existing imports):

```python
import os
import sys

def pytest_addoption(parser):
    """Add --full flag to run entire test suite"""
    parser.addoption(
        "--full",
        action="store_true",
        default=False,
        help="Run full test suite (skip smoke-only mode)"
    )

def pytest_configure(config):
    """Configure test run based on flags"""
    if config.getoption("--full"):
        # Override default -m "smoke" behavior
        config.option.markexpr = ""  # Run all tests

def pytest_sessionfinish(session, exitstatus):
    """Auto-escalate to full suite if smoke tests fail"""
    # Check if auto-escalation is enabled
    auto_escalate = os.getenv("AUTO_ESCALATE", "true").lower() == "true"

    # Check if we're already running full suite
    is_full_run = session.config.getoption("--full") or not session.config.option.markexpr

    # Only escalate if: smoke mode + failures + auto-escalate enabled
    if not is_full_run and exitstatus != 0 and auto_escalate:
        print("\n" + "="*70)
        print("⚠️  Smoke tests failed. Running full test suite...")
        print("="*70 + "\n")

        # Re-run pytest with full suite
        sys.exit(pytest.main(["--full"] + sys.argv[1:]))
```

**Step 3: Test --full flag is recognized**

Run: `pytest --help | grep -A2 "\-\-full"`
Expected: Output showing "--full" flag with description

**Step 4: Commit**

```bash
git add tests/conftest.py
git commit -m "feat(testing): add pytest hooks for smoke test auto-escalation"
```

---

## Task 3: Tag Critical Smoke Tests

**Files:**
- Modify: `tests/test_phase2_integration.py`
- Modify: `tests/actors/test_orchestrate_integration.py`
- Modify: `tests/foundry/test_client.py`
- Modify: `tests/models/test_xml_document.py`
- Modify: `tests/api/test_api_integration.py`
- Modify: `tests/foundry/items/test_fetch.py`

**Step 1: Tag test_full_pipeline_with_models (PDF Processing smoke test)**

Edit `tests/test_phase2_integration.py`:

Find the function `test_full_pipeline_with_models` and add `@pytest.mark.smoke`:

```python
@pytest.mark.smoke  # Added
@pytest.mark.integration
def test_full_pipeline_with_models():
    """Smoke test: Validates entire PDF→XML→Journal→HTML workflow

    This test validates the complete Phase 2 pipeline:
    1. XML parsing with XMLDocument models
    ...
```

**Step 2: Tag test_full_pipeline_end_to_end (Actor Creation smoke test)**

Edit `tests/actors/test_orchestrate_integration.py`:

Find the function `test_full_pipeline_end_to_end` and add `@pytest.mark.smoke`:

```python
@pytest.mark.smoke  # Added
@pytest.mark.integration
@pytest.mark.requires_api
def test_full_pipeline_end_to_end(check_api_key, tmp_path):
    """Smoke test: End-to-end actor creation from description

    Tests complete workflow:
    ...
```

**Step 3: Tag test_create_and_delete (FoundryVTT Integration smoke test)**

Edit `tests/foundry/test_client.py`:

Find the function `test_create_and_delete` in `TestFoundryIntegration` class and add `@pytest.mark.smoke`:

```python
@pytest.mark.smoke  # Added
@pytest.mark.integration
@pytest.mark.requires_foundry
def test_create_and_delete(self, client):
    """Smoke test: Basic FoundryVTT journal CRUD operations

    Tests:
    ...
```

**Step 4: Tag test_xmldocument_parses_real_xml (XMLDocument Parsing smoke test)**

Edit `tests/models/test_xml_document.py`:

Find the function `test_xmldocument_parses_real_xml` in `TestRealXMLIntegration` class and add `@pytest.mark.smoke`:

```python
@pytest.mark.smoke  # Added
@pytest.mark.integration
def test_xmldocument_parses_real_xml(self):
    """Smoke test: Parse real XML files from pdf_to_xml.py

    This test validates that the XMLDocument model can handle real-world
    ...
```

**Step 5: Tag test_extract_maps_integration (Image Asset Processing smoke test)**

Edit `tests/api/test_api_integration.py`:

Find the function `test_extract_maps_integration` and add `@pytest.mark.smoke`:

```python
@pytest.mark.smoke  # Added
@pytest.mark.integration
@pytest.mark.requires_api
def test_extract_maps_integration(check_api_key):
    """Smoke test: Map extraction from PDF via public API

    Tests complete map extraction workflow.
    """
```

**Step 6: Tag test_create_actor_integration (Public API smoke test)**

Edit `tests/api/test_api_integration.py`:

Find the function `test_create_actor_integration` and add `@pytest.mark.smoke`:

```python
@pytest.mark.smoke  # Added
@pytest.mark.integration
@pytest.mark.requires_api
def test_create_actor_integration(check_api_key):
    """Smoke test: End-to-end actor creation via public API

    Tests:
    ...
```

**Step 7: Verify smoke tests can be selected**

Run: `pytest -m smoke --collect-only`
Expected: Output showing 6 smoke tests collected

**Step 8: Commit**

```bash
git add tests/test_phase2_integration.py tests/actors/test_orchestrate_integration.py tests/foundry/test_client.py tests/models/test_xml_document.py tests/api/test_api_integration.py
git commit -m "feat(testing): tag 6 critical tests with @pytest.mark.smoke"
```

---

## Task 4: Test Smoke Suite Runs

**Files:**
- None (verification step)

**Step 1: Run smoke tests only**

Run: `pytest -m smoke -v`
Expected: 6 tests run (all the smoke tests we tagged)

**Step 2: Verify smoke tests complete quickly**

Expected: Tests complete in <5 minutes (should be around 2-3 minutes)

**Step 3: Verify --full flag works**

Run: `pytest --full --collect-only | tail -5`
Expected: Shows "417 tests collected" or similar (all tests, not just smoke)

**Step 4: Document results**

Note: No commit needed - this is verification only

---

## Task 5: Enable Default Smoke Mode

**Files:**
- Modify: `pytest.ini`

**Step 1: Add default smoke mode to pytest.ini**

Edit `pytest.ini` to add `addopts`:

```ini
[pytest]
markers =
    smoke: Critical smoke tests (one per major feature)
    integration: Tests with real API calls
    slow: Long-running tests
    unit: Fast unit tests
    requires_api: Tests requiring API keys
    requires_foundry: Tests requiring FoundryVTT
    requires_pdf: Tests requiring PDF files
    map: Map-related tests

# Default behavior: run smoke tests only
addopts = -m "smoke"
```

**Step 2: Verify default behavior changed**

Run: `pytest --collect-only | grep "test session starts" -A5`
Expected: Output showing only 6 smoke tests collected by default

**Step 3: Verify --full still works**

Run: `pytest --full --collect-only | tail -5`
Expected: Shows all 417 tests collected

**Step 4: Commit**

```bash
git add pytest.ini
git commit -m "feat(testing): enable smoke tests as default mode"
```

---

## Task 6: Test Auto-Escalation

**Files:**
- Modify: `tests/test_phase2_integration.py` (temporarily break a test)

**Step 1: Temporarily break a smoke test**

Edit `tests/test_phase2_integration.py`:

In `test_full_pipeline_with_models`, add a failing assertion at the start:

```python
@pytest.mark.smoke
@pytest.mark.integration
def test_full_pipeline_with_models():
    """Smoke test: Validates entire PDF→XML→Journal→HTML workflow"""
    assert False, "TEMPORARY FAILURE FOR TESTING AUTO-ESCALATION"  # Add this line

    # Use the freshly generated test XML file
    xml_path = Path("output/runs/20251108_233753/documents/02_Part_1_Goblin_Arrows.xml")
    ...
```

**Step 2: Run pytest and observe auto-escalation**

Run: `pytest -v 2>&1 | head -100`
Expected:
- First sees smoke test fail
- Prints "⚠️ Smoke tests failed. Running full test suite..."
- Starts running full test suite

**Step 3: Test disabling auto-escalation**

Run: `AUTO_ESCALATE=false pytest -v`
Expected:
- Smoke test fails
- Does NOT auto-escalate to full suite
- Exits with failure

**Step 4: Restore the test**

Edit `tests/test_phase2_integration.py` and remove the temporary failure line:

```python
@pytest.mark.smoke
@pytest.mark.integration
def test_full_pipeline_with_models():
    """Smoke test: Validates entire PDF→XML→Journal→HTML workflow"""
    # Removed: assert False, "TEMPORARY FAILURE FOR TESTING AUTO-ESCALATION"

    # Use the freshly generated test XML file
    xml_path = Path("output/runs/20251108_233753/documents/02_Part_1_Goblin_Arrows.xml")
    ...
```

**Step 5: Verify smoke tests pass**

Run: `pytest -v`
Expected: All 6 smoke tests PASS

**Step 6: Commit**

```bash
git add tests/test_phase2_integration.py
git commit -m "test(testing): verify auto-escalation works correctly"
```

---

## Task 7: Update Documentation

**Files:**
- Modify: `CLAUDE.md`
- Modify: `README.md`

**Step 1: Update CLAUDE.md with new test workflow**

Edit `CLAUDE.md` and find the "Testing" section. Add smoke test documentation:

```markdown
## Testing

### Test Structure

... (existing content) ...

### Smoke Test Workflow (NEW)

**Default behavior:** Running `pytest` now executes only smoke tests (~6 tests, <2 min)

**Smoke test markers:** Applied to critical tests covering major features:
- PDF Processing: `test_full_pipeline_with_models`
- Actor Creation: `test_full_pipeline_end_to_end`
- FoundryVTT Integration: `test_create_and_delete`
- XMLDocument Parsing: `test_xmldocument_parses_real_xml`
- Image Asset Processing: `test_extract_maps_integration`
- Public API: `test_create_actor_integration`

**Auto-escalation:** If smoke tests fail, automatically runs full suite (set `AUTO_ESCALATE=false` to disable)

**Usage:**
```bash
# Default: smoke tests only (<2 min)
pytest

# Full suite manually
pytest --full

# Disable auto-escalation
AUTO_ESCALATE=false pytest

# Run specific marker (overrides default)
pytest -m integration
```

### Running Tests

```bash
# Smoke tests only (fast, <2 min) - DEFAULT
pytest
pytest -v

# Full suite (comprehensive, ~35 min)
pytest --full
pytest --full -v

# Disable auto-escalation
AUTO_ESCALATE=false pytest

# Unit tests only (fast, no API calls)
uv run pytest -m "not integration and not slow"
```
```

**Step 2: Update README.md with new test workflow**

Edit `README.md` and find the testing section. Update it:

```markdown
## Testing

The project includes a comprehensive test suite with 417 tests.

**Quick Start:**

```bash
# Default: Smoke tests only (~6 tests, <2 min)
pytest

# Full test suite (~417 tests, ~35 min)
pytest --full

# Disable auto-escalation on failure
AUTO_ESCALATE=false pytest
```

**Test Organization:**

- **Smoke tests** (`@pytest.mark.smoke`): 6 critical tests covering major features
- **Integration tests** (`@pytest.mark.integration`): Real API calls (Gemini, FoundryVTT)
- **Unit tests** (`@pytest.mark.unit`): Fast, no external dependencies
- **Slow tests** (`@pytest.mark.slow`): Long-running operations

**Auto-escalation:** If smoke tests fail, the full suite runs automatically (disable with `AUTO_ESCALATE=false`)
```

**Step 3: Commit**

```bash
git add CLAUDE.md README.md
git commit -m "docs: update testing documentation for smoke test workflow"
```

---

## Task 8: Final Verification

**Files:**
- None (verification step)

**Step 1: Run default pytest**

Run: `pytest`
Expected: 6 smoke tests run, all PASS, completes in <2 minutes

**Step 2: Run full suite**

Run: `pytest --full`
Expected: 417 tests run (416 passed, 1 skipped), completes in ~35 minutes

**Step 3: Verify auto-escalation is documented**

Run: `grep -A5 "AUTO_ESCALATE" CLAUDE.md`
Expected: Shows documentation for AUTO_ESCALATE environment variable

**Step 4: Create final summary commit**

If all tests pass, no commit needed. The feature is complete.

---

## Verification Checklist

After completing all tasks:

- [ ] `pytest` runs 6 smoke tests by default
- [ ] Smoke tests complete in <2 minutes
- [ ] `pytest --full` runs all 417 tests
- [ ] `AUTO_ESCALATE=false pytest` disables auto-escalation
- [ ] Breaking a smoke test triggers full suite run
- [ ] `pytest --markers` shows smoke marker
- [ ] CLAUDE.md documents new workflow
- [ ] README.md documents new workflow

---

## Rollback Plan

If issues arise:

1. Remove `addopts = -m "smoke"` from `pytest.ini`
2. Revert to full suite by default
3. Keep smoke markers for future use
