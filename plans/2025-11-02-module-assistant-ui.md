# D&D Module Assistant UI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a chat-based UI for D&D module generation with Gemini integration, allowing users to generate scenes, manage actors, and work with module content through slash commands in a fantasy journal aesthetic.

**Architecture:** FastAPI backend integrating with existing module generation pipeline (src/scene_extraction/, src/actors/, src/foundry/). React frontend with shadcn/ui using wax seal variant design. WebSocket connection for streaming Gemini responses. Backend reuses existing GeminiAPI utility and Scene/Actor models.

**Tech Stack:** React, shadcn/ui, Tailwind CSS, FastAPI, WebSockets, Pydantic, existing Gemini utilities

---

## Task 1: Backend Project Setup

**Files:**
- Create: `ui/backend/app/__init__.py`
- Create: `ui/backend/app/main.py`
- Create: `ui/backend/requirements.txt`
- Create: `ui/backend/.env.example`

**Step 1: Create backend directory structure**

```bash
mkdir -p ui/backend/app/{routers,services,models}
touch ui/backend/app/__init__.py
touch ui/backend/app/routers/__init__.py
touch ui/backend/app/services/__init__.py
touch ui/backend/app/models/__init__.py
```

**Step 2: Create requirements.txt**

Create `ui/backend/requirements.txt`:
```txt
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
websockets>=12.0
pydantic>=2.0.0
python-dotenv>=1.0.0
google-genai
aiohttp>=3.9.0
```

**Step 3: Create .env.example**

Create `ui/backend/.env.example`:
```bash
# Gemini API
GEMINI_API_KEY=your_gemini_api_key_here

# FoundryVTT (optional)
FOUNDRY_RELAY_URL=http://localhost:3010
FOUNDRY_API_KEY=
FOUNDRY_CLIENT_ID=

# Module paths
MODULE_OUTPUT_DIR=../../output/runs
MODULE_DATA_DIR=../../data
```

**Step 4: Create main.py with basic FastAPI app**

Create `ui/backend/app/main.py`:
```python
"""D&D Module Assistant API."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="D&D Module Assistant API",
    description="Backend API for D&D module generation and management",
    version="0.1.0"
)

# CORS middleware for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "module-assistant-api"}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "D&D Module Assistant API",
        "docs": "/docs",
        "health": "/health"
    }
```

**Step 5: Test basic FastAPI server**

Run: `cd ui/backend && uvicorn app.main:app --reload --port 8000`

Expected: Server starts on http://localhost:8000, visit http://localhost:8000/docs to see Swagger UI

**Step 6: Commit**

```bash
git add ui/backend/
git commit -m "feat: initialize FastAPI backend for module assistant UI"
```

---

## Task 2: Backend Models

**Files:**
- Create: `ui/backend/app/models/chat.py`
- Create: `ui/backend/app/models/scene.py`

**Step 1: Write test for ChatMessage model**

Create `ui/backend/tests/test_models.py`:
```python
"""Tests for API models."""

import pytest
from app.models.chat import ChatMessage, ChatRole, ChatRequest, ChatResponse


def test_chat_message_creation():
    """Test ChatMessage model creation."""
    msg = ChatMessage(role=ChatRole.USER, content="Hello")
    assert msg.role == ChatRole.USER
    assert msg.content == "Hello"
    assert msg.timestamp is not None


def test_chat_request_validation():
    """Test ChatRequest validates message."""
    req = ChatRequest(message="test message")
    assert req.message == "test message"
    assert req.context == {}


def test_chat_response_creation():
    """Test ChatResponse model."""
    resp = ChatResponse(
        message="Generated response",
        type="text"
    )
    assert resp.message == "Generated response"
    assert resp.type == "text"
    assert resp.data is None
```

**Step 2: Run test to verify it fails**

Run: `cd ui/backend && pytest tests/test_models.py -v`

Expected: FAIL with "ModuleNotFoundError: No module named 'app.models.chat'"

**Step 3: Create chat models**

Create `ui/backend/app/models/chat.py`:
```python
"""Chat models for D&D Module Assistant."""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class ChatRole(str, Enum):
    """Chat message role."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatMessage(BaseModel):
    """Single chat message."""
    role: ChatRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)


class ChatRequest(BaseModel):
    """Request to chat endpoint."""
    message: str = Field(..., min_length=1, max_length=10000)
    context: Dict[str, Any] = Field(default_factory=dict)
    conversation_history: List[ChatMessage] = Field(default_factory=list)


class ChatResponse(BaseModel):
    """Response from chat endpoint."""
    message: str
    type: str  # "text", "scene", "list", "error"
    data: Optional[Dict[str, Any]] = None
    scene: Optional[Any] = None  # Will reference Scene model
```

**Step 4: Run test to verify it passes**

Run: `cd ui/backend && pytest tests/test_models.py::test_chat_message_creation -v`

Expected: PASS

**Step 5: Create scene models**

Create `ui/backend/app/models/scene.py`:
```python
"""Scene models - reusing existing Scene from src/scene_extraction."""

import sys
from pathlib import Path

# Add project src to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from scene_extraction.models import Scene, ChapterContext  # noqa: E402

__all__ = ["Scene", "ChapterContext"]
```

**Step 6: Test scene model import**

Add to `ui/backend/tests/test_models.py`:
```python
from app.models.scene import Scene


def test_scene_model_import():
    """Test Scene model can be imported."""
    scene = Scene(
        section_path="Chapter 1 → Area 1",
        name="Test Cave",
        description="A dark cave entrance",
        location_type="underground"
    )
    assert scene.name == "Test Cave"
    assert scene.location_type == "underground"
```

Run: `cd ui/backend && pytest tests/test_models.py::test_scene_model_import -v`

Expected: PASS

**Step 7: Commit**

```bash
git add ui/backend/app/models/ ui/backend/tests/
git commit -m "feat: add chat and scene models for API"
```

---

## Task 3: Slash Command Parser

**Files:**
- Create: `ui/backend/app/services/command_parser.py`
- Create: `ui/backend/tests/test_command_parser.py`

**Step 1: Write failing tests for command parser**

