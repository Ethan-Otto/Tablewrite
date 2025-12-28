# FoundryVTT Module Architecture: Pull-Based Approach

**Date:** 2025-12-27

**Goal:** Transform the project from an external tool that pushes data into Foundry via a relay server, to a FoundryVTT module that pulls data from a backend API.

**Status:** Proposed

---

## Executive Summary

The current architecture requires users to install a third-party REST API module and run a relay server. This proposal replaces that with a simpler "pull" architecture where a custom Foundry module fetches processed data from a backend API and creates entities directly using Foundry's native API.

---

## Architecture Comparison

### Current Architecture (Push)

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Python App  │────▶│ Relay Server │◀───▶│REST API Mod  │────▶│   Foundry    │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
                      WebSocket queue      3rd party module      Creates actors,
                      You must run this    User must install     journals, etc.
```

**Components:**
1. Python application (processes PDFs, calls Gemini)
2. Relay server (WebSocket bridge, Docker)
3. REST API module (third-party, installed in Foundry)
4. FoundryVTT instance

**Problems:**
- 4 components that must all work together
- User must install third-party module
- Relay server adds complexity and failure points
- WebSocket chain is hard to debug and test
- Push architecture fights against browser security model

### Proposed Architecture (Pull)

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         USER'S BROWSER                                   │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │                    YOUR FOUNDRY MODULE                             │  │
│  │  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │  │
│  │  │   UI Layer   │───▶│  API Client  │───▶│  Foundry API Calls   │  │  │
│  │  │ Upload, Config│    │  fetch()     │    │  Actor.create()      │  │  │
│  │  └──────────────┘    └──────────────┘    │  Scene.create()      │  │  │
│  │                             │            │  JournalEntry.create()│  │  │
│  │                             │            └──────────────────────┘  │  │
│  └─────────────────────────────┼──────────────────────────────────────┘  │
└────────────────────────────────┼─────────────────────────────────────────┘
                                 │ HTTPS
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                         BACKEND API                                      │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────────┐   │
│  │  FastAPI     │───▶│  Processing  │───▶│  Gemini API              │   │
│  │  Endpoints   │    │  Pipeline    │    │  (PDF, actors, scenes)   │   │
│  └──────────────┘    └──────────────┘    └──────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────┘
```

**Components:**
1. Backend API (Python/FastAPI, processes PDFs, calls Gemini)
2. Foundry Module (JavaScript, UI + Foundry API calls)

**Why this works:**
- Browsers can make outbound HTTP requests (fetch) to any server
- Browsers cannot receive incoming connections (why relay was needed)
- Foundry module runs in user's browser, has full access to Foundry API
- No third-party dependencies

---

## Pros and Cons

### Advantages

| Benefit | Description |
|---------|-------------|
| **Simpler user setup** | Install 1 module vs. install module + run relay |
| **Fewer dependencies** | No REST API module required |
| **Fewer failure points** | 2 components vs. 4 components |
| **Easier debugging** | HTTP requests vs. WebSocket chains |
| **Easier testing** | Mock HTTP vs. mock WebSocket |
| **Standard patterns** | fetch() + REST API is well-understood |
| **Works everywhere** | Local Foundry, The Forge, Molten Hosting |
| **Better UX** | Native Foundry UI, progress indicators, settings |

### Disadvantages

| Drawback | Description | Mitigation |
|----------|-------------|------------|
| **Backend must be reachable** | Need network connection to API | Already need internet for Gemini |
| **CORS configuration** | Backend must allow Foundry origins | Standard FastAPI middleware |
| **No background jobs** | Browser must stay open during processing | Add job queue later if needed |
| **Progress updates harder** | Can't push from server to browser | Poll for status, or add WebSocket for progress only |
| **Backend hosting decision** | Where does the API run? | Options: self-host, cloud, serverless |
| **New JavaScript codebase** | Must write Foundry module | Straightforward, well-documented |

### Non-Issues (Previously Thought to be Problems)

| Concern | Why It's Not a Problem |
|---------|------------------------|
| **"Must be online"** | Already required for Gemini API calls |
| **"Doesn't work with The Forge"** | Module runs in user's browser, can reach any public URL |
| **"Large file uploads"** | Standard multipart upload, can show progress |

---

## Infrastructure Options

### Backend Deployment

