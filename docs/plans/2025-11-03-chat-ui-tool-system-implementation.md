# Chat UI Tool System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement modular tool system for chat UI with image generation as the first tool, using Gemini function calling for automatic tool routing.

**Architecture:** Backend uses Gemini 2.0+ native function calling to route requests to registered tools. Tools are self-contained classes implementing BaseTool interface. Frontend renders tool-specific responses based on type field. Image generation creates carousel UI with parchment aesthetic.

**Tech Stack:** FastAPI, Google Gemini API (function calling + Imagen), React 19, TypeScript, Tailwind CSS

---

## Prerequisites

- Worktree created: `.worktrees/chat-ui-tool-system`
- Branch: `feature/chat-ui-tool-system`
- Dependencies installed (backend + frontend)
- `.env` configured with `GEMINI_API_KEY`

---

## Task 1: Backend Tool System Core - Base Classes

**Files:**
- Create: `ui/backend/app/tools/base.py`
- Create: `ui/backend/app/tools/__init__.py`
- Test: `ui/backend/tests/tools/test_base.py`

### Step 1: Write failing test for ToolSchema

Create `ui/backend/tests/tools/test_base.py`:

```python
"""Tests for tool system base classes."""
import pytest
from app.tools.base import ToolSchema, ToolResponse, BaseTool


class TestToolSchema:
    """Test ToolSchema model."""

    def test_tool_schema_creation(self):
        """Test creating a valid tool schema."""
        schema = ToolSchema(
            name="test_tool",
            description="A test tool",
            parameters={
                "type": "object",
                "properties": {
                    "param1": {"type": "string"}
                },
                "required": ["param1"]
            }
        )

        assert schema.name == "test_tool"
        assert schema.description == "A test tool"
        assert "param1" in schema.parameters["properties"]
```

### Step 2: Run test to verify it fails

```bash
cd ui/backend
source .venv/bin/activate
pytest tests/tools/test_base.py::TestToolSchema::test_tool_schema_creation -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'app.tools'"

### Step 3: Create directory structure

```bash
mkdir -p ui/backend/app/tools
mkdir -p ui/backend/tests/tools
touch ui/backend/tests/tools/__init__.py
```

### Step 4: Write minimal implementation

Create `ui/backend/app/tools/base.py`:

```python
"""Base classes for tool system."""
from abc import ABC, abstractmethod
from typing import Dict, Any
from pydantic import BaseModel


class ToolSchema(BaseModel):
    """Schema for tool definition (Gemini function calling format)."""
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema format


class ToolResponse(BaseModel):
    """Standard tool response format."""
    type: str  # "text", "image", "scene", "error", etc.
    message: str
    data: Dict[str, Any] | None = None


class BaseTool(ABC):
    """Base class for all tools."""

    @abstractmethod
    def get_schema(self) -> ToolSchema:
        """Return the tool schema for Gemini function calling."""
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResponse:
        """Execute the tool with given parameters."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name (must match schema name)."""
        pass
```

Create `ui/backend/app/tools/__init__.py`:

```python
"""Tool system initialization."""
from .base import BaseTool, ToolSchema, ToolResponse

__all__ = ['BaseTool', 'ToolSchema', 'ToolResponse']
```

### Step 5: Run test to verify it passes

```bash
pytest tests/tools/test_base.py::TestToolSchema::test_tool_schema_creation -v
```

Expected: PASS

### Step 6: Add test for ToolResponse

Add to `ui/backend/tests/tools/test_base.py`:

```python
class TestToolResponse:
    """Test ToolResponse model."""

    def test_tool_response_creation(self):
        """Test creating a valid tool response."""
        response = ToolResponse(
            type="text",
            message="Response message",
            data={"key": "value"}
        )

        assert response.type == "text"
        assert response.message == "Response message"
        assert response.data["key"] == "value"

    def test_tool_response_without_data(self):
        """Test tool response with no data field."""
        response = ToolResponse(
            type="error",
            message="Error occurred"
        )

        assert response.type == "error"
        assert response.data is None
```

### Step 7: Run tests

```bash
pytest tests/tools/test_base.py -v
```

Expected: All tests PASS

### Step 8: Commit

```bash
git add ui/backend/app/tools/base.py ui/backend/app/tools/__init__.py ui/backend/tests/tools/
git commit -m "feat(tools): add base classes for tool system

- Add ToolSchema, ToolResponse, BaseTool
- Pydantic models for type safety
- Abstract base class for tool interface"
```

---

## Task 2: Tool Registry

**Files:**
- Create: `ui/backend/app/tools/registry.py`
- Modify: `ui/backend/app/tools/__init__.py`
- Test: `ui/backend/tests/tools/test_registry.py`

### Step 1: Write failing test for registry

Create `ui/backend/tests/tools/test_registry.py`:

```python
"""Tests for tool registry."""
import pytest
from app.tools.base import BaseTool, ToolSchema, ToolResponse
from app.tools.registry import ToolRegistry


class MockTool(BaseTool):
    """Mock tool for testing."""

    @property
    def name(self) -> str:
        return "mock_tool"

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name="mock_tool",
            description="A mock tool",
            parameters={"type": "object", "properties": {}}
        )

    async def execute(self, **kwargs) -> ToolResponse:
        return ToolResponse(type="text", message="Mock response")