Create `ui/backend/tests/test_command_parser.py`:
```python
"""Tests for slash command parser."""

import pytest
from app.services.command_parser import (
    CommandParser,
    ParsedCommand,
    CommandType
)


def test_parse_generate_scene():
    """Test parsing /generate-scene command."""
    parser = CommandParser()
    cmd = parser.parse("/generate-scene dark cave entrance")

    assert cmd.type == CommandType.GENERATE_SCENE
    assert cmd.args == "dark cave entrance"
    assert cmd.is_command is True


def test_parse_list_scenes():
    """Test parsing /list-scenes command."""
    parser = CommandParser()
    cmd = parser.parse("/list-scenes Chapter 2")

    assert cmd.type == CommandType.LIST_SCENES
    assert cmd.args == "Chapter 2"


def test_parse_help():
    """Test parsing /help command."""
    parser = CommandParser()
    cmd = parser.parse("/help")

    assert cmd.type == CommandType.HELP
    assert cmd.args == ""


def test_parse_regular_message():
    """Test parsing non-command message."""
    parser = CommandParser()
    cmd = parser.parse("Hello, how are you?")

    assert cmd.type == CommandType.CHAT
    assert cmd.args == "Hello, how are you?"
    assert cmd.is_command is False


def test_parse_unknown_command():
    """Test parsing unknown slash command."""
    parser = CommandParser()
    cmd = parser.parse("/unknown-command test")

    assert cmd.type == CommandType.UNKNOWN
    assert cmd.is_command is True
```

**Step 2: Run tests to verify they fail**

Run: `cd ui/backend && pytest tests/test_command_parser.py -v`

Expected: FAIL with "ModuleNotFoundError: No module named 'app.services.command_parser'"

**Step 3: Implement command parser**

Create `ui/backend/app/services/command_parser.py`:
```python
"""Slash command parser for Module Assistant."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel


class CommandType(str, Enum):
    """Available command types."""
    GENERATE_SCENE = "generate_scene"
    LIST_SCENES = "list_scenes"
    LIST_ACTORS = "list_actors"
    HELP = "help"
    CHAT = "chat"  # Regular message, not a command
    UNKNOWN = "unknown"


class ParsedCommand(BaseModel):
    """Parsed command result."""
    type: CommandType
    args: str
    is_command: bool
    original_message: str


class CommandParser:
    """Parser for slash commands."""

    COMMAND_MAP = {
        "/generate-scene": CommandType.GENERATE_SCENE,
        "/list-scenes": CommandType.LIST_SCENES,
        "/list-actors": CommandType.LIST_ACTORS,
        "/help": CommandType.HELP,
    }

    def parse(self, message: str) -> ParsedCommand:
        """
        Parse a message into a command.

        Args:
            message: User input message

        Returns:
            ParsedCommand with type and arguments
        """
        message = message.strip()

        # Check if it's a command (starts with /)
        if not message.startswith("/"):
            return ParsedCommand(
                type=CommandType.CHAT,
                args=message,
                is_command=False,
                original_message=message
            )

        # Split command and args
        parts = message.split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        # Look up command type
        cmd_type = self.COMMAND_MAP.get(command, CommandType.UNKNOWN)

        return ParsedCommand(
            type=cmd_type,
            args=args,
            is_command=True,
            original_message=message
        )
```

**Step 4: Run tests to verify they pass**

Run: `cd ui/backend && pytest tests/test_command_parser.py -v`

Expected: All tests PASS

**Step 5: Commit**

```bash
git add ui/backend/app/services/command_parser.py ui/backend/tests/test_command_parser.py
git commit -m "feat: add slash command parser"
```

---

## Task 4: Gemini Service Integration

**Files:**
- Create: `ui/backend/app/services/gemini_service.py`
- Create: `ui/backend/tests/test_gemini_service.py`

**Step 1: Write test for Gemini service**

Create `ui/backend/tests/test_gemini_service.py`:
```python
"""Tests for Gemini service."""

import pytest
from unittest.mock import Mock, patch
from app.services.gemini_service import GeminiService


@pytest.fixture
def gemini_service():
    """Create GeminiService with mocked API."""
    with patch('app.services.gemini_service.GeminiAPI') as mock_api:
        service = GeminiService()
        service.api = mock_api.return_value
        return service


def test_generate_chat_response(gemini_service):
    """Test generating chat response."""
    # Mock API response
    mock_response = Mock()
    mock_response.text = "This is a test response from Gemini."
    gemini_service.api.generate_content.return_value = mock_response

    result = gemini_service.generate_chat_response(
        message="Hello",
        context={}
    )

    assert result == "This is a test response from Gemini."
    gemini_service.api.generate_content.assert_called_once()


def test_generate_scene_description(gemini_service):
    """Test generating scene description."""
    mock_response = Mock()
    mock_response.text = "A dark cave with dripping water and moss-covered walls."
    gemini_service.api.generate_content.return_value = mock_response

    result = gemini_service.generate_scene_description("dark cave")

    assert "dark cave" in result.lower() or "dripping water" in result
```

**Step 2: Run test to verify it fails**

Run: `cd ui/backend && pytest tests/test_gemini_service.py -v`

Expected: FAIL with "ModuleNotFoundError: No module named 'app.services.gemini_service'"

**Step 3: Implement Gemini service**

Create `ui/backend/app/services/gemini_service.py`:
```python
"""Gemini service for Module Assistant."""

import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Add project src to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from util.gemini import GeminiAPI  # noqa: E402


class GeminiService:
    """Service for interacting with Gemini API."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Gemini service.

        Args:
            api_key: Optional API key (loads from .env if not provided)
        """
        self.api = GeminiAPI(model_name="gemini-2.0-flash", api_key=api_key)

    def generate_chat_response(
        self,
        message: str,
        context: Dict[str, Any]
    ) -> str:
        """
        Generate a chat response using Gemini.

        Args:
            message: User message
            context: Conversation context

        Returns:
            Generated response text
        """
        # Build prompt with context
        prompt = self._build_chat_prompt(message, context)

        # Generate response
        response = self.api.generate_content(prompt)
        return response.text

    def generate_scene_description(self, scene_request: str) -> str:
        """
        Generate a detailed scene description.

        Args:
            scene_request: User's scene request

        Returns:
            Generated scene description
        """
        prompt = f"""You are a D&D Dungeon Master describing a scene.

User request: {scene_request}

Generate a vivid, atmospheric description of this scene/location. Include:
- Physical layout and dimensions
- Lighting and atmosphere
- Notable features and details
- Sounds, smells, or other sensory details

Keep it concise (2-3 sentences) and evocative."""

        response = self.api.generate_content(prompt)
        return response.text.strip()

    def _build_chat_prompt(
        self,
        message: str,
        context: Dict[str, Any]
    ) -> str:
        """Build prompt with context."""
        prompt = """You are a helpful D&D Module Assistant. You help users work with D&D module content, generate scenes, and manage actors.

Available commands:
- /generate-scene [description] - Generate a new scene
- /list-scenes [chapter] - List scenes in a chapter
- /list-actors - List all actors/NPCs
- /help - Show help

"""

        if context.get("module"):
            prompt += f"Current module: {context['module']}\n"
        if context.get("chapter"):
            prompt += f"Current chapter: {context['chapter']}\n"

        prompt += f"\nUser: {message}\n\nAssistant:"

        return prompt
```

