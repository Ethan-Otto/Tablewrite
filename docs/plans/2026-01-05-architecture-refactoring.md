# Architecture Refactoring Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Eliminate brittle import patterns, consolidate confusing module naming, extract caches to a dedicated layer, and standardize configuration management.

**Architecture:** Create centralized `src/config.py` for path/env management, rename `src/actors/` to `src/actor_pipeline/` for clarity, extract caches from `foundry/` to `src/caches/`, and create a base exception hierarchy.

**Tech Stack:** Python 3.11, Pydantic, pytest, dotenv

---

## Phase 1: Centralized Configuration (High Impact, Medium Effort)

### Task 1.1: Create src/config.py Module

**Files:**
- Create: `src/config.py`
- Test: `tests/test_config.py`

**Step 1: Write the failing test**

Create `tests/test_config.py`:
```python
"""Tests for centralized configuration module."""

import pytest
import os
from pathlib import Path


class TestProjectConfig:
    """Tests for project configuration."""

    def test_project_root_is_correct(self):
        """Should return the project root directory."""
        from config import PROJECT_ROOT

        # Project root should contain key files
        assert (PROJECT_ROOT / "pyproject.toml").exists()
        assert (PROJECT_ROOT / "src").is_dir()

    def test_src_dir_is_correct(self):
        """Should return the src directory."""
        from config import SRC_DIR

        assert SRC_DIR.is_dir()
        assert (SRC_DIR / "api.py").exists()

    def test_get_env_returns_value(self):
        """Should return environment variable value."""
        from config import get_env

        # Set a test variable
        os.environ["TEST_CONFIG_VAR"] = "test_value"

        result = get_env("TEST_CONFIG_VAR")

        assert result == "test_value"

        # Cleanup
        del os.environ["TEST_CONFIG_VAR"]

    def test_get_env_returns_default(self):
        """Should return default when env var not set."""
        from config import get_env

        result = get_env("NONEXISTENT_VAR_12345", default="fallback")

        assert result == "fallback"

    def test_get_env_raises_without_default(self):
        """Should raise KeyError when var not set and no default."""
        from config import get_env

        with pytest.raises(KeyError):
            get_env("NONEXISTENT_VAR_12345")
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_config.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'config'"

**Step 3: Create the config module**

Create `src/config.py`:
```python
"""Centralized configuration for the D&D module converter.

This module provides:
- PROJECT_ROOT and SRC_DIR paths
- Environment variable access with get_env()
- Automatic .env loading

Usage:
    from config import PROJECT_ROOT, get_env

    api_key = get_env("GeminiImageAPI")
    data_dir = PROJECT_ROOT / "data" / "pdfs"
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Calculate paths once at import time
SRC_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SRC_DIR.parent.resolve()

# Load .env from project root
_env_path = PROJECT_ROOT / ".env"
if _env_path.exists():
    load_dotenv(_env_path)


def get_env(key: str, default: Optional[str] = None) -> str:
    """Get environment variable value.

    Args:
        key: Environment variable name
        default: Default value if not set. If None and key not found, raises KeyError.

    Returns:
        Environment variable value or default

    Raises:
        KeyError: If key not found and no default provided
    """
    value = os.environ.get(key)
    if value is not None:
        return value
    if default is not None:
        return default
    raise KeyError(f"Environment variable '{key}' not set and no default provided")


# Common configuration values
def get_gemini_api_key() -> str:
    """Get Gemini API key from environment."""
    return get_env("GeminiImageAPI")


def get_backend_url() -> str:
    """Get backend URL for API calls."""
    return get_env("BACKEND_URL", default="http://localhost:8000")


def get_foundry_url() -> str:
    """Get FoundryVTT URL."""
    return get_env("FOUNDRY_URL", default="http://localhost:30000")
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_config.py -v`
Expected: PASS (5 tests)

**Step 5: Commit**

```bash
git add src/config.py tests/test_config.py
git commit -m "feat: add centralized config module"
```

---

### Task 1.2: Update pdf_processing Imports

**Files:**
- Modify: `src/pdf_processing/pdf_to_xml.py`
- Modify: `src/pdf_processing/split_pdf.py`

**Step 1: Check current import pattern in pdf_to_xml.py**

Run: `head -30 src/pdf_processing/pdf_to_xml.py`
Expected: See `sys.path.insert` and `os.path.dirname` patterns

**Step 2: Update pdf_to_xml.py imports**

Replace the path manipulation at the top of `src/pdf_processing/pdf_to_xml.py`:

Old pattern (remove):
```python
import sys
import os
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))
from logging_config import setup_logging
```

New pattern:
```python
from config import PROJECT_ROOT, get_env
from logging_config import setup_logging
```

**Step 3: Update split_pdf.py imports**

Apply same pattern to `src/pdf_processing/split_pdf.py`.

**Step 4: Test pdf_processing still works**

Run: `uv run pytest tests/pdf_processing/ -v -m "not integration and not slow" -k "not full_pdf"`
Expected: PASS

**Step 5: Commit**

```bash
git add src/pdf_processing/pdf_to_xml.py src/pdf_processing/split_pdf.py
git commit -m "refactor: use config module in pdf_processing"
```

---

### Task 1.3: Update wall_detection Imports

**Files:**
- Modify: `src/wall_detection/redline_walls.py`

**Step 1: Read current imports**

Run: `head -30 src/wall_detection/redline_walls.py`

**Step 2: Update imports**

Replace path manipulation with:
```python
from config import PROJECT_ROOT, get_env
```

**Step 3: Test wall_detection**

Run: `uv run pytest tests/wall_detection/ -v -m "not integration"`
Expected: PASS

**Step 4: Commit**

```bash
git add src/wall_detection/redline_walls.py
git commit -m "refactor: use config module in wall_detection"
```

---

### Task 1.4: Update scene_extraction Imports

**Files:**
- Modify: `src/scene_extraction/generate_artwork.py`
- Modify: `src/scene_extraction/extract_scenes.py`

**Step 1: Update imports in both files**

Replace path manipulation with:
```python
from config import PROJECT_ROOT, get_env
```

**Step 2: Test scene_extraction**

Run: `uv run pytest tests/scene_extraction/ -v -m "not integration"`
Expected: PASS

**Step 3: Commit**

```bash
git add src/scene_extraction/
git commit -m "refactor: use config module in scene_extraction"
```

---

### Task 1.5: Update Backend Tools Imports

**Files:**
- Modify: `ui/backend/app/tools/actor_creator.py`
- Modify: `ui/backend/app/tools/batch_actor_creator.py`
- Modify: `ui/backend/app/tools/scene_creator.py`
- Modify: `ui/backend/app/tools/image_generator.py`

**Step 1: Update actor_creator.py**

Replace:
```python
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))
env_path = project_root / ".env"
load_dotenv(env_path)
```

With:
```python
# Add src to path for imports (backend tools run from ui/backend)
import sys
from pathlib import Path
_src_dir = Path(__file__).parent.parent.parent.parent.parent / "src"
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

from config import PROJECT_ROOT, get_env
```

**Step 2: Apply same pattern to other tools**

Update `batch_actor_creator.py`, `scene_creator.py`, `image_generator.py`.

**Step 3: Test backend tools**

Run: `cd ui/backend && uv run pytest tests/ -v -k "tool" --ignore=tests/integration`
Expected: PASS

**Step 4: Commit**

```bash
git add ui/backend/app/tools/
git commit -m "refactor: use config module in backend tools"
```

---

### Task 1.6: Phase 1 Checkpoint

**Step 1: Run smoke tests**

Run: `uv run pytest -m smoke -v`
Expected: All PASS

**Step 2: Verify no remaining sys.path.insert patterns in src/**

Run: `grep -r "sys.path.insert" src/ --include="*.py" | wc -l`
Expected: 0 (or minimal necessary)

**Step 3: Commit checkpoint**

```bash
git add -A
git commit -m "checkpoint: Phase 1 complete - centralized configuration"
```

---

## Phase 2: Extract Caches to Dedicated Layer (Medium Impact, Medium Effort)

### Task 2.1: Create src/caches Module Structure

**Files:**
- Create: `src/caches/__init__.py`
- Create: `src/caches/spell_cache.py`
- Create: `src/caches/icon_cache.py`
- Test: `tests/caches/__init__.py`
- Test: `tests/caches/test_spell_cache.py`

**Step 1: Write the failing test**

Create `tests/caches/__init__.py`:
```python
"""Tests for caches module."""
```

Create `tests/caches/test_spell_cache.py`:
```python
"""Tests for spell_cache module."""

import pytest


class TestSpellCacheImports:
    """Tests that SpellCache can be imported from caches."""

    def test_imports_from_caches(self):
        """Should import SpellCache from caches module."""
        from caches import SpellCache

        assert SpellCache is not None

    def test_spell_cache_has_get_method(self):
        """Should have get_spell_uuid method."""
        from caches import SpellCache

        cache = SpellCache()
        assert hasattr(cache, 'get_spell_uuid')
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/caches/test_spell_cache.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'caches'"

**Step 3: Create caches module by copying from foundry/actors/**

```bash
mkdir -p src/caches
```

Create `src/caches/__init__.py`:
```python
"""Centralized caching for external resource lookups.

