# Module Processing Tab Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a "Module" tab to the Tablewrite sidebar that allows users to upload D&D module PDFs and import them into FoundryVTT as journals, actors, scenes, and generated artwork.

**Architecture:** A new TypeScript UI component (`ModuleUpload.ts`) handles PDF upload with checkboxes for extraction options. A new Python backend router (`modules.py`) orchestrates the existing `full_pipeline.py` functions. Results are organized into Foundry folders named after the module. Progress is simulated client-side while the long-running backend operation completes.

**Tech Stack:** TypeScript (Foundry module), Python/FastAPI (backend), existing pipeline modules

---

## Task 1: Backend Models and Router Skeleton

**Files:**
- Create: `ui/backend/app/routers/modules.py`
- Modify: `ui/backend/app/main.py:57-65`
- Test: `ui/backend/tests/routers/test_modules.py`

**Step 1: Write the failing test**

Create `ui/backend/tests/routers/test_modules.py`:

```python
"""Tests for POST /api/modules/process endpoint."""

import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from app.main import app

client = TestClient(app)

# Test fixture path - navigate from ui/backend/tests/routers/ to project root
TEST_PDF = Path(__file__).parent.parent.parent.parent.parent / "data/pdfs/Lost_Mine_of_Phandelver_test.pdf"


def test_process_module_endpoint_exists():
    """Test that the endpoint exists and rejects requests without a file."""
    response = client.post("/api/modules/process", data={})
    # 422 means endpoint exists but validation failed (no file)
    assert response.status_code == 422


def test_process_module_success():
    """Test successful module processing with mocked pipeline."""
    assert TEST_PDF.exists(), f"Test fixture not found: {TEST_PDF}"

    # Mock the entire pipeline function
    mock_result = {
        "success": True,
        "folders": {
            "actors": "Folder.abc123",
            "scenes": "Folder.def456",
            "journals": "Folder.ghi789"
        },
        "created": {
            "journal": {"uuid": "JournalEntry.xyz", "name": "Test Module", "page_count": 5},
            "actors": [{"uuid": "Actor.a1", "name": "Goblin"}],
            "scenes": [{"uuid": "Scene.s1", "name": "Cave", "wall_count": 10}],
            "artwork_journal": None
        }
    }

    with patch("app.routers.modules.process_module_sync", return_value=mock_result):
        with open(TEST_PDF, "rb") as f:
            response = client.post(
                "/api/modules/process",
                files={"file": ("test_module.pdf", f, "application/pdf")},
                data={
                    "module_name": "Test Module",
                    "extract_journal": "true",
                    "extract_actors": "true",
                    "extract_battle_maps": "true",
                    "generate_scene_artwork": "false"
                },
            )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["created"]["journal"]["uuid"] == "JournalEntry.xyz"
    assert len(data["created"]["actors"]) == 1


def test_process_module_options_parsed():
    """Test that options are correctly parsed and passed to pipeline."""
    assert TEST_PDF.exists()

    mock_result = {
        "success": True,
        "folders": {},
        "created": {"journal": None, "actors": [], "scenes": [], "artwork_journal": None}
    }

    with patch("app.routers.modules.process_module_sync", return_value=mock_result) as mock_fn:
        with open(TEST_PDF, "rb") as f:
            response = client.post(
                "/api/modules/process",
                files={"file": ("test.pdf", f, "application/pdf")},
                data={
                    "module_name": "My Module",
                    "extract_journal": "true",
                    "extract_actors": "false",
                    "extract_battle_maps": "true",
                    "generate_scene_artwork": "false"
                },
            )

    assert response.status_code == 200
    # Verify options were passed correctly
    call_kwargs = mock_fn.call_args.kwargs
    assert call_kwargs["module_name"] == "My Module"
    assert call_kwargs["extract_journal"] is True
    assert call_kwargs["extract_actors"] is False
    assert call_kwargs["extract_battle_maps"] is True
    assert call_kwargs["generate_scene_artwork"] is False
```

**Step 2: Run test to verify it fails**

Run: `cd ui/backend && uv run pytest tests/routers/test_modules.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'app.routers.modules'"

**Step 3: Write minimal router implementation**

Create `ui/backend/app/routers/modules.py`:

```python
"""Module processing endpoint - orchestrates full PDF to FoundryVTT pipeline."""

import asyncio
import logging
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, UploadFile

# Add src to path for pipeline imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "src"))

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/modules", tags=["modules"])


def process_module_sync(
    pdf_path: Path,
    module_name: str,
    extract_journal: bool = True,
    extract_actors: bool = True,
    extract_battle_maps: bool = True,
    generate_scene_artwork: bool = True,
) -> dict:
    """
    Synchronous wrapper for module processing pipeline.

    This is a placeholder - will be implemented in Task 2.
    """
    return {
        "success": True,
        "folders": {},
        "created": {
            "journal": None,
            "actors": [],
            "scenes": [],
            "artwork_journal": None
        }
    }


@router.post("/process")
async def process_module_endpoint(
    file: UploadFile = File(...),
    module_name: str = Form(...),
    extract_journal: bool = Form(True),
    extract_actors: bool = Form(True),
    extract_battle_maps: bool = Form(True),
    generate_scene_artwork: bool = Form(True),
):
    """
    Process a D&D module PDF and import into FoundryVTT.

    Runs the full pipeline: split PDF -> XML -> actors -> scenes -> journals.
    This is a long-running operation (5-30 minutes depending on module size).

    Args:
        file: D&D module PDF file
        module_name: Name for the module (used for folder names)
        extract_journal: Extract journal content (default: True)
        extract_actors: Extract actors from stat blocks (default: True)
        extract_battle_maps: Extract battle maps as scenes (default: True)
        generate_scene_artwork: Generate AI scene artwork (default: True)

    Returns:
        Processing result with created items and folder UUIDs
    """
    # Save uploaded file to temp location
    temp_dir = Path(tempfile.mkdtemp())
    temp_file = temp_dir / file.filename
    try:
        content = await file.read()
        with open(temp_file, "wb") as f:
            f.write(content)

        # Run pipeline in thread pool (blocking operations)
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: process_module_sync(
                pdf_path=temp_file,
                module_name=module_name,
                extract_journal=extract_journal,
                extract_actors=extract_actors,
                extract_battle_maps=extract_battle_maps,
                generate_scene_artwork=generate_scene_artwork,
            )
        )

        return result
    finally:
        # Cleanup temp file
        shutil.rmtree(temp_dir, ignore_errors=True)