**Step 4: Run tests to verify they pass**

Run: `cd ui/backend && pytest tests/test_gemini_service.py -v`

Expected: Tests PASS

**Step 5: Commit**

```bash
git add ui/backend/app/services/gemini_service.py ui/backend/tests/test_gemini_service.py
git commit -m "feat: add Gemini service for chat and scene generation"
```

---

## Task 5: Chat Router (API Endpoint)

**Files:**
- Create: `ui/backend/app/routers/chat.py`
- Modify: `ui/backend/app/main.py`
- Create: `ui/backend/tests/test_chat_router.py`

**Step 1: Write test for chat endpoint**

Create `ui/backend/tests/test_chat_router.py`:
```python
"""Tests for chat router."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock
from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


def test_chat_endpoint_basic(client):
    """Test basic chat endpoint."""
    with patch('app.routers.chat.GeminiService') as mock_service:
        mock_instance = Mock()
        mock_instance.generate_chat_response.return_value = "Hello! How can I help?"
        mock_service.return_value = mock_instance

        response = client.post(
            "/api/chat",
            json={"message": "Hello", "context": {}}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "text"
        assert "Hello" in data["message"]


def test_chat_endpoint_generate_scene_command(client):
    """Test /generate-scene command."""
    with patch('app.routers.chat.GeminiService') as mock_service:
        mock_instance = Mock()
        mock_instance.generate_scene_description.return_value = "A dark cave entrance"
        mock_service.return_value = mock_instance

        response = client.post(
            "/api/chat",
            json={"message": "/generate-scene dark cave", "context": {}}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "scene"
        assert "cave" in data["message"].lower()


def test_chat_endpoint_help_command(client):
    """Test /help command."""
    response = client.post(
        "/api/chat",
        json={"message": "/help", "context": {}}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "text"
    assert "commands" in data["message"].lower()
```

**Step 2: Run test to verify it fails**

Run: `cd ui/backend && pytest tests/test_chat_router.py -v`

Expected: FAIL (404 Not Found on /api/chat)

**Step 3: Create chat router**

Create `ui/backend/app/routers/chat.py`:
```python
"""Chat router for Module Assistant API."""

from fastapi import APIRouter, HTTPException
from app.models.chat import ChatRequest, ChatResponse
from app.services.command_parser import CommandParser, CommandType
from app.services.gemini_service import GeminiService

router = APIRouter(prefix="/api", tags=["chat"])

# Initialize services
command_parser = CommandParser()
gemini_service = GeminiService()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Main chat endpoint.

    Handles both regular chat messages and slash commands.
    """
    try:
        # Parse command
        cmd = command_parser.parse(request.message)

        # Handle different command types
        if cmd.type == CommandType.HELP:
            return _handle_help_command()

        elif cmd.type == CommandType.GENERATE_SCENE:
            return await _handle_generate_scene(cmd.args, request.context)

        elif cmd.type == CommandType.LIST_SCENES:
            return _handle_list_scenes(cmd.args, request.context)

        elif cmd.type == CommandType.LIST_ACTORS:
            return _handle_list_actors(request.context)

        elif cmd.type == CommandType.UNKNOWN:
            return ChatResponse(
                message=f"Unknown command: {cmd.original_message}. Type /help for available commands.",
                type="error"
            )

        else:  # Regular chat
            response_text = gemini_service.generate_chat_response(
                message=request.message,
                context=request.context
            )
            return ChatResponse(message=response_text, type="text")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _handle_help_command() -> ChatResponse:
    """Handle /help command."""
    help_text = """**Available Commands:**

- `/generate-scene [description]` - Generate a new scene with AI
- `/list-scenes [chapter]` - List all scenes (optionally filtered by chapter)
- `/list-actors` - List all actors and NPCs
- `/help` - Show this help message

You can also chat naturally without using commands!"""

    return ChatResponse(message=help_text, type="text")


async def _handle_generate_scene(args: str, context: dict) -> ChatResponse:
    """Handle /generate-scene command."""
    if not args:
        return ChatResponse(
            message="Please provide a scene description. Example: `/generate-scene dark cave entrance`",
            type="error"
        )

    # Generate scene description
    description = gemini_service.generate_scene_description(args)

    # TODO: In future, also generate scene image and save to database
    # For now, just return the description

    response_message = f"**Generated Scene**\n\n{description}\n\n_Note: Scene image generation coming soon!_"

    return ChatResponse(
        message=response_message,
        type="scene",
        data={"description": description, "request": args}
    )


def _handle_list_scenes(chapter_filter: str, context: dict) -> ChatResponse:
    """Handle /list-scenes command."""
    # TODO: Integrate with actual scene database
    # For now, return placeholder

    message = f"**Scenes in {chapter_filter or 'All Chapters'}**\n\n"
    message += "1. Cragmaw Hideout Entrance\n"
    message += "2. Twin Pools Cave\n"
    message += "3. Goblin Den\n"
    message += "4. Klarg's Cave\n\n"
    message += "_Note: Scene database integration coming soon!_"

    return ChatResponse(message=message, type="list")


def _handle_list_actors(context: dict) -> ChatResponse:
    """Handle /list-actors command."""
    # TODO: Integrate with actual actor database
    # For now, return placeholder

    message = "**Available Actors**\n\n"
    message += "1. Klarg (Bugbear)\n"
    message += "2. Sildar Hallwinter (Human Fighter)\n"
    message += "3. Goblin\n"
    message += "4. Wolf\n\n"
    message += "_Note: Actor database integration coming soon!_"

    return ChatResponse(message=message, type="list")
```

**Step 4: Register router in main.py**

Modify `ui/backend/app/main.py`:
```python
"""D&D Module Assistant API."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import chat  # Add this import

app = FastAPI(
    title="D&D Module Assistant API",
    description="Backend API for D&D module generation and management",
    version="0.1.0"
)

# CORS middleware for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(chat.router)  # Add this line


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "module-assistant-api"}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "D&D Module Assistant API",
        "docs": "/docs",
        "health": "/health"
    }
```

**Step 5: Run tests to verify they pass**

Run: `cd ui/backend && pytest tests/test_chat_router.py -v`

Expected: All tests PASS

**Step 6: Test manually with curl**

Start server: `cd ui/backend && uvicorn app.main:app --reload --port 8000`

Test: `curl -X POST http://localhost:8000/api/chat -H "Content-Type: application/json" -d '{"message": "/help", "context": {}}'`

Expected: JSON response with help text

**Step 7: Commit**

```bash
git add ui/backend/app/routers/chat.py ui/backend/app/main.py ui/backend/tests/test_chat_router.py
git commit -m "feat: add chat API endpoint with slash command support"
```

---