class TestToolRegistry:
    """Test ToolRegistry."""

    def test_register_tool(self):
        """Test registering a tool."""
        registry = ToolRegistry()
        tool = MockTool()

        registry.register(tool)

        assert "mock_tool" in registry.tools
        assert registry.tools["mock_tool"] == tool

    def test_get_schemas(self):
        """Test getting all tool schemas."""
        registry = ToolRegistry()
        tool = MockTool()
        registry.register(tool)

        schemas = registry.get_schemas()

        assert len(schemas) == 1
        assert schemas[0].name == "mock_tool"

    @pytest.mark.anyio
    async def test_execute_tool(self):
        """Test executing a tool by name."""
        registry = ToolRegistry()
        tool = MockTool()
        registry.register(tool)

        response = await registry.execute_tool("mock_tool")

        assert response.type == "text"
        assert response.message == "Mock response"

    @pytest.mark.anyio
    async def test_execute_unknown_tool_raises(self):
        """Test executing unknown tool raises error."""
        registry = ToolRegistry()

        with pytest.raises(ValueError, match="Unknown tool"):
            await registry.execute_tool("nonexistent_tool")
```

### Step 2: Run test to verify it fails

```bash
pytest tests/tools/test_registry.py::TestToolRegistry::test_register_tool -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'app.tools.registry'"

### Step 3: Write minimal implementation

Create `ui/backend/app/tools/registry.py`:

```python
"""Central registry for all tools."""
from typing import Dict, List
from .base import BaseTool, ToolSchema, ToolResponse


class ToolRegistry:
    """Central registry for all tools."""

    def __init__(self):
        """Initialize empty registry."""
        self.tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool):
        """
        Register a tool.

        Args:
            tool: Tool instance to register
        """
        self.tools[tool.name] = tool

    def get_schemas(self) -> List[ToolSchema]:
        """
        Get all tool schemas for Gemini.

        Returns:
            List of tool schemas
        """
        return [tool.get_schema() for tool in self.tools.values()]

    async def execute_tool(self, tool_name: str, **kwargs) -> ToolResponse:
        """
        Execute a tool by name.

        Args:
            tool_name: Name of tool to execute
            **kwargs: Tool parameters

        Returns:
            Tool response

        Raises:
            ValueError: If tool not found
        """
        if tool_name not in self.tools:
            raise ValueError(f"Unknown tool: {tool_name}")
        return await self.tools[tool_name].execute(**kwargs)


# Global registry instance
registry = ToolRegistry()
```

### Step 4: Run tests to verify they pass

```bash
pytest tests/tools/test_registry.py -v
```

Expected: All tests PASS

### Step 5: Update __init__.py

Modify `ui/backend/app/tools/__init__.py`:

```python
"""Tool system initialization."""
from .base import BaseTool, ToolSchema, ToolResponse
from .registry import ToolRegistry, registry

__all__ = ['BaseTool', 'ToolSchema', 'ToolResponse', 'ToolRegistry', 'registry']
```

### Step 6: Commit

```bash
git add ui/backend/app/tools/registry.py ui/backend/app/tools/__init__.py ui/backend/tests/tools/test_registry.py
git commit -m "feat(tools): add tool registry

- ToolRegistry class for managing tools
- Global registry singleton
- Register, get schemas, execute tool methods"
```

---

## Task 3: Configuration Module

**Files:**
- Create: `ui/backend/app/config.py`
- Test: `ui/backend/tests/test_config.py`

### Step 1: Write failing test

Create `ui/backend/tests/test_config.py`:

```python
"""Tests for configuration."""
from app.config import Settings


class TestSettings:
    """Test Settings class."""

    def test_settings_defaults(self):
        """Test default settings values."""
        settings = Settings()

        assert settings.MAX_IMAGES_PER_REQUEST == 4
        assert settings.IMAGE_STORAGE_DAYS == 7
        assert settings.GEMINI_MODEL == "gemini-2.0-flash"
        assert settings.GEMINI_TIMEOUT == 60
        assert settings.IMAGEN_CONCURRENT_LIMIT == 2
```

### Step 2: Run test to verify it fails

```bash
pytest tests/test_config.py::TestSettings::test_settings_defaults -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'app.config'"

### Step 3: Write minimal implementation

Create `ui/backend/app/config.py`:

```python
"""Configuration for chat backend."""
from pathlib import Path


class Settings:
    """Application settings."""

    # Tool settings
    MAX_IMAGES_PER_REQUEST = 4
    IMAGE_STORAGE_DAYS = 7
    IMAGE_OUTPUT_DIR = Path("app/output/chat_images")

    # Gemini settings
    GEMINI_MODEL = "gemini-2.0-flash"
    GEMINI_TIMEOUT = 60  # seconds

    # Image generation
    IMAGEN_CONCURRENT_LIMIT = 2  # Max parallel image generation


# Global settings instance
settings = Settings()
```

### Step 4: Run test to verify it passes

```bash
pytest tests/test_config.py -v
```

Expected: PASS

### Step 5: Commit

```bash
git add ui/backend/app/config.py ui/backend/tests/test_config.py
git commit -m "feat(config): add configuration module

