# Battle Map Upload UI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a UI to the Foundry module's Tablewrite tab that allows users to upload a battle map image and create a FoundryVTT scene with automatically detected walls.

**Architecture:** The Foundry module UI sends the image to a new backend endpoint (`POST /api/scenes/create-from-map`) which runs the existing `create_scene_from_map_sync()` pipeline (wall detection, grid detection, upload, scene creation) and returns the scene UUID. The UI shows simulated progress during the ~60 second operation.

**Tech Stack:** FastAPI (Python backend), TypeScript (Foundry module), Playwright (verification)

---

## Task 1: Backend Endpoint - Failing Test

**Files:**
- Create: `ui/backend/tests/routers/test_scenes_upload.py`

**Step 1: Write the failing test**

```python
"""Tests for POST /api/scenes/create-from-map endpoint."""

import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app

client = TestClient(app)

# Test fixture path
TEST_MAP = Path(__file__).parent.parent.parent.parent / "tests/scenes/fixtures/gridded_map.webp"


def test_create_scene_from_map_success():
    """Test successful scene creation from uploaded map."""
    assert TEST_MAP.exists(), f"Test fixture not found: {TEST_MAP}"

    # Mock the scene creation to avoid real API calls
    mock_result = MagicMock()
    mock_result.uuid = "Scene.test123"
    mock_result.name = "Test Map"
    mock_result.grid_size = 100
    mock_result.wall_count = 50
    mock_result.image_dimensions = {"width": 1000, "height": 800}
    mock_result.foundry_image_path = "worlds/test/uploaded-maps/test.webp"

    with patch("app.routers.scenes.create_scene_from_map_sync", return_value=mock_result):
        with open(TEST_MAP, "rb") as f:
            response = client.post(
                "/api/scenes/create-from-map",
                files={"file": ("test_map.webp", f, "image/webp")},
                data={"name": "Test Map", "skip_walls": "false"},
            )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["uuid"] == "Scene.test123"
    assert data["name"] == "Test Map"
    assert data["wall_count"] == 50


def test_create_scene_from_map_no_file():
    """Test error when no file uploaded."""
    response = client.post("/api/scenes/create-from-map", data={})
    assert response.status_code == 422  # Validation error


def test_create_scene_from_map_skip_walls():
    """Test scene creation with wall detection skipped."""
    assert TEST_MAP.exists()

    mock_result = MagicMock()
    mock_result.uuid = "Scene.nowalls"
    mock_result.name = "No Walls Map"
    mock_result.grid_size = 100
    mock_result.wall_count = 0
    mock_result.image_dimensions = {"width": 1000, "height": 800}
    mock_result.foundry_image_path = "worlds/test/uploaded-maps/nowalls.webp"

    with patch("app.routers.scenes.create_scene_from_map_sync", return_value=mock_result) as mock_fn:
        with open(TEST_MAP, "rb") as f:
            response = client.post(
                "/api/scenes/create-from-map",
                files={"file": ("test.webp", f, "image/webp")},
                data={"skip_walls": "true"},
            )

    assert response.status_code == 200
    # Verify skip_walls was passed to the function
    call_kwargs = mock_fn.call_args.kwargs
    assert call_kwargs.get("skip_walls") is True
```

**Step 2: Run test to verify it fails**

Run: `cd ui/backend && uv run pytest tests/routers/test_scenes_upload.py -v`

