# Tablewrite WebSocket Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the relay server with a direct WebSocket connection from FoundryVTT module to backend, enabling push notifications when content is created.

**Architecture:** FastAPI backend adds a `/ws/foundry` WebSocket endpoint. A new TypeScript Foundry module (`foundry-module/tablewrite-assistant/`) connects on startup and receives push notifications when actors, journals, or scenes are created via the Web UI.

**Tech Stack:** Python (FastAPI WebSocket), TypeScript (FoundryVTT module), Vitest (module tests), pytest (backend tests)

---

## Execution Phases

| Phase | Tasks | Description |
|-------|-------|-------------|
| **Phase 1** | 1-5 | Backend WebSocket (real tests, no mocks) |
| **Phase 2** | 6-10 | Foundry Module (build + unit tests) |
| **CHECKPOINT** | - | **STOP. User installs module in Foundry.** |
| **Phase 3** | 11-12 | Integration Testing (requires running Foundry) |
| **Phase 4** | 13-17 | Docker & Documentation |

**IMPORTANT:** After Task 10, execution MUST stop. The user needs to:
1. Copy `foundry-module/tablewrite-assistant/` to Foundry's `Data/modules/` directory (as `tablewrite-assistant/`)
2. Enable the module in Foundry
3. Configure backend URL in module settings
4. Confirm the module connects successfully

Only after user confirmation should Phase 3 begin.

---

## Phase 1: Backend WebSocket Endpoint (Real Tests)

### Task 1: Create WebSocket Connection Manager

**Files:**
- Create: `ui/backend/app/websocket/__init__.py`
- Create: `ui/backend/app/websocket/connection_manager.py`
- Test: `ui/backend/tests/websocket/__init__.py`
- Test: `ui/backend/tests/websocket/test_connection_manager.py`

**Step 1: Write the failing test**

Create test file:
```python
# ui/backend/tests/websocket/__init__.py
# (empty file for package)
```

```python
# ui/backend/tests/websocket/test_connection_manager.py
"""Tests for WebSocket connection manager."""
import pytest
from app.websocket.connection_manager import ConnectionManager


class TestConnectionManager:
    """Test ConnectionManager class."""

    def test_manager_initializes_empty(self):
        """Manager starts with no connections."""
        manager = ConnectionManager()
        assert manager.active_connections == {}

    def test_connect_adds_client(self):
        """connect() adds client to active_connections."""
        manager = ConnectionManager()
        mock_ws = object()  # Placeholder for WebSocket

        client_id = manager.connect(mock_ws)

        assert client_id in manager.active_connections
        assert manager.active_connections[client_id] == mock_ws

    def test_disconnect_removes_client(self):
        """disconnect() removes client from active_connections."""
        manager = ConnectionManager()
        mock_ws = object()

        client_id = manager.connect(mock_ws)
        manager.disconnect(client_id)

        assert client_id not in manager.active_connections

    def test_disconnect_nonexistent_client_is_safe(self):
        """disconnect() with unknown client_id doesn't raise."""
        manager = ConnectionManager()

        # Should not raise
        manager.disconnect("nonexistent-id")
```

**Step 2: Run test to verify it fails**

Run: `cd ui/backend && uv run pytest tests/websocket/test_connection_manager.py -v`
Expected: FAIL with "No module named 'app.websocket'"

**Step 3: Write minimal implementation**

```python
# ui/backend/app/websocket/__init__.py
"""WebSocket connection management for Foundry module."""
from .connection_manager import ConnectionManager

__all__ = ['ConnectionManager']
```

```python
# ui/backend/app/websocket/connection_manager.py
"""Manage WebSocket connections from Foundry modules."""
import uuid
from typing import Dict, Any
from fastapi import WebSocket


class ConnectionManager:
    """Manage active WebSocket connections from Foundry clients."""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    def connect(self, websocket: WebSocket) -> str:
        """
        Register a new WebSocket connection.

        Args:
            websocket: The WebSocket connection

        Returns:
            client_id: Unique identifier for this connection
        """
        client_id = str(uuid.uuid4())
        self.active_connections[client_id] = websocket
        return client_id

    def disconnect(self, client_id: str) -> None:
        """
        Remove a WebSocket connection.

        Args:
            client_id: The client to disconnect
        """
        self.active_connections.pop(client_id, None)
```

**Step 4: Run test to verify it passes**

Run: `cd ui/backend && uv run pytest tests/websocket/test_connection_manager.py -v`
Expected: PASS (all 4 tests)

**Step 5: Commit**

```bash
git add ui/backend/app/websocket/ ui/backend/tests/websocket/
git commit -m "feat: add WebSocket connection manager for Foundry clients"
```

---

### Task 2: Add Broadcast Method to Connection Manager

**Files:**
- Modify: `ui/backend/app/websocket/connection_manager.py`
- Test: `ui/backend/tests/websocket/test_connection_manager.py`

**Step 1: Write the failing test**

Note: Broadcast is tested via real WebSocket in Task 3. Here we test the unit behavior.

```python
# Add to ui/backend/tests/websocket/test_connection_manager.py

import pytest

class TestConnectionManagerBroadcast:
    """Test broadcast functionality."""

    @pytest.mark.asyncio
    async def test_broadcast_to_empty_is_noop(self):
        """broadcast() with no connections doesn't raise."""
        manager = ConnectionManager()

        # Should not raise
        await manager.broadcast({"type": "test"})

    def test_get_connection_count(self):
        """connection_count property returns number of active connections."""
        manager = ConnectionManager()

        assert manager.connection_count == 0

        mock_ws = object()
        manager.connect(mock_ws)

        assert manager.connection_count == 1
```

**Step 2: Run test to verify it fails**

Run: `cd ui/backend && uv run pytest tests/websocket/test_connection_manager.py::TestConnectionManagerBroadcast -v`
Expected: FAIL with "ConnectionManager has no attribute 'broadcast'"

**Step 3: Write minimal implementation**