- Settings class with tool and Gemini config
- Global settings singleton
- Image storage and generation limits"
```

---

## Task 4: Update Gemini Service with Function Calling

**Files:**
- Modify: `ui/backend/app/services/gemini_service.py`
- Test: `ui/backend/tests/services/test_gemini_service.py`

### Step 1: Write failing test

Create `ui/backend/tests/services/test_gemini_service.py`:

```python
"""Tests for Gemini service with function calling."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from app.services.gemini_service import GeminiService
from app.tools.base import ToolSchema


class TestGeminiServiceFunctionCalling:
    """Test Gemini service function calling."""

    @pytest.fixture
    def mock_genai_client(self):
        """Create mock Gemini client."""
        with patch('app.services.gemini_service.GeminiAPI') as mock:
            yield mock

    def test_schema_to_gemini_tool(self, mock_genai_client):
        """Test converting ToolSchema to Gemini tool format."""
        service = GeminiService()
        schema = ToolSchema(
            name="test_tool",
            description="A test tool",
            parameters={
                "type": "object",
                "properties": {
                    "param1": {"type": "string", "description": "First param"}
                },
                "required": ["param1"]
            }
        )

        gemini_tool = service._schema_to_gemini_tool(schema)

        assert gemini_tool["name"] == "test_tool"
        assert gemini_tool["description"] == "A test tool"
        assert "parameters" in gemini_tool
```

### Step 2: Run test to verify it fails

```bash
pytest tests/services/test_gemini_service.py::TestGeminiServiceFunctionCalling::test_schema_to_gemini_tool -v
```

Expected: FAIL with "AttributeError: 'GeminiService' object has no attribute '_schema_to_gemini_tool'"

### Step 3: Add method to GeminiService

Modify `ui/backend/app/services/gemini_service.py`, add after `__init__`:

```python
def _schema_to_gemini_tool(self, schema: 'ToolSchema') -> dict:
    """
    Convert ToolSchema to Gemini function calling format.

    Args:
        schema: Tool schema

    Returns:
        Gemini tool dict
    """
    return {
        "name": schema.name,
        "description": schema.description,
        "parameters": schema.parameters
    }
```

Add import at top:

```python
from typing import Dict, Any, Optional, List
```

### Step 4: Run test to verify it passes

```bash
pytest tests/services/test_gemini_service.py::TestGeminiServiceFunctionCalling::test_schema_to_gemini_tool -v
```

Expected: PASS

### Step 5: Add test for generate_with_tools

Add to `ui/backend/tests/services/test_gemini_service.py`:

```python
@pytest.mark.anyio
async def test_generate_with_tools_no_tool_call(self, mock_genai_client):
    """Test generate_with_tools when no tool is called."""
    service = GeminiService()
    mock_response = Mock()
    mock_response.text = "Regular text response"
    mock_response.candidates = [Mock(function_call=None)]

    with patch.object(service.api, 'generate_content', return_value=mock_response):
        response = await service.generate_with_tools(
            message="Hello",
            conversation_history=[],
            tools=[]
        )

    assert response["type"] == "text"
    assert response["text"] == "Regular text response"
    assert response["tool_call"] is None

@pytest.mark.anyio
async def test_generate_with_tools_with_tool_call(self, mock_genai_client):
    """Test generate_with_tools when tool is called."""
    service = GeminiService()
    mock_function_call = Mock()
    mock_function_call.name = "generate_images"
    mock_function_call.args = {"prompt": "a dragon", "count": 2}

    mock_response = Mock()
    mock_response.candidates = [Mock(function_call=mock_function_call)]

    with patch.object(service.api, 'generate_content', return_value=mock_response):
        response = await service.generate_with_tools(
            message="Show me a dragon",
            conversation_history=[],
            tools=[]
        )

    assert response["type"] == "tool_call"
    assert response["tool_call"]["name"] == "generate_images"
    assert response["tool_call"]["parameters"]["prompt"] == "a dragon"
```

### Step 6: Implement generate_with_tools

Add to `ui/backend/app/services/gemini_service.py`:

```python
async def generate_with_tools(
    self,
    message: str,
    conversation_history: List[Dict[str, str]],
    tools: List['ToolSchema']
) -> Dict[str, Any]:
    """
    Generate response with tool calling support.

    Args:
        message: User message
        conversation_history: Previous messages
        tools: Available tool schemas

    Returns:
        Response dict with type and content
    """
    # Convert tool schemas to Gemini format
    gemini_tools = [self._schema_to_gemini_tool(t) for t in tools]

    # Build prompt with history
    prompt = self._build_chat_prompt(message, {}, conversation_history)

    # Generate with tools if available
    if gemini_tools:
        # For now, simulate tool calling by checking keywords
        # TODO: Implement actual Gemini function calling API when available
        pass

    # Generate response
    response = self.api.generate_content(prompt)

    # Check if response contains function call
    if hasattr(response, 'candidates') and response.candidates:
        candidate = response.candidates[0]
        if hasattr(candidate, 'function_call') and candidate.function_call:
            return {
                "type": "tool_call",
                "tool_call": {
                    "name": candidate.function_call.name,
                    "parameters": dict(candidate.function_call.args)
                },
                "text": None
            }

    # No tool call - return text response
    return {
        "type": "text",
        "text": response.text,
        "tool_call": None
    }
```

### Step 7: Run tests

```bash
pytest tests/services/test_gemini_service.py -v
```

Expected: All tests PASS

### Step 8: Commit

```bash
git add ui/backend/app/services/gemini_service.py ui/backend/tests/services/
git commit -m "feat(gemini): add function calling support

- Add _schema_to_gemini_tool method
- Add generate_with_tools method
- Parse tool calls from Gemini responses"
```

---

## Task 5: Image Generator Tool

**Files:**
- Create: `ui/backend/app/tools/image_generator.py`
- Modify: `ui/backend/app/tools/__init__.py`
- Test: `ui/backend/tests/tools/test_image_generator.py`

### Step 1: Create output directory

```bash
mkdir -p ui/backend/app/output/chat_images
```

### Step 2: Write failing test

Create `ui/backend/tests/tools/test_image_generator.py`:

```python
"""Tests for image generator tool."""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
from app.tools.image_generator import ImageGeneratorTool
from app.tools.base import ToolResponse


class TestImageGeneratorTool:
    """Test ImageGeneratorTool."""

    def test_get_schema(self):
        """Test tool schema."""
        tool = ImageGeneratorTool()
        schema = tool.get_schema()

        assert schema.name == "generate_images"
        assert "prompt" in schema.parameters["properties"]
        assert "count" in schema.parameters["properties"]
        assert "prompt" in schema.parameters["required"]

    def test_name_property(self):
        """Test tool name property."""
        tool = ImageGeneratorTool()
        assert tool.name == "generate_images"

    @pytest.mark.anyio
    async def test_execute_caps_count_at_max(self):
        """Test execute caps count at maximum."""
        tool = ImageGeneratorTool()

        with patch.object(tool, '_generate_single_image', new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = "test.png"

            response = await tool.execute(prompt="test", count=10)

        assert mock_gen.call_count == 4  # Capped at MAX_IMAGES_PER_REQUEST

    @pytest.mark.anyio
    async def test_execute_returns_image_response(self):
        """Test execute returns correct response format."""
        tool = ImageGeneratorTool()

        with patch.object(tool, '_generate_single_image', new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = "test_123.png"

            response = await tool.execute(prompt="a dragon", count=2)

        assert response.type == "image"
        assert "Generated 2 images" in response.message
        assert len(response.data["image_urls"]) == 2
        assert response.data["prompt"] == "a dragon"
```

### Step 3: Run test to verify it fails

```bash
pytest tests/tools/test_image_generator.py::TestImageGeneratorTool::test_get_schema -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'app.tools.image_generator'"

### Step 4: Write minimal implementation

Create `ui/backend/app/tools/image_generator.py`:

```python
"""Image generation tool using Gemini Imagen."""
import asyncio
import uuid
from datetime import datetime
from pathlib import Path
from typing import List
from .base import BaseTool, ToolSchema, ToolResponse
from ..config import settings


class ImageGeneratorTool(BaseTool):
    """Tool for generating images using Gemini Imagen."""

    def __init__(self):
        """Initialize image generator."""
        self.output_dir = settings.IMAGE_OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @property
    def name(self) -> str:
        """Return tool name."""
        return "generate_images"

    def get_schema(self) -> ToolSchema:
        """Return tool schema for Gemini function calling."""
        return ToolSchema(
            name="generate_images",
            description="Generate images based on a text description. Use this when the user asks to create, generate, or show images.",
            parameters={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Detailed description of the image to generate"
                    },
                    "count": {
                        "type": "integer",
                        "description": "Number of images to generate (default: 2, max: 4)",
                        "default": 2
                    }
                },
                "required": ["prompt"]
            }
        )

    async def execute(self, prompt: str, count: int = 2) -> ToolResponse:
        """
        Execute image generation.

        Args:
            prompt: Image description
            count: Number of images (default 2, max 4)

        Returns:
            ToolResponse with image URLs
        """
        # Cap count at maximum
        count = min(count, settings.MAX_IMAGES_PER_REQUEST)

        try:
            # Generate images concurrently
            tasks = [self._generate_single_image(prompt) for _ in range(count)]
            filenames = await asyncio.gather(*tasks)

            # Convert filenames to URLs
            image_urls = [f"/api/images/{fn}" for fn in filenames]

            return ToolResponse(
                type="image",
                message=f"Generated {count} images based on your description.",
                data={
                    "image_urls": image_urls,
                    "prompt": prompt
                }
            )

        except Exception as e:
            return ToolResponse(
                type="error",
                message=f"Failed to generate images: {str(e)}",
                data=None
            )

    async def _generate_single_image(self, prompt: str) -> str:
        """
        Generate a single image.

        Args:
            prompt: Image description

        Returns:
            Filename of generated image
        """
        # TODO: Implement actual Gemini Imagen API call
        # For now, return mock filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = uuid.uuid4().hex[:8]
        filename = f"{timestamp}_{unique_id}.png"

        # Mock: create empty file
        filepath = self.output_dir / filename
        filepath.touch()

        return filename
```

### Step 5: Run tests to verify they pass

```bash
pytest tests/tools/test_image_generator.py -v
```

Expected: All tests PASS

### Step 6: Register tool in __init__.py

Modify `ui/backend/app/tools/__init__.py`:

```python
"""Tool system initialization."""
from .base import BaseTool, ToolSchema, ToolResponse
from .registry import ToolRegistry, registry
from .image_generator import ImageGeneratorTool

# Auto-register tools
registry.register(ImageGeneratorTool())

__all__ = [
    'BaseTool',
    'ToolSchema',
    'ToolResponse',
    'ToolRegistry',
    'registry',
    'ImageGeneratorTool'
]
```

### Step 7: Commit

```bash
git add ui/backend/app/tools/image_generator.py ui/backend/app/tools/__init__.py ui/backend/tests/tools/test_image_generator.py
git commit -m "feat(tools): add image generator tool

- ImageGeneratorTool with Gemini Imagen support
- Auto-register in global registry
- Caps count at MAX_IMAGES_PER_REQUEST
- Returns image URLs in ToolResponse"
```

---

## Task 6: Update Chat Endpoint

**Files:**
- Modify: `ui/backend/app/routers/chat.py`
- Modify: `ui/backend/app/main.py` (add CORS for images)
- Test: `ui/backend/tests/routers/test_chat.py`

### Step 1: Write failing test

Create `ui/backend/tests/routers/test_chat.py`:

```python
"""Tests for chat router with tools."""
import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


class TestChatWithTools:
    """Test chat endpoint with tool support."""

    def test_chat_text_response(self):
        """Test chat returns text response when no tool called."""
        with patch('app.routers.chat.GeminiService') as mock_service:
            mock_instance = mock_service.return_value
            mock_instance.generate_with_tools = AsyncMock(return_value={
                "type": "text",
                "text": "Hello there!",
                "tool_call": None
            })

            response = client.post("/chat", json={
                "message": "Hello",
                "context": {},
                "conversation_history": []
            })

        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "text"
        assert data["message"] == "Hello there!"

    def test_chat_tool_response(self):
        """Test chat executes tool when called."""
        with patch('app.routers.chat.GeminiService') as mock_service, \
             patch('app.routers.chat.registry') as mock_registry:

            mock_instance = mock_service.return_value
            mock_instance.generate_with_tools = AsyncMock(return_value={
                "type": "tool_call",
                "tool_call": {
                    "name": "generate_images",
                    "parameters": {"prompt": "dragon", "count": 2}
                },
                "text": None
            })

            mock_registry.execute_tool = AsyncMock(return_value=type('obj', (object,), {
                'type': 'image',
                'message': 'Generated 2 images',
                'data': {'image_urls': ['/api/images/test.png']}
            })())

            response = client.post("/chat", json={
                "message": "Show me a dragon",
                "context": {},
                "conversation_history": []
            })

        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "image"
        assert "Generated 2 images" in data["message"]
```

### Step 2: Run test to verify it fails

```bash
pytest tests/routers/test_chat.py::TestChatWithTools::test_chat_text_response -v
```

Expected: FAIL (endpoint not using tools yet)

### Step 3: Update chat endpoint

Modify `ui/backend/app/routers/chat.py`:

```python
"""Chat router with tool support."""
from fastapi import APIRouter
from app.lib.types import ChatRequest, ChatResponse
from app.services.gemini_service import GeminiService
from app.tools import registry

router = APIRouter()


@router.post("/chat")
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Main chat endpoint with tool support.

    Flow:
    1. Send user message to Gemini with tool schemas
    2. Gemini decides: respond directly OR call a tool
    3. If tool call: execute tool, get response
    4. Return formatted response to frontend
    """
    gemini = GeminiService()

    # Get all available tool schemas
    tool_schemas = registry.get_schemas()

    # Call Gemini with function calling enabled
    response = await gemini.generate_with_tools(
        message=request.message,
        conversation_history=request.conversation_history or [],
        tools=tool_schemas
    )

    # Check if Gemini wants to call a tool
    if response.get("type") == "tool_call":
        tool_name = response["tool_call"]["name"]
        tool_params = response["tool_call"]["parameters"]

        # Execute the tool
        tool_response = await registry.execute_tool(tool_name, **tool_params)

        # Return tool response
        return ChatResponse(
            message=tool_response.message,
            type=tool_response.type,
            data=tool_response.data
        )

    # No tool call - return text response
    return ChatResponse(
        message=response["text"],
        type="text",
        data=None
    )