## Task 6: Frontend Project Setup

**Files:**
- Create: `ui/frontend/package.json`
- Create: `ui/frontend/vite.config.ts`
- Create: `ui/frontend/tsconfig.json`
- Create: `ui/frontend/tailwind.config.js`
- Create: `ui/frontend/src/main.tsx`
- Create: `ui/frontend/src/App.tsx`
- Create: `ui/frontend/index.html`

**Step 1: Initialize React project with Vite**

```bash
cd ui
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
```

**Step 2: Install shadcn/ui and dependencies**

```bash
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
npm install class-variance-authority clsx tailwind-merge
npm install lucide-react
```

**Step 3: Initialize shadcn/ui**

```bash
npx shadcn@latest init
```

When prompted:
- Style: Default
- Base color: Slate
- CSS variables: Yes

**Step 4: Install additional dependencies**

```bash
npm install @tanstack/react-query
npm install axios
```

**Step 5: Install Google Fonts**

Create `ui/frontend/src/index.css`:
```css
@import url('https://fonts.googleapis.com/css2?family=IM+Fell+DW+Pica:ital@0;1&family=UnifrakturMaguntia&family=Crimson+Pro:wght@400;600&display=swap');

@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --font-heading: 'UnifrakturMaguntia', cursive;
    --font-body: 'IM Fell DW Pica', serif;
    --font-ui: 'Crimson Pro', serif;

    /* Parchment colors */
    --parchment-bg: 45 25 15;
    --parchment-light: 248 242 230;
    --parchment-medium: 228 212 185;
    --parchment-dark: 180 157 125;
    --wax-red: 139 31 31;
  }

  body {
    font-family: var(--font-body);
  }

  h1, h2, h3, h4, h5, h6 {
    font-family: var(--font-heading);
  }
}
```

**Step 6: Test dev server**

Run: `npm run dev`

Expected: Vite dev server starts on http://localhost:5173

**Step 7: Commit**

```bash
git add ui/frontend/
git commit -m "feat: initialize React frontend with Vite and shadcn/ui"
```

---

## Task 7: Frontend API Client

**Files:**
- Create: `ui/frontend/src/lib/api.ts`
- Create: `ui/frontend/src/lib/types.ts`

**Step 1: Create TypeScript types**

Create `ui/frontend/src/lib/types.ts`:
```typescript
/**
 * TypeScript types for Module Assistant API.
 */

export enum ChatRole {
  USER = 'user',
  ASSISTANT = 'assistant',
  SYSTEM = 'system',
}

export interface ChatMessage {
  role: ChatRole;
  content: string;
  timestamp: string;
}

export interface ChatRequest {
  message: string;
  context?: Record<string, any>;
  conversation_history?: ChatMessage[];
}

export interface ChatResponse {
  message: string;
  type: 'text' | 'scene' | 'list' | 'error';
  data?: Record<string, any> | null;
  scene?: any | null;
}

export interface Scene {
  section_path: string;
  name: string;
  description: string;
  location_type: string;
  xml_section_id?: string | null;
}
```

**Step 2: Create API client**

Create `ui/frontend/src/lib/api.ts`:
```typescript
/**
 * API client for Module Assistant backend.
 */

import axios, { AxiosInstance } from 'axios';
import { ChatRequest, ChatResponse } from './types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

class ModuleAssistantAPI {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }

  /**
   * Send a chat message to the backend.
   */
  async chat(request: ChatRequest): Promise<ChatResponse> {
    const response = await this.client.post<ChatResponse>('/api/chat', request);
    return response.data;
  }

  /**
   * Health check endpoint.
   */
  async health(): Promise<{ status: string; service: string }> {
    const response = await this.client.get('/health');
    return response.data;
  }
}

// Export singleton instance
export const api = new ModuleAssistantAPI();
```

**Step 3: Create .env file**

Create `ui/frontend/.env`:
```bash
VITE_API_URL=http://localhost:8000
```

**Step 4: Test API client in browser console**

Add to `ui/frontend/src/App.tsx`:
```typescript
import { api } from './lib/api';

// Test in useEffect
useEffect(() => {
  api.health().then(console.log).catch(console.error);
}, []);
```

Run: `npm run dev`

Expected: Open browser console, should see `{status: 'healthy', service: 'module-assistant-api'}`

**Step 5: Commit**

```bash
git add ui/frontend/src/lib/
git commit -m "feat: add API client for backend communication"
```

---

## Task 8: Chat UI Components - Header

**Files:**
- Create: `ui/frontend/src/components/Header.tsx`
- Modify: `ui/frontend/src/App.tsx`

**Step 1: Create Header component**

Create `ui/frontend/src/components/Header.tsx`:
```typescript
/**
 * Header component with wax seal aesthetic.
 */

export function Header() {
  return (
    <div className="relative px-10 py-6 bg-gradient-to-b from-[#c4b098] to-[#b89d7d] border-4 border-[#8d7555] border-b-2 border-b-[#7d5a3d]">
      {/* Left flourish */}
      <div className="absolute left-32 top-1/2 -translate-y-1/2 text-2xl text-[#7d5a3d]">
        ⚜
      </div>

      {/* Title */}
      <h1 className="text-center text-[#5c3d2e] text-4xl tracking-[0.2em] font-normal drop-shadow-sm">
        Module Assistant
      </h1>

      {/* Right flourish */}
      <div className="absolute right-32 top-1/2 -translate-y-1/2 text-2xl text-[#7d5a3d]">
        ⚜
      </div>
    </div>
  );
}
```

**Step 2: Update App.tsx to use Header**

Modify `ui/frontend/src/App.tsx`:
```typescript
import { Header } from './components/Header';
import './index.css';

function App() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-[#d4c4a8] via-[#c4b098] to-[#d4c4a8] flex items-center justify-center p-5">
      <div className="w-full max-w-4xl h-[85vh] flex flex-col shadow-2xl">
        <Header />

        {/* Chat window placeholder */}
        <div className="flex-1 bg-[#f8f5ea] border-l-4 border-r-4 border-[#8d7555]">
          <p className="p-8 text-[#5c3d2e]">Chat window will go here...</p>
        </div>

        {/* Input area placeholder */}
        <div className="px-10 py-6 bg-gradient-to-b from-[#b89d7d] to-[#c4b098] border-4 border-[#8d7555] border-t-2 border-t-[#7d5a3d]">
          <p className="text-center text-[#5c3d2e]">Input area will go here...</p>
        </div>
      </div>
    </div>
  );
}

export default App;
```

**Step 3: Test in browser**

Run: `npm run dev`

Expected: See header with "Module Assistant" title and fleur-de-lis flourishes

**Step 4: Commit**