Expected: FAIL with `404 Not Found` (endpoint doesn't exist yet)

**Step 3: Commit test file**

```bash
git add ui/backend/tests/routers/test_scenes_upload.py
git commit -m "test: add failing tests for create-scene-from-map endpoint"
```

---

## Task 2: Backend Endpoint - Implementation

**Files:**
- Modify: `ui/backend/app/routers/scenes.py`

**Step 1: Add the endpoint implementation**

Add these imports at the top of `ui/backend/app/routers/scenes.py`:

```python
import asyncio
import shutil
import tempfile
from pathlib import Path
from fastapi import File, Form, UploadFile
from typing import Optional

# Add to existing imports section
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "src"))
from scenes.orchestrate import create_scene_from_map_sync
```

Add this endpoint after the existing endpoints:

```python
@router.post("/api/scenes/create-from-map")
async def create_scene_from_map_endpoint(
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    grid_size: Optional[int] = Form(None),
    skip_walls: bool = Form(False),
):
    """
    Create a FoundryVTT scene from an uploaded battle map image.

    Runs full pipeline: wall detection -> grid detection -> upload -> scene create.
    Takes 40-75 seconds depending on image size.
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
            lambda: create_scene_from_map_sync(
                image_path=temp_file,
                scene_name=name,
                skip_walls=skip_walls,
                grid_size_override=grid_size,
            )
        )

        return {
            "success": True,
            "uuid": result.uuid,
            "name": result.name,
            "grid_size": result.grid_size,
            "wall_count": result.wall_count,
            "image_dimensions": result.image_dimensions,
            "foundry_image_path": result.foundry_image_path,
        }
    finally:
        # Cleanup temp file
        shutil.rmtree(temp_dir, ignore_errors=True)
```

**Step 2: Run tests to verify they pass**

Run: `cd ui/backend && uv run pytest tests/routers/test_scenes_upload.py -v`

Expected: All 3 tests PASS

**Step 3: Commit**

```bash
git add ui/backend/app/routers/scenes.py
git commit -m "feat: add POST /api/scenes/create-from-map endpoint"
```

---

## Task 3: Foundry Module - BattleMapUpload Component Test

**Files:**
- Create: `foundry-module/tablewrite-assistant/tests/ui/BattleMapUpload.test.ts`

**Step 1: Write the failing test**

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock DOM environment
const createMockContainer = () => {
  const container = document.createElement('div');
  return container;
};

// We'll import the class after it exists
describe('BattleMapUpload', () => {
  it('renders upload form with all required elements', async () => {
    // Dynamic import to handle module not existing yet
    const { BattleMapUpload } = await import('../../src/ui/BattleMapUpload');

    const container = createMockContainer();
    const upload = new BattleMapUpload(container, 'http://localhost:8000');
    upload.render();

    expect(container.querySelector('#battlemap-file')).toBeTruthy();
    expect(container.querySelector('#scene-name')).toBeTruthy();
    expect(container.querySelector('#grid-size-mode')).toBeTruthy();
    expect(container.querySelector('#skip-walls')).toBeTruthy();
    expect(container.querySelector('#create-scene-btn')).toBeTruthy();
  });

  it('shows error notification when no file selected', async () => {
    const { BattleMapUpload } = await import('../../src/ui/BattleMapUpload');

    // Mock Foundry's ui.notifications
    (globalThis as any).ui = {
      notifications: {
        error: vi.fn(),
        info: vi.fn(),
      }
    };

    const container = createMockContainer();
    const upload = new BattleMapUpload(container, 'http://localhost:8000');
    upload.render();

    // Click create without selecting file
    const btn = container.querySelector('#create-scene-btn') as HTMLButtonElement;
    btn.click();

    expect((globalThis as any).ui.notifications.error).toHaveBeenCalledWith(
      'Please select a battle map image'
    );
  });

  it('shows manual grid input when mode changed to manual', async () => {
    const { BattleMapUpload } = await import('../../src/ui/BattleMapUpload');

    const container = createMockContainer();
    const upload = new BattleMapUpload(container, 'http://localhost:8000');
    upload.render();

    const gridModeSelect = container.querySelector('#grid-size-mode') as HTMLSelectElement;
    const gridSizeInput = container.querySelector('#grid-size') as HTMLInputElement;

    // Initially hidden
    expect(gridSizeInput.style.display).toBe('none');

    // Change to manual
    gridModeSelect.value = 'manual';
    gridModeSelect.dispatchEvent(new Event('change'));

    // Should now be visible
    expect(gridSizeInput.style.display).toBe('block');
  });
});
```

**Step 2: Run test to verify it fails**

Run: `cd foundry-module/tablewrite-assistant && npm test -- tests/ui/BattleMapUpload.test.ts`

Expected: FAIL with "Cannot find module '../../src/ui/BattleMapUpload'"

**Step 3: Commit test file**

```bash
git add foundry-module/tablewrite-assistant/tests/ui/BattleMapUpload.test.ts
git commit -m "test: add failing tests for BattleMapUpload component"
```

---

## Task 4: Foundry Module - BattleMapUpload Component Implementation

**Files:**
- Create: `foundry-module/tablewrite-assistant/src/ui/BattleMapUpload.ts`

**Step 1: Create the component**

```typescript
/**
 * Battle Map Upload component for creating FoundryVTT scenes from images.
 */
export class BattleMapUpload {
  private container: HTMLElement;
  private backendUrl: string;
  private progressInterval: ReturnType<typeof setInterval> | null = null;

  constructor(container: HTMLElement, backendUrl: string) {
    this.container = container;
    this.backendUrl = backendUrl;
  }

  render(): void {
    this.container.innerHTML = `
      <div class="battlemap-upload">
        <h3>Create Scene from Battle Map</h3>

        <div class="upload-form">
          <div class="form-group">
            <label>Battle Map Image</label>
            <input type="file" id="battlemap-file" accept="image/*" />
          </div>

          <div class="form-group">
            <label>Scene Name (optional)</label>
            <input type="text" id="scene-name" placeholder="Auto-derived from filename" />
          </div>

          <div class="form-group">
            <label>Grid Size</label>
            <select id="grid-size-mode">
              <option value="auto">Auto-detect</option>
              <option value="manual">Manual</option>
            </select>
            <input type="number" id="grid-size" placeholder="100" style="display: none" />
          </div>

          <div class="form-group">
            <label>
              <input type="checkbox" id="skip-walls" />
              Skip wall detection
            </label>
          </div>

          <button id="create-scene-btn" class="primary">Create Scene</button>
        </div>

        <div class="progress-container" style="display: none">
          <div class="progress-bar">
            <div class="progress-fill"></div>
          </div>
          <div class="progress-status">Preparing...</div>
        </div>

        <div class="result-container" style="display: none">
          <div class="success-message"></div>
          <button id="open-scene-btn">Open Scene</button>
          <button id="reset-btn">Create Another</button>
        </div>
      </div>
    `;

    this.attachEventListeners();
  }

  private attachEventListeners(): void {
    const gridModeSelect = this.container.querySelector('#grid-size-mode');
    const createBtn = this.container.querySelector('#create-scene-btn');
    const resetBtn = this.container.querySelector('#reset-btn');

    gridModeSelect?.addEventListener('change', (e) => {
      const target = e.target as HTMLSelectElement;
      const gridSizeInput = this.container.querySelector('#grid-size') as HTMLInputElement;
      gridSizeInput.style.display = target.value === 'manual' ? 'block' : 'none';
    });

    createBtn?.addEventListener('click', () => this.handleCreateScene());
    resetBtn?.addEventListener('click', () => this.resetForm());
  }

  private async handleCreateScene(): Promise<void> {
    const fileInput = this.container.querySelector('#battlemap-file') as HTMLInputElement;
    const file = fileInput.files?.[0];

    if (!file) {
      (globalThis as any).ui?.notifications?.error('Please select a battle map image');
      return;
    }

    this.showProgress('Uploading image...');

    try {
      const formData = new FormData();
      formData.append('file', file);

      const nameInput = this.container.querySelector('#scene-name') as HTMLInputElement;
      if (nameInput.value) {
        formData.append('name', nameInput.value);
      }

      const skipWalls = (this.container.querySelector('#skip-walls') as HTMLInputElement).checked;
      formData.append('skip_walls', skipWalls.toString());

      const gridMode = (this.container.querySelector('#grid-size-mode') as HTMLSelectElement).value;
      if (gridMode === 'manual') {
        const gridSize = (this.container.querySelector('#grid-size') as HTMLInputElement).value;
        if (gridSize) {
          formData.append('grid_size', gridSize);
        }
      }

      this.simulateProgress();

      const response = await fetch(`${this.backendUrl}/api/scenes/create-from-map`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${await response.text()}`);
      }

      const result = await response.json();

      if (result.success) {
        this.showSuccess(result);
      } else {
        throw new Error(result.error || 'Unknown error');
      }
    } catch (error: any) {
      (globalThis as any).ui?.notifications?.error(`Failed to create scene: ${error.message}`);
      this.hideProgress();
    }
  }

  private simulateProgress(): void {
    const stages = [
      { pct: 10, msg: 'Saving image...' },
      { pct: 20, msg: 'Detecting walls (this may take a minute)...' },
      { pct: 60, msg: 'Processing wall geometry...' },
      { pct: 75, msg: 'Detecting grid...' },
      { pct: 85, msg: 'Uploading to Foundry...' },
      { pct: 95, msg: 'Creating scene...' },
    ];

    let i = 0;
    this.progressInterval = setInterval(() => {
      if (i < stages.length) {
        this.updateProgress(stages[i].pct, stages[i].msg);
        i++;
      }
    }, 8000);
  }

  private showProgress(message: string): void {
    const progressContainer = this.container.querySelector('.progress-container') as HTMLElement;
    const formContainer = this.container.querySelector('.upload-form') as HTMLElement;

    formContainer.style.display = 'none';
    progressContainer.style.display = 'block';

    this.updateProgress(5, message);
  }

  private updateProgress(percent: number, message: string): void {
    const progressFill = this.container.querySelector('.progress-fill') as HTMLElement;
    const progressStatus = this.container.querySelector('.progress-status') as HTMLElement;

    progressFill.style.width = `${percent}%`;
    progressStatus.textContent = message;
  }

  private hideProgress(): void {
    if (this.progressInterval) {
      clearInterval(this.progressInterval);
      this.progressInterval = null;
    }

    const progressContainer = this.container.querySelector('.progress-container') as HTMLElement;
    const formContainer = this.container.querySelector('.upload-form') as HTMLElement;

    progressContainer.style.display = 'none';
    formContainer.style.display = 'block';
  }

  private showSuccess(result: any): void {
    if (this.progressInterval) {
      clearInterval(this.progressInterval);
      this.progressInterval = null;
    }

    const progressContainer = this.container.querySelector('.progress-container') as HTMLElement;
    const resultContainer = this.container.querySelector('.result-container') as HTMLElement;
    const successMessage = this.container.querySelector('.success-message') as HTMLElement;

    progressContainer.style.display = 'none';
    resultContainer.style.display = 'block';

    successMessage.innerHTML = `
      <p><strong>Scene created!</strong></p>
      <p>Name: ${result.name}</p>
      <p>Walls: ${result.wall_count}</p>
      <p>Grid: ${result.grid_size || 'None detected'}px</p>
    `;

    const openBtn = this.container.querySelector('#open-scene-btn');
    openBtn?.addEventListener('click', async () => {
      const scene = await (globalThis as any).fromUuid?.(result.uuid);
      if (scene) {
        scene.view();
      }
    });

    (globalThis as any).ui?.notifications?.info(
      `Created scene: ${result.name} with ${result.wall_count} walls`
    );
  }

  private resetForm(): void {
    const resultContainer = this.container.querySelector('.result-container') as HTMLElement;
    const formContainer = this.container.querySelector('.upload-form') as HTMLElement;

    resultContainer.style.display = 'none';
    formContainer.style.display = 'block';

    // Clear form
    (this.container.querySelector('#battlemap-file') as HTMLInputElement).value = '';
    (this.container.querySelector('#scene-name') as HTMLInputElement).value = '';
    (this.container.querySelector('#skip-walls') as HTMLInputElement).checked = false;
    (this.container.querySelector('#grid-size-mode') as HTMLSelectElement).value = 'auto';
    (this.container.querySelector('#grid-size') as HTMLInputElement).style.display = 'none';
  }
}
```

**Step 2: Run tests to verify they pass**

Run: `cd foundry-module/tablewrite-assistant && npm test -- tests/ui/BattleMapUpload.test.ts`

Expected: All 3 tests PASS

**Step 3: Commit**

```bash
git add foundry-module/tablewrite-assistant/src/ui/BattleMapUpload.ts
git commit -m "feat: add BattleMapUpload component"
```

---

## Task 5: Integrate BattleMapUpload into TablewriteTab

**Files:**
- Modify: `foundry-module/tablewrite-assistant/src/ui/TablewriteTab.ts`

**Step 1: Read current TablewriteTab to understand structure**

Run: `cat foundry-module/tablewrite-assistant/src/ui/TablewriteTab.ts`

**Step 2: Add import and integration**

Add import at top:
```typescript
import { BattleMapUpload } from './BattleMapUpload';
```

Add property to class:
```typescript
private battleMapUpload: BattleMapUpload | null = null;
```

Modify the `render()` method to wrap existing chat UI with tabs:

```typescript
render(): void {
  // Wrap existing content in tabs structure
  this.container.innerHTML = `
    <div class="tablewrite-container">
      <div class="tablewrite-tabs">
        <button class="tab-btn active" data-tab="chat">Chat</button>
        <button class="tab-btn" data-tab="battlemap">Battle Map</button>
      </div>

      <div class="tab-content" id="chat-tab">
        <div class="tablewrite-chat">
          <div class="tablewrite-messages"></div>
          <form class="tablewrite-input-form">
            <textarea class="tablewrite-input" placeholder="Ask me anything..."></textarea>
          </form>
        </div>
      </div>

      <div class="tab-content" id="battlemap-tab" style="display: none">
        <!-- BattleMapUpload renders here -->
      </div>
    </div>
  `;

  // Initialize BattleMapUpload
  const battlemapContainer = this.container.querySelector('#battlemap-tab') as HTMLElement;
  this.battleMapUpload = new BattleMapUpload(battlemapContainer, this.backendUrl);
  this.battleMapUpload.render();

  // Attach tab switching listeners
  this.attachTabListeners();

  // Existing chat setup...
  this.attachListeners();
}

private attachTabListeners(): void {
  const tabBtns = this.container.querySelectorAll('.tab-btn');
  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const tabId = (btn as HTMLElement).dataset.tab;

      // Update active tab button
      tabBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      // Show/hide tab content
      this.container.querySelectorAll('.tab-content').forEach(c => {
        (c as HTMLElement).style.display = c.id === `${tabId}-tab` ? 'block' : 'none';
      });
    });
  });
}
```

**Step 3: Build and verify no TypeScript errors**

Run: `cd foundry-module/tablewrite-assistant && npm run build`

Expected: Build succeeds with no errors

**Step 4: Commit**

```bash
git add foundry-module/tablewrite-assistant/src/ui/TablewriteTab.ts
git commit -m "feat: integrate BattleMapUpload into TablewriteTab with tabs"
```

---

## Task 6: Add CSS Styling

**Files:**
- Modify: `foundry-module/tablewrite-assistant/styles/module.css`

**Step 1: Add tab and upload form styles**

Append to end of `module.css`:

```css
/* Tab styling */
.tablewrite-tabs {
  display: flex;
  border-bottom: 1px solid #444;
  margin-bottom: 10px;
}

.tab-btn {
  padding: 8px 16px;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  color: #aaa;
  font-size: 13px;
}

.tab-btn.active {
  color: #fff;
  border-bottom-color: #7a4;
}

.tab-btn:hover {
  color: #fff;
}

/* Battle Map Upload */
.battlemap-upload {
  padding: 10px;
}

.battlemap-upload h3 {
  margin: 0 0 15px 0;
  font-size: 14px;
}

.battlemap-upload .form-group {
  margin-bottom: 12px;
}

.battlemap-upload label {
  display: block;
  margin-bottom: 4px;
  font-weight: 500;
  font-size: 12px;
}

.battlemap-upload input[type="text"],
.battlemap-upload input[type="number"],
.battlemap-upload select {
  width: 100%;
  padding: 6px 8px;
  border: 1px solid #555;
  border-radius: 4px;
  background: #333;
  color: #fff;
  font-size: 12px;
}

.battlemap-upload input[type="file"] {
  padding: 8px 0;
  font-size: 12px;
}

.battlemap-upload input[type="checkbox"] {
  margin-right: 6px;
}

.battlemap-upload button.primary {
  width: 100%;
  padding: 10px;
  background: #7a4;
  border: none;
  border-radius: 4px;
  color: #fff;
  font-weight: bold;
  cursor: pointer;
  margin-top: 10px;
}

.battlemap-upload button.primary:hover {
  background: #8b5;
}

/* Progress bar */
.progress-container {
  margin-top: 20px;
  padding: 10px;
}

.progress-bar {
  height: 20px;
  background: #333;
  border-radius: 10px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #7a4, #5a2);
  width: 0%;
  transition: width 0.3s ease;
}

.progress-status {
  margin-top: 8px;
  text-align: center;
  color: #aaa;
  font-size: 12px;
}

/* Result container */
.result-container {
  text-align: center;
  padding: 20px 10px;
}

.success-message {
  margin-bottom: 15px;
  font-size: 13px;
}

.success-message p {
  margin: 4px 0;
}

#open-scene-btn,
#reset-btn {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  color: #fff;
  cursor: pointer;
  margin: 4px;
  font-size: 12px;
}

#open-scene-btn {
  background: #47a;
}

#open-scene-btn:hover {
  background: #58b;
}

#reset-btn {
  background: #555;
}

#reset-btn:hover {
  background: #666;
}
```

**Step 2: Rebuild module**

Run: `cd foundry-module/tablewrite-assistant && npm run build`

Expected: Build succeeds

**Step 3: Commit**

```bash
git add foundry-module/tablewrite-assistant/styles/module.css
git commit -m "style: add CSS for tabs and battle map upload form"
```

---

## Task 7: Create Playwright Verification Script

**Files:**
- Create: `foundry-module/tablewrite-assistant/scripts/feedback/verify_battlemap_upload.py`

**Step 1: Create the verification script**

```python
#!/usr/bin/env python3
"""
Verify battle map upload UI is working correctly.

Usage:
    python verify_battlemap_upload.py [--headed] [--map PATH]

Requires:
- Backend running at localhost:8000
- FoundryVTT running at localhost:30000
- Tablewrite module enabled

Screenshots saved to: /tmp/battlemap_upload/
"""

import argparse
import time
from pathlib import Path
from foundry_helper import FoundrySession

DEFAULT_MAP = Path(__file__).parent.parent.parent.parent.parent / "tests/scenes/fixtures/gridded_map.webp"
SCREENSHOT_DIR = Path("/tmp/battlemap_upload")


def verify_battlemap_upload(map_path: Path, headless: bool = True):
    """Run through the battle map upload flow and capture screenshots."""
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    results = {"success": False, "screenshots": [], "error": None}

    print(f"\n{'='*60}")
    print("BATTLE MAP UPLOAD VERIFICATION")
    print(f"{'='*60}")
    print(f"Map: {map_path}")
    print(f"Screenshots: {SCREENSHOT_DIR}")
    print(f"{'='*60}\n")

    with FoundrySession(headless=headless) as session:
        page = session.page

        try:
            # Step 1: Go to Tablewrite tab
            print("[1/7] Opening Tablewrite tab...")
            session.goto_tablewrite()
            time.sleep(0.5)
            shot = SCREENSHOT_DIR / "01_tablewrite_tab.png"
            page.locator("#sidebar").screenshot(path=str(shot))
            results["screenshots"].append(str(shot))
            print(f"      Screenshot: {shot}")

            # Step 2: Click Battle Map sub-tab
            print("[2/7] Switching to Battle Map tab...")
            battlemap_btn = page.locator('.tab-btn:has-text("Battle Map")')
            if battlemap_btn.count() == 0:
                raise Exception("Battle Map tab not found - is the UI implemented?")
            battlemap_btn.click()
            time.sleep(0.5)
            shot = SCREENSHOT_DIR / "02_battlemap_form.png"
            page.locator("#sidebar").screenshot(path=str(shot))
            results["screenshots"].append(str(shot))
            print(f"      Screenshot: {shot}")

            # Step 3: Upload map file
            print(f"[3/7] Uploading map: {map_path.name}...")
            file_input = page.locator('#battlemap-file')
            file_input.set_input_files(str(map_path))
            time.sleep(0.3)
            page.locator('#scene-name').fill("Verification Test Scene")
            shot = SCREENSHOT_DIR / "03_file_selected.png"
            page.locator("#sidebar").screenshot(path=str(shot))
            results["screenshots"].append(str(shot))
            print(f"      Screenshot: {shot}")

            # Step 4: Click Create Scene
            print("[4/7] Creating scene (this may take 60-90 seconds)...")
            page.locator('#create-scene-btn').click()
            time.sleep(1)
            shot = SCREENSHOT_DIR / "04_progress.png"
            page.locator("#sidebar").screenshot(path=str(shot))
            results["screenshots"].append(str(shot))
            print(f"      Screenshot: {shot}")

            # Step 5: Wait for completion
            print("      Waiting for wall detection...")
            start = time.time()
            result_container = page.locator('.result-container')
            while time.time() - start < 120:
                if result_container.count() > 0 and result_container.is_visible():
                    break
                time.sleep(2)
                elapsed = int(time.time() - start)
                print(f"      [{elapsed}s] Still processing...")

            if not result_container.is_visible():
                raise Exception("Timeout waiting for scene creation (120s)")

            # Step 6: Capture success
            print("[5/7] Scene created! Capturing result...")
            shot = SCREENSHOT_DIR / "05_scene_created.png"
            page.locator("#sidebar").screenshot(path=str(shot))
            results["screenshots"].append(str(shot))
            print(f"      Screenshot: {shot}")

            success_msg = page.locator('.success-message').text_content()
            print(f"      Result: {success_msg}")
            results["result_text"] = success_msg

            # Step 7: Open scene and capture with walls
            print("[6/7] Opening scene to view walls...")
            page.locator('#open-scene-btn').click()
            time.sleep(3)
            shot = SCREENSHOT_DIR / "06_scene_with_walls.png"
            page.screenshot(path=str(shot), full_page=True)
            results["screenshots"].append(str(shot))
            print(f"      Screenshot: {shot}")

            # Verify in scenes list
            print("[7/7] Verifying scene in scenes list...")
            page.locator('a[data-tab="scenes"]').click()
            time.sleep(0.5)
            shot = SCREENSHOT_DIR / "07_scenes_list.png"
            page.locator("#sidebar").screenshot(path=str(shot))
            results["screenshots"].append(str(shot))
            print(f"      Screenshot: {shot}")

            results["success"] = True
            print(f"\n{'='*60}")
            print("VERIFICATION PASSED")
            print(f"{'='*60}")
            print(f"Screenshots saved to: {SCREENSHOT_DIR}")
            print(f"Final scene: {SCREENSHOT_DIR / '06_scene_with_walls.png'}")

        except Exception as e:
            results["error"] = str(e)
            print(f"\nVERIFICATION FAILED: {e}")
            shot = SCREENSHOT_DIR / "error_state.png"
            page.screenshot(path=str(shot), full_page=True)
            results["screenshots"].append(str(shot))
            print(f"Error screenshot: {shot}")

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify battle map upload UI")
    parser.add_argument("--headed", action="store_true", help="Run with visible browser")
    parser.add_argument("--map", type=Path, default=DEFAULT_MAP, help="Path to test map")
    args = parser.parse_args()

    if not args.map.exists():
        print(f"Error: Map not found: {args.map}")
        exit(1)

    results = verify_battlemap_upload(args.map, headless=not args.headed)
    exit(0 if results["success"] else 1)
```

**Step 2: Test script runs (will fail until UI is deployed)**

Run: `python foundry-module/tablewrite-assistant/scripts/feedback/verify_battlemap_upload.py --headed`

Expected: Script runs, opens browser, fails at "Battle Map tab not found" (UI not deployed yet)

**Step 3: Commit**

```bash
git add foundry-module/tablewrite-assistant/scripts/feedback/verify_battlemap_upload.py
git commit -m "feat: add Playwright verification script for battle map upload"
```

---

## Task 8: Integration Test

**Files:**
- Create: `tests/scenes/test_battlemap_upload_integration.py`

**Step 1: Write integration test**

```python
"""Integration test for battle map upload endpoint."""

import pytest
from pathlib import Path
import httpx

BACKEND_URL = "http://localhost:8000"
TEST_MAP = Path(__file__).parent / "fixtures" / "gridded_map.webp"


@pytest.mark.integration
@pytest.mark.slow
def test_battlemap_upload_creates_scene_with_walls(ensure_foundry_connected):
    """Test full pipeline: upload map -> detect walls -> create scene."""
    assert TEST_MAP.exists(), f"Test map not found: {TEST_MAP}"

    with open(TEST_MAP, "rb") as f:
        response = httpx.post(
            f"{BACKEND_URL}/api/scenes/create-from-map",
            files={"file": ("test_map.webp", f, "image/webp")},
            data={"name": "Integration Test Scene"},
            timeout=120.0,  # Wall detection takes time
        )

    assert response.status_code == 200, f"Failed: {response.text}"
    data = response.json()

    assert data["success"] is True
    assert data["uuid"].startswith("Scene.")
    assert data["name"] == "Integration Test Scene"
    assert data["wall_count"] > 0, "Expected walls to be detected"
    assert data["image_dimensions"]["width"] > 0
    assert data["image_dimensions"]["height"] > 0

    # Cleanup: delete the test scene
    scene_uuid = data["uuid"]
    delete_response = httpx.delete(
        f"{BACKEND_URL}/api/foundry/scene/{scene_uuid}",
        timeout=10.0,
    )
    assert delete_response.status_code == 200


@pytest.mark.integration
def test_battlemap_upload_skip_walls(ensure_foundry_connected):
    """Test upload with wall detection skipped (faster)."""
    assert TEST_MAP.exists()

    with open(TEST_MAP, "rb") as f:
        response = httpx.post(
            f"{BACKEND_URL}/api/scenes/create-from-map",
            files={"file": ("test.webp", f, "image/webp")},
            data={"name": "No Walls Test", "skip_walls": "true"},
            timeout=30.0,
        )

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert data["wall_count"] == 0, "Expected no walls when skipped"

    # Cleanup
    httpx.delete(f"{BACKEND_URL}/api/foundry/scene/{data['uuid']}", timeout=10.0)
```

**Step 2: Run test (requires backend + Foundry)**

Run: `uv run pytest tests/scenes/test_battlemap_upload_integration.py -v -m integration`

Expected: Tests pass (or skip if Foundry not connected)

**Step 3: Commit**

```bash
git add tests/scenes/test_battlemap_upload_integration.py
git commit -m "test: add integration tests for battle map upload"
```

---

## Task 9: Final Verification

**Step 1: Rebuild Foundry module**

Run: `cd foundry-module/tablewrite-assistant && npm run build`

**Step 2: Copy to Foundry modules folder**

Run: `cp -r foundry-module/tablewrite-assistant ~/.local/share/FoundryVTT/Data/modules/`

(Adjust path for your Foundry installation)

**Step 3: Reload Foundry world**

Refresh browser at localhost:30000

**Step 4: Run Playwright verification**

Run: `python foundry-module/tablewrite-assistant/scripts/feedback/verify_battlemap_upload.py --headed`

Expected: All 7 steps pass, screenshots saved to `/tmp/battlemap_upload/`

**Step 5: Review final screenshot**

Open: `/tmp/battlemap_upload/06_scene_with_walls.png`

Verify: Scene is displayed with red wall outlines visible

**Step 6: Final commit**

```bash
git add -A
git commit -m "feat: complete battle map upload UI implementation"
```

---

## Summary

| Task | Description | Time |
|------|-------------|------|
| 1 | Backend endpoint test | 10 min |
| 2 | Backend endpoint implementation | 15 min |
| 3 | BattleMapUpload component test | 10 min |
| 4 | BattleMapUpload component | 30 min |
| 5 | TablewriteTab integration | 20 min |
| 6 | CSS styling | 15 min |
| 7 | Playwright verification script | 20 min |
| 8 | Integration test | 15 min |
| 9 | Final verification | 15 min |
| **Total** | | **~2.5 hours** |
