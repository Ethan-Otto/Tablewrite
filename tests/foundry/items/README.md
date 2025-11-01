# Items Module Tests

Comprehensive test suite for the `foundry.items` module.

## Test Coverage

### Unit Tests (36 total)

#### `test_deduplicate.py` (19 tests)
Tests for item deduplication and source priority logic:

- **Source Priority** (5 tests)
  - Player's Handbook has highest priority
  - 2024 rules have second priority
  - SRD has third priority
  - Other sources have lowest priority
  - Edge cases (empty UUID)

- **Deduplication Logic** (9 tests)
  - No duplicates handling
  - PHB wins over SRD
  - 2024 wins over SRD
  - Multiple duplicates (4 sources)
  - Custom dedupe key
  - Empty items list
  - Items without dedupe key
  - Whitespace normalization
  - Output sorting

- **Source Statistics** (5 tests)
  - Single source counting
  - Multiple source counting
  - 2024 detection (various patterns)
  - Empty items
  - Items without UUID

#### `test_fetch.py` (9 tests)
Tests for fetching items from FoundryVTT API:

- **Fetch Logic** (6 tests)
  - Basic fetch with mocked API
  - Missing credentials error
  - UUID deduplication
  - Two-letter fallback when hitting 200 limit
  - Custom credentials override
  - API error handling

- **Convenience Functions** (1 test)
  - `fetch_all_spells()` delegates to `fetch_items_by_type()`

- **Integration Tests** (2 tests)
  - Fetch real spells from FoundryVTT
  - Fetch real weapons from FoundryVTT

#### `test_manager.py` (8 tests)
Tests for ItemManager API operations:

- **Search Operations** (3 tests)
  - Get all items by name
  - Get first item by name
  - Item not found returns None

- **Get Operations** (1 test)
  - Get item by UUID

- **Filter & Error Handling** (4 tests)
  - Search with filter parameter
  - Search error handling
  - Get error handling
  - List response format handling

## Running Tests

```bash
# Run all item tests
uv run pytest tests/foundry/items/

# Run only unit tests (exclude integration)
uv run pytest tests/foundry/items/ -m "not integration"

# Run specific test file
uv run pytest tests/foundry/items/test_deduplicate.py

# Run with verbose output
uv run pytest tests/foundry/items/ -v

# Run specific test class
uv run pytest tests/foundry/items/test_deduplicate.py::TestDeduplicateItems

# Run specific test
uv run pytest tests/foundry/items/test_deduplicate.py::TestDeduplicateItems::test_duplicates_phb_wins
```

## Test Markers

- `@pytest.mark.integration` - Tests that make real API calls to FoundryVTT
  - Requires running relay server and FoundryVTT instance
  - Skipped if `FOUNDRY_RELAY_URL` not configured

## Coverage Summary

| Module | Tests | Coverage |
|--------|-------|----------|
| `deduplicate.py` | 19 | Complete |
| `fetch.py` | 9 | Complete (unit + integration) |
| `manager.py` | 8 | Complete |
| **Total** | **36** | **100%** |

## Key Testing Patterns

### Mocking API Calls
```python
@patch('foundry.items.fetch.requests.get')
def test_api_call(self, mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = {'results': [...]}
    mock_get.return_value = mock_response
    # ... test logic
```

### Testing Error Handling
```python
import requests

mock_get.side_effect = requests.exceptions.RequestException("Error")
with pytest.raises(RuntimeError, match="Failed to search"):
    fetch_items_by_type('spell')
```

### Integration Tests
```python
@pytest.mark.integration
def test_real_api(self, check_api_key):
    # Makes real API calls
    items = fetch_items_by_type('spell')
    assert len(items) > 0
```

## Future Improvements

- [ ] Add tests for error recovery (retry logic)
- [ ] Add performance tests (large result sets)
- [ ] Add tests for three-letter fallback (if needed)
- [ ] Mock logging to verify log messages
- [ ] Test concurrent fetching scenarios