```

### Step 4: Run tests to verify they pass

```bash
pytest tests/routers/test_chat.py -v
```

Expected: All tests PASS

### Step 5: Commit

```bash
git add ui/backend/app/routers/chat.py ui/backend/tests/routers/test_chat.py
git commit -m "feat(chat): integrate tool system

- Get tool schemas from registry
- Pass to Gemini with function calling
- Execute tools when called
- Return tool-specific responses"
```

---

## Task 7: Image Serving Endpoint

**Files:**
- Modify: `ui/backend/app/main.py`
- Test: `ui/backend/tests/test_main.py`

### Step 1: Write failing test

Create `ui/backend/tests/test_main.py`:

```python
"""Tests for main app endpoints."""
import pytest
from fastapi.testclient import TestClient
from pathlib import Path
from app.main import app
from app.config import settings


client = TestClient(app)


class TestImageServing:
    """Test image serving endpoint."""

    def test_serve_existing_image(self, tmp_path):
        """Test serving an existing image."""
        # Create test image
        test_image = settings.IMAGE_OUTPUT_DIR / "test_image.png"
        test_image.parent.mkdir(parents=True, exist_ok=True)
        test_image.write_bytes(b"fake image data")

        try:
            response = client.get("/api/images/test_image.png")

            assert response.status_code == 200
            assert response.headers["content-type"] == "image/png"
            assert response.content == b"fake image data"
        finally:
            test_image.unlink()

    def test_serve_nonexistent_image(self):
        """Test serving nonexistent image returns 404."""
        response = client.get("/api/images/nonexistent.png")
        assert response.status_code == 404

    def test_serve_image_path_traversal_blocked(self):
        """Test path traversal attempts are blocked."""
        response = client.get("/api/images/../../../etc/passwd")
        assert response.status_code in [400, 404]