```

**Step 4: Register router in main.py**

Edit `ui/backend/app/main.py` to add import and registration:

```python
# At top with other imports (around line 14):
from app.routers import modules

# In router registration section (around line 65):
app.include_router(modules.router)
```

**Step 5: Run tests to verify they pass**

Run: `cd ui/backend && uv run pytest tests/routers/test_modules.py -v`
Expected: PASS (all 3 tests)

**Step 6: Commit**

```bash
git add ui/backend/app/routers/modules.py ui/backend/tests/routers/test_modules.py ui/backend/app/main.py
git commit -m "feat: add module processing endpoint skeleton"
```

---

## Task 2: Implement Pipeline Orchestration

**Files:**
- Modify: `ui/backend/app/routers/modules.py`
- Test: `ui/backend/tests/routers/test_modules.py` (add integration test)

**Step 1: Write integration test (for later verification)**

Add to `ui/backend/tests/routers/test_modules.py`:

```python
@pytest.mark.integration
@pytest.mark.slow
def test_process_module_integration():
    """Integration test: Process real test PDF (journal only, no actors/scenes).

    This test uses the 7-page test PDF and only extracts journal content
    to keep runtime reasonable (~2 minutes).
    """
    assert TEST_PDF.exists(), f"Test fixture not found: {TEST_PDF}"

    with open(TEST_PDF, "rb") as f:
        response = client.post(
            "/api/modules/process",
            files={"file": ("Lost_Mine_of_Phandelver_test.pdf", f, "application/pdf")},
            data={
                "module_name": "Integration Test Module",
                "extract_journal": "true",
                "extract_actors": "false",
                "extract_battle_maps": "false",
                "generate_scene_artwork": "false"
            },
            timeout=300.0,  # 5 minute timeout
        )

    assert response.status_code == 200, f"Failed: {response.text}"
    data = response.json()
    assert data["success"] is True
    assert data["created"]["journal"] is not None
    assert data["created"]["journal"]["uuid"].startswith("JournalEntry.")
```

**Step 2: Implement process_module_sync**

Replace the placeholder in `ui/backend/app/routers/modules.py`:

```python
"""Module processing endpoint - orchestrates full PDF to FoundryVTT pipeline."""

import asyncio
import logging
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, File, Form, UploadFile

# Add src to path for pipeline imports
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from pdf_processing.split_pdf import split_pdf
from pdf_processing.pdf_to_xml import process_pdf_sections
from actors.process_actors import process_actors_for_run
from pdf_processing.image_asset_processing.extract_map_assets import extract_maps_from_pdf
from foundry.upload_journal_to_foundry import upload_journal_to_foundry
from app.websocket.push import get_or_create_folder

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/modules", tags=["modules"])


def process_module_sync(
    pdf_path: Path,
    module_name: str,
    extract_journal: bool = True,
    extract_actors: bool = True,
    extract_battle_maps: bool = True,
    generate_scene_artwork: bool = True,
) -> dict:
    """
    Synchronous wrapper for module processing pipeline.

    Orchestrates: split PDF -> XML -> actors -> scenes -> artwork -> journals
    All items are placed in folders named after the module.

    Args:
        pdf_path: Path to uploaded PDF file
        module_name: Name for module (used for folder names)
        extract_journal: Whether to create journal entries
        extract_actors: Whether to extract and create actors
        extract_battle_maps: Whether to extract maps as scenes
        generate_scene_artwork: Whether to generate AI artwork

    Returns:
        Dict with success status, folders, and created items
    """
    result = {
        "success": True,
        "error": None,
        "folders": {},
        "created": {
            "journal": None,
            "actors": [],
            "scenes": [],
            "artwork_journal": None
        }
    }

    # Create timestamped run directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = PROJECT_ROOT / "output" / "runs" / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Step 1: Copy PDF to data directory and split into chapters
        logger.info(f"Step 1: Splitting PDF into chapters")
        pdf_sections_dir = PROJECT_ROOT / "data" / "pdf_sections" / module_name
        pdf_sections_dir.mkdir(parents=True, exist_ok=True)

        # Copy source PDF to expected location
        source_pdf = PROJECT_ROOT / "data" / "pdfs" / pdf_path.name
        source_pdf.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(pdf_path, source_pdf)

        split_pdf(str(source_pdf), str(pdf_sections_dir))

        # Step 2: Convert chapters to XML
        logger.info(f"Step 2: Converting chapters to XML")
        process_pdf_sections(str(pdf_sections_dir), str(run_dir))

        # Step 3: Extract actors (if enabled)
        if extract_actors:
            logger.info(f"Step 3: Extracting actors from stat blocks")
            try:
                actor_results = process_actors_for_run(run_dir, folder_name=module_name)
                result["created"]["actors"] = [
                    {"uuid": a.uuid, "name": a.name}
                    for a in actor_results
                ]
            except Exception as e:
                logger.error(f"Actor extraction failed: {e}")
                result["error"] = {"stage": "extract_actors", "message": str(e)}
                result["success"] = False
                return result

        # Step 4: Extract battle maps as scenes (if enabled)
        if extract_battle_maps:
            logger.info(f"Step 4: Extracting battle maps")
            try:
                map_results = extract_maps_from_pdf(
                    pdf_path=source_pdf,
                    output_dir=run_dir / "map_assets",
                    folder_name=module_name
                )
                result["created"]["scenes"] = [
                    {"uuid": s.uuid, "name": s.name, "wall_count": s.wall_count}
                    for s in map_results
                ]
            except Exception as e:
                logger.error(f"Map extraction failed: {e}")
                result["error"] = {"stage": "extract_battle_maps", "message": str(e)}
                result["success"] = False
                return result

        # Step 5: Generate scene artwork (if enabled)
        if generate_scene_artwork:
            logger.info(f"Step 5: Generating scene artwork")
            try:
                # Import here to avoid circular dependency
                from scripts.generate_scene_art import process_run_for_artwork
                artwork_result = process_run_for_artwork(run_dir, folder_name=module_name)
                if artwork_result:
                    result["created"]["artwork_journal"] = {
                        "uuid": artwork_result.uuid,
                        "name": artwork_result.name,
                        "image_count": artwork_result.image_count
                    }
            except Exception as e:
                logger.error(f"Artwork generation failed: {e}")
                # Non-fatal - continue with journal upload

        # Step 6: Upload journal to Foundry (if enabled)
        if extract_journal:
            logger.info(f"Step 6: Uploading journal to FoundryVTT")
            try:
                journal_result = upload_journal_to_foundry(
                    run_dir=run_dir,
                    journal_name=module_name,
                    folder_name=module_name
                )
                result["created"]["journal"] = {
                    "uuid": journal_result.uuid,
                    "name": journal_result.name,
                    "page_count": journal_result.page_count
                }
            except Exception as e:
                logger.error(f"Journal upload failed: {e}")
                result["error"] = {"stage": "upload_journal", "message": str(e)}
                result["success"] = False
                return result

        logger.info(f"Module processing complete: {module_name}")
        return result

    except Exception as e:
        logger.error(f"Module processing failed: {e}")
        result["success"] = False
        result["error"] = {"stage": "unknown", "message": str(e)}
        return result


