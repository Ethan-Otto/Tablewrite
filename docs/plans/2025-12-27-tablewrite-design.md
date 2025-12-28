# Tablewrite Design Document

**Date:** 2025-12-27
**Status:** Approved
**Module Name:** Tablewrite

---

## Overview

Tablewrite is a FoundryVTT module + backend system that enables GMs to create D&D content through natural language. Users describe what they want, and it appears in Foundry automatically.

**Core capabilities:**
- PDF → Module (journals, actors, scenes)
- Chat & Edit (interactive refinement)
- Create (actors from descriptions)
- Battlemap Creator (maps → scenes with walls)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      WEB UI (React/TypeScript)              │
│  Chat, Edit, Create actors, Process PDFs, Battlemap tools  │
└─────────────────────────────────────────────────────────────┘
                            │ HTTP
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                 BACKEND (FastAPI + WebSocket)               │
│  - Existing ui/backend/ + src/ processing                   │
│  - WebSocket endpoint for Foundry module                    │
│  - Gemini API calls, PDF processing, wall detection         │
└─────────────────────────────────────────────────────────────┘
                            ▲ WebSocket (persistent)
                            │
┌─────────────────────────────────────────────────────────────┐
│              FOUNDRY MODULE (TypeScript)                    │
│  - Connects to backend on startup                           │
│  - Receives push notifications                              │
│  - Calls Actor.create(), Scene.create(), etc.               │
│  - Settings: backend URL, optional API key                  │
└─────────────────────────────────────────────────────────────┘
```

**Key insight:** WebSocket goes FROM Foundry TO backend (browser-allowed direction), enabling the backend to push content through that connection.

**User flow:**
1. User runs Docker (`docker-compose up`) - backend starts
2. User opens Foundry - module connects via WebSocket
3. User works in Web UI - creates content, processes PDFs
4. Content appears in Foundry automatically (creation = permission)

---

## Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Primary user | Personal + sharable with GMs | Start with own use, make easy to share |
| MVP scope | Everything | All features from day one |
| Interaction model | Web UI primary, Foundry receives | Web UI allows richer UX than Foundry dialogs |
| Connection method | WebSocket push | Automatic, no extra clicks |
| Backend hosting (MVP) | Users self-host (Docker) | No hosting costs, plan for hosted later |
| Authentication | No auth for localhost | Self-hosted is trusted |
| Credentials | Both .env and module settings | Flexible - power users use .env, others use UI |
| Module language | TypeScript | Better DX, autocomplete, error catching |
| Module name | Tablewrite | Unique, searchable, clear meaning |

---

## Backend Changes

Minimal changes to existing `ui/backend/`. Add one WebSocket endpoint.

**New file: `ui/backend/app/websocket.py`**

```python
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict
import uuid

# Track connected Foundry clients
foundry_connections: Dict[str, WebSocket] = {}

@app.websocket("/ws/foundry")
async def foundry_websocket(websocket: WebSocket):
    await websocket.accept()
    client_id = str(uuid.uuid4())
    foundry_connections[client_id] = websocket

    try:
        while True:
            data = await websocket.receive_json()

            # Handle auth with API key from module
            if data.get("type") == "auth":
                # Store API key for this connection if not in .env
                pass

    except WebSocketDisconnect:
        del foundry_connections[client_id]

async def push_to_foundry(content: dict):
    """Push content to all connected Foundry clients"""
    for ws in foundry_connections.values():
        await ws.send_json(content)
```

**Integration with existing tools:**

When content is created, automatically push to Foundry:

```python
@app.post("/api/actors/create")
async def create_actor(...):
    actor_data = await generate_actor(...)

    # Creation = permission to push
    await push_to_foundry({
        "type": "actor",
        "data": actor_data
    })

    return actor_data
```

---

## Foundry Module Structure

```
tablewrite/
├── module.json              # Manifest
├── src/
│   ├── main.ts              # Entry point, hooks
│   ├── settings.ts          # Backend URL, API key config
│   ├── websocket/
│   │   └── client.ts        # WebSocket connection manager
│   └── handlers/
│       ├── actor.ts         # Actor.create() logic
│       ├── journal.ts       # JournalEntry.create() logic
│       └── scene.ts         # Scene.create() with walls
├── styles/
│   └── module.css
└── lang/
    └── en.json
