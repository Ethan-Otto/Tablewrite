# Efficient Test Workflow Design

**Date:** 2025-11-09
**Goal:** Faster local development with smart test escalation
**Approach:** Pytest hooks with smoke test markers

## Problem Statement

Current test suite takes 35 minutes to run 417 tests, which is too slow for rapid local development feedback. Need a way to run critical smoke tests quickly (<2 min), with automatic escalation to full suite on failures.

## Requirements

1. **Fast feedback loop:** Default test run completes in <2 minutes
2. **Smart escalation:** Auto-run full suite when smoke tests fail
3. **Manual override:** `--full` flag to run complete suite
4. **Non-breaking:** Preserve existing test markers and CI/CD workflows
5. **Minimal smoke tests:** ~10-20 tests covering critical paths (one per major feature)

## Architecture

### Core Components

1. **New pytest marker: `@pytest.mark.smoke`**
   - Applied to 10-20 critical tests (one per major feature)
   - Subset overlay on existing test organization
   - Does not replace existing markers (`@pytest.mark.integration`, etc.)

2. **pytest.ini configuration**
   - Define smoke marker
   - Set default behavior: `addopts = -m "smoke"`

3. **conftest.py hooks**
   - `pytest_addoption()`: Add `--full` flag
   - `pytest_configure()`: Override marker selection when `--full` is used
   - `pytest_sessionfinish()`: Detect failures and trigger full rerun

4. **Environment variable: `AUTO_ESCALATE`**
   - Default: `true` (auto-run full suite on smoke failures)
   - Set to `false` to disable auto-escalation

### Workflow

```
Developer runs: pytest
    ↓
Runs ~10-20 smoke tests (<2 min)
    ↓
If smoke tests PASS → Done
    ↓
If smoke tests FAIL + AUTO_ESCALATE=true:
    - Print: "⚠️ Smoke tests failed. Running full suite..."
    - Re-execute with --full flag
    - Takes ~35 min total (2 min smoke + 33 min full)
```

## Test Selection

### Smoke Test Candidates

Each major feature gets ONE smoke test:

1. **PDF Processing**
   - `test_full_pipeline_with_models` - PDF→XML→Journal→HTML workflow

2. **Actor Creation**
   - `test_full_pipeline_end_to_end` - Create actor from description

3. **FoundryVTT Integration**
   - `test_create_and_delete` - Basic journal CRUD

4. **XMLDocument Parsing**
   - `test_xmldocument_parses_real_xml` - Parse real XML files

5. **Image Asset Processing**
   - `test_extract_maps_integration` - Map extraction from PDF

6. **Public API**
   - `test_create_actor_integration` - End-to-end API test

### Marker Application Pattern

```python
@pytest.mark.smoke  # New marker
@pytest.mark.integration  # Keep existing markers
def test_full_pipeline_with_models():
    """Smoke test: Validates entire PDF→HTML workflow"""
    ...
```

## Implementation

### pytest.ini Changes

```ini
[pytest]
markers =
    smoke: Critical smoke tests (one per major feature)
    integration: Tests with real API calls
    slow: Long-running tests
    unit: Fast unit tests

# Default behavior: run smoke tests only
addopts = -m "smoke"
```

### conftest.py Implementation

```python
import os
import sys
import pytest

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

## Usage Examples

```bash
# Default: smoke tests only (<2 min)
pytest

# Smoke tests with verbose output
pytest -v

# Full suite manually
pytest --full

# Full suite with verbose output
pytest --full -v

# Disable auto-escalation
AUTO_ESCALATE=false pytest

# Run specific marker (overrides default)
pytest -m integration

# CI/CD: always run full suite
pytest --full
```

## Migration Strategy

**Step-by-step rollout (low-risk approach):**

1. **Add smoke marker definition to pytest.ini** (non-breaking)
   - Adds marker, but doesn't change default behavior yet
   - Can validate: `pytest -m smoke`

2. **Tag 6-10 critical tests with `@pytest.mark.smoke`** (non-breaking)
   - Tests still run as before
   - Can test smoke suite: `pytest -m smoke`

3. **Add conftest.py hooks** (non-breaking)
   - Hooks are present but `addopts` isn't set yet
   - No behavior change

4. **Enable default smoke mode in pytest.ini** (breaking change)
   - Add `addopts = -m "smoke"`
   - This is the "flip the switch" moment

5. **Update documentation** (CLAUDE.md, README)
   - Document new workflow
   - Update CI/CD configuration if needed

### Rollback Plan

- Remove `addopts = -m "smoke"` from pytest.ini
- Everything reverts to running full suite by default

### Gradual Adoption

- Developers can opt-in early: `pytest -m smoke` before step 4
- CI/CD can keep running `pytest --full` throughout migration
- No forced adoption until step 4

## Benefits

1. **Fast feedback:** <2 minutes for most development workflows
2. **Comprehensive coverage:** Auto-escalation ensures issues don't slip through
3. **Cost reduction:** Fewer Gemini API calls during development
4. **Flexible:** Manual override for thorough testing
5. **CI/CD compatible:** Can run full suite in CI while developers use smoke tests
6. **Non-invasive:** Works with existing test organization

## Trade-offs

- **Initial setup:** Need to identify and tag smoke tests
- **Maintenance:** Must update smoke tests as critical paths change
- **False confidence:** Developers might skip full suite runs
- **Escalation delay:** Smoke failures add 2 minutes before full suite starts

## Success Metrics

- **Developer feedback time:** <2 minutes for successful smoke runs
- **Smoke test coverage:** 6-10 critical paths covered
- **False positive rate:** <5% (smoke passes but full suite fails)
- **Adoption rate:** >80% of local test runs use smoke mode

## Future Enhancements

1. **Parallel smoke tests:** Run smoke tests in parallel for <1 min execution
2. **Smart selection:** Auto-select relevant smoke tests based on changed files
3. **Progressive escalation:** Run unit → smoke → integration → full tiers
4. **Cache results:** Skip smoke tests if nothing changed since last run
