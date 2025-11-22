# Actor Creation Orchestration Design

**Date:** 2025-11-03
**Status:** Approved
**Location:** `src/actors/create_actor.py`

## Overview

Design for a single async orchestration function that creates a complete D&D 5e actor from a natural language description and uploads it to FoundryVTT. The function chains together the entire pipeline: text generation → stat block parsing → detailed parsing → FoundryVTT conversion → upload.

## Requirements

### Functional Requirements
- Accept natural language description and optional CR
- Generate complete stat block and biography using Gemini
- Parse stat block into structured data
- Convert to FoundryVTT actor format
- Upload to FoundryVTT server
- Save all intermediate outputs for debugging

### Design Constraints
- **Architecture:** Single async pipeline function (function-based coding preference)
- **Error Handling:** Fail fast - stop on first error, no retries
- **Intermediate Files:** Save all intermediate outputs (txt, StatBlock JSON, ParsedActorData JSON, FoundryVTT JSON)
- **Duplicates:** Always create new actors (allow duplicates in FoundryVTT)

## Architecture

### Function Signature

```python
async def create_actor_from_description(
    description: str,
    challenge_rating: Optional[float] = None,
    name: Optional[str] = None,
    bio_context: Optional[str] = None,
    foundry_client: Optional[FoundryClient] = None,
    output_dir: Optional[Path] = None
) -> ActorCreationResult
```

**Parameters:**
- `description`: Natural language description of creature/NPC
- `challenge_rating`: Optional CR (0.125-30). If None, Gemini auto-determines appropriate CR
- `name`: Optional custom name (Gemini generates if not provided)
- `bio_context`: Optional additional context for biography
- `foundry_client`: Optional FoundryClient for upload. If None, stops after JSON generation (dry run)
- `output_dir`: Optional custom output directory (defaults to `output/actors/`)

### Pipeline Flow

```
1. generate_actor_from_description()
   ↓ (generates actor.txt)
2. parse_raw_text_to_statblock()
   ↓ (produces StatBlock)
3. parse_stat_block_parallel()
   ↓ (produces ParsedActorData with SpellCache)
4. convert_to_foundry()
   ↓ (produces FoundryVTT JSON)
5. ActorManager.create_actor()
   ↓ (returns actor UUID)
```

### Result Model

```python
@dataclass
class ActorCreationResult:
    """Complete result of actor creation pipeline."""
    actor_uuid: str                        # FoundryVTT actor UUID
    actor_name: str                        # Final actor name
    challenge_rating: float                # Final CR (useful when auto-determined)
    text_file_path: Path                   # Generated .txt file
    stat_block: StatBlock                  # Parsed stat block
    parsed_data: ParsedActorData           # Detailed parse with attacks/traits
    foundry_json: dict                     # FoundryVTT actor JSON
    output_directory: Path                 # Where all files saved
    metadata: dict                         # Pipeline execution metadata
```

## Data Flow & Outputs

### Output Directory Structure

```
output/actors/<timestamp>_<actor_name>/
├── actor.txt                    # Generated stat block + bio
├── stat_block.json              # Parsed StatBlock
├── parsed_actor_data.json       # ParsedActorData with attacks/traits
├── foundry_actor.json           # Final FoundryVTT format
└── metadata.json                # Pipeline metadata (CR used, timestamps, etc.)
```

**Directory Naming:**
- Format: `<YYYYMMDD_HHMMSS>_<sanitized_actor_name>/`
- Example: `20241103_210530_grok_silverblade/`
- Prevents conflicts, allows multiple generations of same actor