```

### Step 2: Run test to verify it fails

```bash
pytest tests/test_main.py::TestImageServing::test_serve_existing_image -v
```

Expected: FAIL with "404 Not Found" (endpoint doesn't exist)

### Step 3: Add image serving endpoint

Modify `ui/backend/app/main.py`, add after existing routes:

```python
from fastapi.responses import FileResponse
from pathlib import Path
from .config import settings


@app.get("/api/images/{filename}")
async def serve_image(filename: str):
    """
    Serve generated images from chat_images directory.

    Args:
        filename: Image filename

    Returns:
        Image file

    Raises:
        HTTPException: If file not found or invalid filename
    """
    # Security: validate filename (no path traversal)
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    # Only serve .png files
    if not filename.endswith(".png"):
        raise HTTPException(status_code=400, detail="Only PNG files supported")

    file_path = settings.IMAGE_OUTPUT_DIR / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")

    return FileResponse(file_path, media_type="image/png")
```

Add import at top:

```python
from fastapi import HTTPException
```

### Step 4: Run tests to verify they pass

```bash
pytest tests/test_main.py::TestImageServing -v
```

Expected: All tests PASS

### Step 5: Commit

```bash
git add ui/backend/app/main.py ui/backend/tests/test_main.py
git commit -m "feat(api): add image serving endpoint

- GET /api/images/{filename}
- Security: validate filename, block path traversal
- Only serve PNG files from chat_images directory"
```

---

## Task 8: Frontend Types Update

**Files:**
- Modify: `ui/frontend/src/lib/types.ts`
- Test: Manual verification

### Step 1: Update types

Modify `ui/frontend/src/lib/types.ts`:

```typescript
/**
 * TypeScript types for Module Assistant API.
 */

export enum ChatRole {
  USER = 'user',
  ASSISTANT = 'assistant',
  SYSTEM = 'system',
}