This module provides caches for:
- SpellCache: Spell name → compendium UUID
- IconCache: Icon path lookups

These caches are separated from foundry/ because they are data structures,
not network operations.
"""

from .spell_cache import SpellCache
from .icon_cache import IconCache

__all__ = ["SpellCache", "IconCache"]
```

**Step 4: Copy and update spell_cache.py**

```bash
cp src/foundry/actors/spell_cache.py src/caches/spell_cache.py
```

Update imports in `src/caches/spell_cache.py`:
```python
"""Spell cache for resolving spell names to compendium UUIDs."""

import logging
from typing import Dict, Optional, List
from config import get_backend_url

logger = logging.getLogger(__name__)
```

**Step 5: Copy and update icon_cache.py**

```bash
cp src/foundry/icon_cache.py src/caches/icon_cache.py
```

Update imports similarly.

**Step 6: Run test to verify it passes**

Run: `uv run pytest tests/caches/test_spell_cache.py -v`
Expected: PASS

**Step 7: Commit**

```bash
git add src/caches/ tests/caches/
git commit -m "feat: extract caches to dedicated src/caches module"
```

---

### Task 2.2: Update Consumers to Use New Cache Location

**Files:**
- Modify: `src/actors/orchestrate.py`
- Modify: `src/foundry_converters/actors/converter.py`
- Modify: `ui/backend/app/tools/actor_creator.py`

**Step 1: Update orchestrate.py**

Change:
```python
from foundry.actors.spell_cache import SpellCache
from foundry.icon_cache import IconCache
```

To:
```python
from caches import SpellCache, IconCache
```

**Step 2: Update converter.py if it imports caches**

Check and update similarly.

**Step 3: Update backend tools**

Update `actor_creator.py` and `batch_actor_creator.py`.

**Step 4: Run tests**

Run: `uv run pytest tests/actors/ tests/foundry_converters/ -v -m "not integration"`
Expected: PASS

**Step 5: Commit**

```bash
git add src/actors/ src/foundry_converters/ ui/backend/app/tools/
git commit -m "refactor: update imports to use caches module"
```

---

### Task 2.3: Delete Old Cache Files

**Files:**
- Delete: `src/foundry/actors/spell_cache.py`
- Delete: `src/foundry/icon_cache.py`

**Step 1: Verify no remaining imports**

Run: `grep -r "from foundry.actors.spell_cache" src/ --include="*.py"`
Run: `grep -r "from foundry.icon_cache" src/ --include="*.py"`
Expected: No matches

**Step 2: Delete old files**

```bash
rm src/foundry/actors/spell_cache.py
rm src/foundry/icon_cache.py
```

**Step 3: Run tests**

Run: `uv run pytest -m smoke -v`
Expected: PASS

**Step 4: Commit**

```bash
git add -A
git commit -m "chore: delete old cache files from foundry/"
```

---

### Task 2.4: Phase 2 Checkpoint

**Step 1: Run smoke tests**

Run: `uv run pytest -m smoke -v`
Expected: All PASS

**Step 2: Commit checkpoint**

```bash
git add -A
git commit -m "checkpoint: Phase 2 complete - caches extracted to dedicated layer"
```

---

## Phase 3: Rename Confusing Module (Medium Impact, Low Effort)

### Task 3.1: Rename src/actors to src/actor_pipeline

**Files:**
- Rename: `src/actors/` → `src/actor_pipeline/`
- Update: All imports throughout codebase

**Step 1: Create new directory and copy files**

```bash
mkdir -p src/actor_pipeline
cp -r src/actors/* src/actor_pipeline/
```

**Step 2: Update __init__.py**

Create `src/actor_pipeline/__init__.py`:
```python
"""Actor creation pipeline.