| Option | Cost | Complexity | Best For |
|--------|------|------------|----------|
| **Your hosted server** | $5-20/mo | Medium | Production, controlled costs |
| **Serverless (Vercel/Cloudflare Workers)** | Pay per use | Low | Variable usage, auto-scaling |
| **User runs locally (Docker)** | Free | User setup | Power users, privacy, development |

### Recommended: Hybrid Approach

```
┌─────────────────────────────────────────────────────────────┐
│                  MODULE SETTINGS                            │
├─────────────────────────────────────────────────────────────┤
│  Backend Mode:                                              │
│    ○ Hosted Service (recommended) - api.dndmodulegen.com   │
│    ○ Local Server - http://localhost:8000                  │
│    ○ Custom URL - [________________]                       │
│                                                             │
│  API Key: [________________] (for local/custom only)       │
└─────────────────────────────────────────────────────────────┘
```

- **Default:** Your hosted backend (easy for most users)
- **Option:** Local Docker (power users, privacy-conscious)
- **Option:** Custom URL (enterprise, self-hosted)

### Backend Architecture

```
backend/
├── app/
│   ├── main.py              # FastAPI application
│   ├── api/
│   │   ├── routes/
│   │   │   ├── process.py   # PDF processing endpoints
│   │   │   ├── actors.py    # Actor generation endpoints
│   │   │   └── health.py    # Health check
│   │   └── deps.py          # Dependencies (Gemini client, etc.)
│   ├── core/
│   │   ├── config.py        # Settings
│   │   └── security.py      # API key validation
│   └── services/
│       └── ...              # Existing src/ code
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

**Key Endpoints:**

```python
# Process PDF and return all data
POST /api/v1/process
Request: multipart/form-data with PDF file
Response: {
  "actors": [...],
  "journals": [...],
  "scenes": [...],
  "items": [...]
}

# Create single actor from description
POST /api/v1/actors
Request: { "description": "A goblin warrior", "cr": 0.25 }
Response: { "actor": {...}, "foundry_format": {...} }

# Check processing status (for long jobs)
GET /api/v1/jobs/{job_id}
Response: { "status": "processing", "progress": 45, "message": "Extracting actors..." }

# Health check
GET /api/v1/health
Response: { "status": "ok", "version": "1.0.0" }
```

### Foundry Module Structure

```
foundry-module/
├── module.json              # Module manifest
├── scripts/
│   ├── main.js              # Entry point, Hooks registration
│   ├── settings.js          # Module settings (backend URL, etc.)
│   ├── ui/
│   │   ├── ImportDialog.js  # Main import dialog
│   │   ├── ProgressBar.js   # Processing progress
│   │   └── ActorCreator.js  # Quick actor creation
│   ├── api/
│   │   └── client.js        # Backend API wrapper
│   └── importers/
│       ├── actors.js        # Actor.create() logic
│       ├── journals.js      # JournalEntry.create() logic
│       └── scenes.js        # Scene.create() logic
├── templates/
│   ├── import-dialog.html
│   ├── progress.html
│   └── settings.html
├── styles/
│   └── module.css
├── lang/
│   └── en.json              # Localization
└── packs/                   # Optional: bundled compendiums
```

**Module Entry Point:**

```javascript
// scripts/main.js
import { ImportDialog } from './ui/ImportDialog.js';
import { registerSettings } from './settings.js';

Hooks.once('init', () => {
  registerSettings();
});

Hooks.once('ready', () => {
  // Add button to sidebar
  game.dndModuleGen = {
    importDialog: new ImportDialog()
  };
});

Hooks.on('getSceneControlButtons', (controls) => {
  controls.push({
    name: 'dnd-module-gen',
    title: 'D&D Module Generator',
    icon: 'fas fa-dragon',
    button: true,
    onClick: () => game.dndModuleGen.importDialog.render(true)
  });
});
```

---

## Testing Strategy

### Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         TESTING PYRAMID                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│                          ┌─────────┐                                    │
│                          │   E2E   │  Playwright + real Foundry        │
│                          └────┬────┘  (optional, slow)                 │
│                       ┌───────┴───────┐                                 │
│                       │  Integration  │  Backend + mocked Foundry      │
│                       └───────┬───────┘  (real HTTP, mocked APIs)      │
│                 ┌─────────────┴─────────────┐                           │
│                 │         Unit Tests        │  Isolated functions      │
│                 └───────────────────────────┘  (fast, no network)      │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Backend Tests (Python - pytest)

**No changes to existing tests.** Backend becomes a pure API that returns JSON.

```python
# tests/api/test_endpoints.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_create_actor():
    response = client.post("/api/v1/actors", json={
        "description": "A goblin warrior",
        "challenge_rating": 0.25
    })
    assert response.status_code == 200
    data = response.json()
    assert "actor" in data
    assert data["actor"]["name"] is not None