```bash
git add ui/frontend/src/components/Header.tsx ui/frontend/src/App.tsx
git commit -m "feat: add Header component with wax seal aesthetic"
```

---

## Task 9: Chat UI Components - Message Bubbles

**Files:**
- Create: `ui/frontend/src/components/Message.tsx`
- Install: shadcn/ui Avatar component

**Step 1: Install Avatar component**

```bash
npx shadcn@latest add avatar
```

**Step 2: Create Message component**

Create `ui/frontend/src/components/Message.tsx`:
```typescript
/**
 * Message bubble component.
 */

import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { ChatRole } from '@/lib/types';
import { cn } from '@/lib/utils';

interface MessageProps {
  role: ChatRole;
  content: string;
  timestamp?: string;
}

export function Message({ role, content, timestamp }: MessageProps) {
  const isUser = role === ChatRole.USER;
  const isAssistant = role === ChatRole.ASSISTANT;

  return (
    <div
      className={cn(
        'mb-9 flex gap-4 animate-in fade-in slide-in-from-bottom-2',
        isUser && 'flex-row-reverse'
      )}
    >
      {/* Avatar */}
      <Avatar className="h-12 w-12 border-2 border-[#7d5a3d] shadow-md bg-gradient-to-br from-[#e8dcc5] to-[#d4c4a8]">
        <AvatarFallback className="text-xl">
          {isAssistant ? '✒' : <span className="grayscale brightness-0">🧙</span>}
        </AvatarFallback>
      </Avatar>

      {/* Message content */}
      <div
        className={cn(
          'max-w-[70%] rounded px-7 py-5 font-[var(--font-body)] leading-relaxed',
          isAssistant &&
            'bg-gradient-to-br from-[#f8f2e6]/90 to-[#f0e8d7]/90 text-[#3d2817] border-2 border-[#c4b098] border-l-[3px] border-l-[#7d5a3d] shadow-[3px_3px_0_rgba(125,90,61,0.08),0_5px_12px_rgba(0,0,0,0.12)]',
          isUser &&
            'bg-gradient-to-br from-[#c4b098]/30 to-[#a89070]/30 text-[#3d2817] border-2 border-[#7d5a3d] border-r-[3px] border-r-[#5c3d2e] shadow-[-3px_3px_0_rgba(125,90,61,0.08),0_5px_12px_rgba(0,0,0,0.12)]'
        )}
      >
        {/* Label */}
        <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-[#7d5a3d] font-[var(--font-ui)]">
          {isAssistant ? 'Assistant' : 'You'}
        </div>

        {/* Content */}
        <div className="whitespace-pre-wrap">{content}</div>
      </div>
    </div>
  );
}
```

**Step 3: Test Message component in App.tsx**

Modify `ui/frontend/src/App.tsx`:
```typescript
import { Header } from './components/Header';
import { Message } from './components/Message';
import { ChatRole } from './lib/types';
import './index.css';

function App() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-[#d4c4a8] via-[#c4b098] to-[#d4c4a8] flex items-center justify-center p-5">
      <div className="w-full max-w-4xl h-[85vh] flex flex-col shadow-2xl">
        <Header />

        {/* Chat window with test messages */}
        <div className="flex-1 bg-[#f8f5ea] border-l-4 border-r-4 border-[#8d7555] overflow-y-auto p-12">
          <Message
            role={ChatRole.ASSISTANT}
            content="Greetings, adventurer! I am your Module Assistant. I can help you generate scenes, manage actors, and work with your D&D modules. Try typing **/help** to see available commands."
          />
          <Message
            role={ChatRole.USER}
            content="/generate-scene the entrance to the Cragmaw Hideout cave"
          />
        </div>

        {/* Input area placeholder */}
        <div className="px-10 py-6 bg-gradient-to-b from-[#b89d7d] to-[#c4b098] border-4 border-[#8d7555] border-t-2 border-t-[#7d5a3d]">
          <p className="text-center text-[#5c3d2e]">Input area will go here...</p>
        </div>
      </div>
    </div>
  );
}

export default App;
```

**Step 4: Test in browser**

Run: `npm run dev`

Expected: See two message bubbles with proper styling and avatars

**Step 5: Commit**

```bash
git add ui/frontend/src/components/Message.tsx ui/frontend/src/App.tsx
git commit -m "feat: add Message component with parchment aesthetic"
```

---

## Task 10: Chat UI Components - Wax Seal Input

**Files:**
- Create: `ui/frontend/src/components/InputArea.tsx`
- Install: shadcn/ui Input and Button components

**Step 1: Install UI components**

```bash
npx shadcn@latest add input button
```

**Step 2: Create InputArea component**

Create `ui/frontend/src/components/InputArea.tsx`:
```typescript
/**
 * Input area with wax seal send button.
 */

import { useState, KeyboardEvent } from 'react';
import { Input } from '@/components/ui/input';

interface InputAreaProps {
  onSendMessage: (message: string) => void;
  disabled?: boolean;
}

export function InputArea({ onSendMessage, disabled = false }: InputAreaProps) {
  const [message, setMessage] = useState('');

  const handleSend = () => {
    if (message.trim() && !disabled) {
      onSendMessage(message.trim());
      setMessage('');
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="px-10 py-6 bg-gradient-to-b from-[#b89d7d] to-[#c4b098] border-4 border-[#8d7555] border-t-2 border-t-[#7d5a3d] shadow-inner">
      <div className="flex gap-4 items-center">
        {/* Input field */}
        <Input
          type="text"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          placeholder="/generate-scene [description]"
          className="flex-1 bg-[#f8f2e6]/95 border-2 border-[#7d5a3d] px-6 py-4 font-[var(--font-body)] text-base text-[#3d2817] placeholder:text-[#9d8565] placeholder:italic focus-visible:ring-[#5c3d2e] focus-visible:ring-offset-0 shadow-inner"
        />

        {/* Wax seal send button */}
        <button
          onClick={handleSend}
          disabled={disabled || !message.trim()}
          className="relative w-[78px] h-[78px] flex-shrink-0 rounded-[44%_56%_48%_52%/53%_47%_53%_47%] bg-gradient-radial from-[#a83030] via-[#8b1f1f] to-[#5a1212] shadow-[0_1px_3px_rgba(0,0,0,0.4),inset_0_1px_2px_rgba(168,48,48,0.4)] transition-all hover:shadow-[0_2px_6px_rgba(0,0,0,0.5),inset_0_2px_3px_rgba(168,48,48,0.5)] active:shadow-[0_1px_2px_rgba(0,0,0,0.4),inset_0_1px_4px_rgba(0,0,0,0.6)] disabled:opacity-50 disabled:cursor-not-allowed"
          style={{
            background:
              'radial-gradient(circle at 35% 30%, #a83030 0%, #9d2424 20%, #8b1f1f 40%, #721818 70%, #5a1212 100%)',
          }}
        >
          {/* Wax texture overlay */}
          <div className="absolute inset-0 rounded-[44%_56%_48%_52%/53%_47%_53%_47%] bg-[repeating-radial-gradient(circle_at_40%_30%,rgba(0,0,0,0)_0px,rgba(0,0,0,0.03)_1px,rgba(0,0,0,0)_2px,rgba(0,0,0,0)_8px)]" />

          {/* Embossed ring */}
          <div className="absolute inset-0 rounded-[44%_56%_48%_52%/53%_47%_53%_47%] shadow-[inset_0_0_0_3px_rgba(0,0,0,0.15)]" />

          {/* Fleur-de-lis symbol */}
          <div className="absolute inset-0 flex items-center justify-center text-5xl text-black/40 select-none">
            ⚜
          </div>

          {/* Ribbon underneath */}
          <div className="absolute -bottom-2 left-1/2 -translate-x-1/2 w-20 h-3 bg-gradient-to-b from-[#6d4d3e] to-[#5c3d2e] rounded-sm shadow-md -z-10" />
        </button>
      </div>

      {/* Command hint */}
      <p className="mt-3 text-center text-sm text-[#5c3d2e] font-[var(--font-body)] italic">
        Variant 1: Wax Seal • Fleur-de-lis emblem
      </p>
    </div>
  );
}
```