@router.post("/process")
async def process_module_endpoint(
    file: UploadFile = File(...),
    module_name: str = Form(...),
    extract_journal: bool = Form(True),
    extract_actors: bool = Form(True),
    extract_battle_maps: bool = Form(True),
    generate_scene_artwork: bool = Form(True),
):
    """
    Process a D&D module PDF and import into FoundryVTT.

    Runs the full pipeline: split PDF -> XML -> actors -> scenes -> journals.
    This is a long-running operation (5-30 minutes depending on module size).

    Args:
        file: D&D module PDF file
        module_name: Name for the module (used for folder names)
        extract_journal: Extract journal content (default: True)
        extract_actors: Extract actors from stat blocks (default: True)
        extract_battle_maps: Extract battle maps as scenes (default: True)
        generate_scene_artwork: Generate AI scene artwork (default: True)

    Returns:
        Processing result with created items and folder UUIDs
    """
    # Save uploaded file to temp location
    temp_dir = Path(tempfile.mkdtemp())
    temp_file = temp_dir / file.filename
    try:
        content = await file.read()
        with open(temp_file, "wb") as f:
            f.write(content)

        # Run pipeline in thread pool (blocking operations)
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: process_module_sync(
                pdf_path=temp_file,
                module_name=module_name,
                extract_journal=extract_journal,
                extract_actors=extract_actors,
                extract_battle_maps=extract_battle_maps,
                generate_scene_artwork=generate_scene_artwork,
            )
        )

        return result
    finally:
        # Cleanup temp file
        shutil.rmtree(temp_dir, ignore_errors=True)
```

**Step 3: Run unit tests**

Run: `cd ui/backend && uv run pytest tests/routers/test_modules.py -v -k "not integration"`
Expected: PASS

**Step 4: Commit**

```bash
git add ui/backend/app/routers/modules.py ui/backend/tests/routers/test_modules.py
git commit -m "feat: implement module processing pipeline orchestration"
```

---

## Task 3: Add Folder Creation for All Document Types

**Files:**
- Modify: `ui/backend/app/routers/modules.py`
- Test: `ui/backend/tests/routers/test_modules.py`

**Step 1: Write failing test for folder creation**

Add to `ui/backend/tests/routers/test_modules.py`:

```python
@pytest.mark.asyncio
async def test_process_module_creates_folders():
    """Test that processing creates folders for each document type."""
    from app.routers.modules import create_folders_for_module

    # Mock the folder creation function
    with patch("app.routers.modules.get_or_create_folder") as mock_folder:
        mock_folder.return_value = MagicMock(
            success=True,
            folder_id="folder123",
            folder_uuid="Folder.folder123"
        )

        folders = await create_folders_for_module("Test Module")

        # Verify all 3 folder types created
        assert mock_folder.call_count == 3
        call_args = [call.args for call in mock_folder.call_args_list]
        assert ("Test Module", "Actor") in call_args
        assert ("Test Module", "Scene") in call_args
        assert ("Test Module", "JournalEntry") in call_args

        # Verify folder IDs returned
        assert folders["actors"] == "folder123"
        assert folders["scenes"] == "folder123"
        assert folders["journals"] == "folder123"
```

**Step 2: Run test to verify it fails**

Run: `cd ui/backend && uv run pytest tests/routers/test_modules.py::test_process_module_creates_folders -v`
Expected: FAIL with "cannot import name 'create_folders_for_module'"

**Step 3: Implement folder creation function**

Add to `ui/backend/app/routers/modules.py` (before `process_module_sync`):

```python
async def create_folders_for_module(module_name: str) -> Dict[str, str]:
    """
    Create folders for actors, scenes, and journals.

    Args:
        module_name: Name for the folders

    Returns:
        Dict mapping document type to folder ID
    """
    folders = {}

    for doc_type, key in [("Actor", "actors"), ("Scene", "scenes"), ("JournalEntry", "journals")]:
        result = await get_or_create_folder(module_name, doc_type)
        if result.success and result.folder_id:
            folders[key] = result.folder_id
            logger.info(f"Created/found {doc_type} folder: {module_name} -> {result.folder_id}")
        else:
            logger.warning(f"Failed to create {doc_type} folder: {result.error}")

    return folders