This module handles the generation, parsing, and orchestration of actor creation.
For FoundryVTT CRUD operations, see src/foundry/actors/.

Pipeline:
    Description → StatBlock text → StatBlock model → ParsedActorData → FoundryVTT JSON
"""

from .models import StatBlock
from .orchestrate import (
    create_actor_from_description,
    create_actor_from_description_sync,
    create_actors_batch,
    create_actors_batch_sync,
    ActorCreationResult,
)

__all__ = [
    "StatBlock",
    "create_actor_from_description",
    "create_actor_from_description_sync",
    "create_actors_batch",
    "create_actors_batch_sync",
    "ActorCreationResult",
]
```

**Step 3: Update api.py imports**

Change in `src/api.py`:
```python
from actors.orchestrate import create_actor_from_description_sync
```

To:
```python
from actor_pipeline.orchestrate import create_actor_from_description_sync
```

**Step 4: Update all other imports**

Run: `grep -r "from actors\." src/ --include="*.py" -l`

Update each file to use `actor_pipeline` instead of `actors`.

**Step 5: Run tests**

Run: `uv run pytest tests/actors/ -v -m "not integration"`
Expected: PASS

**Step 6: Commit**

```bash
git add src/actor_pipeline/ src/api.py
git commit -m "feat: create actor_pipeline module (copy from actors)"
```

---

### Task 3.2: Update Test Imports

**Files:**
- Rename: `tests/actors/` → `tests/actor_pipeline/`

**Step 1: Create new test directory**

```bash
mkdir -p tests/actor_pipeline
cp -r tests/actors/* tests/actor_pipeline/
```

**Step 2: Update imports in test files**

Change all:
```python
from actors import ...
```

To:
```python
from actor_pipeline import ...
```

**Step 3: Run tests from new location**

Run: `uv run pytest tests/actor_pipeline/ -v -m "not integration"`
Expected: PASS

**Step 4: Commit**

```bash
git add tests/actor_pipeline/
git commit -m "test: copy tests to actor_pipeline"
```

---

### Task 3.3: Delete Old actors Directory

**Files:**
- Delete: `src/actors/`
- Delete: `tests/actors/`

**Step 1: Verify no remaining imports**

Run: `grep -r "from actors\." src/ ui/backend/ --include="*.py" | grep -v actor_pipeline`
Expected: No matches

**Step 2: Delete old directories**

```bash
rm -rf src/actors/
rm -rf tests/actors/
```

**Step 3: Run smoke tests**

Run: `uv run pytest -m smoke -v`
Expected: PASS

**Step 4: Commit**

```bash
git add -A
git commit -m "chore: delete old actors directory (replaced by actor_pipeline)"
```

---

### Task 3.4: Phase 3 Checkpoint

**Step 1: Verify module naming is clear**

Run: `ls -la src/`
Expected: See `actor_pipeline/` (generation) and `foundry/actors/` (CRUD) clearly separated

**Step 2: Commit checkpoint**

```bash
git add -A
git commit -m "checkpoint: Phase 3 complete - module naming clarified"
```

---

## Phase 4: Standardize Error Handling (Low Impact, Low Effort)

### Task 4.1: Create Exception Hierarchy

**Files:**
- Create: `src/exceptions.py`
- Test: `tests/test_exceptions.py`

**Step 1: Write the failing test**

Create `tests/test_exceptions.py`:
```python
"""Tests for exception hierarchy."""

import pytest


class TestExceptionHierarchy:
    """Tests for exception classes."""

    def test_base_exception_exists(self):
        """Should have DNDModuleError base exception."""
        from exceptions import DNDModuleError

        assert issubclass(DNDModuleError, Exception)

    def test_conversion_error_inherits(self):
        """ConversionError should inherit from DNDModuleError."""
        from exceptions import DNDModuleError, ConversionError

        assert issubclass(ConversionError, DNDModuleError)

    def test_foundry_error_inherits(self):
        """FoundryError should inherit from DNDModuleError."""
        from exceptions import DNDModuleError, FoundryError

        assert issubclass(FoundryError, DNDModuleError)

    def test_configuration_error_inherits(self):
        """ConfigurationError should inherit from DNDModuleError."""
        from exceptions import DNDModuleError, ConfigurationError

        assert issubclass(ConfigurationError, DNDModuleError)

    def test_exception_has_message(self):
        """Exceptions should store message."""
        from exceptions import ConversionError

        err = ConversionError("parsing failed")

        assert str(err) == "parsing failed"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_exceptions.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'exceptions'"

**Step 3: Create exceptions module**

Create `src/exceptions.py`:
```python
"""Centralized exception hierarchy for D&D module converter.