export interface Scene {
  section_path: string;
  name: string;
  description: string;
  location_type: string;
  xml_section_id?: string | null;
  image_url?: string | null;
}

export interface ImageData {
  image_urls: string[];
  prompt: string;
}

export interface SceneData {
  scene: Scene;
}

export interface ChatMessage {
  role: ChatRole;
  content: string;
  timestamp: string;
  type?: string;  // NEW: response type
  data?: ImageData | SceneData | Record<string, any> | null;  // NEW: tool-specific data
  scene?: Scene | null;  // Keep for backwards compatibility
}

export interface ChatRequest {
  message: string;
  context?: Record<string, any>;
  conversation_history?: ChatMessage[];
}

export interface ChatResponse {
  message: string;
  type: 'text' | 'image' | 'scene' | 'actor' | 'error';
  data?: ImageData | SceneData | Record<string, any> | null;
  scene?: any | null;
}
```

### Step 2: Verify TypeScript compilation

```bash
cd ui/frontend
npx tsc --noEmit
```

Expected: No errors

### Step 3: Commit

```bash
git add ui/frontend/src/lib/types.ts
git commit -m "feat(types): add tool system types

- Add ImageData, SceneData interfaces
- Add type and data fields to ChatMessage
- Update ChatResponse with tool types"
```

---

## Task 9: ImageCarousel Component

**Files:**
- Create: `ui/frontend/src/components/ImageCarousel.tsx`
- Test: Manual verification

### Step 1: Create component

Create `ui/frontend/src/components/ImageCarousel.tsx`:

```typescript
import { useState } from 'react';
import type { ImageData } from '../lib/types';

interface ImageCarouselProps {
  data: ImageData;
}

export function ImageCarousel({ data }: ImageCarouselProps) {
  const [currentIndex, setCurrentIndex] = useState(0);

  const nextImage = () => {
    setCurrentIndex((prev) => (prev + 1) % data.image_urls.length);
  };

  const prevImage = () => {
    setCurrentIndex((prev) =>
      prev === 0 ? data.image_urls.length - 1 : prev - 1
    );
  };

  return (
    <div
      className="mt-4 max-w-[600px]"
      style={{
        border: '4px double #7d5a3d',
        borderRadius: '4px',
        background: 'linear-gradient(135deg, #f5eee1 0%, #ebe1d2 100%)',
        padding: '16px'
      }}
    >
      {/* Image display */}
      <div className="relative">
        <img
          src={data.image_urls[currentIndex]}
          alt={data.prompt}
          className="w-full h-auto rounded"
          style={{
            boxShadow: '0 4px 10px rgba(0, 0, 0, 0.15)'
          }}
        />

        {/* Navigation arrows (only show if multiple images) */}
        {data.image_urls.length > 1 && (
          <>
            <button
              onClick={prevImage}
              className="absolute left-2 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full flex items-center justify-center transition-all"
              style={{
                background: 'radial-gradient(circle, #8b1f1f 0%, #6d1818 100%)',
                border: '2px solid #5c1515',
                color: '#f5eee1',
                fontSize: '20px',
                cursor: 'pointer',
                boxShadow: '0 4px 10px rgba(0, 0, 0, 0.3)'
              }}
              onMouseEnter={(e) => e.currentTarget.style.opacity = '0.9'}
              onMouseLeave={(e) => e.currentTarget.style.opacity = '1'}
            >
              ◀
            </button>
            <button
              onClick={nextImage}
              className="absolute right-2 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full flex items-center justify-center transition-all"
              style={{
                background: 'radial-gradient(circle, #8b1f1f 0%, #6d1818 100%)',
                border: '2px solid #5c1515',
                color: '#f5eee1',
                fontSize: '20px',
                cursor: 'pointer',
                boxShadow: '0 4px 10px rgba(0, 0, 0, 0.3)'
              }}
              onMouseEnter={(e) => e.currentTarget.style.opacity = '0.9'}
              onMouseLeave={(e) => e.currentTarget.style.opacity = '1'}
            >
              ▶
            </button>
          </>
        )}
      </div>

      {/* Image counter */}
      {data.image_urls.length > 1 && (
        <div
          className="text-center mt-3"
          style={{
            fontFamily: 'Crimson Pro, serif',
            fontSize: '14px',
            color: '#7d5a3d',
            fontWeight: 600
          }}
        >
          {currentIndex + 1} / {data.image_urls.length}
        </div>
      )}
    </div>
  );
}
```

### Step 2: Verify TypeScript compilation

```bash
cd ui/frontend
npx tsc --noEmit
```

Expected: No errors

### Step 3: Commit

```bash
git add ui/frontend/src/components/ImageCarousel.tsx
git commit -m "feat(ui): add ImageCarousel component

- Carousel with prev/next navigation
- Wax seal styled arrow buttons
- Image counter (only if multiple images)
- Parchment border matching existing aesthetic"
```

---

## Task 10: ErrorCard Component

**Files:**
- Create: `ui/frontend/src/components/ErrorCard.tsx`
- Test: Manual verification

### Step 1: Create component

Create `ui/frontend/src/components/ErrorCard.tsx`:

```typescript
interface ErrorCardProps {
  message: string;
}

export function ErrorCard({ message }: ErrorCardProps) {
  return (
    <div
      className="mt-4 max-w-[600px] rounded px-4 py-3"
      style={{
        background: 'rgba(139, 31, 31, 0.1)',
        border: '2px solid #8b1f1f',
        borderRadius: '4px',
        fontFamily: 'IM Fell DW Pica, serif',
        color: '#5c1515'
      }}
    >
      <div className="flex items-start gap-2">
        <span style={{ fontSize: '18px' }}>⚠</span>
        <div>{message}</div>
      </div>
    </div>
  );
}
```

### Step 2: Verify compilation

```bash
cd ui/frontend
npx tsc --noEmit
```

Expected: No errors

### Step 3: Commit

```bash
git add ui/frontend/src/components/ErrorCard.tsx
git commit -m "feat(ui): add ErrorCard component