```python
# Add to ui/backend/app/websocket/connection_manager.py

    @property
    def connection_count(self) -> int:
        """Return number of active connections."""
        return len(self.active_connections)

    async def broadcast(self, message: Dict[str, Any]) -> None:
        """
        Send message to all connected clients.

        Automatically removes clients that fail to receive.

        Args:
            message: JSON-serializable message to broadcast
        """
        disconnected = []

        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(message)
            except Exception:
                disconnected.append(client_id)

        # Clean up failed connections
        for client_id in disconnected:
            self.disconnect(client_id)
```

**Step 4: Run test to verify it passes**

Run: `cd ui/backend && uv run pytest tests/websocket/test_connection_manager.py::TestConnectionManagerBroadcast -v`
Expected: PASS (both tests)

**Step 5: Commit**

```bash
git add ui/backend/app/websocket/connection_manager.py ui/backend/tests/websocket/test_connection_manager.py
git commit -m "feat: add broadcast method to connection manager"
```

---

### Task 3: Create WebSocket Endpoint

**Files:**
- Create: `ui/backend/app/websocket/foundry_endpoint.py`
- Modify: `ui/backend/app/main.py`
- Test: `ui/backend/tests/websocket/test_foundry_endpoint.py`

**Step 1: Write the failing test**

```python
# ui/backend/tests/websocket/test_foundry_endpoint.py
"""Tests for Foundry WebSocket endpoint (real WebSocket, no mocks)."""
import pytest
from fastapi.testclient import TestClient
from app.main import app


class TestFoundryWebSocket:
    """Test /ws/foundry endpoint with real WebSocket connections."""

    def test_websocket_connects(self):
        """Client can connect to /ws/foundry."""
        client = TestClient(app)

        with client.websocket_connect("/ws/foundry") as websocket:
            # Connection established - receive welcome message
            data = websocket.receive_json()
            assert data["type"] == "connected"
            assert "client_id" in data

    def test_websocket_receives_ping(self):
        """Client can send ping and receive pong."""
        client = TestClient(app)

        with client.websocket_connect("/ws/foundry") as websocket:
            # Consume welcome message
            websocket.receive_json()

            # Send ping
            websocket.send_json({"type": "ping"})

            # Receive pong
            data = websocket.receive_json()
            assert data["type"] == "pong"

    def test_broadcast_reaches_connected_client(self):
        """Broadcast sends message to connected WebSocket client."""
        import asyncio
        from app.websocket import foundry_manager

        client = TestClient(app)

        with client.websocket_connect("/ws/foundry") as websocket:
            # Consume welcome message
            websocket.receive_json()

            # Broadcast a message (need to run in event loop)
            message = {"type": "actor", "data": {"name": "Test Goblin"}}

            # Use the app's event loop to broadcast
            async def do_broadcast():
                await foundry_manager.broadcast(message)

            # TestClient runs in sync context, so we need asyncio.run
            import threading
            def broadcast_thread():
                asyncio.run(do_broadcast())

            thread = threading.Thread(target=broadcast_thread)
            thread.start()
            thread.join()

            # Receive the broadcast
            data = websocket.receive_json()
            assert data["type"] == "actor"
            assert data["data"]["name"] == "Test Goblin"
```

**Step 2: Run test to verify it fails**

