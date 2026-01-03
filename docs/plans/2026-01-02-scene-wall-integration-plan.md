# Scene & Wall Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a complete pipeline that takes a battle map image, detects walls using AI, uploads the image to FoundryVTT, and creates a scene with walls embedded.

**Architecture:** File upload via base64 WebSocket message → Scene creation with embedded walls → Round-trip integration tests. Modular functions compose into single `create_scene_from_map()` orchestrator.

**Tech Stack:** Python (FastAPI, Pydantic, asyncio), TypeScript (Foundry module), Gemini Vision API, FoundryVTT v10+ API

---

## Implementation Order

1. **Task 1-4**: File upload infrastructure (Foundry module → backend → Python client)
2. **Task 5-8**: Scene creation with walls (complete SceneManager)
3. **Task 9-11**: Grid detection modules (AI + fallback)
4. **Task 12-15**: Orchestration pipeline (main function + models)
5. **Task 16-18**: Integration tests (round-trip verification)

---

### Task 1: Add File Upload Handler to Foundry Module

**Files:**
- Modify: `foundry-module/tablewrite-assistant/src/handlers/files.ts`
- Modify: `foundry-module/tablewrite-assistant/src/handlers/index.ts`

**Step 1: Write the file upload handler function**

Add to `files.ts`:

```typescript
/**
 * Upload a file to FoundryVTT world folder.
 *
 * Uses FilePicker.upload() for proper Foundry integration.
 */
export async function handleFileUpload(data: {
  filename: string;
  content: string;      // base64 encoded
  destination: string;  // relative path like "uploaded-maps"
}): Promise<FileUploadResult> {
  try {
    const { filename, content, destination } = data;

    // Decode base64 to binary
    const binaryString = atob(content);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }
    const blob = new Blob([bytes]);
    const file = new File([blob], filename);

    // Construct target path: worlds/<current-world>/<destination>/
    const worldPath = `worlds/${game.world.id}/${destination}`;

    // Upload using FilePicker (creates folder if needed)
    const response = await FilePicker.upload(
      "data",
      worldPath,
      file,
      {}
    );

    if (!response.path) {
      throw new Error("Upload failed: no path returned");
    }

    console.log('[Tablewrite] Uploaded file:', response.path);

    return {
      success: true,
      path: response.path
    };
  } catch (error) {
    console.error('[Tablewrite] Failed to upload file:', error);
    return {
      success: false,
      error: String(error)
    };
  }
}
```

**Step 2: Add FileUploadResult interface to index.ts**

```typescript
export interface FileUploadResult {
  success: boolean;
  path?: string;
  error?: string;
}
```

**Step 3: Export the handler in index.ts**

Update exports:
```typescript
export { handleListFiles, handleFileUpload } from './files.js';
```

Update imports:
```typescript
import { handleListFiles, handleFileUpload } from './files.js';
```

**Step 4: Add message type to MessageType union**

```typescript
export type MessageType = 'actor' | 'journal' | 'delete_journal' | 'scene' | 'get_actor' | 'delete_actor' | 'list_actors' | 'give_items' | 'search_items' | 'get_item' | 'list_compendium_items' | 'list_files' | 'upload_file' | 'connected' | 'pong';
```

**Step 5: Add message routing in handleMessage()**

```typescript
case 'upload_file':
  if (message.data) {
    const result = await handleFileUpload(message.data as {
      filename: string;
      content: string;
      destination: string;
    });
    return {
      responseType: result.success ? 'file_uploaded' : 'file_error',
      request_id: message.request_id,
      data: result,
      error: result.error
    };
  }
  return {
    responseType: 'file_error',
    request_id: message.request_id,
    error: 'Missing data for upload_file'
  };
```

**Step 6: Build the module**

Run: `cd foundry-module/tablewrite-assistant && npm run build`
Expected: Build completes without errors

**Step 7: Commit**

```bash
git add foundry-module/tablewrite-assistant/src/handlers/files.ts foundry-module/tablewrite-assistant/src/handlers/index.ts
git commit -m "$(cat <<'EOF'
feat(foundry-module): add file upload handler

Add handleFileUpload() to upload base64-encoded files to Foundry
world folder via FilePicker.upload(). Supports destination subfolders.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Add File Upload WebSocket Push Function

**Files:**
- Modify: `ui/backend/app/websocket/push.py`

**Step 1: Write the failing test**

Create `tests/backend/test_push_upload.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_upload_file_success():
    """upload_file returns path on success."""
    from app.websocket.push import upload_file

    mock_response = {
        "type": "file_uploaded",
        "data": {"success": True, "path": "worlds/test/uploaded-maps/castle.webp"}
    }

    with patch('app.websocket.push.foundry_manager') as mock_mgr:
        mock_mgr.broadcast_and_wait = AsyncMock(return_value=mock_response)

        result = await upload_file(
            filename="castle.webp",
            content="dGVzdA==",  # base64 "test"
            destination="uploaded-maps"
        )

        assert result.success
        assert result.path == "worlds/test/uploaded-maps/castle.webp"
```

**Step 2: Run test to verify it fails**

Run: `cd ui/backend && uv run pytest tests/backend/test_push_upload.py -v`
Expected: FAIL with "cannot import name 'upload_file'"

**Step 3: Write the upload_file function**

Add to `ui/backend/app/websocket/push.py`:

```python
@dataclass
class FileUploadResult:
    """Result of uploading a file to Foundry."""
    success: bool
    path: Optional[str] = None
    error: Optional[str] = None


async def upload_file(
    filename: str,
    content: str,
    destination: str = "uploaded-maps",
    timeout: float = 60.0
) -> FileUploadResult:
    """
    Upload a file to FoundryVTT world folder via WebSocket.

    Args:
        filename: Name of the file (e.g., "castle.webp")
        content: Base64-encoded file content
        destination: Subdirectory in world folder (default: "uploaded-maps")
        timeout: Maximum seconds to wait for response

    Returns:
        FileUploadResult with Foundry-relative path if successful
    """
    response = await foundry_manager.broadcast_and_wait(
        {
            "type": "upload_file",
            "data": {
                "filename": filename,
                "content": content,
                "destination": destination
            }
        },
        timeout=timeout
    )

    if response is None:
        return FileUploadResult(
            success=False,
            error="No Foundry client connected or timeout waiting for response"
        )

    if response.get("type") == "file_uploaded":
        data = response.get("data", {})
        return FileUploadResult(
            success=True,
            path=data.get("path")
        )
    elif response.get("type") == "file_error":
        return FileUploadResult(
            success=False,
            error=response.get("error", "Unknown upload error")
        )
    else:
        return FileUploadResult(
            success=False,
            error=f"Unexpected response type: {response.get('type')}"
        )
```

**Step 4: Run test to verify it passes**

Run: `cd ui/backend && uv run pytest tests/backend/test_push_upload.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add ui/backend/app/websocket/push.py tests/backend/test_push_upload.py
git commit -m "$(cat <<'EOF'
feat(backend): add upload_file WebSocket push function

Add FileUploadResult dataclass and upload_file() async function
to upload base64-encoded files to Foundry via WebSocket.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Add File Upload REST Endpoint

**Files:**
- Modify: `ui/backend/app/routers/files.py`

**Step 1: Write the failing test**

Add to `tests/backend/test_files_router.py`:

```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
import base64

def test_upload_file_endpoint():
    """POST /api/foundry/files/upload returns path."""
    from app.main import app

    client = TestClient(app)

    mock_result = type('MockResult', (), {
        'success': True,
        'path': 'worlds/test/uploaded-maps/castle.webp'
    })()

    with patch('app.routers.files.upload_file', new_callable=AsyncMock) as mock_upload:
        mock_upload.return_value = mock_result

        # Create minimal file
        file_content = b"fake image data"

        response = client.post(
            "/api/foundry/files/upload",
            files={"file": ("castle.webp", file_content, "image/webp")},
            data={"destination": "uploaded-maps"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["path"] == "worlds/test/uploaded-maps/castle.webp"
```