**Step 3: Update App.tsx to use InputArea**

Modify `ui/frontend/src/App.tsx`:
```typescript
import { useState } from 'react';
import { Header } from './components/Header';
import { Message } from './components/Message';
import { InputArea } from './components/InputArea';
import { ChatRole, ChatMessage } from './lib/types';
import './index.css';

function App() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: ChatRole.ASSISTANT,
      content:
        'Greetings, adventurer! I am your Module Assistant. I can help you generate scenes, manage actors, and work with your D&D modules. Try typing **/help** to see available commands.',
      timestamp: new Date().toISOString(),
    },
  ]);

  const handleSendMessage = (content: string) => {
    const newMessage: ChatMessage = {
      role: ChatRole.USER,
      content,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, newMessage]);

    // TODO: Send to backend and add response
    console.log('Send message:', content);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#d4c4a8] via-[#c4b098] to-[#d4c4a8] flex items-center justify-center p-5">
      <div className="w-full max-w-4xl h-[85vh] flex flex-col shadow-2xl">
        <Header />

        {/* Chat window */}
        <div className="flex-1 bg-[#f8f5ea] border-l-4 border-r-4 border-[#8d7555] overflow-y-auto p-12">
          {messages.map((msg, index) => (
            <Message key={index} role={msg.role} content={msg.content} />
          ))}
        </div>

        {/* Input area */}
        <InputArea onSendMessage={handleSendMessage} />
      </div>
    </div>
  );
}

export default App;
```

**Step 4: Test in browser**

Run: `npm run dev`

Expected: See wax seal button, type message and press Enter to add to chat

**Step 5: Commit**

```bash
git add ui/frontend/src/components/InputArea.tsx ui/frontend/src/App.tsx
git commit -m "feat: add InputArea with wax seal send button"
```

---

## Task 11: Connect Frontend to Backend

**Files:**
- Create: `ui/frontend/src/hooks/useChat.ts`
- Modify: `ui/frontend/src/App.tsx`

**Step 1: Create useChat hook**

Create `ui/frontend/src/hooks/useChat.ts`:
```typescript
/**
 * Custom hook for managing chat state and API calls.
 */

import { useState } from 'react';
import { ChatMessage, ChatRole, ChatRequest } from '@/lib/types';
import { api } from '@/lib/api';

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: ChatRole.ASSISTANT,
      content:
        'Greetings, adventurer! I am your Module Assistant. I can help you generate scenes, manage actors, and work with your D&D modules. Try typing **/help** to see available commands.',
      timestamp: new Date().toISOString(),
    },
  ]);
  const [isLoading, setIsLoading] = useState(false);

  const sendMessage = async (content: string) => {
    // Add user message immediately
    const userMessage: ChatMessage = {
      role: ChatRole.USER,
      content,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);

    // Send to backend
    setIsLoading(true);
    try {
      const request: ChatRequest = {
        message: content,
        context: {},
        conversation_history: messages,
      };

      const response = await api.chat(request);

      // Add assistant response
      const assistantMessage: ChatMessage = {
        role: ChatRole.ASSISTANT,
        content: response.message,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Failed to send message:', error);

      // Add error message
      const errorMessage: ChatMessage = {
        role: ChatRole.ASSISTANT,
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  return {
    messages,
    sendMessage,
    isLoading,
  };
}
```

**Step 2: Update App.tsx to use useChat**

Modify `ui/frontend/src/App.tsx`:
```typescript
import { Header } from './components/Header';
import { Message } from './components/Message';
import { InputArea } from './components/InputArea';
import { useChat } from './hooks/useChat';
import './index.css';

function App() {
  const { messages, sendMessage, isLoading } = useChat();

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#d4c4a8] via-[#c4b098] to-[#d4c4a8] flex items-center justify-center p-5">
      <div className="w-full max-w-4xl h-[85vh] flex flex-col shadow-2xl">
        <Header />

        {/* Chat window */}
        <div className="flex-1 bg-[#f8f5ea] border-l-4 border-r-4 border-[#8d7555] overflow-y-auto p-12">
          {messages.map((msg, index) => (
            <Message key={index} role={msg.role} content={msg.content} />
          ))}
          {isLoading && (
            <div className="text-center text-[#7d5a3d] italic">
              Consulting the tomes...
            </div>
          )}
        </div>

        {/* Input area */}
        <InputArea onSendMessage={sendMessage} disabled={isLoading} />
      </div>
    </div>
  );
}

export default App;
```

**Step 3: Test end-to-end**

Start backend: `cd ui/backend && uvicorn app.main:app --reload --port 8000`

Start frontend: `cd ui/frontend && npm run dev`

Test:
1. Type "/help" and press Enter
2. Type "/generate-scene dark cave" and press Enter
3. Type "Hello" and press Enter

Expected: All commands return responses from backend

**Step 4: Commit**

```bash
git add ui/frontend/src/hooks/useChat.ts ui/frontend/src/App.tsx
git commit -m "feat: connect frontend to backend with useChat hook"
```

---

## Task 12: Scene Card Component

**Files:**
- Create: `ui/frontend/src/components/SceneCard.tsx`
- Modify: `ui/frontend/src/hooks/useChat.ts`

**Step 1: Install Card component**

```bash
npx shadcn@latest add card
```

**Step 2: Create SceneCard component**