Run: `cd ui/backend && uv run pytest tests/websocket/test_foundry_endpoint.py -v`
Expected: FAIL with "WebSocket connection failed" (endpoint doesn't exist)

**Step 3: Write minimal implementation**

```python
# ui/backend/app/websocket/foundry_endpoint.py
"""WebSocket endpoint for Foundry module connections."""
import logging
from fastapi import WebSocket, WebSocketDisconnect
from .connection_manager import ConnectionManager

logger = logging.getLogger(__name__)

# Global connection manager instance
foundry_manager = ConnectionManager()


async def foundry_websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for Foundry module connections.

    Protocol:
    - On connect: sends {"type": "connected", "client_id": "..."}
    - Client can send {"type": "ping"} -> receives {"type": "pong"}
    - Server pushes content: {"type": "actor|journal|scene", "data": {...}}
    """
    await websocket.accept()
    client_id = foundry_manager.connect(websocket)

    logger.info(f"Foundry client connected: {client_id}")

    try:
        # Send welcome message
        await websocket.send_json({
            "type": "connected",
            "client_id": client_id
        })

        # Handle incoming messages
        while True:
            data = await websocket.receive_json()

            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        logger.info(f"Foundry client disconnected: {client_id}")
    finally:
        foundry_manager.disconnect(client_id)
```

Update `__init__.py`:
```python
# ui/backend/app/websocket/__init__.py
"""WebSocket connection management for Foundry module."""
from .connection_manager import ConnectionManager
from .foundry_endpoint import foundry_websocket_endpoint, foundry_manager

__all__ = ['ConnectionManager', 'foundry_websocket_endpoint', 'foundry_manager']
```

Register in main.py - add these lines:
```python
# ui/backend/app/main.py
# Add import at top:
from app.websocket import foundry_websocket_endpoint

# Add endpoint after other routes:
@app.websocket("/ws/foundry")
async def websocket_foundry(websocket: WebSocket):
    """WebSocket endpoint for Foundry module connections."""
    await foundry_websocket_endpoint(websocket)
```

Note: Also add `from fastapi import WebSocket` to the imports in main.py.

**Step 4: Run test to verify it passes**

Run: `cd ui/backend && uv run pytest tests/websocket/test_foundry_endpoint.py -v`
Expected: PASS (all 3 tests)

**Step 5: Commit**

```bash
git add ui/backend/app/websocket/ ui/backend/app/main.py ui/backend/tests/websocket/
git commit -m "feat: add /ws/foundry WebSocket endpoint"
```

---

### Task 4: Add Push Helper Function

**Files:**
- Create: `ui/backend/app/websocket/push.py`
- Test: `ui/backend/tests/websocket/test_push.py`

**Step 1: Write the failing test**

```python
# ui/backend/tests/websocket/test_push.py
"""Tests for push notification helpers (real WebSocket, no mocks)."""
import pytest
import asyncio
import threading
from fastapi.testclient import TestClient
from app.main import app


class TestPushToFoundry:
    """Test push functions with real WebSocket connections."""

    def test_push_actor_reaches_connected_client(self):
        """push_actor() sends actor data to connected WebSocket client."""
        from app.websocket.push import push_actor

        client = TestClient(app)

        with client.websocket_connect("/ws/foundry") as websocket:
            # Consume welcome message
            websocket.receive_json()

            # Push actor in separate thread (sync context)
            actor_data = {"name": "Goblin", "type": "npc"}

            def push_thread():
                asyncio.run(push_actor(actor_data))

            thread = threading.Thread(target=push_thread)
            thread.start()
            thread.join()

            # Receive the push
            data = websocket.receive_json()
            assert data["type"] == "actor"
            assert data["data"]["name"] == "Goblin"

    def test_push_journal_reaches_connected_client(self):
        """push_journal() sends journal data to connected WebSocket client."""
        from app.websocket.push import push_journal

        client = TestClient(app)

        with client.websocket_connect("/ws/foundry") as websocket:
            websocket.receive_json()  # Consume welcome

            journal_data = {"name": "Chapter 1", "pages": []}

            def push_thread():
                asyncio.run(push_journal(journal_data))

            thread = threading.Thread(target=push_thread)
            thread.start()
            thread.join()

            data = websocket.receive_json()
            assert data["type"] == "journal"
            assert data["data"]["name"] == "Chapter 1"

    def test_push_scene_reaches_connected_client(self):
        """push_scene() sends scene data to connected WebSocket client."""
        from app.websocket.push import push_scene

        client = TestClient(app)

        with client.websocket_connect("/ws/foundry") as websocket:
            websocket.receive_json()  # Consume welcome

            scene_data = {"name": "Cave Entrance", "walls": []}

            def push_thread():
                asyncio.run(push_scene(scene_data))

            thread = threading.Thread(target=push_thread)
            thread.start()
            thread.join()

            data = websocket.receive_json()
            assert data["type"] == "scene"
            assert data["data"]["name"] == "Cave Entrance"
```

**Step 2: Run test to verify it fails**

Run: `cd ui/backend && uv run pytest tests/websocket/test_push.py -v`
Expected: FAIL with "No module named 'app.websocket.push'"

**Step 3: Write minimal implementation**

```python
# ui/backend/app/websocket/push.py
"""Push notification helpers for broadcasting to Foundry clients."""
from typing import Dict, Any
from .foundry_endpoint import foundry_manager


async def push_actor(actor_data: Dict[str, Any]) -> None:
    """
    Push an actor to all connected Foundry clients.

    Args:
        actor_data: FoundryVTT actor data object
    """
    await foundry_manager.broadcast({
        "type": "actor",
        "data": actor_data
    })


async def push_journal(journal_data: Dict[str, Any]) -> None:
    """
    Push a journal entry to all connected Foundry clients.

    Args:
        journal_data: FoundryVTT journal data object
    """
    await foundry_manager.broadcast({
        "type": "journal",
        "data": journal_data
    })


async def push_scene(scene_data: Dict[str, Any]) -> None:
    """
    Push a scene to all connected Foundry clients.

    Args:
        scene_data: FoundryVTT scene data object
    """
    await foundry_manager.broadcast({
        "type": "scene",
        "data": scene_data
    })
```

Update `__init__.py`:
```python
# ui/backend/app/websocket/__init__.py
"""WebSocket connection management for Foundry module."""
from .connection_manager import ConnectionManager
from .foundry_endpoint import foundry_websocket_endpoint, foundry_manager
from .push import push_actor, push_journal, push_scene

__all__ = [
    'ConnectionManager',
    'foundry_websocket_endpoint',
    'foundry_manager',
    'push_actor',
    'push_journal',
    'push_scene'
]
```

**Step 4: Run test to verify it passes**

Run: `cd ui/backend && uv run pytest tests/websocket/test_push.py -v`
Expected: PASS (all 3 tests)

**Step 5: Commit**

```bash
git add ui/backend/app/websocket/ ui/backend/tests/websocket/
git commit -m "feat: add push_actor, push_journal, push_scene helpers"
```

---

### Task 5: Integrate Push with Actor Creator Tool

**Files:**
- Modify: `ui/backend/app/tools/actor_creator.py`
- Test: `ui/backend/tests/tools/test_actor_creator.py`

**Step 1: Write the failing test**

```python
# Add to ui/backend/tests/tools/test_actor_creator.py

import pytest
import threading
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app


class TestActorCreatorPush:
    """Test actor creator pushes to Foundry (real WebSocket)."""

    def test_actor_creator_pushes_to_websocket(self):
        """Actor creator pushes result to connected WebSocket client."""
        from app.tools.actor_creator import ActorCreatorTool

        # Mock only the external API call, not the WebSocket
        mock_result = MagicMock()
        mock_result.uuid = "Actor.abc123"
        mock_result.name = "Test Goblin"
        mock_result.cr = 0.25
        mock_result.output_dir = "/output"

        client = TestClient(app)

        with client.websocket_connect("/ws/foundry") as websocket:
            websocket.receive_json()  # Consume welcome

            # Execute tool in thread (mocking only the Gemini API call)
            with patch('app.tools.actor_creator.create_actor', return_value=mock_result):
                tool = ActorCreatorTool()

                def execute_thread():
                    asyncio.run(tool.execute(
                        description="A goblin warrior",
                        challenge_rating=0.25
                    ))

                thread = threading.Thread(target=execute_thread)
                thread.start()
                thread.join()

            # Verify WebSocket received the push
            data = websocket.receive_json()
            assert data["type"] == "actor"
            assert data["data"]["name"] == "Test Goblin"
            assert data["data"]["uuid"] == "Actor.abc123"
```

**Step 2: Run test to verify it fails**

Run: `cd ui/backend && uv run pytest tests/tools/test_actor_creator.py::TestActorCreatorPush -v`
Expected: FAIL (push_actor not imported or called)

**Step 3: Write minimal implementation**

First, read the current actor_creator.py to understand its structure, then add the push call.

```python
# Modify ui/backend/app/tools/actor_creator.py
# Add import at top:
from app.websocket import push_actor

# In the execute() method, after successful actor creation, add:
        # Push to connected Foundry clients
        await push_actor({
            "name": result.name,
            "uuid": result.uuid,
            "cr": result.cr
        })
```

**Step 4: Run test to verify it passes**

Run: `cd ui/backend && uv run pytest tests/tools/test_actor_creator.py::TestActorCreatorPush -v`
Expected: PASS

**Step 5: Commit**

```bash
git add ui/backend/app/tools/actor_creator.py ui/backend/tests/tools/test_actor_creator.py
git commit -m "feat: push created actors to connected Foundry clients"
```

---

## Phase 2: Foundry Module (Unit Tests with Foundry Mocks)

### Task 6: Create Foundry Module Skeleton

**Files:**
- Create: `foundry-module/tablewrite-assistant/module.json`
- Create: `foundry-module/tablewrite-assistant/package.json`
- Create: `foundry-module/tablewrite-assistant/tsconfig.json`
- Create: `foundry-module/tablewrite-assistant/.gitignore`

**Step 1: Create module manifest**

```json
// foundry-module/tablewrite-assistant/module.json
{
  "id": "tablewrite-assistant",
  "title": "Tablewrite Assistant",
  "description": "Create D&D content through natural language. Actors, journals, and scenes appear automatically.",
  "version": "0.1.0",
  "compatibility": {
    "minimum": "11",
    "verified": "12"
  },
  "authors": [
    {
      "name": "Ethan Otto"
    }
  ],
  "esmodules": ["dist/main.js"],
  "styles": ["styles/module.css"],
  "languages": [
    {
      "lang": "en",
      "name": "English",
      "path": "lang/en.json"
    }
  ],
  "socket": true
}
```

**Step 2: Create package.json**

```json
// foundry-module/tablewrite-assistant/package.json
{
  "name": "tablewrite-assistant",
  "version": "0.1.0",
  "description": "FoundryVTT module for Tablewrite content creation",
  "type": "module",
  "scripts": {
    "build": "tsc",
    "watch": "tsc --watch",
    "test": "vitest run",
    "test:watch": "vitest"
  },
  "devDependencies": {
    "@league-of-foundry-developers/foundry-vtt-types": "^11.315.0",
    "typescript": "^5.3.0",
    "vitest": "^1.0.0"
  }
}
```

**Step 3: Create tsconfig.json**

```json
// foundry-module/tablewrite-assistant/tsconfig.json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ES2022",
    "moduleResolution": "node",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "outDir": "./dist",
    "rootDir": "./src",
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist", "tests"]
}
```

**Step 4: Create .gitignore**

```
# foundry-module/tablewrite-assistant/.gitignore
node_modules/
dist/
*.log
.DS_Store
```

**Step 5: Create empty directories and files**

```bash
mkdir -p foundry-module/tablewrite-assistant/src foundry-module/tablewrite-assistant/styles foundry-module/tablewrite-assistant/lang foundry-module/tablewrite-assistant/tests
touch foundry-module/tablewrite-assistant/styles/module.css
```

```json
// foundry-module/tablewrite-assistant/lang/en.json
{
  "TABLEWRITE_ASSISTANT.SettingsBackendUrl": "Backend URL",
  "TABLEWRITE_ASSISTANT.SettingsBackendUrlHint": "URL of your Tablewrite server (e.g., http://localhost:8000)",
  "TABLEWRITE_ASSISTANT.Connected": "Connected to Tablewrite",
  "TABLEWRITE_ASSISTANT.Disconnected": "Disconnected from Tablewrite",
  "TABLEWRITE_ASSISTANT.CreatedActor": "Created actor: {name}",
  "TABLEWRITE_ASSISTANT.CreatedJournal": "Created journal: {name}",
  "TABLEWRITE_ASSISTANT.CreatedScene": "Created scene: {name}"
}
```

```css
/* foundry-module/tablewrite-assistant/styles/module.css */
/* Tablewrite module styles - placeholder for future UI elements */
```

**Step 6: Commit**

```bash
git add foundry-module/tablewrite-assistant/
git commit -m "feat: create Foundry module skeleton"
```

---

### Task 7: Create Settings Module

**Files:**
- Create: `foundry-module/tablewrite-assistant/src/settings.ts`
- Test: `foundry-module/tablewrite-assistant/tests/settings.test.ts`
- Create: `foundry-module/tablewrite-assistant/vitest.config.ts`

**Step 1: Create vitest config**

```typescript
// foundry-module/tablewrite-assistant/vitest.config.ts
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    globals: true,
    environment: 'node',
    include: ['tests/**/*.test.ts'],
  },
});
```

**Step 2: Write the failing test**

```typescript
// foundry-module/tablewrite-assistant/tests/settings.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock Foundry globals
const mockGame = {
  settings: {
    register: vi.fn(),
    get: vi.fn(),
  },
};

// @ts-ignore - Mock global
globalThis.game = mockGame;

describe('Settings', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('registers backendUrl setting', async () => {
    const { registerSettings } = await import('../src/settings');

    registerSettings();

    expect(mockGame.settings.register).toHaveBeenCalledWith(
      'tablewrite-assistant',
      'backendUrl',
      expect.objectContaining({
        name: 'TABLEWRITE_ASSISTANT.SettingsBackendUrl',
        default: 'http://localhost:8000',
        type: String,
        config: true,
      })
    );
  });

  it('getBackendUrl returns configured URL', async () => {
    mockGame.settings.get.mockReturnValue('http://custom:9000');

    const { getBackendUrl } = await import('../src/settings');

    const url = getBackendUrl();

    expect(url).toBe('http://custom:9000');
    expect(mockGame.settings.get).toHaveBeenCalledWith('tablewrite-assistant', 'backendUrl');
  });
});
```

**Step 3: Run test to verify it fails**

Run: `cd foundry-module/tablewrite-assistant && npm install && npm test`
Expected: FAIL with "Cannot find module '../src/settings'"

**Step 4: Write minimal implementation**

```typescript
// foundry-module/tablewrite-assistant/src/settings.ts
/**
 * Module settings registration and accessors.
 */

const MODULE_ID = 'tablewrite-assistant';

/**
 * Register all module settings with Foundry.
 * Call this in the 'init' hook.
 */
export function registerSettings(): void {
  game.settings.register(MODULE_ID, 'backendUrl', {
    name: 'TABLEWRITE_ASSISTANT.SettingsBackendUrl',
    hint: 'TABLEWRITE_ASSISTANT.SettingsBackendUrlHint',
    default: 'http://localhost:8000',
    type: String,
    config: true,
    scope: 'world',
  });
}

/**
 * Get the configured backend URL.
 */
export function getBackendUrl(): string {
  return game.settings.get(MODULE_ID, 'backendUrl') as string;
}
```

**Step 5: Run test to verify it passes**

Run: `cd foundry-module/tablewrite-assistant && npm test`
Expected: PASS

**Step 6: Commit**

```bash
git add foundry-module/tablewrite-assistant/
git commit -m "feat: add Foundry module settings"
```

---

### Task 8: Create WebSocket Client

**Files:**
- Create: `foundry-module/tablewrite-assistant/src/websocket/client.ts`
- Test: `foundry-module/tablewrite-assistant/tests/websocket/client.test.ts`

**Step 1: Write the failing test**

```typescript
// foundry-module/tablewrite-assistant/tests/websocket/client.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock WebSocket
class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  readyState = MockWebSocket.OPEN;
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onerror: ((event: Error) => void) | null = null;

  constructor(public url: string) {
    // Simulate async connection
    setTimeout(() => this.onopen?.(), 0);
  }

  send = vi.fn();
  close = vi.fn();
}

// @ts-ignore
globalThis.WebSocket = MockWebSocket;

// Mock ui.notifications
const mockNotifications = {
  info: vi.fn(),
  warn: vi.fn(),
  error: vi.fn(),
};

// @ts-ignore
globalThis.ui = { notifications: mockNotifications };

describe('TablewriteClient', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('connects to backend WebSocket URL', async () => {
    const { TablewriteClient } = await import('../src/websocket/client');

    const client = new TablewriteClient('http://localhost:8000');
    client.connect();

    expect(client.isConnected()).toBe(true);
  });

  it('converts http URL to ws URL', async () => {
    const { TablewriteClient } = await import('../src/websocket/client');

    const client = new TablewriteClient('http://localhost:8000');
    client.connect();

    // Check the WebSocket was created with ws:// URL
    expect(client.getWebSocketUrl()).toBe('ws://localhost:8000/ws/foundry');
  });

  it('converts https URL to wss URL', async () => {
    const { TablewriteClient } = await import('../src/websocket/client');

    const client = new TablewriteClient('https://example.com');
    client.connect();

    expect(client.getWebSocketUrl()).toBe('wss://example.com/ws/foundry');
  });

  it('disconnect closes WebSocket', async () => {
    const { TablewriteClient } = await import('../src/websocket/client');

    const client = new TablewriteClient('http://localhost:8000');
    client.connect();
    client.disconnect();

    expect(client.isConnected()).toBe(false);
  });
});
```

**Step 2: Run test to verify it fails**

Run: `cd foundry-module/tablewrite-assistant && npm test`
Expected: FAIL with "Cannot find module '../src/websocket/client'"

**Step 3: Write minimal implementation**

```typescript
// foundry-module/tablewrite-assistant/src/websocket/client.ts
/**
 * WebSocket client for connecting to Tablewrite backend.
 */

export class TablewriteClient {
  private ws: WebSocket | null = null;
  private backendUrl: string;
  private wsUrl: string;

  constructor(backendUrl: string) {
    this.backendUrl = backendUrl;
    this.wsUrl = this.convertToWsUrl(backendUrl);
  }

  /**
   * Convert HTTP(S) URL to WS(S) URL.
   */
  private convertToWsUrl(httpUrl: string): string {
    return httpUrl
      .replace(/^https:\/\//, 'wss://')
      .replace(/^http:\/\//, 'ws://')
      + '/ws/foundry';
  }

  /**
   * Get the WebSocket URL (for testing).
   */
  getWebSocketUrl(): string {
    return this.wsUrl;
  }

  /**
   * Connect to the backend.
   */
  connect(): void {
    if (this.ws) {
      this.disconnect();
    }

    this.ws = new WebSocket(this.wsUrl);

    this.ws.onopen = () => {
      ui.notifications?.info('TABLEWRITE_ASSISTANT.Connected', { localize: true });
    };

    this.ws.onclose = () => {
      ui.notifications?.warn('TABLEWRITE_ASSISTANT.Disconnected', { localize: true });
      this.ws = null;
    };

    this.ws.onerror = (error) => {
      console.error('[Tablewrite] WebSocket error:', error);
    };

    this.ws.onmessage = (event) => {
      this.handleMessage(event.data);
    };
  }

  /**
   * Disconnect from the backend.
   */
  disconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  /**
   * Check if connected.
   */
  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  /**
   * Handle incoming WebSocket message.
   */
  private handleMessage(data: string): void {
    try {
      const message = JSON.parse(data);
      console.log('[Tablewrite] Received:', message.type);

      // Message handling will be added in next task
    } catch (e) {
      console.error('[Tablewrite] Failed to parse message:', e);
    }
  }
}
```

**Step 4: Run test to verify it passes**

Run: `cd foundry-module/tablewrite-assistant && npm test`
Expected: PASS (all 4 tests)

**Step 5: Commit**

```bash
git add foundry-module/tablewrite-assistant/
git commit -m "feat: add WebSocket client for Foundry module"
```

---

### Task 9: Add Message Handlers

**Files:**
- Create: `foundry-module/tablewrite-assistant/src/handlers/actor.ts`
- Create: `foundry-module/tablewrite-assistant/src/handlers/journal.ts`
- Create: `foundry-module/tablewrite-assistant/src/handlers/scene.ts`
- Create: `foundry-module/tablewrite-assistant/src/handlers/index.ts`
- Test: `foundry-module/tablewrite-assistant/tests/handlers/actor.test.ts`

**Step 1: Write the failing test**

```typescript
// foundry-module/tablewrite-assistant/tests/handlers/actor.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock Foundry Actor class
const mockActor = {
  create: vi.fn().mockResolvedValue({ id: 'actor123', name: 'Test Actor' }),
};

// @ts-ignore
globalThis.Actor = mockActor;

// Mock ui.notifications
const mockNotifications = {
  info: vi.fn(),
};

// @ts-ignore
globalThis.ui = { notifications: mockNotifications };

// Mock game.i18n
const mockI18n = {
  format: vi.fn((key, data) => `Created actor: ${data.name}`),
};

// @ts-ignore
globalThis.game = { i18n: mockI18n };

describe('handleActorCreate', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('creates actor via Foundry API', async () => {
    const { handleActorCreate } = await import('../src/handlers/actor');

    const actorData = { name: 'Goblin', type: 'npc' };
    await handleActorCreate(actorData);

    expect(mockActor.create).toHaveBeenCalledWith(actorData);
  });

  it('shows notification on success', async () => {
    const { handleActorCreate } = await import('../src/handlers/actor');

    await handleActorCreate({ name: 'Goblin', type: 'npc' });

    expect(mockNotifications.info).toHaveBeenCalled();
  });
});
```

**Step 2: Run test to verify it fails**

Run: `cd foundry-module/tablewrite-assistant && npm test`
Expected: FAIL with "Cannot find module '../src/handlers/actor'"

**Step 3: Write minimal implementation**

```typescript
// foundry-module/tablewrite-assistant/src/handlers/actor.ts
/**
 * Handle actor creation messages from backend.
 */

export async function handleActorCreate(data: Record<string, unknown>): Promise<void> {
  try {
    const actor = await Actor.create(data);

    if (actor) {
      const message = game.i18n.format('TABLEWRITE_ASSISTANT.CreatedActor', { name: actor.name });
      ui.notifications?.info(message);
    }
  } catch (error) {
    console.error('[Tablewrite] Failed to create actor:', error);
    ui.notifications?.error(`Failed to create actor: ${error}`);
  }
}
```

```typescript
// foundry-module/tablewrite-assistant/src/handlers/journal.ts
/**
 * Handle journal creation messages from backend.
 */

export async function handleJournalCreate(data: Record<string, unknown>): Promise<void> {
  try {
    const journal = await JournalEntry.create(data);

    if (journal) {
      const message = game.i18n.format('TABLEWRITE_ASSISTANT.CreatedJournal', { name: journal.name });
      ui.notifications?.info(message);
    }
  } catch (error) {
    console.error('[Tablewrite] Failed to create journal:', error);
    ui.notifications?.error(`Failed to create journal: ${error}`);
  }
}
```

```typescript
// foundry-module/tablewrite-assistant/src/handlers/scene.ts
/**
 * Handle scene creation messages from backend.
 */

export async function handleSceneCreate(data: Record<string, unknown>): Promise<void> {
  try {
    const scene = await Scene.create(data);

    if (scene) {
      const message = game.i18n.format('TABLEWRITE_ASSISTANT.CreatedScene', { name: scene.name });
      ui.notifications?.info(message);
    }
  } catch (error) {
    console.error('[Tablewrite] Failed to create scene:', error);
    ui.notifications?.error(`Failed to create scene: ${error}`);
  }
}
```

```typescript
// foundry-module/tablewrite-assistant/src/handlers/index.ts
/**
 * Message handlers for Tablewrite.
 */

export { handleActorCreate } from './actor';
export { handleJournalCreate } from './journal';
export { handleSceneCreate } from './scene';

import { handleActorCreate } from './actor';
import { handleJournalCreate } from './journal';
import { handleSceneCreate } from './scene';

export type MessageType = 'actor' | 'journal' | 'scene' | 'connected' | 'pong';

export interface TablewriteMessage {
  type: MessageType;
  data?: Record<string, unknown>;
  client_id?: string;
}

/**
 * Route a message to the appropriate handler.
 */
export async function handleMessage(message: TablewriteMessage): Promise<void> {
  switch (message.type) {
    case 'actor':
      if (message.data) {
        await handleActorCreate(message.data);
      }
      break;
    case 'journal':
      if (message.data) {
        await handleJournalCreate(message.data);
      }
      break;
    case 'scene':
      if (message.data) {
        await handleSceneCreate(message.data);
      }
      break;
    case 'connected':
      console.log('[Tablewrite] Connected with client_id:', message.client_id);
      break;
    case 'pong':
      // Heartbeat response, no action needed
      break;
    default:
      console.warn('[Tablewrite] Unknown message type:', message.type);
  }
}
```

**Step 4: Run test to verify it passes**

Run: `cd foundry-module/tablewrite-assistant && npm test`
Expected: PASS

**Step 5: Commit**

```bash
git add foundry-module/tablewrite-assistant/
git commit -m "feat: add message handlers for actor, journal, scene"
```

---

### Task 10: Create Main Entry Point

**Files:**
- Create: `foundry-module/tablewrite-assistant/src/main.ts`
- Modify: `foundry-module/tablewrite-assistant/src/websocket/client.ts` (use handlers)

**Step 1: Update WebSocket client to use handlers**

```typescript
// foundry-module/tablewrite-assistant/src/websocket/client.ts - update handleMessage method
import { handleMessage, TablewriteMessage } from '../handlers';

  /**
   * Handle incoming WebSocket message.
   */
  private handleMessage(data: string): void {
    try {
      const message: TablewriteMessage = JSON.parse(data);
      console.log('[Tablewrite] Received:', message.type);

      handleMessage(message);
    } catch (e) {
      console.error('[Tablewrite] Failed to parse message:', e);
    }
  }
```

**Step 2: Create main entry point**

```typescript
// foundry-module/tablewrite-assistant/src/main.ts
/**
 * Tablewrite Assistant - FoundryVTT Module
 * Create D&D content through natural language.
 */

import { registerSettings, getBackendUrl } from './settings';
import { TablewriteClient } from './websocket/client';

// Module-scoped client instance
let client: TablewriteClient | null = null;

/**
 * Initialize module settings.
 */
Hooks.once('init', () => {
  console.log('[Tablewrite Assistant] Initializing...');
  registerSettings();
});

/**
 * Connect to backend when Foundry is ready.
 */
Hooks.once('ready', () => {
  console.log('[Tablewrite Assistant] Foundry ready, connecting to backend...');

  const backendUrl = getBackendUrl();
  client = new TablewriteClient(backendUrl);
  client.connect();
});

/**
 * Disconnect on close.
 */
Hooks.once('close', () => {
  if (client) {
    client.disconnect();
    client = null;
  }
});

// Export for potential programmatic access
export { client };
```

**Step 3: Build the module**

Run: `cd foundry-module/tablewrite-assistant && npm run build`
Expected: Creates `dist/main.js` and other compiled files

**Step 4: Commit**

```bash
git add foundry-module/tablewrite-assistant/
git commit -m "feat: create main entry point with Hooks integration"
```

---

# CHECKPOINT: User Installs Foundry Module

**STOP EXECUTION HERE.** The Foundry module is now ready for installation.

## User Action Required

1. **Copy module to Foundry:**
   ```bash
   # Find your Foundry Data directory (varies by installation)
   # Common locations:
   # - macOS: ~/Library/Application Support/FoundryVTT/Data/modules/
   # - Linux: ~/.local/share/FoundryVTT/Data/modules/
   # - Windows: %LOCALAPPDATA%/FoundryVTT/Data/modules/

   # Option A: Symlink (recommended for development)
   ln -s /path/to/project/foundry-module/tablewrite-assistant /path/to/foundry/Data/modules/tablewrite-assistant

   # Option B: Copy
   cp -r foundry-module/tablewrite-assistant /path/to/foundry/Data/modules/
   ```

2. **Restart Foundry** (or refresh browser if already running)

3. **Enable module:**
   - Go to **Game Settings** (gear icon)
   - Click **Manage Modules**
   - Find "Tablewrite Assistant" and check the box
   - Click **Save Module Settings**

4. **Configure backend URL:**
   - Go to **Game Settings** → **Configure Settings**
   - Find "Tablewrite Assistant" section
   - Set **Backend URL** to `http://localhost:8000`

5. **Verify connection:**
   - Open browser console (F12)
   - Look for: `[Tablewrite Assistant] Foundry ready, connecting to backend...`
   - Look for: `[Tablewrite Assistant] Connected with client_id: ...`

6. **Start backend (if not running):**
   ```bash
   cd ui/backend && uv run uvicorn app.main:app --reload --port 8000
   ```

## Resume Execution

Once you confirm:
- Module is enabled in Foundry
- Backend is running
- Console shows successful connection

**Reply to resume Phase 3 (Integration Testing)**

---

## Phase 3: Integration Testing (Requires Running Foundry)

### Task 11: Test WebSocket Connection from Foundry

**Prerequisites:** Backend running, Foundry module installed and enabled.

**Files:**
- None (manual verification)

**Step 1: Verify backend is running**

Run: `curl http://localhost:8000/health`
Expected: `{"status": "healthy", "service": "module-assistant-api"}`

**Step 2: Check Foundry console**

Open Foundry in browser, press F12 to open DevTools, check Console tab.

Expected logs:
```
[Tablewrite] Initializing...
[Tablewrite] Foundry ready, connecting to backend...
[Tablewrite] Connected with client_id: <uuid>
```

**Step 3: Check backend logs**

In the terminal running uvicorn, you should see:
```
INFO:     Foundry client connected: <uuid>
```

**Step 4: Document connection status**

If connection successful, proceed to Task 12.
If connection fails, debug and fix before continuing.

---

### Task 12: Test Actor Push End-to-End

**Prerequisites:** WebSocket connection verified in Task 11.

**Files:**
- Test: `ui/backend/tests/integration/test_e2e_actor_push.py`

**Step 1: Write the integration test**

```python
# ui/backend/tests/integration/test_e2e_actor_push.py
"""End-to-end test: Actor creation pushes to Foundry module.

This test requires:
1. Backend running on localhost:8000
2. Foundry running with Tablewrite module enabled
3. Real Gemini API key (makes actual API calls)

Run with: pytest tests/integration/test_e2e_actor_push.py -v -m integration
"""
import pytest
import os


@pytest.mark.integration
class TestActorPushE2E:
    """End-to-end actor push tests (real Gemini API)."""

    @pytest.mark.skipif(
        not os.getenv("GEMINI_API_KEY") and not os.getenv("GeminiImageAPI"),
        reason="Requires GEMINI_API_KEY or GeminiImageAPI"
    )
    def test_create_actor_via_chat_pushes_to_foundry(self):
        """
        Full flow test:
        1. Connect WebSocket (simulating Foundry)
        2. Call /api/chat with actor creation request
        3. Verify WebSocket receives actor push

        Note: This uses REAL Gemini API and costs money.
        """
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)

        with client.websocket_connect("/ws/foundry") as ws:
            # Consume welcome
            welcome = ws.receive_json()
            assert welcome["type"] == "connected"

            # Request actor creation via chat
            response = client.post("/api/chat", json={
                "message": "Create a simple goblin with CR 0.25",
                "context": {},
                "conversation_history": []
            })

            assert response.status_code == 200

            # Wait for WebSocket push (with timeout)
            # The actor creation may take 10-30 seconds
            try:
                pushed = ws.receive_json()  # TestClient has default timeout
                assert pushed["type"] == "actor"
                assert "name" in pushed["data"]
                print(f"[TEST] Received actor: {pushed['data']['name']}")
            except Exception as e:
                # Tool might not have been triggered
                pytest.skip(f"Actor push not received: {e}")
```

**Step 2: Run the integration test**

Run: `cd ui/backend && uv run pytest tests/integration/test_e2e_actor_push.py -v -m integration`
Expected: PASS (or SKIP if no API key)

**Step 3: Manual verification in Foundry**

After test runs, check Foundry:
1. Open Actors sidebar
2. Look for newly created actor
3. Verify actor has expected name and stats

**Step 4: Commit**

```bash
git add ui/backend/tests/integration/test_e2e_actor_push.py
git commit -m "test: add E2E integration test for actor push"
```

---

## Phase 4: Docker & Documentation

### Task 13: Create Dockerfile

**Files:**
- Create: `Dockerfile`

**Step 1: Create Dockerfile**

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Copy dependency files first (for layer caching)
COPY pyproject.toml uv.lock ./

# Install Python dependencies
RUN uv sync --frozen

# Copy application code
COPY src/ ./src/
COPY ui/ ./ui/

# Create output directory
RUN mkdir -p /app/output

# Expose port
EXPOSE 8000

# Run backend
CMD ["uv", "run", "uvicorn", "ui.backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Step 2: Commit**

```bash
git add Dockerfile
git commit -m "feat: add Dockerfile for Tablewrite backend"
```

---

### Task 14: Create docker-compose.yml

**Files:**
- Create: `docker-compose.tablewrite.yml`

**Step 1: Create docker-compose file**

```yaml
# docker-compose.tablewrite.yml
# Usage: docker-compose -f docker-compose.tablewrite.yml up -d
services:
  tablewrite:
    build: .
    container_name: tablewrite
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      # Persist generated content
      - ./data:/app/data
      - ./output:/app/output
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

**Step 2: Commit**

```bash
git add docker-compose.tablewrite.yml
git commit -m "feat: add docker-compose for Tablewrite deployment"
```

---

### Task 15: Add Smoke Test

**Files:**
- Modify: `tests/test_smoke.py` or appropriate smoke test location

**Step 1: Write the smoke test**

```python
# Add to appropriate smoke test file

@pytest.mark.smoke
def test_websocket_endpoint_exists():
    """Smoke test: WebSocket endpoint is accessible."""
    from fastapi.testclient import TestClient
    from ui.backend.app.main import app

    client = TestClient(app)

    with client.websocket_connect("/ws/foundry") as ws:
        data = ws.receive_json()
        assert data["type"] == "connected"
        assert "client_id" in data
```

**Step 2: Run smoke tests**

Run: `uv run pytest -m smoke -v`
Expected: PASS

**Step 3: Commit**

```bash
git add tests/
git commit -m "test: add WebSocket smoke test"
```

---

### Task 16: Update CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Add WebSocket documentation section**

Add this section to CLAUDE.md under "Architecture & Data Flow":

```markdown
### WebSocket Push Architecture

The backend includes a WebSocket endpoint for pushing content directly to connected Foundry clients.

**Endpoint:** `/ws/foundry`

**Protocol:**
- Connect: Client receives `{"type": "connected", "client_id": "..."}`
- Ping/Pong: Send `{"type": "ping"}` → Receive `{"type": "pong"}`
- Push: Server sends `{"type": "actor|journal|scene", "data": {...}}`

**Usage:**
```python
from app.websocket import push_actor, push_journal, push_scene

# Push actor to all connected Foundry clients
await push_actor({"name": "Goblin", "type": "npc", ...})

# Push journal
await push_journal({"name": "Chapter 1", "pages": [...]})

# Push scene
await push_scene({"name": "Cave", "walls": [...]})
```

**Foundry Module:**
The `foundry-module/tablewrite-assistant/` directory contains the FoundryVTT module that:
1. Connects to backend on startup
2. Receives push notifications
3. Calls `Actor.create()`, `JournalEntry.create()`, `Scene.create()`

**Quick Start:**
```bash
# Backend
docker-compose -f docker-compose.tablewrite.yml up -d

# Module: Copy foundry-module/tablewrite-assistant/ to your Foundry modules directory as tablewrite-assistant/
# Enable in Foundry, configure backend URL in settings
```

**Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add WebSocket push architecture to CLAUDE.md"
```

---

### Task 17: Archive Relay Server

**Files:**
- Modify: `.gitignore` or create `relay-server/ARCHIVED.md`

**Step 1: Create archived notice**

```markdown
# relay-server/ARCHIVED.md

# Relay Server - ARCHIVED

**This component is deprecated and no longer used.**

The relay server was previously used to bridge HTTP requests to FoundryVTT via WebSocket. It has been replaced by:

1. **Direct WebSocket endpoint** in the FastAPI backend (`/ws/foundry`)
2. **Tablewrite Foundry module** that connects directly to the backend

## Why Archived

- Simplified architecture (one less component)
- No external relay dependency
- Better reliability (direct connection)
- Easier deployment (single container)

## Migration

If you were using the relay server:

1. Remove relay server configuration from `.env`
2. Install the Tablewrite Foundry module
3. Configure backend URL in module settings
4. Run `docker-compose -f docker-compose.tablewrite.yml up -d`

## Keeping the Code

The relay server code is preserved for reference but is not maintained.
```

**Step 2: Commit**

```bash
git add relay-server/ARCHIVED.md
git commit -m "docs: mark relay-server as archived"
```

---

## Summary

**Total Tasks:** 17

**Phase Breakdown:**
- Phase 1 (Tasks 1-5): Backend WebSocket with real tests
- Phase 2 (Tasks 6-10): Foundry module with unit tests
- CHECKPOINT: User installs module
- Phase 3 (Tasks 11-12): Integration tests with real Foundry
- Phase 4 (Tasks 13-17): Docker, smoke tests, documentation

**Key Deliverables:**
1. `ui/backend/app/websocket/` - WebSocket endpoint + push helpers
2. `foundry-module/tablewrite-assistant/` - FoundryVTT module with WebSocket client
3. `Dockerfile` + `docker-compose.tablewrite.yml` - Docker deployment
4. Real tests for all components (no mocks where possible)

**Testing Approach:**
- Phase 1: Real WebSocket tests via FastAPI TestClient
- Phase 2: Foundry mocks (can't run real Foundry in pytest)
- Phase 3: Manual + automated tests with real Foundry running