**Step 2: Run test to verify it fails**

Run: `cd ui/backend && uv run pytest tests/backend/test_files_router.py::test_upload_file_endpoint -v`
Expected: FAIL with 404 or endpoint not found

**Step 3: Write the endpoint**

Add to `ui/backend/app/routers/files.py`:

```python
import base64
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.websocket.push import upload_file

router = APIRouter(prefix="/api/foundry/files", tags=["files"])


@router.post("/upload")
async def upload_file_endpoint(
    file: UploadFile = File(...),
    destination: str = Form("uploaded-maps")
):
    """
    Upload a file to FoundryVTT world folder.

    The file is sent to the connected Foundry client via WebSocket,
    which saves it to: worlds/<current-world>/<destination>/<filename>

    Args:
        file: The file to upload
        destination: Subdirectory in world folder (default: "uploaded-maps")

    Returns:
        {"success": true, "path": "worlds/.../<filename>"}
    """
    content = await file.read()
    content_b64 = base64.b64encode(content).decode('utf-8')

    result = await upload_file(
        filename=file.filename,
        content=content_b64,
        destination=destination
    )

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    return {
        "success": True,
        "path": result.path
    }
```

**Step 4: Register router in main.py (if not already)**

Check `ui/backend/app/main.py` includes:
```python
from app.routers import files
app.include_router(files.router)
```

**Step 5: Run test to verify it passes**

Run: `cd ui/backend && uv run pytest tests/backend/test_files_router.py::test_upload_file_endpoint -v`
Expected: PASS

**Step 6: Commit**

```bash
git add ui/backend/app/routers/files.py ui/backend/app/main.py tests/backend/test_files_router.py
git commit -m "$(cat <<'EOF'
feat(backend): add POST /api/foundry/files/upload endpoint

Accept file upload via multipart form, base64 encode, and send
to Foundry module via WebSocket for storage in world folder.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Add File Upload to FoundryClient

**Files:**
- Modify: `src/foundry/client.py`
- Create: `src/foundry/files.py`

**Step 1: Write the failing test**

Create `tests/foundry/test_files.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

def test_file_manager_upload():
    """FileManager.upload_file sends file to backend."""
    from foundry.files import FileManager

    manager = FileManager(backend_url="http://localhost:8000")

    with patch('foundry.files.requests.post') as mock_post:
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"success": True, "path": "worlds/test/uploaded-maps/castle.webp"}
        )

        result = manager.upload_file(
            local_path=Path("tests/fixtures/test_image.png"),
            destination="uploaded-maps"
        )

        assert result["success"] == True
        assert result["path"] == "worlds/test/uploaded-maps/castle.webp"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/foundry/test_files.py -v`
Expected: FAIL with "No module named 'foundry.files'"

**Step 3: Create FileManager class**

Create `src/foundry/files.py`:

```python
"""FoundryVTT file operations via WebSocket backend."""

import logging
import requests
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)


class FileManager:
    """Manages file operations for FoundryVTT via WebSocket backend."""

    def __init__(self, backend_url: str):
        """
        Initialize file manager.

        Args:
            backend_url: URL of the FastAPI backend (e.g., http://localhost:8000)
        """
        self.backend_url = backend_url

    def upload_file(
        self,
        local_path: Path,
        destination: str = "uploaded-maps"
    ) -> Dict[str, Any]:
        """
        Upload a file to FoundryVTT world folder.

        Args:
            local_path: Path to local file
            destination: Subdirectory in world folder (default: "uploaded-maps")

        Returns:
            {"success": True, "path": "worlds/.../filename"} on success
            {"success": False, "error": "..."} on failure
        """
        endpoint = f"{self.backend_url}/api/foundry/files/upload"

        if not local_path.exists():
            return {"success": False, "error": f"File not found: {local_path}"}

        try:
            with open(local_path, 'rb') as f:
                files = {'file': (local_path.name, f)}
                data = {'destination': destination}

                response = requests.post(endpoint, files=files, data=data, timeout=120)

            if response.status_code != 200:
                return {"success": False, "error": f"Upload failed: {response.status_code}"}

            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Upload request failed: {e}")
            return {"success": False, "error": str(e)}
```

**Step 4: Add FileManager to FoundryClient**

Update `src/foundry/client.py`:

```python
from .files import FileManager

# In __init__:
self.files = FileManager(backend_url=self.backend_url)

# Replace the existing upload_file method with:
def upload_file(self, local_path: str, destination: str = "uploaded-maps") -> Dict[str, Any]:
    """Upload a file to FoundryVTT."""
    return self.files.upload_file(Path(local_path), destination)
```

**Step 5: Create test fixture image**

Run: `mkdir -p tests/fixtures && touch tests/fixtures/test_image.png`

Add a tiny valid PNG (1x1 pixel):
```python
# In a Python script or test setup:
from PIL import Image
img = Image.new('RGB', (1, 1), color='red')
img.save('tests/fixtures/test_image.png')
```

**Step 6: Run test to verify it passes**

Run: `uv run pytest tests/foundry/test_files.py -v`
Expected: PASS

**Step 7: Commit**

```bash
git add src/foundry/files.py src/foundry/client.py tests/foundry/test_files.py tests/fixtures/test_image.png
git commit -m "$(cat <<'EOF'
feat(foundry): add FileManager for file uploads

Add FileManager class with upload_file() method that sends files
to backend endpoint. Integrate into FoundryClient.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Implement SceneManager.create_scene()

**Files:**
- Modify: `src/foundry/scenes.py`

**Step 1: Write the failing test**

Add to `tests/foundry/test_scenes.py`:

```python
import pytest
from unittest.mock import patch, MagicMock

def test_create_scene_basic():
    """SceneManager.create_scene sends scene data to backend."""
    from foundry.scenes import SceneManager

    manager = SceneManager(backend_url="http://localhost:8000")

    with patch('foundry.scenes.requests.post') as mock_post:
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"success": True, "uuid": "Scene.abc123", "name": "Castle"}
        )

        result = manager.create_scene(
            name="Castle",
            background_image="worlds/test/uploaded-maps/castle.webp",
            width=1400,
            height=1000,
            grid_size=70,
            walls=[{"c": [0, 0, 100, 100], "move": 0, "sense": 0}]
        )

        assert result["success"] == True
        assert result["uuid"] == "Scene.abc123"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/foundry/test_scenes.py::test_create_scene_basic -v`
Expected: FAIL with NotImplementedError

**Step 3: Implement create_scene()**

Replace the `create_scene` method in `src/foundry/scenes.py`:

```python
def create_scene(
    self,
    name: str,
    background_image: Optional[str] = None,
    width: int = 3000,
    height: int = 2000,
    grid_size: Optional[int] = 100,
    walls: Optional[List[Dict[str, Any]]] = None,
    folder: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a scene in FoundryVTT via the backend WebSocket.

    Args:
        name: Name of the scene
        background_image: Foundry-relative path to background image
        width: Scene width in pixels (default 3000)
        height: Scene height in pixels (default 2000)
        grid_size: Grid size in pixels (None for gridless)
        walls: Optional list of wall objects
        folder: Optional folder ID

    Returns:
        {"success": True, "uuid": "Scene.xxx", "name": "..."} on success
        {"success": False, "error": "..."} on failure
    """
    endpoint = f"{self.backend_url}/api/foundry/scene"

    scene_data = {
        "name": name,
        "width": width,
        "height": height,
    }

    if background_image:
        scene_data["background"] = {"src": background_image}

    if grid_size is not None:
        scene_data["grid"] = {"size": grid_size, "type": 1}

    if walls:
        scene_data["walls"] = walls

    if folder:
        scene_data["folder"] = folder

    payload = {"scene": scene_data}

    logger.debug(f"Creating scene: {name}")

    try:
        response = requests.post(endpoint, json=payload, timeout=60)

        if response.status_code != 200:
            error_msg = response.json().get("detail", f"HTTP {response.status_code}")
            return {"success": False, "error": error_msg}

        data = response.json()
        logger.info(f"Created scene: {data.get('uuid')}")
        return {"success": True, "uuid": data.get("uuid"), "name": data.get("name")}

    except requests.exceptions.RequestException as e:
        logger.error(f"Create scene failed: {e}")
        return {"success": False, "error": str(e)}
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/foundry/test_scenes.py::test_create_scene_basic -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/foundry/scenes.py tests/foundry/test_scenes.py
git commit -m "$(cat <<'EOF'
feat(foundry): implement SceneManager.create_scene()

Add create_scene() method that posts scene data with walls and
grid settings to backend endpoint. Supports gridless scenes.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: Add Scene Creation REST Endpoint

**Files:**
- Create: `ui/backend/app/routers/scenes.py`
- Modify: `ui/backend/app/main.py`

**Step 1: Write the failing test**

Create `tests/backend/test_scenes_router.py`:

```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