**Default output_dir:** `output/actors/` (created if doesn't exist)

### Intermediate File Purposes

| File | Purpose |
|------|---------|
| `actor.txt` | Debug Gemini text generation, manual review |
| `stat_block.json` | Verify basic parsing (AC, HP, CR, abilities) |
| `parsed_actor_data.json` | Debug detailed parsing (attacks, traits, spells) |
| `foundry_actor.json` | Inspect final format before upload |
| `metadata.json` | Track execution (timestamps, models used, warnings) |

## Error Handling

### Strategy: Fail Fast

- Each pipeline step wrapped in try/except
- On error: log detailed error, save partial progress, raise exception immediately
- No automatic retries (user manually retries by calling function again)
- Clean failures with validation at step boundaries

### Validation Points

1. **After text generation:** Verify .txt file exists and has content
2. **After StatBlock parsing:** Validate required fields (AC, HP, CR) present and in valid ranges
3. **After ParsedActorData:** Check at least one action exists
4. **Before FoundryVTT upload:** Verify client connected and authenticated
5. **After upload:** Confirm actor UUID returned

### Partial Progress on Failure

If step 3 fails, steps 1-2 outputs still saved in output directory. User can:
- Inspect intermediate files to debug
- Potentially resume from failed step manually (not automated)

### Error Message Format

```
ActorCreationError: Failed to parse stat block at step 2
  Generated text file: output/actors/20241103_210530_fire_drake/actor.txt
  Error: StatBlock missing required field 'armor_class'
  See logs in: output/actors/20241103_210530_fire_drake/metadata.json
```

## Dependencies

### Existing Modules

```python
from actors.generate_actor_file import generate_actor_from_description
from actors.statblock_parser import parse_raw_text_to_statblock
from actors.models import StatBlock
from foundry.actors.parser import parse_stat_block_parallel
from foundry.actors.converter import convert_to_foundry
from foundry.actors.manager import ActorManager
from foundry.actors.models import ParsedActorData
from foundry.actors.spell_cache import SpellCache
from foundry.client import FoundryClient
```

### Spell Cache Handling

- If `foundry_client` provided: load `SpellCache` once at start
- Pass to `parse_stat_block_parallel()` for spell UUID resolution
- Cache reused across pipeline (no redundant API calls)
- If no client: spell UUIDs not resolved (still works, just no spell links)

### FoundryClient Handling

- **If None:** Pipeline stops after generating `foundry_json` (dry run mode)
- **If provided:** Creates `ActorManager` and uploads to FoundryVTT
- Useful for inspecting generated JSON before uploading

## Usage Examples

### Full Pipeline with Upload

```python
from actors.create_actor import create_actor_from_description
from foundry.client import FoundryClient

client = FoundryClient(target="local")
result = await create_actor_from_description(
    description="A fire-breathing drake with crystalline scales",
    challenge_rating=7,
    foundry_client=client
)
print(f"Created actor: {result.actor_uuid}")
print(f"CR: {result.challenge_rating}")
```

### Dry Run (No Upload)

```python
result = await create_actor_from_description(
    description="An ancient lich with reality-warping powers",
    foundry_client=None  # No upload
)
# Inspect result.foundry_json before uploading
print(f"Generated actor in: {result.output_directory}")
```

### Auto-Determine CR

```python
result = await create_actor_from_description(
    description="A shadowy assassin with teleportation abilities",
    bio_context="Leader of the Nightblade Guild"
    # CR not specified - Gemini determines appropriate level
)
print(f"Gemini chose CR {result.challenge_rating}")
```

## Convenience Functions

### Synchronous Wrapper

```python
def create_actor_sync(
    description: str,
    challenge_rating: Optional[float] = None,
    name: Optional[str] = None,
    bio_context: Optional[str] = None,
    foundry_client: Optional[FoundryClient] = None,
    output_dir: Optional[Path] = None
) -> ActorCreationResult:
    """Synchronous wrapper for create_actor_from_description."""
    return asyncio.run(create_actor_from_description(
        description, challenge_rating, name, bio_context,
        foundry_client, output_dir
    ))
```

### Batch Creation

```python
async def create_multiple_actors(
    descriptions: list[tuple[str, Optional[float]]],
    foundry_client: Optional[FoundryClient] = None
) -> list[ActorCreationResult]:
    """Create multiple actors in parallel.

    Args:
        descriptions: List of (description, challenge_rating) tuples
        foundry_client: Optional client for upload

    Returns:
        List of ActorCreationResult objects
    """
    tasks = [
        create_actor_from_description(desc, cr, foundry_client=foundry_client)
        for desc, cr in descriptions
    ]
    return await asyncio.gather(*tasks)
```

## Implementation Notes

### File Location
- **Main function:** `src/actors/create_actor.py`
- **Result model:** `ActorCreationResult` dataclass in same file

### Metadata Tracking
The `metadata.json` includes:
- Timestamp for each pipeline step
- Which Gemini model was used
- Whether CR was auto-determined (and Gemini's reasoning if so)
- Any warnings or notes during processing
- Total execution time

### Logging
- Use standard `logging` module
- Log at INFO level for each pipeline step
- Log at DEBUG level for intermediate data transformations
- Log at ERROR level for failures with full traceback

## Testing Strategy

### Unit Tests
- Mock each pipeline step
- Test error handling at each validation point
- Verify partial progress saved on failure

### Integration Tests
- End-to-end with real Gemini API calls
- Test with various CR levels (auto and explicit)
- Test dry run mode (no FoundryVTT client)
- Verify all intermediate files saved correctly

### Manual Testing
- Generate actors with complex descriptions
- Verify FoundryVTT upload works
- Inspect intermediate files for debugging workflow