@pytest.mark.integration
def test_process_pdf_real():
    """Integration test with real Gemini API"""
    with open("tests/fixtures/test.pdf", "rb") as f:
        response = client.post(
            "/api/v1/process",
            files={"file": ("test.pdf", f, "application/pdf")}
        )
    assert response.status_code == 200
    data = response.json()
    assert "actors" in data
    assert "journals" in data
```

### Foundry Module Tests (JavaScript - Vitest)

**New test suite for the Foundry module:**

```javascript
// foundry-module/tests/unit/transform.test.js
import { describe, it, expect } from 'vitest';
import { transformActorData } from '../../scripts/importers/actors.js';

describe('transformActorData', () => {
  it('transforms backend response to Foundry format', () => {
    const backendData = {
      name: "Goblin",
      hp: 7,
      ac: 15,
      abilities: { str: 8, dex: 14, con: 10, int: 10, wis: 8, cha: 8 }
    };

    const foundryData = transformActorData(backendData);

    expect(foundryData.name).toBe("Goblin");
    expect(foundryData.type).toBe("npc");
    expect(foundryData.system.attributes.hp.value).toBe(7);
    expect(foundryData.system.attributes.ac.flat).toBe(15);
  });
});
```

```javascript
// foundry-module/tests/integration/import.test.js
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { importActors } from '../../scripts/importers/actors.js';

// Mock Foundry globals
const mockActor = {
  create: vi.fn().mockResolvedValue({ id: 'actor123', name: 'Goblin' })
};

const mockUi = {
  notifications: {
    info: vi.fn(),
    error: vi.fn()
  }
};

beforeEach(() => {
  global.Actor = mockActor;
  global.ui = mockUi;
  vi.clearAllMocks();
});

describe('importActors', () => {
  it('creates actors from backend response', async () => {
    const actors = [
      { name: "Goblin", type: "npc", system: { /* ... */ } },
      { name: "Orc", type: "npc", system: { /* ... */ } }
    ];

    const results = await importActors(actors);

    expect(Actor.create).toHaveBeenCalledTimes(2);
    expect(results).toHaveLength(2);
    expect(results[0].id).toBe('actor123');
  });

  it('handles creation errors gracefully', async () => {
    Actor.create.mockRejectedValueOnce(new Error('Validation failed'));

    const actors = [{ name: "Invalid", type: "npc", system: {} }];

    await expect(importActors(actors)).rejects.toThrow('Validation failed');
    expect(ui.notifications.error).toHaveBeenCalled();
  });
});
```

```javascript
// foundry-module/tests/integration/api-client.test.js
import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { ApiClient } from '../../scripts/api/client.js';

// Uses real backend (must be running)
describe('ApiClient Integration', () => {
  let client;

  beforeAll(() => {
    client = new ApiClient('http://localhost:8000');
  });

  it('creates actor from description', async () => {
    const result = await client.createActor({
      description: 'A goblin warrior',
      challengeRating: 0.25
    });

    expect(result.actor.name).toBeDefined();
    expect(result.foundry_format).toBeDefined();
  });
});
```

### E2E Tests (Optional - Playwright)

**Full end-to-end with real Foundry instance:**

```javascript
// e2e/import.spec.js
import { test, expect } from '@playwright/test';