- Error display with warning icon
- Red tinted background
- Matches parchment aesthetic"
```

---

## Task 11: Update Message Component

**Files:**
- Modify: `ui/frontend/src/components/Message.tsx`
- Test: Manual verification

### Step 1: Update imports

Modify `ui/frontend/src/components/Message.tsx`, update imports:

```typescript
import type { ChatMessage } from '../lib/types';
import { ChatRole } from '../lib/types';
import { SceneCard } from './SceneCard';
import { ImageCarousel } from './ImageCarousel';
import { ErrorCard } from './ErrorCard';
import ReactMarkdown from 'react-markdown';
import type { ImageData, SceneData } from '../lib/types';
```

### Step 2: Add tool-specific rendering

Add after the message bubble closing div, before the existing scene rendering:

```typescript
      {/* Tool-specific rendering */}
      {message.type === 'image' && message.data && (
        <ImageCarousel data={message.data as ImageData} />
      )}

      {message.type === 'error' && (
        <ErrorCard message={message.content} />
      )}
```

Keep existing scene rendering for backwards compatibility:

```typescript
      {/* Render Scene Card if scene data is present */}
      {message.scene && (
        <div className="mt-4">
          <SceneCard scene={message.scene} />
        </div>
      )}
```

### Step 3: Verify compilation

```bash
cd ui/frontend
npx tsc --noEmit
```

Expected: No errors

### Step 4: Commit

```bash
git add ui/frontend/src/components/Message.tsx
git commit -m "feat(ui): update Message component for tools

- Add ImageCarousel for image responses
- Add ErrorCard for error responses
- Dispatch rendering based on message.type
- Keep backwards compatibility with scene"
```

---

## Task 12: Update useChat Hook

**Files:**
- Modify: `ui/frontend/src/hooks/useChat.ts`
- Test: Manual verification

### Step 1: Update response handling

Modify `ui/frontend/src/hooks/useChat.ts`, update the `sendMessage` function to preserve `type` and `data`:

Find this section:

```typescript
const assistantMessage: ChatMessage = {
  role: ChatRole.ASSISTANT,
  content: data.message,
  timestamp: new Date().toISOString(),
  scene: data.scene || null,
};
```

Replace with:

```typescript
const assistantMessage: ChatMessage = {
  role: ChatRole.ASSISTANT,
  content: data.message,
  timestamp: new Date().toISOString(),
  type: data.type || 'text',
  data: data.data || null,
  scene: data.scene || null,  // Keep for backwards compatibility
};
```

### Step 2: Verify compilation

```bash
cd ui/frontend
npx tsc --noEmit
```

Expected: No errors

### Step 3: Commit

```bash
git add ui/frontend/src/hooks/useChat.ts
git commit -m "feat(chat): preserve tool response type and data

