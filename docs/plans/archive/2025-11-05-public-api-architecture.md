# Public API Facade - Architecture Document

**Date:** 2025-11-05
**Status:** Design Complete
**Implementation:** See `2025-11-05-public-api-implementation.md`

## Problem Statement

The D&D module processing system has powerful capabilities (actor creation, map extraction, PDF-to-journal conversion) but no clear public interface for external consumers like the chat UI or CLI tools. Internal functions are scattered across modules, making it unclear which functions are "official" and which are implementation details.

**Goal:** Create a clean, well-documented public API that makes core functionality easily accessible to external applications.

## Requirements (from Brainstorming)

### Decided Architecture
- **Public Python API module** (`src/api.py` facade)
- **Synchronous operations** (blocking, acceptable for chat UI use case)
- **Environment-based configuration** (.env only, no runtime config)
- **Rich dataclass return types** (typed, self-documenting)
- **End-to-end workflows only** (no intermediate steps exposed)

### Primary Consumers
- Chat UI (FastAPI backend)
- CLI tools (potential future use)

### Out of Scope
- REST/HTTP layer (handled by chat UI backend)
- Async operations (not needed for current use cases)
- Per-request configuration overrides (env vars only)
- Exposing intermediate processing steps

## API Surface Design

### Three Core Functions

1. **`create_actor(description, challenge_rating=None) -> ActorCreationResult`**
   - Natural language → FoundryVTT actor
   - Wraps: `actors.orchestrate.create_actor_from_description_sync()`
   - Returns: UUID, name, output paths, CR

2. **`extract_maps(pdf_path, chapter=None) -> MapExtractionResult`**
   - PDF → extracted battle/navigation maps
   - Wraps: `pdf_processing.image_asset_processing.extract_map_assets.main()`
   - Returns: List of maps, output dir, total count

3. **`process_pdf_to_journal(pdf_path, journal_name, skip_upload=False) -> JournalCreationResult`**
   - PDF → XML → FoundryVTT journal
   - Wraps: `scripts.full_pipeline.main()` (relevant portions)
   - Returns: Journal UUID, name, output dir, chapter count

### Result Dataclasses

```python
@dataclass
class ActorCreationResult:
    """Result from creating a D&D actor."""
    foundry_uuid: str
    name: str
    challenge_rating: float
    output_dir: Path
    timestamp: str

@dataclass
class MapExtractionResult:
    """Result from extracting maps from a PDF."""
    maps: List[dict]  # MapMetadata dicts
    output_dir: Path
    total_maps: int
    timestamp: str

@dataclass
class JournalCreationResult:
    """Result from creating a FoundryVTT journal."""
    journal_uuid: str
    journal_name: str
    output_dir: Path
    chapter_count: int
    timestamp: str
```

### Error Handling

**Custom Exception:**
```python
class APIError(Exception):
    """Raised when API operations fail."""
    pass
```

**Wrapping Strategy:**
- Catch internal exceptions (Gemini errors, file errors, FoundryVTT errors)
- Re-raise as `APIError` with clear message
- Preserve original exception as `__cause__`

**Rationale:** Pythonic (exceptions for errors), but provides clean boundary between internal implementation and public API.

## Implementation Strategy

### Phase 1: Create Result Models (TDD)
1. Define dataclasses in `src/api.py`
2. Write tests that instantiate them
3. Verify serialization works (for JSON export)

### Phase 2: Implement `create_actor()` (TDD)
1. Write failing test for happy path
2. Implement thin wrapper around `orchestrate.create_actor_from_description_sync()`
3. Add error handling test
4. Implement APIError wrapping

### Phase 3: Implement `extract_maps()` (TDD)
1. Write failing test with sample PDF
2. Implement wrapper around map extraction
3. Transform output to MapExtractionResult
4. Error handling

### Phase 4: Implement `process_pdf_to_journal()` (TDD)
1. Write failing test (may need mocking due to complexity)
2. Implement wrapper around pipeline components
3. Handle skip_upload flag
4. Error handling

### Phase 5: Documentation & Examples
1. Add comprehensive module docstring
2. Add usage examples to CLAUDE.md
3. Document error cases

## Testing Strategy

### Unit Tests
- `tests/api/test_api.py`: Test each function with mocks/fixtures
- Mock expensive operations (Gemini calls, FoundryVTT API)
- Use existing test PDFs and fixtures

### Integration Tests
- Mark with `@pytest.mark.integration`
- Test real end-to-end workflows
- Verify actual FoundryVTT interactions

### Test Fixtures
- Leverage existing: `test_pdf_path`, `test_output_dir` from conftest.py
- Add new: `mock_foundry_client`, `sample_map_metadata`

## Dependencies

**Existing modules used:**
- `actors.orchestrate` (already has sync wrapper)
- `pdf_processing.image_asset_processing.extract_map_assets`
- `scripts.full_pipeline` (need to refactor to expose reusable functions)
- `foundry.client` (for FoundryVTT operations)

**No new external dependencies required.**

## Migration Path

**Not a breaking change** - existing code continues to work. Chat UI can gradually migrate to use `api.py` instead of direct imports.

**Future:** When adding new capabilities, expose them through `api.py` facade first.

## Alternative Approaches Considered

### Thin Facade (Re-exports)
```python
# src/api.py
from actors.orchestrate import create_actor_from_description_sync as create_actor
```
**Rejected:** Doesn't provide clean return types or error boundary.

### FastAPI Endpoints Directly
**Rejected:** Couples API to HTTP transport. Python API is more flexible.

### Async API
**Rejected:** Added complexity without current need. Chat UI can block on operations.

## Open Questions

None - design validated through brainstorming session.

## Success Criteria

1. Chat UI can import and use all three functions
2. All functions return rich, typed result objects
3. Error handling prevents internal exceptions from leaking
4. Tests provide 100% coverage of happy paths and error cases
5. Documentation makes API self-explanatory

## References

- Brainstorming session: 2025-11-05
- Existing orchestration: `src/actors/orchestrate.py`
- Map extraction: `src/pdf_processing/image_asset_processing/extract_map_assets.py`
- Pipeline: `scripts/full_pipeline.py`