```

**Step 4: Run test to verify it passes**

Run: `cd ui/backend && uv run pytest tests/routers/test_modules.py::test_process_module_creates_folders -v`
Expected: PASS

**Step 5: Commit**

```bash
git add ui/backend/app/routers/modules.py ui/backend/tests/routers/test_modules.py
git commit -m "feat: add folder creation for module documents"
```

---

## Task 4: Create ModuleUpload TypeScript Component

**Files:**
- Create: `foundry-module/tablewrite-assistant/src/ui/ModuleUpload.ts`

**Step 1: Create the component file**

Create `foundry-module/tablewrite-assistant/src/ui/ModuleUpload.ts`:

```typescript
/**
 * Module Upload Component
 *
 * Handles PDF upload and module processing with configurable options.
 */

export class ModuleUpload {
  private container: HTMLElement;
  private backendUrl: string;
  private progressInterval: ReturnType<typeof setInterval> | null = null;

  constructor(container: HTMLElement, backendUrl: string) {
    this.container = container;
    this.backendUrl = backendUrl;
  }

  render(): void {
    this.container.innerHTML = `
      <div class="module-upload">
        <h3>Import D&D Module</h3>

        <div class="upload-form">
          <div class="form-group">
            <label>Module PDF</label>
            <div class="file-drop-zone" id="module-drop-zone">
              <input type="file" id="module-file" accept=".pdf" />
              <p>Drop PDF here or click to select</p>
            </div>
            <div class="file-name" id="selected-file-name"></div>
          </div>

          <div class="form-group">
            <label>Module Name</label>
            <input type="text" id="module-name" placeholder="Auto-derived from filename" />
          </div>

          <div class="form-group options-group">
            <label>Options</label>
            <div class="checkbox-list">
              <label class="checkbox-item">
                <input type="checkbox" id="opt-journal" checked />
                Extract Journal
              </label>
              <label class="checkbox-item">
                <input type="checkbox" id="opt-actors" checked />
                Extract Actors
              </label>
              <label class="checkbox-item">
                <input type="checkbox" id="opt-maps" checked />
                Extract Battle Maps
              </label>
              <label class="checkbox-item">
                <input type="checkbox" id="opt-artwork" checked />
                Generate Scene Artwork
              </label>
            </div>
          </div>

          <button id="import-module-btn" class="primary" disabled>Import Module</button>
        </div>

        <div class="progress-container" style="display: none">
          <div class="progress-bar">
            <div class="progress-fill" id="progress-fill"></div>
          </div>
          <div class="progress-status" id="progress-status">Preparing...</div>
          <button id="cancel-btn" class="secondary">Cancel</button>
        </div>

        <div class="result-container" style="display: none">
          <div class="result-summary" id="result-summary"></div>
          <div class="result-details" id="result-details"></div>
          <button id="import-another-btn" class="secondary">Import Another</button>
        </div>
      </div>
    `;

    this.attachEventListeners();
  }

  private attachEventListeners(): void {
    // File input change
    const fileInput = this.container.querySelector('#module-file') as HTMLInputElement;
    fileInput.addEventListener('change', () => this.handleFileSelect());

    // Drag and drop
    const dropZone = this.container.querySelector('#module-drop-zone') as HTMLElement;
    dropZone.addEventListener('dragover', (e) => {
      e.preventDefault();
      dropZone.classList.add('drag-over');
    });
    dropZone.addEventListener('dragleave', () => {
      dropZone.classList.remove('drag-over');
    });
    dropZone.addEventListener('drop', (e) => {
      e.preventDefault();
      dropZone.classList.remove('drag-over');
      if (e.dataTransfer?.files.length) {
        fileInput.files = e.dataTransfer.files;
        this.handleFileSelect();
      }
    });

    // Import button
    const importBtn = this.container.querySelector('#import-module-btn') as HTMLButtonElement;
    importBtn.addEventListener('click', () => this.handleImport());

    // Cancel button
    const cancelBtn = this.container.querySelector('#cancel-btn') as HTMLButtonElement;
    cancelBtn.addEventListener('click', () => this.handleCancel());

    // Import another button
    const anotherBtn = this.container.querySelector('#import-another-btn') as HTMLButtonElement;
    anotherBtn.addEventListener('click', () => this.resetForm());
  }

  private handleFileSelect(): void {
    const fileInput = this.container.querySelector('#module-file') as HTMLInputElement;
    const fileNameDisplay = this.container.querySelector('#selected-file-name') as HTMLElement;
    const moduleNameInput = this.container.querySelector('#module-name') as HTMLInputElement;
    const importBtn = this.container.querySelector('#import-module-btn') as HTMLButtonElement;

    const file = fileInput.files?.[0];
    if (file) {
      fileNameDisplay.textContent = file.name;

      // Auto-populate module name from filename
      if (!moduleNameInput.value) {
        const baseName = file.name.replace(/\.pdf$/i, '').replace(/_/g, ' ');
        moduleNameInput.value = baseName;
      }

      importBtn.disabled = false;
    } else {
      fileNameDisplay.textContent = '';
      importBtn.disabled = true;
    }
  }