Create `ui/frontend/src/components/SceneCard.tsx`:
```typescript
/**
 * Scene card for displaying generated scenes.
 */

import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';

interface SceneCardProps {
  name: string;
  description: string;
  imageUrl?: string;
}

export function SceneCard({ name, description, imageUrl }: SceneCardProps) {
  return (
    <Card className="relative my-9 border-3 border-[#7d5a3d] rounded bg-gradient-to-br from-[#f8f2e6]/95 to-[#f0e8d7]/95 shadow-[5px_5px_0_rgba(125,90,61,0.12),0_8px_25px_rgba(0,0,0,0.18)]">
      {/* Decorative symbol */}
      <div className="absolute -top-5 left-1/2 -translate-x-1/2 text-4xl text-[#7d5a3d] bg-gradient-to-br from-[#e8dcc5] to-[#d4c4a8] px-5">
        §
      </div>

      <CardHeader className="pb-4 pt-8">
        <CardTitle className="text-center text-[#5c3d2e] text-2xl font-[var(--font-heading)] tracking-wider border-b-2 border-[#7d5a3d] pb-4">
          {name}
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-5">
        {/* Scene image placeholder */}
        {imageUrl ? (
          <img
            src={imageUrl}
            alt={name}
            className="w-full h-70 object-cover rounded border-3 border-[#7d5a3d] shadow-inner"
          />
        ) : (
          <div className="w-full h-70 flex items-center justify-center rounded border-3 border-[#7d5a3d] bg-gradient-to-br from-[#d4c4a8] to-[#c4b098] text-[#7d5a3d] italic shadow-inner">
            [Generated scene image would appear here]
          </div>
        )}

        {/* Scene description */}
        <p className="text-[#3d2817] leading-relaxed font-[var(--font-body)] text-justify">
          {description}
        </p>
      </CardContent>
    </Card>
  );
}
```

**Step 3: Update useChat to handle scene responses**

Modify `ui/frontend/src/hooks/useChat.ts`:
```typescript
/**
 * Custom hook for managing chat state and API calls.
 */

import { useState } from 'react';
import { ChatMessage, ChatRole, ChatRequest } from '@/lib/types';
import { api } from '@/lib/api';

export interface ExtendedChatMessage extends ChatMessage {
  sceneData?: {
    name?: string;
    description: string;
    imageUrl?: string;
  };
}

export function useChat() {
  const [messages, setMessages] = useState<ExtendedChatMessage[]>([
    {
      role: ChatRole.ASSISTANT,
      content:
        'Greetings, adventurer! I am your Module Assistant. I can help you generate scenes, manage actors, and work with your D&D modules. Try typing **/help** to see available commands.',
      timestamp: new Date().toISOString(),
    },
  ]);
  const [isLoading, setIsLoading] = useState(false);

  const sendMessage = async (content: string) => {
    // Add user message immediately
    const userMessage: ExtendedChatMessage = {
      role: ChatRole.USER,
      content,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);

    // Send to backend
    setIsLoading(true);
    try {
      const request: ChatRequest = {
        message: content,
        context: {},
        conversation_history: messages,
      };

      const response = await api.chat(request);

      // Create assistant message with scene data if applicable
      const assistantMessage: ExtendedChatMessage = {
        role: ChatRole.ASSISTANT,
        content: response.message,
        timestamp: new Date().toISOString(),
      };

      // Add scene data if response type is "scene"
      if (response.type === 'scene' && response.data) {
        assistantMessage.sceneData = {
          name: response.data.request || 'Generated Scene',
          description: response.data.description,
        };
      }

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Failed to send message:', error);

      // Add error message
      const errorMessage: ExtendedChatMessage = {
        role: ChatRole.ASSISTANT,
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  return {
    messages,
    sendMessage,
    isLoading,
  };
}
```

**Step 4: Update App.tsx to render SceneCard**

Modify `ui/frontend/src/App.tsx`:
```typescript
import { Header } from './components/Header';
import { Message } from './components/Message';
import { SceneCard } from './components/SceneCard';
import { InputArea } from './components/InputArea';
import { useChat } from './hooks/useChat';
import './index.css';

function App() {
  const { messages, sendMessage, isLoading } = useChat();

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#d4c4a8] via-[#c4b098] to-[#d4c4a8] flex items-center justify-center p-5">
      <div className="w-full max-w-4xl h-[85vh] flex flex-col shadow-2xl">
        <Header />

        {/* Chat window */}
        <div className="flex-1 bg-[#f8f5ea] border-l-4 border-r-4 border-[#8d7555] overflow-y-auto p-12">
          {messages.map((msg, index) => (
            <div key={index}>
              <Message role={msg.role} content={msg.content} />
              {msg.sceneData && (
                <SceneCard
                  name={msg.sceneData.name || 'Generated Scene'}
                  description={msg.sceneData.description}
                  imageUrl={msg.sceneData.imageUrl}
                />
              )}
            </div>
          ))}
          {isLoading && (
            <div className="text-center text-[#7d5a3d] italic">
              Consulting the tomes...
            </div>
          )}
        </div>

        {/* Input area */}
        <InputArea onSendMessage={sendMessage} disabled={isLoading} />
      </div>
    </div>
  );
}

export default App;
```

**Step 5: Test scene generation**

Start both backend and frontend.

Test: Type "/generate-scene mysterious forest clearing" and press Enter

Expected: See scene card with description appear below assistant message

**Step 6: Commit**

```bash
git add ui/frontend/src/components/SceneCard.tsx ui/frontend/src/hooks/useChat.ts ui/frontend/src/App.tsx
git commit -m "feat: add SceneCard component for displaying generated scenes"
```

---

## Task 13: Auto-scroll Chat Window

**Files:**
- Modify: `ui/frontend/src/App.tsx`

**Step 1: Add auto-scroll to chat window**

Modify `ui/frontend/src/App.tsx`:
```typescript
import { useEffect, useRef } from 'react';
import { Header } from './components/Header';
import { Message } from './components/Message';
import { SceneCard } from './components/SceneCard';
import { InputArea } from './components/InputArea';
import { useChat } from './hooks/useChat';
import './index.css';

function App() {
  const { messages, sendMessage, isLoading } = useChat();
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#d4c4a8] via-[#c4b098] to-[#d4c4a8] flex items-center justify-center p-5">
      <div className="w-full max-w-4xl h-[85vh] flex flex-col shadow-2xl">
        <Header />

        {/* Chat window */}
        <div className="flex-1 bg-[#f8f5ea] border-l-4 border-r-4 border-[#8d7555] overflow-y-auto p-12">
          {messages.map((msg, index) => (
            <div key={index}>
              <Message role={msg.role} content={msg.content} />
              {msg.sceneData && (
                <SceneCard
                  name={msg.sceneData.name || 'Generated Scene'}
                  description={msg.sceneData.description}
                  imageUrl={msg.sceneData.imageUrl}
                />
              )}
            </div>
          ))}
          {isLoading && (
            <div className="text-center text-[#7d5a3d] italic">
              Consulting the tomes...
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        {/* Input area */}
        <InputArea onSendMessage={sendMessage} disabled={isLoading} />
      </div>
    </div>
  );
}

export default App;
```