test.describe('PDF Import', () => {
  test.beforeAll(async () => {
    // Ensure backend is running
    // Ensure Foundry is running with module installed
  });

  test('imports PDF and creates actors', async ({ page }) => {
    // Login to Foundry
    await page.goto('http://localhost:30000');
    await page.fill('input[name="userid"]', 'gamemaster');
    await page.click('button[type="submit"]');

    // Open import dialog
    await page.click('[data-control="dnd-module-gen"]');

    // Upload PDF
    const fileInput = await page.locator('input[type="file"]');
    await fileInput.setInputFiles('tests/fixtures/test-adventure.pdf');

    // Start import
    await page.click('button:text("Import")');

    // Wait for completion
    await expect(page.locator('.import-progress')).toContainText('Complete', {
      timeout: 60000
    });

    // Verify actors created
    await page.click('[data-tab="actors"]');
    await expect(page.locator('.directory-item')).toHaveCount.greaterThan(0);
  });
});
```

### Test File Structure

```
project/
├── tests/                              # Python backend tests (existing)
│   ├── conftest.py
│   ├── api/
│   │   ├── test_api.py                 # Existing API tests
│   │   └── test_endpoints.py           # NEW: HTTP endpoint tests
│   ├── actors/
│   ├── foundry/
│   └── fixtures/
│       └── test.pdf
│
├── foundry-module/
│   ├── scripts/
│   ├── tests/                          # NEW: JavaScript tests
│   │   ├── unit/
│   │   │   ├── transform.test.js
│   │   │   └── validation.test.js
│   │   ├── integration/
│   │   │   ├── import.test.js
│   │   │   └── api-client.test.js
│   │   ├── mocks/
│   │   │   └── foundry.js              # Mock Actor, Scene, etc.
│   │   └── setup.js                    # Test setup
│   ├── vitest.config.js
│   └── package.json
│
└── e2e/                                # NEW: Optional E2E tests
    ├── import.spec.js
    ├── playwright.config.js
    └── fixtures/
        └── test-adventure.pdf
```

### Test Commands

```bash
# Backend tests (Python)
uv run pytest                           # Smoke tests
uv run pytest --full                    # Full suite
uv run pytest tests/api/ -v             # API tests only

# Module tests (JavaScript)
cd foundry-module
npm test                                # All JS tests
npm run test:unit                       # Unit tests only
npm run test:integration                # Integration tests

# E2E tests (requires running services)
npm run test:e2e                        # Full E2E
```

### CI/CD Pipeline

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv sync
      - run: uv run pytest

  module:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - run: cd foundry-module && npm ci
      - run: cd foundry-module && npm test

  e2e:
    runs-on: ubuntu-latest
    needs: [backend, module]
    steps:
      - uses: actions/checkout@v4
      - name: Start services
        run: docker-compose up -d
      - name: Run E2E tests
        run: npm run test:e2e
```

---

## Migration Path

### Phase 1: Backend API (Week 1-2)

1. Create FastAPI wrapper around existing `src/api.py`
2. Add CORS middleware
3. Add Dockerfile for main project
4. Add HTTP endpoint tests
5. Deploy to staging (Fly.io or similar)

### Phase 2: Foundry Module Scaffold (Week 2-3)

1. Create module structure
2. Implement settings (backend URL configuration)
3. Create basic UI (import dialog)
4. Implement API client
5. Add unit tests with mocked Foundry

### Phase 3: Import Logic (Week 3-4)

1. Implement actor importer
2. Implement journal importer
3. Implement scene importer (with walls)
4. Add progress indicators
5. Add integration tests

### Phase 4: Polish & Release (Week 4-5)

1. Error handling and user feedback
2. Documentation
3. Module manifest for Foundry package manager
4. E2E tests
5. Production deployment

---

## What Gets Removed

After migration, these components are no longer needed:

| Component | Location | Action |
|-----------|----------|--------|
| Relay server | `relay-server/` | Archive or delete |
| FoundryClient WebSocket logic | `src/foundry/client.py` | Replace with JSON output |
| REST API module dependency | Documentation | Remove from requirements |
| `src/foundry/upload_to_foundry.py` | `src/foundry/` | Replace with endpoint |
| `src/foundry/export_from_foundry.py` | `src/foundry/` | Move to module |

---

## Open Questions

1. **Rate limiting:** How to prevent abuse of hosted backend?
2. **Authentication:** API keys? User accounts? Anonymous access?
3. **Cost model:** Free tier limits? Paid tier for heavy users?
4. **Module distribution:** Foundry package manager? Manual download?
5. **Versioning:** How to handle backend/module version compatibility?

---

## References

- [FoundryVTT Module Development](https://foundryvtt.com/article/module-development/)
- [FoundryVTT API Documentation](https://foundryvtt.com/api/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Vitest Documentation](https://vitest.dev/)
- [DDB-Importer](https://github.com/MrPrimate/ddb-importer) - Similar architecture reference