def test_create_scene_endpoint():
    """POST /api/foundry/scene creates scene via WebSocket."""
    from app.main import app

    client = TestClient(app)

    mock_result = type('MockResult', (), {
        'success': True,
        'uuid': 'Scene.abc123',
        'name': 'Castle'
    })()

    with patch('app.routers.scenes.push_scene', new_callable=AsyncMock) as mock_push:
        mock_push.return_value = mock_result

        response = client.post(
            "/api/foundry/scene",
            json={
                "scene": {
                    "name": "Castle",
                    "width": 1400,
                    "height": 1000,
                    "grid": {"size": 70, "type": 1},
                    "walls": [{"c": [0, 0, 100, 100]}]
                }
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["uuid"] == "Scene.abc123"
```

**Step 2: Run test to verify it fails**

Run: `cd ui/backend && uv run pytest tests/backend/test_scenes_router.py -v`
Expected: FAIL with 404

**Step 3: Create scenes router**

Create `ui/backend/app/routers/scenes.py`:

```python
"""Scene management endpoints."""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from app.websocket.push import push_scene

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/foundry", tags=["scenes"])


class SceneCreateRequest(BaseModel):
    """Request body for scene creation."""
    scene: Dict[str, Any]


@router.post("/scene")
async def create_scene(request: SceneCreateRequest):
    """
    Create a scene in FoundryVTT.

    The scene data is sent to the connected Foundry client via WebSocket.
    Supports battle maps with walls, art scenes, and gridless scenes.

    Returns:
        {"success": true, "uuid": "Scene.xxx", "name": "..."}
    """
    result = await push_scene(request.scene)

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    return {
        "success": True,
        "uuid": result.uuid,
        "name": result.name
    }
```

**Step 4: Register router in main.py**

Add to `ui/backend/app/main.py`:
```python
from app.routers import scenes
app.include_router(scenes.router)
```

**Step 5: Run test to verify it passes**

Run: `cd ui/backend && uv run pytest tests/backend/test_scenes_router.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add ui/backend/app/routers/scenes.py ui/backend/app/main.py tests/backend/test_scenes_router.py
git commit -m "$(cat <<'EOF'
feat(backend): add POST /api/foundry/scene endpoint

Create scenes router with create_scene endpoint that sends scene
data to Foundry module via WebSocket push_scene().

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: Implement SceneManager.get_scene() and delete_scene()

**Files:**
- Modify: `src/foundry/scenes.py`
- Modify: `ui/backend/app/websocket/push.py`
- Modify: `foundry-module/tablewrite-assistant/src/handlers/scene.ts`
- Modify: `foundry-module/tablewrite-assistant/src/handlers/index.ts`

**Step 1: Add get_scene and delete_scene handlers to Foundry module**

Add to `foundry-module/tablewrite-assistant/src/handlers/scene.ts`:

```typescript
export async function handleGetScene(uuid: string): Promise<GetResult> {
  try {
    const scene = game.scenes.get(uuid.replace('Scene.', ''));
    if (!scene) {
      return { success: false, error: `Scene not found: ${uuid}` };
    }

    return {
      success: true,
      entity: scene.toObject()
    };
  } catch (error) {
    console.error('[Tablewrite] Failed to get scene:', error);
    return { success: false, error: String(error) };
  }
}

export async function handleDeleteScene(uuid: string): Promise<DeleteResult> {
  try {
    const id = uuid.replace('Scene.', '');
    const scene = game.scenes.get(id);
    if (!scene) {
      return { success: false, error: `Scene not found: ${uuid}` };
    }

    const name = scene.name;
    await scene.delete();

    console.log('[Tablewrite] Deleted scene:', name);
    ui.notifications?.info(`Deleted scene: ${name}`);

    return { success: true, uuid, name: name ?? undefined };
  } catch (error) {
    console.error('[Tablewrite] Failed to delete scene:', error);
    return { success: false, error: String(error) };
  }
}
```

**Step 2: Update index.ts with message routing**

Add to `handleMessage()`:
```typescript
case 'get_scene':
  if (message.data?.uuid) {
    const result = await handleGetScene(message.data.uuid as string);
    return {
      responseType: result.success ? 'scene_data' : 'scene_error',
      request_id: message.request_id,
      data: result,
      error: result.error
    };
  }
  return {
    responseType: 'scene_error',
    request_id: message.request_id,
    error: 'Missing uuid for get_scene'
  };
case 'delete_scene':
  if (message.data?.uuid) {
    const result = await handleDeleteScene(message.data.uuid as string);
    return {
      responseType: result.success ? 'scene_deleted' : 'scene_error',
      request_id: message.request_id,
      data: result,
      error: result.error
    };
  }
  return {
    responseType: 'scene_error',
    request_id: message.request_id,
    error: 'Missing uuid for delete_scene'
  };
```

**Step 3: Add push functions to backend**

Add to `ui/backend/app/websocket/push.py`:

```python
async def fetch_scene(uuid: str, timeout: float = 30.0) -> FetchResult:
    """Fetch a scene from Foundry by UUID."""
    response = await foundry_manager.broadcast_and_wait(
        {"type": "get_scene", "data": {"uuid": uuid}},
        timeout=timeout
    )

    if response is None:
        return FetchResult(success=False, error="No Foundry client connected or timeout")

    if response.get("type") == "scene_data":
        return FetchResult(success=True, entity=response.get("data", {}).get("entity"))
    elif response.get("type") == "scene_error":
        return FetchResult(success=False, error=response.get("error"))
    else:
        return FetchResult(success=False, error=f"Unexpected response type: {response.get('type')}")


async def delete_scene(uuid: str, timeout: float = 30.0) -> DeleteResult:
    """Delete a scene from Foundry by UUID."""
    response = await foundry_manager.broadcast_and_wait(
        {"type": "delete_scene", "data": {"uuid": uuid}},
        timeout=timeout
    )

    if response is None:
        return DeleteResult(success=False, error="No Foundry client connected or timeout")

    if response.get("type") == "scene_deleted":
        data = response.get("data", {})
        return DeleteResult(success=True, uuid=data.get("uuid"), name=data.get("name"))
    elif response.get("type") == "scene_error":
        return DeleteResult(success=False, error=response.get("error"))
    else:
        return DeleteResult(success=False, error=f"Unexpected response type: {response.get('type')}")
```

**Step 4: Implement SceneManager methods**

Add to `src/foundry/scenes.py`:

```python
def get_scene(self, scene_uuid: str) -> Dict[str, Any]:
    """Retrieve a Scene by UUID."""
    endpoint = f"{self.backend_url}/api/foundry/scene/{scene_uuid}"

    try:
        response = requests.get(endpoint, timeout=30)
        if response.status_code != 200:
            return {"success": False, "error": f"HTTP {response.status_code}"}
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": str(e)}

def delete_scene(self, scene_uuid: str) -> Dict[str, Any]:
    """Delete a scene."""
    endpoint = f"{self.backend_url}/api/foundry/scene/{scene_uuid}"

    try:
        response = requests.delete(endpoint, timeout=30)
        if response.status_code != 200:
            return {"success": False, "error": f"HTTP {response.status_code}"}
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": str(e)}
```

**Step 5: Add REST endpoints for get/delete scene**

Add to `ui/backend/app/routers/scenes.py`:

```python
@router.get("/scene/{uuid}")
async def get_scene(uuid: str):
    """Get a scene by UUID."""
    from app.websocket.push import fetch_scene

    result = await fetch_scene(uuid)
    if not result.success:
        raise HTTPException(status_code=404, detail=result.error)
    return {"success": True, "entity": result.entity}


@router.delete("/scene/{uuid}")
async def delete_scene_endpoint(uuid: str):
    """Delete a scene by UUID."""
    from app.websocket.push import delete_scene

    result = await delete_scene(uuid)
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    return {"success": True, "uuid": result.uuid, "name": result.name}
```

**Step 6: Build module and run tests**

Run: `cd foundry-module/tablewrite-assistant && npm run build`
Expected: Build succeeds

**Step 7: Commit**

```bash
git add -A
git commit -m "$(cat <<'EOF'
feat(scenes): add get_scene and delete_scene operations

Add handlers in Foundry module, push functions in backend, and
SceneManager methods for fetching and deleting scenes.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 8: Create Scene Models

**Files:**
- Create: `src/scenes/__init__.py`
- Create: `src/scenes/models.py`

**Step 1: Write the model file**

Create `src/scenes/__init__.py`:
```python
"""Scene processing and creation modules."""
```

Create `src/scenes/models.py`:

```python
"""Data models for scene creation pipeline."""

from pathlib import Path
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict


class GridDetectionResult(BaseModel):
    """Result from detect_gridlines()."""
    model_config = ConfigDict(frozen=True)

    has_grid: bool
    grid_size: Optional[int] = None  # Side length in pixels (e.g., 100 = 100x100px)
    confidence: float = 0.0  # 0.0-1.0


class SceneCreationResult(BaseModel):
    """Result from create_scene_from_map()."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Core identifiers (matches ActorCreationResult pattern)
    uuid: str                          # "Scene.abc123"
    name: str                          # "Castle" (derived from filename)
    output_dir: Path                   # output/runs/.../scenes/castle/
    timestamp: str                     # "20241102_143022"

    # Scene-specific details
    foundry_image_path: str            # "worlds/myworld/uploaded-maps/castle.webp"
    grid_size: Optional[int] = None    # Side length in pixels, None if gridless
    wall_count: int = 0                # Number of walls created
    image_dimensions: Dict[str, int]   # {"width": 1380, "height": 940}

    # Debug artifacts (paths to intermediate files)
    debug_artifacts: Dict[str, Path] = {}  # {grayscale, redlined, overlay, walls_json}
```

**Step 2: Write unit test**

Create `tests/scenes/__init__.py`:
```python
"""Tests for scene processing modules."""
```

Create `tests/scenes/test_models.py`:

```python
import pytest
from pathlib import Path
from scenes.models import GridDetectionResult, SceneCreationResult


def test_grid_detection_result_immutable():
    """GridDetectionResult should be frozen/immutable."""
    result = GridDetectionResult(has_grid=True, grid_size=70, confidence=0.95)

    assert result.has_grid == True
    assert result.grid_size == 70
    assert result.confidence == 0.95

    with pytest.raises(Exception):  # ValidationError or AttributeError
        result.grid_size = 100


def test_scene_creation_result():
    """SceneCreationResult holds all pipeline outputs."""
    result = SceneCreationResult(
        uuid="Scene.abc123",
        name="Castle",
        output_dir=Path("output/runs/20241102/scenes/castle"),
        timestamp="20241102_143022",
        foundry_image_path="worlds/test/uploaded-maps/castle.webp",
        grid_size=70,
        wall_count=150,
        image_dimensions={"width": 1400, "height": 1000},
        debug_artifacts={
            "overlay": Path("output/runs/20241102/scenes/castle/05_final_overlay.png")
        }
    )

    assert result.uuid == "Scene.abc123"
    assert result.wall_count == 150
    assert "width" in result.image_dimensions
```

**Step 3: Run test to verify it passes**

Run: `PYTHONPATH=src uv run pytest tests/scenes/test_models.py -v`
Expected: PASS

**Step 4: Commit**

```bash
git add src/scenes/__init__.py src/scenes/models.py tests/scenes/__init__.py tests/scenes/test_models.py
git commit -m "$(cat <<'EOF'
feat(scenes): add GridDetectionResult and SceneCreationResult models

Create Pydantic models for grid detection output and scene creation
pipeline results. GridDetectionResult is frozen for immutability.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 9: Create Grid Detection Module

**Files:**
- Create: `src/scenes/detect_gridlines.py`

**Step 1: Write the failing test**

Create `tests/scenes/test_detect_gridlines.py`:

```python
import pytest
from pathlib import Path
from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
async def test_detect_gridlines_with_grid():
    """detect_gridlines detects grid and returns size."""
    from scenes.detect_gridlines import detect_gridlines

    # Mock Gemini response indicating grid detected
    mock_response = """
    {
        "has_grid": true,
        "grid_size": 70,
        "confidence": 0.92
    }
    """

    with patch('scenes.detect_gridlines.genai') as mock_genai:
        mock_model = AsyncMock()
        mock_model.generate_content_async.return_value.text = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        result = await detect_gridlines(Path("tests/fixtures/test_image.png"))

        assert result.has_grid == True
        assert result.grid_size == 70
        assert result.confidence >= 0.9


@pytest.mark.asyncio
async def test_detect_gridlines_no_grid():
    """detect_gridlines correctly identifies gridless maps."""
    from scenes.detect_gridlines import detect_gridlines

    mock_response = """
    {
        "has_grid": false,
        "grid_size": null,
        "confidence": 0.85
    }
    """

    with patch('scenes.detect_gridlines.genai') as mock_genai:
        mock_model = AsyncMock()
        mock_model.generate_content_async.return_value.text = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        result = await detect_gridlines(Path("tests/fixtures/test_image.png"))

        assert result.has_grid == False
        assert result.grid_size is None
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src uv run pytest tests/scenes/test_detect_gridlines.py -v`
Expected: FAIL with "No module named 'scenes.detect_gridlines'"

**Step 3: Write the implementation**

Create `src/scenes/detect_gridlines.py`:

```python
"""AI-powered grid detection for battle maps using Gemini Vision."""

import json
import logging
import os
from pathlib import Path
from dotenv import load_dotenv

import google.generativeai as genai
from PIL import Image

from scenes.models import GridDetectionResult

load_dotenv()

logger = logging.getLogger(__name__)

GRID_DETECTION_PROMPT = """Analyze this battle map image for grid lines.

Look for:
1. Regular horizontal and vertical lines forming a grid pattern
2. Square grid cells (most common in D&D battle maps)

Return a JSON object with:
{
    "has_grid": true/false,
    "grid_size": <integer pixels between grid lines, or null if no grid>,
    "confidence": <0.0 to 1.0 confidence in your detection>
}

If you detect a grid, estimate the pixel spacing between lines.
If the image has no visible grid lines, return has_grid: false.

Return ONLY the JSON object, no other text."""


async def detect_gridlines(
    image_path: Path,
    model_name: str = "gemini-2.0-flash"
) -> GridDetectionResult:
    """
    Analyze battle map image for grid lines using Gemini Vision.

    Args:
        image_path: Path to battle map image
        model_name: Gemini model to use

    Returns:
        GridDetectionResult with has_grid, grid_size, confidence
    """
    logger.info(f"Detecting grid lines in: {image_path}")

    api_key = os.getenv("GeminiImageAPI")
    if not api_key:
        raise RuntimeError("GeminiImageAPI environment variable not set")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)

    # Load and prepare image
    image = Image.open(image_path)

    # Send to Gemini
    response = await model.generate_content_async([GRID_DETECTION_PROMPT, image])

    # Parse JSON response
    response_text = response.text.strip()

    # Handle markdown code blocks
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        response_text = "\n".join(lines[1:-1])

    try:
        data = json.loads(response_text)

        return GridDetectionResult(
            has_grid=data.get("has_grid", False),
            grid_size=data.get("grid_size"),
            confidence=data.get("confidence", 0.0)
        )
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse grid detection response: {e}")
        logger.warning(f"Response was: {response_text}")

        # Return default no-grid result
        return GridDetectionResult(
            has_grid=False,
            grid_size=None,
            confidence=0.0
        )
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src uv run pytest tests/scenes/test_detect_gridlines.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/scenes/detect_gridlines.py tests/scenes/test_detect_gridlines.py
git commit -m "$(cat <<'EOF'
feat(scenes): add AI grid detection using Gemini Vision

Add detect_gridlines() that analyzes battle maps for grid lines
and returns grid size in pixels. Falls back gracefully on parse errors.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 10: Create Scene Size Estimation Module

**Files:**
- Create: `src/scenes/estimate_scene_size.py`

**Step 1: Write the failing test**

Create `tests/scenes/test_estimate_scene_size.py`:

```python
import pytest
from pathlib import Path
from PIL import Image
import tempfile
import os

def test_estimate_scene_size_wide_image():
    """estimate_scene_size calculates grid for wide images."""
    from scenes.estimate_scene_size import estimate_scene_size

    # Create a 2000x1000 test image
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
        img = Image.new('RGB', (2000, 1000), color='white')
        img.save(f.name)

        result = estimate_scene_size(Path(f.name))

        # Target ~25 squares on longest edge (2000px)
        # 2000 / 25 = 80px grid
        assert 60 <= result <= 100

        os.unlink(f.name)


def test_estimate_scene_size_tall_image():
    """estimate_scene_size works for tall images."""
    from scenes.estimate_scene_size import estimate_scene_size

    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
        img = Image.new('RGB', (1000, 3000), color='white')
        img.save(f.name)

        result = estimate_scene_size(Path(f.name))

        # Target ~25 squares on longest edge (3000px)
        # 3000 / 25 = 120px grid
        assert 100 <= result <= 150

        os.unlink(f.name)


def test_estimate_scene_size_custom_target():
    """estimate_scene_size respects target_squares parameter."""
    from scenes.estimate_scene_size import estimate_scene_size

    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
        img = Image.new('RGB', (1000, 1000), color='white')
        img.save(f.name)

        # Target 10 squares
        result = estimate_scene_size(Path(f.name), target_squares=10)

        # 1000 / 10 = 100px grid
        assert result == 100

        os.unlink(f.name)
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src uv run pytest tests/scenes/test_estimate_scene_size.py -v`
Expected: FAIL with "No module named 'scenes.estimate_scene_size'"

**Step 3: Write the implementation**

Create `src/scenes/estimate_scene_size.py`:

```python
"""Simple grid size estimation for gridless battle maps."""

import logging
from pathlib import Path
from PIL import Image

logger = logging.getLogger(__name__)


def estimate_scene_size(
    image_path: Path,
    target_squares: int = 25
) -> int:
    """
    Calculate reasonable grid size for gridless maps.

    Strategy:
        - Load image dimensions
        - Target N grid squares on longest edge (typical battle map: 20-40)
        - Return grid_size that achieves this

    Args:
        image_path: Path to image file
        target_squares: Target number of grid squares on longest edge
                       (default: 25, typical range: 20-40)

    Returns:
        Grid size in pixels (rounded to nearest 10)

    Example:
        2000px wide image with target 25 squares:
        2000 / 25 = 80px grid → ~25 squares across
    """
    image = Image.open(image_path)
    width, height = image.size

    longest_edge = max(width, height)

    # Calculate base grid size
    grid_size = longest_edge / target_squares

    # Round to nearest 10 for cleaner numbers
    grid_size = round(grid_size / 10) * 10

    # Clamp to reasonable range (50-200px per square)
    grid_size = max(50, min(200, grid_size))

    logger.info(f"Estimated grid size: {grid_size}px for {width}x{height} image")

    return int(grid_size)
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src uv run pytest tests/scenes/test_estimate_scene_size.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/scenes/estimate_scene_size.py tests/scenes/test_estimate_scene_size.py
git commit -m "$(cat <<'EOF'
feat(scenes): add grid size estimation for gridless maps

Add estimate_scene_size() that calculates a reasonable grid size
based on image dimensions. Targets ~25 squares on longest edge.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 11: Create Integration Test for Grid Detection

**Files:**
- Create: `tests/scenes/test_detect_gridlines_integration.py`

**Step 1: Write the integration test**

```python
"""Integration tests for grid detection with real Gemini API."""

import pytest
from pathlib import Path

@pytest.mark.integration
@pytest.mark.asyncio
async def test_detect_gridlines_real_api():
    """Test grid detection with real Gemini API call."""
    from scenes.detect_gridlines import detect_gridlines

    # Use test fixture (should be a map with or without grid)
    test_image = Path("tests/fixtures/test_image.png")

    if not test_image.exists():
        pytest.skip("Test image not found")

    result = await detect_gridlines(test_image)

    # Just verify we get a valid result structure
    assert isinstance(result.has_grid, bool)
    assert 0.0 <= result.confidence <= 1.0

    if result.has_grid:
        assert result.grid_size is not None
        assert result.grid_size > 0
    else:
        # Gridless is fine
        pass
```

**Step 2: Run test (marked as integration, won't run by default)**

Run: `PYTHONPATH=src uv run pytest tests/scenes/test_detect_gridlines_integration.py -v -m integration`
Expected: PASS (if API key configured and test image exists)

**Step 3: Commit**

```bash
git add tests/scenes/test_detect_gridlines_integration.py
git commit -m "$(cat <<'EOF'
test(scenes): add integration test for grid detection

Test detect_gridlines() with real Gemini API call.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 12: Create Scene Orchestration Function (Part 1 - Core Logic)

**Files:**
- Create: `src/scenes/orchestrate.py`

**Step 1: Write the failing test**

Create `tests/scenes/test_orchestrate.py`:

```python
import pytest
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock
import tempfile
from PIL import Image
import os

@pytest.mark.asyncio
async def test_create_scene_from_map_basic():
    """create_scene_from_map runs full pipeline."""
    from scenes.orchestrate import create_scene_from_map
    from scenes.models import GridDetectionResult

    # Create temp image
    with tempfile.NamedTemporaryFile(suffix='.webp', delete=False) as f:
        img = Image.new('RGB', (1400, 1000), color='white')
        img.save(f.name)
        temp_path = Path(f.name)

    try:
        # Mock all external calls
        mock_walls_result = {
            'original_png': temp_path.with_suffix('.png'),
            'overlay': temp_path.with_suffix('.png'),
            'foundry_walls_json': temp_path.with_suffix('.json'),
        }

        with patch('scenes.orchestrate.redline_walls', new_callable=AsyncMock) as mock_walls, \
             patch('scenes.orchestrate.detect_gridlines', new_callable=AsyncMock) as mock_grid, \
             patch('scenes.orchestrate.FoundryClient') as mock_client_class:

            mock_walls.return_value = mock_walls_result
            mock_grid.return_value = GridDetectionResult(has_grid=True, grid_size=70, confidence=0.9)

            mock_client = MagicMock()
            mock_client.files.upload_file.return_value = {
                "success": True,
                "path": "worlds/test/uploaded-maps/test.webp"
            }
            mock_client.scenes.create_scene.return_value = {
                "success": True,
                "uuid": "Scene.abc123",
                "name": "Test"
            }
            mock_client_class.return_value = mock_client

            # Need to mock the walls JSON file reading
            walls_json_content = {
                "walls": [{"c": [0, 0, 100, 100]}],
                "image_dimensions": {"width": 1400, "height": 1000},
                "total_walls": 1
            }
            with patch('builtins.open', MagicMock()):
                with patch('json.load', return_value=walls_json_content):
                    result = await create_scene_from_map(temp_path)

            assert result.uuid == "Scene.abc123"
            assert result.grid_size == 70
            assert result.wall_count >= 0
    finally:
        os.unlink(temp_path)
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src uv run pytest tests/scenes/test_orchestrate.py -v`
Expected: FAIL with "No module named 'scenes.orchestrate'"

**Step 3: Write the orchestration function**

Create `src/scenes/orchestrate.py`:

```python
"""Orchestrate full scene creation pipeline: image → walls → upload → scene."""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Union, Optional

from scenes.models import SceneCreationResult, GridDetectionResult
from scenes.detect_gridlines import detect_gridlines
from scenes.estimate_scene_size import estimate_scene_size
from wall_detection.redline_walls import redline_walls
from foundry.client import FoundryClient

logger = logging.getLogger(__name__)


def _derive_scene_name(image_path: Path) -> str:
    """Derive scene name from filename."""
    # Remove extension and convert underscores/hyphens to spaces
    name = image_path.stem
    name = name.replace('_', ' ').replace('-', ' ')
    # Title case
    return name.title()


async def create_scene_from_map(
    image_path: Union[str, Path],
    name: Optional[str] = None,
    output_dir_base: str = "output/runs",
    foundry_client: Optional[FoundryClient] = None,
    skip_wall_detection: bool = False,
    skip_grid_detection: bool = False,
    grid_size_override: Optional[int] = None
) -> SceneCreationResult:
    """
    Complete pipeline: image → walls → upload → scene.

    Steps:
        1. Derive scene name from filename (if not provided)
        2. Create timestamped output directory
        3. Run wall detection pipeline (redline_walls)
        4. Detect grid lines (detect_gridlines)
           - If no grid: use estimate_scene_size() as fallback
        5. Upload image to Foundry (POST /files/upload)
        6. Create scene with walls (POST /scene)
        7. Return SceneCreationResult with all details

    Args:
        image_path: Path to battle map image
        name: Scene name (derived from filename if not provided)
        output_dir_base: Base directory for output
        foundry_client: Optional FoundryClient (created if None)
        skip_wall_detection: Skip AI wall detection
        skip_grid_detection: Skip AI grid detection
        grid_size_override: Force specific grid size

    Returns:
        SceneCreationResult with UUID, paths, and debug artifacts
    """
    image_path = Path(image_path)

    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    # Step 1: Derive scene name
    scene_name = name or _derive_scene_name(image_path)
    logger.info(f"Creating scene: {scene_name} from {image_path}")

    # Step 2: Create output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(output_dir_base) / timestamp / "scenes" / scene_name.lower().replace(' ', '_')
    output_dir.mkdir(parents=True, exist_ok=True)

    # Step 3: Run wall detection
    walls = []
    image_dimensions = {"width": 0, "height": 0}
    debug_artifacts = {}

    if not skip_wall_detection:
        logger.info("Running wall detection pipeline...")
        wall_result = await redline_walls(
            input_image=image_path,
            save_dir=output_dir,
            make_run=False
        )

        debug_artifacts = {k: v for k, v in wall_result.items() if isinstance(v, Path)}

        # Load walls from JSON
        walls_json_path = wall_result['foundry_walls_json']
        with open(walls_json_path, 'r') as f:
            walls_data = json.load(f)
            walls = walls_data.get('walls', [])
            image_dimensions = walls_data.get('image_dimensions', {})
    else:
        # Get image dimensions without wall detection
        from PIL import Image
        with Image.open(image_path) as img:
            image_dimensions = {"width": img.width, "height": img.height}

    # Step 4: Detect grid
    if grid_size_override is not None:
        grid_size = grid_size_override
        logger.info(f"Using grid size override: {grid_size}")
    elif not skip_grid_detection:
        logger.info("Detecting grid lines...")
        grid_result = await detect_gridlines(image_path)

        if grid_result.has_grid and grid_result.grid_size:
            grid_size = grid_result.grid_size
            logger.info(f"Detected grid: {grid_size}px (confidence: {grid_result.confidence:.2f})")
        else:
            grid_size = estimate_scene_size(image_path)
            logger.info(f"No grid detected, estimated: {grid_size}px")
    else:
        grid_size = estimate_scene_size(image_path)
        logger.info(f"Skipped grid detection, estimated: {grid_size}px")

    # Step 5: Initialize client and upload image
    client = foundry_client or FoundryClient()

    logger.info("Uploading image to Foundry...")
    upload_result = client.files.upload_file(
        local_path=image_path,
        destination="uploaded-maps"
    )

    if not upload_result.get("success"):
        raise RuntimeError(f"Failed to upload image: {upload_result.get('error')}")

    foundry_image_path = upload_result["path"]
    logger.info(f"Uploaded to: {foundry_image_path}")

    # Step 6: Create scene
    logger.info(f"Creating scene with {len(walls)} walls...")
    scene_result = client.scenes.create_scene(
        name=scene_name,
        background_image=foundry_image_path,
        width=image_dimensions.get("width", 1000),
        height=image_dimensions.get("height", 1000),
        grid_size=grid_size,
        walls=walls if walls else None
    )

    if not scene_result.get("success"):
        raise RuntimeError(f"Failed to create scene: {scene_result.get('error')}")

    scene_uuid = scene_result["uuid"]
    logger.info(f"Created scene: {scene_uuid}")

    # Step 7: Save result summary
    result = SceneCreationResult(
        uuid=scene_uuid,
        name=scene_name,
        output_dir=output_dir,
        timestamp=timestamp,
        foundry_image_path=foundry_image_path,
        grid_size=grid_size,
        wall_count=len(walls),
        image_dimensions=image_dimensions,
        debug_artifacts=debug_artifacts
    )

    # Save result to JSON
    result_path = output_dir / "07_scene_result.json"
    with open(result_path, 'w') as f:
        json.dump(result.model_dump(mode='json'), f, indent=2, default=str)

    return result


def create_scene_from_map_sync(
    image_path: Union[str, Path],
    name: Optional[str] = None,
    **kwargs
) -> SceneCreationResult:
    """Synchronous wrapper for create_scene_from_map()."""
    return asyncio.run(create_scene_from_map(image_path, name, **kwargs))
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src uv run pytest tests/scenes/test_orchestrate.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/scenes/orchestrate.py tests/scenes/test_orchestrate.py
git commit -m "$(cat <<'EOF'
feat(scenes): add create_scene_from_map orchestration function

Full pipeline: wall detection → grid detection → upload → scene creation.
Supports skip flags and grid size override for flexibility.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 13: Add Scene Creation to Public API

**Files:**
- Modify: `src/api.py`

**Step 1: Write the failing test**

Add to `tests/api/test_api.py`:

```python
def test_create_scene_api(tmp_path):
    """create_scene API function returns SceneCreationResult."""
    from api import create_scene
    from PIL import Image

    # Create test image
    test_image = tmp_path / "test_map.webp"
    img = Image.new('RGB', (1000, 1000), color='white')
    img.save(test_image)

    with patch('api.create_scene_from_map_sync') as mock_create:
        mock_create.return_value = MagicMock(
            uuid="Scene.abc123",
            name="Test Map",
            wall_count=50
        )

        result = create_scene(str(test_image))

        assert result.uuid == "Scene.abc123"
        assert result.name == "Test Map"
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src uv run pytest tests/api/test_api.py::test_create_scene_api -v`
Expected: FAIL with "cannot import name 'create_scene'"

**Step 3: Add to public API**

Add to `src/api.py`:

```python
from scenes.orchestrate import create_scene_from_map_sync
from scenes.models import SceneCreationResult


def create_scene(
    image_path: str,
    name: Optional[str] = None,
    skip_wall_detection: bool = False,
    grid_size: Optional[int] = None
) -> SceneCreationResult:
    """
    Create a FoundryVTT scene from a battle map image.

    Args:
        image_path: Path to battle map image (webp, png, jpg)
        name: Scene name (derived from filename if not provided)
        skip_wall_detection: Skip AI wall detection
        grid_size: Override auto-detected grid size

    Returns:
        SceneCreationResult with UUID, name, wall_count, etc.

    Raises:
        APIError: If scene creation fails

    Example:
        result = create_scene("maps/castle.webp")
        print(f"Created: {result.uuid} with {result.wall_count} walls")
    """
    try:
        return create_scene_from_map_sync(
            image_path=image_path,
            name=name,
            skip_wall_detection=skip_wall_detection,
            grid_size_override=grid_size
        )
    except Exception as e:
        raise APIError(f"Scene creation failed: {e}") from e
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src uv run pytest tests/api/test_api.py::test_create_scene_api -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/api.py tests/api/test_api.py
git commit -m "$(cat <<'EOF'
feat(api): add create_scene to public API

Expose create_scene() for creating FoundryVTT scenes from battle
map images with automatic wall detection and grid detection.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 14: Create Test Fixtures

**Files:**
- Create: `tests/scenes/fixtures/` with test maps

**Step 1: Create fixture directory and test images**

```bash
mkdir -p tests/scenes/fixtures
```

Create simple test images using Python:

```python
# Run this to create test fixtures
from PIL import Image, ImageDraw

# Create gridded map (simple checkerboard)
img = Image.new('RGB', (700, 700), color='#f5e6c8')  # Parchment color
draw = ImageDraw.Draw(img)

# Draw grid lines every 70 pixels
for i in range(0, 700, 70):
    draw.line([(i, 0), (i, 700)], fill='#cccccc', width=1)
    draw.line([(0, i), (700, i)], fill='#cccccc', width=1)

# Draw some "walls"
draw.rectangle([100, 100, 600, 120], fill='#8b4513')  # Top wall
draw.rectangle([100, 100, 120, 600], fill='#8b4513')  # Left wall
draw.rectangle([100, 580, 600, 600], fill='#8b4513')  # Bottom wall
draw.rectangle([580, 100, 600, 600], fill='#8b4513')  # Right wall

img.save('tests/scenes/fixtures/gridded_map.webp')

# Create gridless map
img2 = Image.new('RGB', (1000, 800), color='#f5e6c8')
draw2 = ImageDraw.Draw(img2)

# Draw some terrain features
draw2.ellipse([200, 200, 400, 400], fill='#228b22')  # Forest
draw2.rectangle([600, 300, 800, 500], fill='#8b4513')  # Building

img2.save('tests/scenes/fixtures/gridless_map.webp')
```

**Step 2: Verify fixtures exist**

Run: `ls tests/scenes/fixtures/`
Expected: `gridded_map.webp  gridless_map.webp`

**Step 3: Commit**

```bash
git add tests/scenes/fixtures/
git commit -m "$(cat <<'EOF'
test(scenes): add test map fixtures

Add gridded_map.webp (700x700 with 70px grid) and gridless_map.webp
(1000x800 with terrain features) for integration tests.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 15: Add Scene Creator Tool to Chat Backend

**Files:**
- Modify: `ui/backend/app/tools/scene_creator.py`

**Step 1: Write the failing test**

Add to `tests/backend/test_scene_creator_tool.py`:

```python
import pytest
from unittest.mock import patch, MagicMock

@pytest.mark.asyncio
async def test_scene_creator_tool_execution():
    """SceneCreatorTool executes scene creation pipeline."""
    from app.tools.scene_creator import SceneCreatorTool

    tool = SceneCreatorTool()

    with patch('app.tools.scene_creator.create_scene') as mock_create:
        mock_create.return_value = MagicMock(
            uuid="Scene.abc123",
            name="Castle",
            wall_count=150,
            grid_size=70
        )

        result = await tool.execute(
            image_path="/path/to/castle.webp",
            name="Castle"
        )

        assert result.success == True
        assert "Scene.abc123" in result.content
        assert "150 walls" in result.content
```

**Step 2: Run test to verify it fails**

Run: `cd ui/backend && uv run pytest tests/backend/test_scene_creator_tool.py -v`
Expected: FAIL (tool not implemented or doesn't work as expected)

**Step 3: Update scene creator tool**

Update `ui/backend/app/tools/scene_creator.py`:

```python
"""Scene creator tool for chat interface."""

import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from app.tools.base import BaseTool, ToolSchema, ToolResponse

# Import from main src
import sys
sys.path.insert(0, '/path/to/src')  # Adjust path as needed
from api import create_scene

logger = logging.getLogger(__name__)


class SceneCreatorTool(BaseTool):
    """Tool for creating FoundryVTT scenes from battle map images."""

    @property
    def name(self) -> str:
        return "create_scene"

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name=self.name,
            description="Create a FoundryVTT scene from a battle map image with automatic wall detection",
            parameters={
                "type": "object",
                "properties": {
                    "image_path": {
                        "type": "string",
                        "description": "Path to battle map image file (webp, png, jpg)"
                    },
                    "name": {
                        "type": "string",
                        "description": "Optional scene name (derived from filename if not provided)"
                    },
                    "skip_walls": {
                        "type": "boolean",
                        "description": "Skip AI wall detection (default: false)"
                    },
                    "grid_size": {
                        "type": "integer",
                        "description": "Override auto-detected grid size in pixels"
                    }
                },
                "required": ["image_path"]
            }
        )

    async def execute(
        self,
        image_path: str,
        name: Optional[str] = None,
        skip_walls: bool = False,
        grid_size: Optional[int] = None
    ) -> ToolResponse:
        """Execute scene creation pipeline."""
        try:
            logger.info(f"Creating scene from: {image_path}")

            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as pool:
                result = await loop.run_in_executor(
                    pool,
                    lambda: create_scene(
                        image_path=image_path,
                        name=name,
                        skip_wall_detection=skip_walls,
                        grid_size=grid_size
                    )
                )

            content = f"""**Scene Created Successfully!**

**Name:** {result.name}
**UUID:** `{result.uuid}`
**Walls:** {result.wall_count} walls detected
**Grid Size:** {result.grid_size}px
**Image:** {result.foundry_image_path}
**Output:** {result.output_dir}"""

            return ToolResponse(
                success=True,
                content=content
            )

        except Exception as e:
            logger.error(f"Scene creation failed: {e}")
            return ToolResponse(
                success=False,
                content=f"Scene creation failed: {e}"
            )
```

**Step 4: Register tool in registry**

Add to `ui/backend/app/tools/__init__.py`:
```python
from .scene_creator import SceneCreatorTool
registry.register(SceneCreatorTool())
```

**Step 5: Run test to verify it passes**

Run: `cd ui/backend && uv run pytest tests/backend/test_scene_creator_tool.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add ui/backend/app/tools/scene_creator.py ui/backend/app/tools/__init__.py tests/backend/test_scene_creator_tool.py
git commit -m "$(cat <<'EOF'
feat(backend): add scene creator chat tool

Add create_scene tool that creates FoundryVTT scenes from battle
maps via chat interface. Includes wall detection and grid detection.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 16: Integration Test - File Upload Round-Trip

**Files:**
- Create: `tests/scenes/test_file_upload_integration.py`

**Step 1: Write the integration test**

```python
"""Integration tests for file upload to FoundryVTT."""

import pytest
from pathlib import Path
from PIL import Image
import tempfile
import os

@pytest.mark.integration
@pytest.mark.requires_foundry
def test_file_upload_roundtrip():
    """Upload file to Foundry and verify it exists."""
    from foundry.client import FoundryClient

    client = FoundryClient()

    # Check connection first
    assert client.is_connected(), "Foundry not connected - start backend and connect Foundry module"

    # Create a unique test image
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
        img = Image.new('RGB', (100, 100), color='red')
        img.save(f.name)
        temp_path = Path(f.name)

    try:
        # Upload to tests subfolder
        result = client.files.upload_file(
            local_path=temp_path,
            destination="uploaded-maps/tests"
        )

        assert result.get("success") == True, f"Upload failed: {result.get('error')}"
        assert "path" in result
        assert result["path"].endswith(".png")

        # Verify file exists by listing files
        # (File listing integration would go here)

    finally:
        os.unlink(temp_path)
```

**Step 2: Run test (requires Foundry)**

Run: `PYTHONPATH=src uv run pytest tests/scenes/test_file_upload_integration.py -v -m integration`
Expected: PASS (if Foundry connected)

**Step 3: Commit**

```bash
git add tests/scenes/test_file_upload_integration.py
git commit -m "$(cat <<'EOF'
test(scenes): add file upload integration test

Verify file upload to Foundry works via WebSocket pipeline.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 17: Integration Test - Scene Creation Round-Trip

**Files:**
- Create: `tests/scenes/test_scene_creation_integration.py`

**Step 1: Write the comprehensive integration test**

```python
"""Integration tests for complete scene creation pipeline."""

import pytest
from pathlib import Path

@pytest.mark.integration
@pytest.mark.requires_foundry
@pytest.mark.asyncio
async def test_scene_creation_roundtrip():
    """Create scene in Foundry, fetch it back, verify walls exist."""
    from scenes.orchestrate import create_scene_from_map
    from foundry.client import FoundryClient

    client = FoundryClient()

    # Check connection
    assert client.is_connected(), "Foundry not connected - start backend and connect Foundry module"

    # Use test fixture
    test_map = Path("tests/scenes/fixtures/gridded_map.webp")

    if not test_map.exists():
        pytest.skip("Test map fixture not found")

    # Create scene (in tests folder)
    result = await create_scene_from_map(
        image_path=test_map,
        name="Integration Test Scene",
        output_dir_base="tests/output/test_runs"
    )

    # Verify result
    assert result.uuid.startswith("Scene.")
    assert result.name == "Integration Test Scene"
    assert result.wall_count > 0, "Expected walls to be detected"
    assert result.grid_size is not None

    # Fetch scene back from Foundry
    scene_data = client.scenes.get_scene(result.uuid)

    assert scene_data.get("success") == True, f"Failed to fetch scene: {scene_data.get('error')}"

    entity = scene_data.get("entity", {})

    # Verify scene properties
    assert entity.get("name") == "Integration Test Scene"
    assert len(entity.get("walls", [])) == result.wall_count
    assert "background" in entity
    assert entity["background"]["src"] == result.foundry_image_path


@pytest.mark.integration
@pytest.mark.requires_foundry
@pytest.mark.asyncio
async def test_scene_creation_gridless():
    """Create gridless scene and verify grid estimation."""
    from scenes.orchestrate import create_scene_from_map

    test_map = Path("tests/scenes/fixtures/gridless_map.webp")

    if not test_map.exists():
        pytest.skip("Gridless test map fixture not found")

    result = await create_scene_from_map(
        image_path=test_map,
        name="Gridless Test Scene",
        skip_wall_detection=True,  # Skip walls for speed
        output_dir_base="tests/output/test_runs"
    )

    # Should have estimated grid size
    assert result.grid_size is not None
    assert result.grid_size > 0

    # Verify scene was created
    assert result.uuid.startswith("Scene.")
```

**Step 2: Run test (requires Foundry)**

Run: `PYTHONPATH=src uv run pytest tests/scenes/test_scene_creation_integration.py -v -m integration`
Expected: PASS (if Foundry connected and fixtures exist)

**Step 3: Commit**

```bash
git add tests/scenes/test_scene_creation_integration.py
git commit -m "$(cat <<'EOF'
test(scenes): add scene creation round-trip integration tests

Verify complete pipeline: wall detection → upload → scene creation.
Includes tests for gridded and gridless maps.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 18: Final Cleanup and Documentation

**Files:**
- Modify: `CLAUDE.md` (update with new modules)
- Create: `docs/plans/2026-01-02-scene-wall-integration-design.md` (already exists, update)

**Step 1: Update CLAUDE.md with new modules**

Add to the appropriate section in `CLAUDE.md`:

```markdown
### Scene Creation Pipeline

**NEW**: Complete pipeline for creating FoundryVTT scenes from battle map images.

**Module**: `src/scenes/orchestrate.py`

**Workflow**:
```
Battle Map Image
    ↓
Wall Detection (redline_walls)
    ↓
Grid Detection (detect_gridlines / estimate_scene_size)
    ↓
Upload Image to Foundry
    ↓
Create Scene with Walls
    ↓
SceneCreationResult
```

**Usage**:

```python
from api import create_scene

# Create scene with automatic wall and grid detection
result = create_scene("maps/castle.webp")
print(f"Created: {result.uuid} with {result.wall_count} walls")

# Skip wall detection for art scenes
result = create_scene("art/chapter_splash.webp", skip_wall_detection=True)
```

**Key Modules**:
- `src/scenes/orchestrate.py` - Main pipeline
- `src/scenes/detect_gridlines.py` - AI grid detection
- `src/scenes/estimate_scene_size.py` - Fallback grid estimation
- `src/scenes/models.py` - SceneCreationResult, GridDetectionResult
- `src/foundry/files.py` - FileManager for uploads
```

**Step 2: Run full test suite**

Run: `PYTHONPATH=src uv run pytest --full -x 2>&1 | tee test_output.log`
Expected: All tests pass

**Step 3: Commit documentation**

```bash
git add CLAUDE.md
git commit -m "$(cat <<'EOF'
docs: add scene creation pipeline documentation

Document new scene creation workflow with wall detection and
grid detection. Update CLAUDE.md with usage examples.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Summary

This plan implements the scene & wall integration feature in 18 tasks:

1. **Tasks 1-4**: File upload infrastructure (Foundry module → backend → client)
2. **Tasks 5-7**: Scene CRUD operations (create/get/delete)
3. **Task 8**: Scene models (SceneCreationResult, GridDetectionResult)
4. **Tasks 9-11**: Grid detection (AI + fallback + integration test)
5. **Tasks 12-13**: Orchestration pipeline and public API
6. **Tasks 14-15**: Test fixtures and chat tool
7. **Tasks 16-18**: Integration tests and documentation

Each task follows TDD: failing test → implementation → passing test → commit.