Usage:
    from exceptions import ConversionError, FoundryError

    raise ConversionError("Failed to parse stat block")
    raise FoundryError("Failed to upload actor")
"""


class DNDModuleError(Exception):
    """Base exception for all D&D module converter errors."""
    pass


class ConversionError(DNDModuleError):
    """Raised when parsing or conversion fails.

    Examples:
        - XML parsing failure
        - StatBlock parsing failure
        - Invalid data format
    """
    pass


class FoundryError(DNDModuleError):
    """Raised when FoundryVTT operations fail.

    Examples:
        - WebSocket connection failure
        - Actor creation failure
        - Journal upload failure
    """
    pass


class ConfigurationError(DNDModuleError):
    """Raised when configuration is invalid or missing.

    Examples:
        - Missing API key
        - Invalid file path
        - Missing .env file
    """
    pass


class ValidationError(DNDModuleError):
    """Raised when validation fails.

    Examples:
        - Invalid challenge rating
        - Missing required fields
        - Data integrity check failure
    """
    pass
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_exceptions.py -v`
Expected: PASS (5 tests)

**Step 5: Commit**

```bash
git add src/exceptions.py tests/test_exceptions.py
git commit -m "feat: add centralized exception hierarchy"
```

---

### Task 4.2: Update api.py to Use New Exceptions

**Files:**
- Modify: `src/api.py`

**Step 1: Update api.py**

Replace:
```python
class APIError(Exception):
    """Raised when API operations fail."""
    pass
```

With:
```python
from exceptions import FoundryError, ConversionError, ConfigurationError

# Re-export for backwards compatibility
APIError = FoundryError
```

**Step 2: Run API tests**

Run: `uv run pytest tests/api/ -v`
Expected: PASS

**Step 3: Commit**

```bash
git add src/api.py
git commit -m "refactor: use exception hierarchy in api.py"
```

---

### Task 4.3: Phase 4 Checkpoint

**Step 1: Run all tests**

Run: `uv run pytest -m smoke -v`
Expected: All PASS

**Step 2: Commit checkpoint**

```bash
git add -A
git commit -m "checkpoint: Phase 4 complete - standardized error handling"
```

---

## Phase 5: Update Documentation and Final Verification

### Task 5.1: Update CLAUDE.md Architecture Section

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Update architecture diagram**

Update the Architecture section to reflect new structure:
```
src/
├── actor_pipeline/         # Actor creation pipeline (generation, parsing)
├── caches/                 # Centralized caches (SpellCache, IconCache)
├── config.py               # Centralized configuration
├── exceptions.py           # Exception hierarchy
├── foundry/                # Network operations (CRUD, WebSocket)
├── foundry_converters/     # Pure conversion logic (no network)
├── models/                 # Core data models
├── pdf_processing/         # PDF extraction
├── scene_extraction/       # Scene artwork generation
├── scenes/                 # Scene creation orchestration
├── wall_detection/         # Wall detection
├── util/                   # Utilities
└── api.py                  # Public API
```

**Step 2: Update import examples**

Update code examples to use new import paths.

**Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md for new architecture"
```

---

### Task 5.2: Run Full Test Suite

**Step 1: Run smoke tests**

Run: `uv run pytest -m smoke -v`
Expected: All PASS

**Step 2: Run full test suite**

Run: `uv run pytest --full -v 2>&1 | tee test_full_output.log`
Expected: All tests PASS

**Step 3: Verify import patterns**

Run: `grep -r "sys.path.insert.*PROJECT_ROOT\|os.path.dirname.*__file__" src/ --include="*.py" | wc -l`
Expected: 0 or minimal necessary

**Step 4: Commit**

```bash
git add -A
git commit -m "test: verify full test suite passes after refactoring"
```

---

### Task 5.3: Final Summary Commit

**Step 1: Create summary commit**

```bash
git add -A
git commit -m "feat: complete architecture refactoring

Summary of changes:
- Created src/config.py for centralized path/env management
- Extracted caches to src/caches/ (SpellCache, IconCache)
- Renamed src/actors/ to src/actor_pipeline/ for clarity
- Created src/exceptions.py with exception hierarchy
- Updated all imports throughout codebase
- Updated CLAUDE.md documentation

Benefits:
- No more brittle sys.path manipulation
- Clear separation: actor_pipeline (generation) vs foundry/actors (CRUD)
- Caches are data structures, not network operations
- Consistent error handling with typed exceptions"
```

---

## Success Criteria Checklist

- [ ] `from config import PROJECT_ROOT, get_env` works everywhere
- [ ] No `sys.path.insert` with `os.path.dirname` patterns in src/
- [ ] `src/caches/` contains SpellCache and IconCache
- [ ] `src/actor_pipeline/` contains generation/parsing logic
- [ ] `src/foundry/actors/` contains only CRUD operations
- [ ] `src/exceptions.py` provides typed exception hierarchy
- [ ] `uv run pytest -m smoke` passes
- [ ] `uv run pytest --full` passes (with Foundry connected)
- [ ] CLAUDE.md reflects new structure