**Step 2: Test auto-scroll**

Test: Send multiple messages and verify chat scrolls to bottom automatically

**Step 3: Commit**

```bash
git add ui/frontend/src/App.tsx
git commit -m "feat: add auto-scroll to chat window"
```

---

## Task 14: Documentation and README

**Files:**
- Create: `ui/README.md`
- Create: `ui/backend/README.md`
- Create: `ui/frontend/README.md`

**Step 1: Create main UI README**

Create `ui/README.md`:
```markdown
# D&D Module Assistant UI

Chat-based interface for D&D module generation with Gemini integration.

## Architecture

- **Frontend:** React + shadcn/ui + Tailwind CSS
- **Backend:** FastAPI + Gemini API
- **Design:** Wax seal variant (fantasy journal aesthetic)

## Quick Start

### Backend

```bash
cd ui/backend
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your Gemini API key
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd ui/frontend
npm install
npm run dev
```

Visit http://localhost:5173

## Features

- **Slash Commands:**
  - `/generate-scene [description]` - Generate AI scene
  - `/list-scenes [chapter]` - List all scenes
  - `/list-actors` - List all actors
  - `/help` - Show help

- **Natural Chat:** Ask questions without commands

- **Fantasy Aesthetic:** Wax seal design inspired by Baldur's Gate 2

## Development

Run tests:
```bash
# Backend
cd ui/backend && pytest

# Frontend
cd ui/frontend && npm test
```

## Integration with Module Pipeline

Backend reuses existing modules:
- `src/util/gemini.py` - Gemini API wrapper
- `src/scene_extraction/` - Scene models and generation
- `src/actors/` - Actor models
- `src/foundry/` - FoundryVTT integration

Future: Connect to scene database and actor database for full integration.
```

**Step 2: Create backend README**

Create `ui/backend/README.md`:
```markdown
# Module Assistant Backend

FastAPI backend for D&D Module Assistant chat interface.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add GEMINI_API_KEY
```

## Run

```bash
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

## Project Structure

```
app/
├── main.py              # FastAPI app
├── routers/
│   └── chat.py          # Chat endpoint
├── services/
│   ├── command_parser.py # Slash command parser
│   └── gemini_service.py # Gemini API wrapper
└── models/
    ├── chat.py          # Chat models
    └── scene.py         # Scene models (from src/)
```

## Testing

```bash
pytest
pytest -v  # Verbose
pytest tests/test_chat_router.py  # Specific file
```

## API Endpoints

### POST /api/chat

Send chat message or slash command.

Request:
```json
{
  "message": "/generate-scene dark cave",
  "context": {},
  "conversation_history": []
}
```

Response:
```json
{
  "message": "Generated scene description...",
  "type": "scene",
  "data": {
    "description": "...",
    "request": "dark cave"
  }
}
```
```

**Step 3: Create frontend README**

Create `ui/frontend/README.md`:
```markdown
# Module Assistant Frontend

React frontend for D&D Module Assistant with wax seal design.

## Setup

```bash
npm install
```

## Run

```bash
npm run dev
```

Visit http://localhost:5173

## Build

```bash
npm run build
npm run preview  # Preview production build
```

## Project Structure

```
src/
├── components/
│   ├── Header.tsx       # App header with flourishes
│   ├── Message.tsx      # Chat message bubble
│   ├── SceneCard.tsx    # Scene display card
│   └── InputArea.tsx    # Input with wax seal button
├── hooks/
│   └── useChat.ts       # Chat state management
├── lib/
│   ├── api.ts           # API client
│   └── types.ts         # TypeScript types
└── App.tsx              # Main app component
```

## Design System

- **Fonts:**
  - Headers: UnifrakturMaguntia (blackletter)
  - Body: IM Fell DW Pica (classical serif)
  - UI: Crimson Pro

- **Colors:**
  - Parchment background: `#f8f5ea`
  - Parchment borders: `#8d7555`, `#7d5a3d`
  - Wax seal: Red gradient (`#a83030` to `#5a1212`)
  - Text: `#3d2817`, `#5c3d2e`

## Components

All components use shadcn/ui primitives with custom parchment styling.

### Message
- User messages: Right-aligned, lighter background
- Assistant messages: Left-aligned, darker borders
- Both: Pen/wizard avatars, parchment textures

### SceneCard
- Section symbol (§) decoration
- Optional scene image
- Blackletter title
- Justified description

### InputArea
- Wax seal send button with fleur-de-lis
- Irregular circular shape (CSS border-radius)
- Ribbon detail underneath
```

**Step 4: Commit**

```bash
git add ui/README.md ui/backend/README.md ui/frontend/README.md
git commit -m "docs: add comprehensive README files for UI project"
```

---

## Summary

This plan implements a complete D&D Module Assistant UI with:

**Backend (FastAPI):**
- ✅ Slash command parser (/generate-scene, /list-scenes, /help)
- ✅ Gemini service integration (reuses `src/util/gemini.py`)
- ✅ Chat API endpoint with command routing
- ✅ Scene models (reuses `src/scene_extraction/models.py`)
- ✅ Full test coverage

**Frontend (React + shadcn/ui):**
- ✅ Wax seal aesthetic (chosen variant)
- ✅ Header with fleur-de-lis flourishes
- ✅ Message bubbles (user/assistant)
- ✅ Scene cards with section symbol decoration
- ✅ Input area with wax seal send button
- ✅ Auto-scroll chat window
- ✅ API integration with useChat hook

**Integration:**
- ✅ Backend reuses existing Gemini utilities
- ✅ Scene models imported from `src/scene_extraction/`
- ⏳ Scene database integration (TODO in backend)
- ⏳ Actor database integration (TODO in backend)
- ⏳ Scene image generation (TODO - requires Imagen API)

**Testing:**
- ✅ Backend: pytest with mocked Gemini API
- ✅ Frontend: Manual testing (no automated tests in plan)

**Documentation:**
- ✅ README files for all components
- ✅ API documentation in Swagger UI
- ✅ TypeScript types for all models

**Next Steps (Future Tasks):**
1. Integrate with scene database (read from `output/runs/`)
2. Integrate with actor database (FoundryVTT actors)
3. Add scene image generation (Gemini Imagen)
4. Add WebSocket support for streaming responses
5. Add authentication/authorization
6. Deploy to production