```

**Entry point:**

```typescript
// src/main.ts
Hooks.once('ready', () => {
  const backendUrl = game.settings.get('tablewrite', 'backendUrl');
  TablewriteClient.connect(backendUrl);
});
```

**WebSocket client:**

```typescript
// src/websocket/client.ts
class TablewriteClient {
  static connect(url: string) {
    const ws = new WebSocket(`${url}/ws/foundry`);

    ws.onopen = () => {
      // Send API key if configured in module
      const apiKey = game.settings.get('tablewrite', 'geminiApiKey');
      if (apiKey) {
        ws.send(JSON.stringify({ type: 'auth', apiKey }));
      }
    };

    ws.onmessage = async (event) => {
      const message = JSON.parse(event.data);

      switch (message.type) {
        case 'actor':
          await Actor.create(message.data);
          ui.notifications.info(`Created actor: ${message.data.name}`);
          break;
        case 'journal':
          await JournalEntry.create(message.data);
          ui.notifications.info(`Created journal: ${message.data.name}`);
          break;
        case 'scene':
          await Scene.create(message.data);
          ui.notifications.info(`Created scene: ${message.data.name}`);
          break;
      }
    };
  }
}
```

**Settings:**

```typescript
// src/settings.ts
Hooks.once('init', () => {
  game.settings.register('tablewrite', 'backendUrl', {
    name: 'Backend URL',
    hint: 'URL of your Tablewrite server',
    default: 'http://localhost:8000',
    type: String,
    config: true
  });

  game.settings.register('tablewrite', 'geminiApiKey', {
    name: 'Gemini API Key',
    hint: 'Your Google Gemini API key (optional if set in .env)',
    default: '',
    type: String,
    config: true,
    scope: 'world'  // Only GM sees this
  });
});
```

---

## Docker Deployment

**Dockerfile:**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy project
COPY pyproject.toml uv.lock ./
COPY src/ ./src/
COPY ui/ ./ui/

# Install dependencies
RUN uv sync

# Expose port
EXPOSE 8000

# Run backend
CMD ["uv", "run", "uvicorn", "ui.backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**docker-compose.yml:**

```yaml
services:
  tablewrite:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./data:/app/data
      - ./output:/app/output
```

**.env.example:**

```bash
# Optional: Set here OR in Foundry module settings
GEMINI_API_KEY=your_key_here

# Optional: Model selection
GEMINI_MODEL=gemini-2.0-flash
```

**User setup:**

```bash
git clone https://github.com/you/tablewrite
cp .env.example .env
# Edit .env OR configure API key in Foundry module
docker-compose up -d
# Install Foundry module, set backend URL to http://localhost:8000
```

---

## Testing Strategy

### Backend Tests (Python - pytest)

```python
# tests/websocket/test_foundry_ws.py
def test_websocket_connection():
    """Module can connect via WebSocket"""
    with client.websocket_connect("/ws/foundry") as ws:
        ws.send_json({"type": "auth", "apiKey": "test-key"})

def test_push_to_foundry():
    """Content pushed to connected clients"""
    with client.websocket_connect("/ws/foundry") as ws:
        client.post("/api/actors/create", json={...})

        data = ws.receive_json()
        assert data["type"] == "actor"
        assert data["data"]["name"] == "Goblin"
```

### Module Tests (TypeScript - Vitest)

```typescript
// tablewrite/tests/handlers/actor.test.ts
global.Actor = { create: vi.fn() };
global.ui = { notifications: { info: vi.fn() } };

test('creates actor from WebSocket message', async () => {
  const message = { type: 'actor', data: { name: 'Goblin', type: 'npc' } };

  await handleActorCreate(message.data);

  expect(Actor.create).toHaveBeenCalledWith(
    expect.objectContaining({ name: 'Goblin' })
  );
});
```

### Integration Tests (real Gemini)

```python
@pytest.mark.integration
def test_actor_creation_e2e():
    """Full flow: description → Gemini → Foundry format"""
    with client.websocket_connect("/ws/foundry") as ws:
        ws.send_json({"type": "auth", "apiKey": os.getenv("GEMINI_API_KEY")})

        response = client.post("/api/actors/create", json={
            "description": "A goblin warrior",
            "cr": 0.25
        })

        pushed = ws.receive_json()
        assert pushed["data"]["name"]
```

---

## Migration Path

### Stays the Same

| Component | Location |
|-----------|----------|
| PDF processing | `src/pdf_processing/` |
| Actor extraction | `src/actors/` |
| Wall detection | `src/wall_detection/` |
| Web UI frontend | `ui/frontend/` |
| Web UI backend | `ui/backend/` (add WebSocket) |
| Core API | `src/api.py` |

### New

| Component | Location |
|-----------|----------|
| Foundry module | `tablewrite/` |
| Docker config | `Dockerfile`, `docker-compose.yml` |
| WebSocket endpoint | `ui/backend/app/websocket.py` |

### Removed

| Component | Location |
|-----------|----------|
| Relay server | `relay-server/` |
| FoundryClient WebSocket | `src/foundry/client.py` |
| REST API module dependency | Docs |

### Phase Order

1. Add WebSocket endpoint to backend
2. Build Tablewrite Foundry module
3. Add Docker configuration
4. Test end-to-end
5. Archive/remove relay server

---

## Open Questions (For Later)

- Rate limiting for future hosted backend
- Module distribution (Foundry package manager vs manual)
- Backend/module version compatibility
