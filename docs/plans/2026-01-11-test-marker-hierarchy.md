# Test Marker Hierarchy Plan

**Goal:** Create clear, hierarchical test markers where `foundry` and `gemini` are children of `integration`.

---

## Current Problems

1. **Inconsistent markers**: Some tests marked `integration` don't actually integrate with anything (exception tests)
2. **Mislabeled tests**: `test_basic_pipeline_creates_scene` is mocked but should be a real integration test
3. **Confusing overlap**: `requires_foundry`, `requires_api`, `integration` all exist but relationship unclear
4. **No inheritance**: Marking a test `foundry` doesn't automatically make it `integration`

## New Marker Hierarchy

```
integration (base - any test requiring external services)
├── foundry (requires Foundry WebSocket connection)
└── gemini (requires Gemini API key)
```

### Marker Definitions

| Marker | Description | Implies |
|--------|-------------|---------|
| `integration` | Base marker for tests requiring external services | - |
| `foundry` | Requires Foundry running and WebSocket connected | `integration` |
| `gemini` | Requires Gemini API key and network access | `integration` |
| `unit` | Pure unit test, no external dependencies | - |
| `smoke` | Critical path test (can be unit OR integration) | - |
| `slow` | Takes >10 seconds | - |

### Automatic Inheritance

Tests marked with `foundry` or `gemini` automatically get `integration` added via pytest hook.

```python
# conftest.py
def pytest_collection_modifyitems(items):
    for item in items:
        # foundry implies integration
        if item.get_closest_marker("foundry"):
            item.add_marker(pytest.mark.integration)
        # gemini implies integration
        if item.get_closest_marker("gemini"):
            item.add_marker(pytest.mark.integration)
```

### Usage Examples

```python
# Test that needs Foundry
@pytest.mark.foundry
def test_create_actor():
    ...

# Test that needs Gemini API
@pytest.mark.gemini
def test_extract_maps():
    ...

# Test that needs both
@pytest.mark.foundry
@pytest.mark.gemini
def test_full_pipeline():
    ...

# Pure unit test
@pytest.mark.unit
def test_parse_stat_block():
    ...

# Smoke test that's also an integration test
@pytest.mark.smoke
@pytest.mark.foundry
def test_actor_roundtrip():
    ...
```

### CLI Usage

```bash
# Run all tests
pytest --full

# Run only smoke tests (default)
pytest

# Run integration tests (foundry + gemini)
pytest -m integration

# Run only foundry tests
pytest -m foundry

# Run only gemini tests (no foundry needed)
pytest -m gemini

# Run unit tests only (no external deps)
pytest -m "not integration"

# Run non-foundry tests (CI mode - gemini OK, foundry not)
pytest -m "not foundry"
```

---

## Implementation Steps

### 1. Update pytest.ini

Remove redundant markers, add clear hierarchy:

```ini
markers =
    # Test categories
    smoke: Critical smoke tests (one per major feature)
    unit: Pure unit tests with no external dependencies
    slow: Tests taking >10 seconds

    # Integration hierarchy
    integration: Base marker - requires external services (auto-added by foundry/gemini)
    foundry: Requires Foundry WebSocket connection (implies integration)
    gemini: Requires Gemini API key (implies integration)

    # Utility markers
    flaky: May fail intermittently (auto-retries enabled)
    playwright: Uses Playwright browser automation
```

### 2. Add Hook to conftest.py

```python
def pytest_collection_modifyitems(items):
    """Add integration marker to foundry/gemini tests automatically."""
    for item in items:
        if item.get_closest_marker("foundry") or item.get_closest_marker("gemini"):
            if not item.get_closest_marker("integration"):
                item.add_marker(pytest.mark.integration)
```

### 3. Update Existing Tests

| File | Current Marker | New Marker |
|------|----------------|------------|
| `test_exceptions.py::TestExceptionIntegration` | `@pytest.mark.integration` | `@pytest.mark.unit` (rename class) |
| `test_orchestrate.py::test_basic_pipeline_creates_scene` | `@pytest.mark.smoke` (mocked) | `@pytest.mark.smoke` + `@pytest.mark.foundry` (real) |
| `test_api_integration.py::test_create_actor_integration` | `@pytest.mark.integration` | `@pytest.mark.foundry` + `@pytest.mark.gemini` |
| `test_extract_map_assets.py::TestExtractionPerformance` | `@pytest.mark.integration` | `@pytest.mark.gemini` |
| `test_client.py::test_create_and_delete` | `@pytest.mark.integration` | `@pytest.mark.foundry` |
| `test_caches_integration.py::test_caches_load_without_error` | `@pytest.mark.integration` | `@pytest.mark.foundry` |

### 4. Update CI Configuration

```python
# conftest.py pytest_configure
if is_ci:
    # CI has no Foundry, but has Gemini API key
    config.option.markexpr = "not foundry"
```

---

## Verification

After implementation:

```bash
# Should show foundry tests
pytest --collect-only -m foundry

# Should show gemini tests
pytest --collect-only -m gemini

# Should show all integration (foundry + gemini)
pytest --collect-only -m integration

# foundry tests should also appear in integration
pytest --collect-only -m "foundry and integration"  # Same as -m foundry
```