  private async handleImport(): Promise<void> {
    const fileInput = this.container.querySelector('#module-file') as HTMLInputElement;
    const file = fileInput.files?.[0];

    if (!file) {
      (globalThis as any).ui?.notifications?.error('Please select a PDF file');
      return;
    }

    const moduleNameInput = this.container.querySelector('#module-name') as HTMLInputElement;
    const moduleName = moduleNameInput.value || file.name.replace(/\.pdf$/i, '').replace(/_/g, ' ');

    // Get options
    const extractJournal = (this.container.querySelector('#opt-journal') as HTMLInputElement).checked;
    const extractActors = (this.container.querySelector('#opt-actors') as HTMLInputElement).checked;
    const extractMaps = (this.container.querySelector('#opt-maps') as HTMLInputElement).checked;
    const generateArtwork = (this.container.querySelector('#opt-artwork') as HTMLInputElement).checked;

    // Build form data
    const formData = new FormData();
    formData.append('file', file);
    formData.append('module_name', moduleName);
    formData.append('extract_journal', extractJournal.toString());
    formData.append('extract_actors', extractActors.toString());
    formData.append('extract_battle_maps', extractMaps.toString());
    formData.append('generate_scene_artwork', generateArtwork.toString());

    this.showProgress('Starting import...');
    this.simulateProgress();

    try {
      const response = await fetch(`${this.backendUrl}/api/modules/process`, {
        method: 'POST',
        body: formData,
      });

      this.stopProgress();

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${await response.text()}`);
      }

      const result = await response.json();

      if (result.success) {
        this.showSuccess(result);
      } else {
        this.showError(result.error);
      }
    } catch (error: any) {
      this.stopProgress();
      (globalThis as any).ui?.notifications?.error(`Import failed: ${error.message}`);
      this.showError({ stage: 'network', message: error.message });
    }
  }

  private handleCancel(): void {
    this.stopProgress();
    this.resetForm();
    (globalThis as any).ui?.notifications?.info('Import cancelled');
  }

  private showProgress(message: string): void {
    const form = this.container.querySelector('.upload-form') as HTMLElement;
    const progress = this.container.querySelector('.progress-container') as HTMLElement;
    const result = this.container.querySelector('.result-container') as HTMLElement;

    form.style.display = 'none';
    progress.style.display = 'block';
    result.style.display = 'none';

    this.updateProgress(0, message);
  }

  private updateProgress(percent: number, message: string): void {
    const fill = this.container.querySelector('#progress-fill') as HTMLElement;
    const status = this.container.querySelector('#progress-status') as HTMLElement;

    fill.style.width = `${percent}%`;
    status.textContent = message;
  }

  private simulateProgress(): void {
    const stages = [
      { pct: 5, msg: 'Uploading PDF...' },
      { pct: 10, msg: 'Splitting into chapters...' },
      { pct: 25, msg: 'Converting to XML (this takes a while)...' },
      { pct: 50, msg: 'Extracting actors...' },
      { pct: 65, msg: 'Processing battle maps...' },
      { pct: 80, msg: 'Generating scene artwork...' },
      { pct: 90, msg: 'Uploading to FoundryVTT...' },
      { pct: 95, msg: 'Finalizing...' },
    ];

    let i = 0;
    this.progressInterval = setInterval(() => {
      if (i < stages.length) {
        this.updateProgress(stages[i].pct, stages[i].msg);
        i++;
      }
    }, 30000); // Update every 30 seconds
  }

  private stopProgress(): void {
    if (this.progressInterval) {
      clearInterval(this.progressInterval);
      this.progressInterval = null;
    }
  }

  private showSuccess(result: any): void {
    const progress = this.container.querySelector('.progress-container') as HTMLElement;
    const resultContainer = this.container.querySelector('.result-container') as HTMLElement;
    const summary = this.container.querySelector('#result-summary') as HTMLElement;
    const details = this.container.querySelector('#result-details') as HTMLElement;

    progress.style.display = 'none';
    resultContainer.style.display = 'block';

    summary.innerHTML = '<span class="success-icon">✓</span> Import Complete';
    summary.classList.add('success');

    // Build details HTML
    let detailsHtml = '';

    if (result.created.journal) {
      detailsHtml += `
        <div class="result-section">
          <h4>Journal</h4>
          <div class="result-item">
            <a href="#" data-uuid="${result.created.journal.uuid}">${result.created.journal.name}</a>
            <span class="count">(${result.created.journal.page_count} pages)</span>
          </div>
        </div>
      `;
    }

    if (result.created.actors?.length > 0) {
      detailsHtml += `
        <div class="result-section">
          <h4 class="collapsible">Actors <span class="count">(${result.created.actors.length})</span></h4>
          <div class="result-list collapsed">
            ${result.created.actors.map((a: any) => `
              <div class="result-item">
                <a href="#" data-uuid="${a.uuid}">${a.name}</a>
              </div>
            `).join('')}
          </div>
        </div>
      `;
    }

    if (result.created.scenes?.length > 0) {
      detailsHtml += `
        <div class="result-section">
          <h4 class="collapsible">Scenes <span class="count">(${result.created.scenes.length})</span></h4>
          <div class="result-list collapsed">
            ${result.created.scenes.map((s: any) => `
              <div class="result-item">
                <a href="#" data-uuid="${s.uuid}">${s.name}</a>
                <span class="meta">${s.wall_count} walls</span>
              </div>
            `).join('')}
          </div>
        </div>
      `;
    }

    if (result.created.artwork_journal) {
      detailsHtml += `
        <div class="result-section">
          <h4>Scene Artwork Gallery</h4>
          <div class="result-item">
            <a href="#" data-uuid="${result.created.artwork_journal.uuid}">${result.created.artwork_journal.name}</a>
            <span class="count">(${result.created.artwork_journal.image_count} images)</span>
          </div>
        </div>
      `;
    }

    details.innerHTML = detailsHtml;

    // Attach click handlers for UUIDs
    details.querySelectorAll('a[data-uuid]').forEach(link => {
      link.addEventListener('click', (e) => {
        e.preventDefault();
        const uuid = (link as HTMLElement).dataset.uuid;
        this.openByUuid(uuid!);
      });
    });

    // Attach collapse/expand handlers
    details.querySelectorAll('h4.collapsible').forEach(header => {
      header.addEventListener('click', () => {
        const list = header.nextElementSibling as HTMLElement;
        list.classList.toggle('collapsed');
        header.classList.toggle('expanded');
      });
    });
  }

  private showError(error: any): void {
    const progress = this.container.querySelector('.progress-container') as HTMLElement;
    const resultContainer = this.container.querySelector('.result-container') as HTMLElement;
    const summary = this.container.querySelector('#result-summary') as HTMLElement;
    const details = this.container.querySelector('#result-details') as HTMLElement;

    progress.style.display = 'none';
    resultContainer.style.display = 'block';

    summary.innerHTML = `<span class="error-icon">✗</span> Import Failed at: ${error.stage || 'unknown'}`;
    summary.classList.add('error');

    details.innerHTML = `<div class="error-message">${error.message || 'Unknown error'}</div>`;
  }

  private openByUuid(uuid: string): void {
    // Parse UUID to determine document type
    const [type, id] = uuid.split('.');

    // Use Foundry's document retrieval
    const doc = (globalThis as any).fromUuidSync?.(uuid);
    if (doc) {
      doc.sheet?.render(true);
    } else {
      (globalThis as any).ui?.notifications?.warn(`Could not find document: ${uuid}`);
    }
  }

  private resetForm(): void {
    const form = this.container.querySelector('.upload-form') as HTMLElement;
    const progress = this.container.querySelector('.progress-container') as HTMLElement;
    const result = this.container.querySelector('.result-container') as HTMLElement;

    form.style.display = 'block';
    progress.style.display = 'none';
    result.style.display = 'none';

    // Reset form inputs
    const fileInput = this.container.querySelector('#module-file') as HTMLInputElement;
    const fileNameDisplay = this.container.querySelector('#selected-file-name') as HTMLElement;
    const moduleNameInput = this.container.querySelector('#module-name') as HTMLInputElement;
    const importBtn = this.container.querySelector('#import-module-btn') as HTMLButtonElement;

    fileInput.value = '';
    fileNameDisplay.textContent = '';
    moduleNameInput.value = '';
    importBtn.disabled = true;

    // Reset summary styling
    const summary = this.container.querySelector('#result-summary') as HTMLElement;
    summary.classList.remove('success', 'error');
  }
}
```

**Step 2: Build the module to verify TypeScript compiles**

Run: `cd foundry-module/tablewrite-assistant && npm run build`
Expected: PASS (no TypeScript errors)

**Step 3: Commit**

```bash
git add foundry-module/tablewrite-assistant/src/ui/ModuleUpload.ts
git commit -m "feat: add ModuleUpload TypeScript component"
```

---

## Task 5: Integrate Module Tab into TablewriteTab

**Files:**
- Modify: `foundry-module/tablewrite-assistant/src/ui/TablewriteTab.ts`

**Step 1: Read current TablewriteTab.ts structure**

Run: `cat foundry-module/tablewrite-assistant/src/ui/TablewriteTab.ts`
Note the existing tab structure and where to add the new tab.

**Step 2: Add Module tab to TablewriteTab**

Add import at top:
```typescript
import { ModuleUpload } from './ModuleUpload.js';
```

Add new tab button in tabs div (after Battle Map button):
```typescript
<button class="tab-btn" data-tab="module">Module</button>
```

Add new tab content div (after battlemap-tab):
```typescript
<div class="tab-content" id="module-tab" style="display: none"></div>
```

Initialize ModuleUpload in render method (after BattleMapUpload initialization):
```typescript
const moduleContainer = this.container.querySelector('#module-tab');
if (moduleContainer) {
  const moduleUpload = new ModuleUpload(moduleContainer as HTMLElement, this.backendUrl);
  moduleUpload.render();
}
```

**Step 3: Build to verify compilation**

Run: `cd foundry-module/tablewrite-assistant && npm run build`
Expected: PASS

**Step 4: Commit**

```bash
git add foundry-module/tablewrite-assistant/src/ui/TablewriteTab.ts
git commit -m "feat: integrate Module tab into TablewriteTab"
```

---

## Task 6: Add CSS Styles for Module Tab

**Files:**
- Modify: `foundry-module/tablewrite-assistant/styles/module.css`

**Step 1: Add styles for module upload component**

Append to `foundry-module/tablewrite-assistant/styles/module.css`:

```css
/* ==================== Module Upload Tab ==================== */

.module-upload {
  padding: 10px;
}

.module-upload h3 {
  margin: 0 0 15px 0;
  font-size: 14px;
  color: #fff;
}

/* File drop zone */
.module-upload .file-drop-zone {
  border: 2px dashed #555;
  border-radius: 8px;
  padding: 20px;
  text-align: center;
  cursor: pointer;
  transition: border-color 0.2s, background-color 0.2s;
  position: relative;
}

.module-upload .file-drop-zone:hover,
.module-upload .file-drop-zone.drag-over {
  border-color: #7a4;
  background-color: rgba(119, 170, 68, 0.1);
}

.module-upload .file-drop-zone input[type="file"] {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  opacity: 0;
  cursor: pointer;
}

.module-upload .file-drop-zone p {
  margin: 0;
  color: #888;
  font-size: 12px;
}

.module-upload .file-name {
  margin-top: 8px;
  font-size: 12px;
  color: #7a4;
  font-weight: 500;
}

/* Options checkboxes */
.module-upload .options-group {
  margin-top: 15px;
}

.module-upload .checkbox-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.module-upload .checkbox-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #ccc;
  cursor: pointer;
}

.module-upload .checkbox-item input[type="checkbox"] {
  width: 14px;
  height: 14px;
  cursor: pointer;
}

/* Form inputs */
.module-upload .form-group {
  margin-bottom: 12px;
}

.module-upload .form-group > label {
  display: block;
  margin-bottom: 4px;
  font-weight: 500;
  font-size: 12px;
  color: #aaa;
}

.module-upload input[type="text"] {
  width: 100%;
  padding: 8px;
  border: 1px solid #555;
  border-radius: 4px;
  background: #333;
  color: #fff;
  font-size: 12px;
}

.module-upload input[type="text"]:focus {
  border-color: #7a4;
  outline: none;
}

/* Buttons */
.module-upload button.primary {
  width: 100%;
  padding: 12px;
  background: #7a4;
  border: none;
  border-radius: 4px;
  color: #fff;
  font-weight: bold;
  font-size: 13px;
  cursor: pointer;
  margin-top: 15px;
  transition: background-color 0.2s;
}

.module-upload button.primary:hover:not(:disabled) {
  background: #8b5;
}

.module-upload button.primary:disabled {
  background: #444;
  color: #666;
  cursor: not-allowed;
}

.module-upload button.secondary {
  width: 100%;
  padding: 10px;
  background: #444;
  border: none;
  border-radius: 4px;
  color: #ccc;
  font-size: 12px;
  cursor: pointer;
  margin-top: 10px;
}

.module-upload button.secondary:hover {
  background: #555;
}

/* Progress section */
.module-upload .progress-container {
  padding: 20px 10px;
}

.module-upload .progress-bar {
  height: 24px;
  background: #333;
  border-radius: 12px;
  overflow: hidden;
}

.module-upload .progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #7a4, #5a2);
  width: 0%;
  transition: width 0.5s ease;
}

.module-upload .progress-status {
  margin-top: 12px;
  text-align: center;
  color: #aaa;
  font-size: 12px;
}

/* Result section */
.module-upload .result-container {
  padding: 10px;
}

.module-upload .result-summary {
  padding: 12px;
  border-radius: 6px;
  margin-bottom: 15px;
  font-size: 14px;
  font-weight: 500;
}

.module-upload .result-summary.success {
  background: rgba(119, 170, 68, 0.2);
  color: #7a4;
}

.module-upload .result-summary.error {
  background: rgba(200, 60, 60, 0.2);
  color: #c44;
}

.module-upload .success-icon,
.module-upload .error-icon {
  margin-right: 8px;
}

.module-upload .result-section {
  margin-bottom: 15px;
}

.module-upload .result-section h4 {
  font-size: 12px;
  color: #aaa;
  margin: 0 0 8px 0;
  padding-bottom: 4px;
  border-bottom: 1px solid #444;
}

.module-upload .result-section h4.collapsible {
  cursor: pointer;
}

.module-upload .result-section h4.collapsible:hover {
  color: #fff;
}

.module-upload .result-section h4.collapsible::before {
  content: '▶ ';
  font-size: 10px;
}

.module-upload .result-section h4.collapsible.expanded::before {
  content: '▼ ';
}

.module-upload .result-list {
  max-height: 200px;
  overflow-y: auto;
}

.module-upload .result-list.collapsed {
  display: none;
}

.module-upload .result-item {
  padding: 6px 0;
  font-size: 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.module-upload .result-item a {
  color: #4b8b3b;
  text-decoration: none;
}

.module-upload .result-item a:hover {
  color: #7a4;
  text-decoration: underline;
}

.module-upload .result-item .count,
.module-upload .result-item .meta {
  color: #666;
  font-size: 11px;
}

.module-upload .error-message {
  padding: 10px;
  background: rgba(200, 60, 60, 0.1);
  border-radius: 4px;
  color: #c44;
  font-size: 12px;
}
```

**Step 2: Build module to verify CSS is included**

Run: `cd foundry-module/tablewrite-assistant && npm run build`
Expected: PASS

**Step 3: Commit**

```bash
git add foundry-module/tablewrite-assistant/styles/module.css
git commit -m "feat: add CSS styles for Module upload tab"
```

---

## Task 7: Playwright UI Verification

**Files:**
- Create: `foundry-module/tablewrite-assistant/scripts/feedback/test_module_tab.py`

**Step 1: Write the Playwright verification script**

Create `foundry-module/tablewrite-assistant/scripts/feedback/test_module_tab.py`:

```python
#!/usr/bin/env python3
"""
Playwright verification for Module tab UI.

Usage:
    cd foundry-module/tablewrite-assistant/scripts/feedback
    python test_module_tab.py
"""

from foundry_helper import FoundrySession
import time


def verify_module_tab():
    """Verify Module tab renders correctly and is interactive."""
    results = {
        "tab_visible": False,
        "tab_clickable": False,
        "form_elements": {},
        "screenshot": None
    }

    with FoundrySession(headless=False) as session:
        # Navigate to Tablewrite
        session.goto_tablewrite()
        time.sleep(1)

        # Check if Module tab button exists
        module_btn = session.page.locator('.tab-btn[data-tab="module"]')
        results["tab_visible"] = module_btn.count() > 0
        print(f"Module tab visible: {results['tab_visible']}")

        if not results["tab_visible"]:
            print("ERROR: Module tab button not found!")
            return results

        # Click Module tab
        module_btn.click()
        time.sleep(0.5)
        results["tab_clickable"] = True
        print("Module tab clicked successfully")

        # Verify form elements exist
        form_checks = {
            "file_input": '#module-file',
            "module_name": '#module-name',
            "opt_journal": '#opt-journal',
            "opt_actors": '#opt-actors',
            "opt_maps": '#opt-maps',
            "opt_artwork": '#opt-artwork',
            "import_btn": '#import-module-btn',
            "drop_zone": '#module-drop-zone'
        }

        for name, selector in form_checks.items():
            el = session.page.locator(selector)
            exists = el.count() > 0
            results["form_elements"][name] = exists
            status = "OK" if exists else "MISSING"
            print(f"  {name}: {status}")

        # Verify checkboxes are checked by default
        for opt in ['opt_journal', 'opt_actors', 'opt_maps', 'opt_artwork']:
            checkbox = session.page.locator(f'#{opt}')
            if checkbox.count() > 0:
                checked = checkbox.is_checked()
                print(f"  {opt} checked: {checked}")

        # Verify import button is disabled (no file selected)
        import_btn = session.page.locator('#import-module-btn')
        if import_btn.count() > 0:
            disabled = import_btn.is_disabled()
            print(f"  Import button disabled (expected): {disabled}")

        # Take screenshot
        results["screenshot"] = session.screenshot("/tmp/module_tab.png", "#sidebar")

        # Verify CSS styling
        drop_zone = session.page.locator('#module-drop-zone')
        if drop_zone.count() > 0:
            styles = drop_zone.evaluate('''el => {
                const s = window.getComputedStyle(el);
                return {
                    border: s.border,
                    borderRadius: s.borderRadius,
                    padding: s.padding
                };
            }''')
            print(f"  Drop zone styles: {styles}")

    # Summary
    all_elements_ok = all(results["form_elements"].values())
    print(f"\n{'SUCCESS' if all_elements_ok else 'FAILURE'}: All form elements present: {all_elements_ok}")

    return results


if __name__ == "__main__":
    verify_module_tab()
```

**Step 2: Run the verification**

Prerequisites:
- Foundry running at localhost:30000
- "Testing" user available (no password)
- Tablewrite module enabled and built

Run: `cd foundry-module/tablewrite-assistant/scripts/feedback && python test_module_tab.py`

Expected output:
```
Module tab visible: True
Module tab clicked successfully
  file_input: OK
  module_name: OK
  opt_journal: OK
  opt_actors: OK
  opt_maps: OK
  opt_artwork: OK
  import_btn: OK
  drop_zone: OK
  opt_journal checked: True
  opt_actors checked: True
  opt_maps checked: True
  opt_artwork checked: True
  Import button disabled (expected): True
Screenshot saved: /tmp/module_tab.png
  Drop zone styles: {...}

SUCCESS: All form elements present: True
```

**Step 3: Review screenshot**

Open `/tmp/module_tab.png` and verify:
1. Tab button shows "Module"
2. Drop zone is styled with dashed border
3. Module name input is visible
4. All 4 checkboxes are visible and checked
5. Import button is styled and disabled
6. Overall layout matches design

**Step 4: Fix any issues found**

If elements are missing or styled incorrectly, fix the TypeScript/CSS and rebuild:
```bash
cd foundry-module/tablewrite-assistant && npm run build
# Then re-run verification
```

**Step 5: Commit verification script**

```bash
git add foundry-module/tablewrite-assistant/scripts/feedback/test_module_tab.py
git commit -m "test: add Playwright verification for Module tab UI"
```

---

## Task 8: Integration Test with Real PDF

**Files:**
- Modify: `ui/backend/tests/routers/test_modules.py`

**Step 1: Run the integration test**

Run: `cd ui/backend && uv run pytest tests/routers/test_modules.py::test_process_module_integration -v --timeout=600`

Expected: PASS (creates journal in Foundry with test PDF content)

Note: This test requires:
1. Backend running: `cd ui/backend && uvicorn app.main:app --reload`
2. Foundry connected with Tablewrite module
3. Valid API keys in .env

**Step 2: Manual UI verification**

1. Open Foundry at localhost:30000
2. Click the Tablewrite tab in sidebar
3. Click "Module" tab
4. Upload test PDF: `data/pdfs/Lost_Mine_of_Phandelver_test.pdf`
5. Verify module name auto-populates
6. Uncheck "Extract Actors" and "Extract Battle Maps" for quick test
7. Click "Import Module"
8. Verify progress updates
9. Verify success shows created journal
10. Click journal link to open it

**Step 3: Commit any fixes from testing**

```bash
git add -A
git commit -m "fix: integration test corrections from manual testing"
```

---

## Task 9: Add Smoke Test for Module Processing

**Files:**
- Create: `tests/api/test_modules_smoke.py`

**Step 1: Write smoke test**

Create `tests/api/test_modules_smoke.py`:

```python
"""Smoke tests for module processing endpoint."""

import pytest
from pathlib import Path
import httpx


TEST_PDF = Path(__file__).parent.parent.parent / "data/pdfs/Lost_Mine_of_Phandelver_test.pdf"


@pytest.mark.smoke
@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.asyncio
async def test_module_processing_smoke(check_api_key, ensure_foundry_connected):
    """Smoke test: Process test PDF with journal only (fastest option).

    Creates a journal from the 7-page test PDF.
    Takes ~2 minutes with Gemini API.
    """
    assert TEST_PDF.exists(), f"Test PDF not found: {TEST_PDF}"

    async with httpx.AsyncClient() as client:
        with open(TEST_PDF, "rb") as f:
            response = await client.post(
                "http://localhost:8000/api/modules/process",
                files={"file": ("test_module.pdf", f, "application/pdf")},
                data={
                    "module_name": "Smoke Test Module",
                    "extract_journal": "true",
                    "extract_actors": "false",
                    "extract_battle_maps": "false",
                    "generate_scene_artwork": "false"
                },
                timeout=300.0,
            )

    assert response.status_code == 200, f"Request failed: {response.text}"
    result = response.json()

    assert result["success"] is True, f"Processing failed: {result.get('error')}"
    assert result["created"]["journal"] is not None
    assert result["created"]["journal"]["uuid"].startswith("JournalEntry.")
    assert result["created"]["journal"]["page_count"] > 0
```

**Step 2: Run smoke test**

Run: `uv run pytest tests/api/test_modules_smoke.py -v`
Expected: PASS

**Step 3: Commit**

```bash
git add tests/api/test_modules_smoke.py
git commit -m "test: add smoke test for module processing"
```

---

## Task 10: Final Verification and Cleanup

**Step 1: Run all unit tests**

Run: `cd ui/backend && uv run pytest tests/routers/test_modules.py -v -k "not integration"`
Expected: All PASS

**Step 2: Build Foundry module**

Run: `cd foundry-module/tablewrite-assistant && npm run build`
Expected: No errors

**Step 3: Copy module to Foundry**

Run: `cp -r foundry-module/tablewrite-assistant/* /path/to/foundry/Data/modules/tablewrite-assistant/`

**Step 4: Reload Foundry and test**

1. Refresh Foundry browser
2. Verify Module tab appears
3. Upload a test PDF
4. Verify complete flow works

**Step 5: Final commit**

```bash
git add -A
git commit -m "feat: complete Module Processing Tab implementation"
```

---

## Summary

| Task | Description | Est. Time |
|------|-------------|-----------|
| 1 | Backend router skeleton + tests | 15 min |
| 2 | Pipeline orchestration implementation | 30 min |
| 3 | Folder creation for documents | 15 min |
| 4 | ModuleUpload TypeScript component | 45 min |
| 5 | TablewriteTab integration | 15 min |
| 6 | CSS styles | 20 min |
| 7 | Playwright UI verification | 20 min |
| 8 | Integration testing | 30 min |
| 9 | Smoke test | 15 min |
| 10 | Final verification | 15 min |

**Total: ~4 hours**

## Dependencies

- `scripts/full_pipeline.py` - Existing pipeline orchestration
- `src/pdf_processing/split_pdf.py` - PDF splitting
- `src/pdf_processing/pdf_to_xml.py` - XML conversion
- `src/actors/process_actors.py` - Actor extraction
- `src/pdf_processing/image_asset_processing/extract_map_assets.py` - Map extraction
- `scripts/generate_scene_art.py` - Artwork generation
- `src/foundry/upload_journal_to_foundry.py` - Journal upload
- `ui/backend/app/websocket/push.py` - Folder creation via WebSocket