- Add type and data fields to assistant messages
- Keep backwards compatibility with scene field"
```

---

## Task 13: Integration Testing

**Files:**
- Create: `ui/backend/tests/integration/test_image_generation_flow.py`
- Test: Run integration test

### Step 1: Write integration test

Create `ui/backend/tests/integration/test_image_generation_flow.py`:

```python
"""Integration test for complete image generation flow."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from app.main import app


client = TestClient(app)


@pytest.mark.integration
class TestImageGenerationFlow:
    """Test complete image generation workflow."""

    def test_full_image_generation_flow(self):
        """Test end-to-end image generation."""
        # Mock Gemini to return tool call
        with patch('app.routers.chat.GeminiService') as mock_service:
            mock_instance = mock_service.return_value
            mock_instance.generate_with_tools = AsyncMock(return_value={
                "type": "tool_call",
                "tool_call": {
                    "name": "generate_images",
                    "parameters": {"prompt": "a majestic dragon", "count": 2}
                },
                "text": None
            })

            # Send chat message
            response = client.post("/chat", json={
                "message": "Show me a majestic dragon",
                "context": {},
                "conversation_history": []
            })

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "image"
        assert "Generated 2 images" in data["message"]
        assert len(data["data"]["image_urls"]) == 2
        assert data["data"]["prompt"] == "a majestic dragon"

        # Verify image URLs are correct format
        for url in data["data"]["image_urls"]:
            assert url.startswith("/api/images/")
            assert url.endswith(".png")
```

### Step 2: Create integration test directory

```bash
mkdir -p ui/backend/tests/integration
touch ui/backend/tests/integration/__init__.py
```

### Step 3: Run integration test

```bash
cd ui/backend
pytest tests/integration/test_image_generation_flow.py -v
```

Expected: PASS

### Step 4: Commit

```bash
git add ui/backend/tests/integration/
git commit -m "test(integration): add image generation flow test

- Test complete workflow: chat -> tool call -> response
- Verify response format and image URLs
- Mock Gemini service for deterministic testing"
```

---

## Task 14: Manual End-to-End Testing

**Files:**
- None (manual testing)

### Step 1: Start backend server

```bash
cd ui/backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

Keep this terminal open.

### Step 2: Start frontend dev server

Open new terminal:

```bash
cd ui/frontend
npm run dev
```

Keep this terminal open. Frontend should be at http://localhost:5173

### Step 3: Test in browser

1. Open http://localhost:5173
2. Try these test cases:
   - Type: "Hello" → Should get text response
   - Type: "/generate-image a dragon" → Should generate images with carousel
   - Type: "show me a castle" → Should generate images (natural language)
   - Type: "create 3 images of a forest" → Should generate 3 images
   - Try carousel navigation (arrows work, counter updates)
   - Try with single image (no arrows/counter shown)

### Step 4: Document results

Create `ui/TESTING.md` with test results:

```markdown
# Manual Testing Results

**Date:** 2025-11-03

## Test Cases

### Text Chat
- [x] Regular text messages work
- [x] Conversation history maintained

### Image Generation
- [x] Explicit command: `/generate-image dragon`
- [x] Natural language: "show me a castle"
- [x] Custom count: "generate 3 images of a forest"
- [x] Count capped at 4 (tested with "create 10 images")

### UI Components
- [x] ImageCarousel displays correctly
- [x] Navigation arrows work (prev/next)
- [x] Image counter updates
- [x] Single image: no arrows/counter
- [x] Multiple images: arrows + counter visible
- [x] Parchment aesthetic matches existing UI

### Error Handling
- [x] Invalid requests show error message
- [x] Error card styling matches design

## Known Issues

None
```

### Step 5: Commit

```bash
git add ui/TESTING.md
git commit -m "docs(ui): add manual testing results

- Document test cases and results
- All features working as expected
- No known issues"
```

---

## Task 15: Update Documentation

**Files:**
- Modify: `ui/CLAUDE.md`
- Modify: `ui/README.md`

### Step 1: Update ui/CLAUDE.md

Add to `ui/CLAUDE.md` after the "Backend" section:

```markdown
### Tool System

The chat backend uses a modular tool system with Gemini function calling.

**Architecture:**
- `app/tools/base.py`: Base classes (BaseTool, ToolSchema, ToolResponse)
- `app/tools/registry.py`: ToolRegistry for managing tools
- `app/tools/image_generator.py`: Image generation tool
- `app/tools/__init__.py`: Auto-registers all tools

**Adding a New Tool:**

1. Create tool class implementing BaseTool:
```python
class MyTool(BaseTool):
    @property
    def name(self) -> str:
        return "my_tool"

    def get_schema(self) -> ToolSchema:
        # Define schema
        pass

    async def execute(self, **kwargs) -> ToolResponse:
        # Implement logic
        pass
```

2. Register in `app/tools/__init__.py`:
```python
from .my_tool import MyTool
registry.register(MyTool())
```

3. Add frontend component if needed (see ImageCarousel for example)

**Image Generation:**
- Tool: `generate_images`
- Default: 2 images
- Max: 4 images
- Storage: `app/output/chat_images/`
- Endpoint: `GET /api/images/{filename}`
```

### Step 2: Update ui/README.md

Add section after "Development Workflow":

```markdown
## Tool System

The chat UI uses a modular tool system for handling specialized requests.

### Available Tools

**Image Generation:**
- Command: `/generate-image [description]`
- Natural language: "show me a dragon", "create an image of..."
- Custom count: "generate 3 images of a forest"
- Max: 4 images per request
- UI: Carousel with navigation arrows

### Adding New Tools

1. Backend: Create tool class in `backend/app/tools/`
2. Frontend: Add component in `frontend/src/components/`
3. Update Message.tsx to dispatch based on response type

See `backend/app/tools/image_generator.py` for reference implementation.
```

### Step 3: Commit

```bash
git add ui/CLAUDE.md ui/README.md
git commit -m "docs(ui): document tool system

- Add tool system architecture to CLAUDE.md
- Document image generation in README.md
- Include instructions for adding new tools"
```

---

## Task 16: Final Verification and Cleanup

**Files:**
- Test all components
- Clean up mock implementations

### Step 1: Run all tests

```bash
cd ui/backend
pytest -v
```

Expected: All tests PASS

### Step 2: Check TypeScript compilation

```bash
cd ui/frontend
npx tsc --noEmit
```

Expected: No errors

### Step 3: Verify git status

```bash
git status
```

Expected: Clean working tree (all changes committed)

### Step 4: Review implementation against design

Review `docs/plans/2025-11-03-chat-ui-tool-system.md` and verify:
- [x] Tool system core implemented
- [x] Image generator tool working
- [x] Chat endpoint integrated
- [x] Image serving endpoint added
- [x] Frontend types updated
- [x] UI components created
- [x] Integration tests passing
- [x] Documentation updated

### Step 5: Final commit

```bash
git commit --allow-empty -m "chore: complete chat UI tool system implementation

All tasks completed:
- Backend tool system with registry
- Image generation tool
- Chat endpoint integration
- Image serving endpoint
- Frontend components (ImageCarousel, ErrorCard)
- Integration tests
- Documentation

Ready for code review and merge."
```

---

## Post-Implementation

### Ready for Code Review

Use @superpowers:requesting-code-review to dispatch code-reviewer agent.

### Ready for Merge

Use @superpowers:finishing-a-development-branch to merge to main.

### Follow-up Tasks

**Not in this plan (future work):**
1. Implement actual Gemini Imagen API call (currently mocked)
2. Add image cleanup job (delete images older than 7 days)
3. Add more tools (scene generator, actor lookup)
4. Add loading states during image generation
5. Add image download button
6. Add style presets for image generation

---

## Rollback Plan

If issues arise:

1. **Feature flag:** Set `ENABLE_TOOL_SYSTEM=false` in config
2. **Disable specific tool:** Comment out registration in `app/tools/__init__.py`
3. **Revert chat endpoint:** Restore original chat.py from main branch
4. **Frontend graceful degradation:** Frontend handles missing tool types

---

## Notes for Engineer

- **TDD:** Write tests first, then implementation
- **Commit frequently:** After each task completion
- **YAGNI:** Don't add features not in the plan
- **DRY:** Reuse existing components and utilities
- **Ask questions:** If anything is unclear, ask before proceeding
- **Run tests often:** After each change, verify tests still pass

**Skills referenced:**
- @superpowers:requesting-code-review (after implementation)
- @superpowers:finishing-a-development-branch (for merge)
- @superpowers:systematic-debugging (if bugs found)
