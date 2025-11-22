# Chat UI Tool System Design

**Date:** 2025-11-03
**Status:** Design Complete, Ready for Implementation
**Context:** Modular tool system for D&D Module Assistant chat UI

## Overview

This design introduces a modular tool system for the chat UI, with image generation as the first tool. The system uses Gemini's native function calling to automatically route user requests to appropriate tools. The architecture is designed to make adding new tools (scene generation, actor lookup, etc.) trivial.

## Requirements

### Functional Requirements

1. **Image Generation Tool**:
   - Generate images from text descriptions using Gemini Imagen
   - Default: 2 images per request
   - Support custom counts (user can specify 1-4 images)
   - Two trigger methods:
     - Explicit command: `/generate-image [description]`
     - Natural language detection: "show me a dragon", "create an image of..."

2. **Carousel UI**:
   - Display images in a single message bubble
   - Navigation arrows to switch between images (if multiple)
   - Image counter: "1 / 2"
   - Smooth fade transitions
   - Match existing parchment/wax seal aesthetic

3. **Loading States**:
   - Show placeholder with animated spinner while generating
   - Clear indication of progress

4. **Error Handling**:
   - Display friendly error messages in chat bubble
   - Handle API failures, content policy violations, timeouts
   - Cap image count at maximum (4 images)

### Non-Functional Requirements

1. **Modularity**: Adding new tools requires zero changes to core chat logic
2. **Testability**: Tools are independently testable
3. **Performance**: Async tool execution (image generation takes 10-30 seconds)
4. **Maintainability**: Clear separation of concerns, tool-specific code isolated

## Architecture

### High-Level Flow

```
User Message
    ↓
Chat Endpoint (/chat)
    ↓
Gemini Function Calling API (with tool schemas)
    ↓
Tool Registry (decides which tool to call)
    ↓
Tool Executor (runs the selected tool)
    ↓
Tool Response Formatter
    ↓
ChatResponse (type-specific: text, image, scene, actor, etc.)
    ↓
Frontend renders based on response type
```

### Component Architecture

#### Backend Components

1. **Tool System Core** (`ui/backend/app/tools/`):

   - `base.py`: Base classes and interfaces
     - `BaseTool` (abstract class all tools inherit from)
     - `ToolSchema` (Pydantic model for tool definitions)
     - `ToolResponse` (standard response format)

   - `registry.py`: Central tool registry
     - `ToolRegistry` (singleton that manages all tools)
     - Methods: `register()`, `get_schemas()`, `execute_tool()`

   - `image_generator.py`: Image generation tool
     - `ImageGeneratorTool` (implements BaseTool)
     - Integrates with Gemini Imagen API
     - Saves images to `app/output/chat_images/`

2. **Chat Integration** (`ui/backend/app/routers/chat.py`):
   - Updated to use tool registry
   - Passes tool schemas to Gemini
   - Routes tool calls to appropriate handlers
   - Tool-agnostic (no hardcoded tool logic)

3. **Gemini Service** (`ui/backend/app/services/gemini_service.py`):
   - New method: `generate_with_tools()`
   - Uses Gemini 2.0+ function calling API
   - Maintains conversation history across tool calls

4. **Image Serving** (`ui/backend/app/main.py`):
   - New endpoint: `GET /api/images/{filename}`
   - Serves images from `app/output/chat_images/`
   - Security: validates filename (no path traversal)

#### Frontend Components

1. **Type Definitions** (`ui/frontend/src/lib/types.ts`):
   - Updated `ChatResponse` with `type` field
   - Updated `ChatMessage` with `type` and `data` fields
   - New interfaces: `ImageData`, `SceneData`

2. **Message Component** (`ui/frontend/src/components/Message.tsx`):
   - Updated to dispatch based on `message.type`
   - Renders tool-specific components conditionally
   - Maintains existing aesthetic

3. **ImageCarousel Component** (`ui/frontend/src/components/ImageCarousel.tsx`):
   - Displays images with navigation arrows
   - State management for current image index
   - Parchment-styled border matching existing UI
   - Only shows arrows/counter if multiple images

4. **ErrorCard Component** (`ui/frontend/src/components/ErrorCard.tsx`):
   - Displays error messages with red tint
   - Matches existing card styling

## Detailed Design

### Tool Interface

All tools implement the `BaseTool` interface:

```python
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

### Image Generator Tool

**Schema:**
```python
{
    "name": "generate_images",
    "description": "Generate images based on a text description. Use this when the user asks to create, generate, or show images.",
    "parameters": {
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
}
```

**Execution Flow:**
1. Validate count (cap at 4)
2. Generate images using Gemini Imagen API (parallel, max 2 concurrent)
3. Save images to `app/output/chat_images/<timestamp>_<uuid>.png`
4. Return `ToolResponse` with:
   - `type: "image"`
   - `message: "Generated {count} images based on your description."`
   - `data: {image_urls: [...], prompt: "..."}`

**Error Handling:**
- API failure → Return error response with friendly message
- Content policy violation → "Unable to generate images for this request. Try a different description."
- Timeout (>60s) → Cancel and return timeout error
- Invalid count → Auto-cap at 4, add warning to message

### Chat Endpoint Integration

**Request Flow:**

```python
@router.post("/chat")
async def chat(request: ChatRequest) -> ChatResponse:
    gemini = GeminiService()

    # Get all available tool schemas
    tool_schemas = registry.get_schemas()

    # Call Gemini with function calling enabled
    response = await gemini.generate_with_tools(
        message=request.message,
        conversation_history=request.conversation_history,
        tools=tool_schemas
    )

    # Check if Gemini wants to call a tool
    if response.has_tool_call():
        tool_name = response.tool_call.name
        tool_params = response.tool_call.parameters

        # Execute the tool
        tool_response = await registry.execute_tool(tool_name, **tool_params)

        return ChatResponse(
            message=tool_response.message,
            type=tool_response.type,
            data=tool_response.data
        )

    # No tool call - return text response
    return ChatResponse(
        message=response.text,
        type="text"
    )
```

**Key Points:**
- Chat endpoint is tool-agnostic
- Gemini decides whether to call a tool
- Tool execution is async
- Conversation history maintained across tool calls

### Frontend Response Handling

**Message Component Dispatch Logic:**

```typescript
export function Message({ message }: MessageProps) {
  const isUser = message.role === ChatRole.USER;

  return (
    <div className="w-full">
      {/* Standard message bubble */}
      <div className={`flex gap-[15px] ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
        <Avatar isUser={isUser} />
        <MessageBubble isUser={isUser}>
          <ReactMarkdown>{message.content}</ReactMarkdown>
        </MessageBubble>
      </div>

      {/* Tool-specific rendering */}
      {message.type === 'image' && message.data && (
        <ImageCarousel data={message.data as ImageData} />
      )}

      {message.type === 'scene' && message.data && (
        <SceneCard scene={(message.data as SceneData).scene} />
      )}

      {message.type === 'error' && (
        <ErrorCard message={message.content} />
      )}
    </div>
  );
}
```

**ImageCarousel Component:**

```typescript
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
    <div className="mt-4 max-w-[600px]" style={{
      border: '4px double #7d5a3d',
      borderRadius: '4px',
      background: 'linear-gradient(135deg, #f5eee1 0%, #ebe1d2 100%)',
      padding: '16px'
    }}>
      {/* Image display */}
      <div className="relative">
        <img
          src={data.image_urls[currentIndex]}
          alt={data.prompt}
          className="w-full h-auto rounded"
        />

        {/* Navigation arrows (only if multiple images) */}
        {data.image_urls.length > 1 && (
          <>
            <button onClick={prevImage} className="carousel-arrow left">◀</button>
            <button onClick={nextImage} className="carousel-arrow right">▶</button>
          </>
        )}
      </div>

      {/* Image counter */}
      {data.image_urls.length > 1 && (
        <div className="text-center mt-2 text-sm text-[#7d5a3d]">
          {currentIndex + 1} / {data.image_urls.length}
        </div>
      )}
    </div>
  );
}
```

**Styling:**
- Carousel arrows: Circular buttons matching wax seal aesthetic
- Image border: `4px double #7d5a3d` (matches existing cards)
- Background: Parchment gradient
- Transitions: Smooth fade between images

## File Organization

### Backend Structure

```
ui/backend/
├── app/
│   ├── main.py                    # FastAPI app, adds image serving endpoint
│   ├── config.py                  # NEW: Settings (max images, storage, etc.)
│   ├── routers/
│   │   └── chat.py                # Updated with tool integration
│   ├── services/
│   │   └── gemini_service.py      # Updated with function calling
│   ├── tools/                     # NEW: Tool system
│   │   ├── __init__.py           # Auto-registers all tools
│   │   ├── base.py               # BaseTool, ToolSchema, ToolResponse
│   │   ├── registry.py           # ToolRegistry singleton
│   │   └── image_generator.py    # ImageGeneratorTool
│   └── output/
│       └── chat_images/           # Generated images stored here
└── requirements.txt               # Add: Pillow
```

### Frontend Structure

```
ui/frontend/
├── src/
│   ├── components/
│   │   ├── Message.tsx            # Updated with type-based rendering
│   │   ├── ImageCarousel.tsx      # NEW: Image carousel component
│   │   ├── ErrorCard.tsx          # NEW: Error display component
│   │   ├── ChatWindow.tsx         # (unchanged)
│   │   ├── InputArea.tsx          # (unchanged)
│   │   └── Header.tsx             # (unchanged)
│   └── lib/
│       └── types.ts               # Updated with tool types
```

## Configuration

### Backend Settings

```python
# ui/backend/app/config.py
class Settings:
    # Tool settings
    MAX_IMAGES_PER_REQUEST = 4
    IMAGE_STORAGE_DAYS = 7
    IMAGE_OUTPUT_DIR = "app/output/chat_images"

    # Gemini settings
    GEMINI_MODEL = "gemini-2.0-flash"
    GEMINI_TIMEOUT = 60  # seconds

    # Image generation
    IMAGEN_CONCURRENT_LIMIT = 2  # Max parallel image generation
```

## Adding New Tools

The tool system is designed to make adding new tools trivial. Here's the complete process:

### Step 1: Create Tool Class

```python
# ui/backend/app/tools/my_new_tool.py
from .base import BaseTool, ToolSchema, ToolResponse

class MyNewTool(BaseTool):
    @property
    def name(self) -> str:
        return "my_tool"

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name="my_tool",
            description="Description of what this tool does",
            parameters={
                "type": "object",
                "properties": {
                    "param1": {
                        "type": "string",
                        "description": "Description of param1"
                    }
                },
                "required": ["param1"]
            }
        )

    async def execute(self, param1: str) -> ToolResponse:
        # Implement tool logic here
        result = await self._do_something(param1)

        return ToolResponse(
            type="my_tool",
            message="Tool executed successfully",
            data={"result": result}
        )
```

### Step 2: Register Tool

```python
# ui/backend/app/tools/__init__.py
from .registry import registry
from .image_generator import ImageGeneratorTool
from .my_new_tool import MyNewTool  # Import new tool

# Auto-register tools
registry.register(ImageGeneratorTool())
registry.register(MyNewTool())  # Register new tool

__all__ = ['registry']
```

### Step 3: Add Frontend Component (if needed)

```typescript
// ui/frontend/src/components/MyToolComponent.tsx
interface MyToolProps {
  data: MyToolData;
}

export function MyToolComponent({ data }: MyToolProps) {
  return (
    <div className="tool-result">
      {/* Render tool-specific UI */}
    </div>
  );
}
```

### Step 4: Update Message Component

```typescript
// ui/frontend/src/components/Message.tsx
{message.type === 'my_tool' && message.data && (
  <MyToolComponent data={message.data as MyToolData} />
)}
```

**That's it!** No changes to chat endpoint, Gemini service, or core logic needed.

## Testing Strategy

### Backend Tests

1. **Tool System Tests** (`tests/ui/backend/tools/`):
   - `test_registry.py`: Tool registration, schema generation, execution
   - `test_image_generator.py`: Image generation, error handling, count validation
   - Mock Gemini Imagen API responses

2. **Integration Tests**:
   - End-to-end chat flow with tool calling
   - Real Gemini API calls (marked `@pytest.mark.integration`)
   - Verify image files created and served

3. **Unit Tests**:
   - Intent classification (various phrasings)
   - Parameter extraction (counts, prompts)
   - Error handling (API failures, timeouts, content policy)

### Frontend Tests

1. **Component Tests**:
   - `ImageCarousel`: Navigation, boundary conditions, single vs multiple images
   - `Message`: Rendering different types (text, image, error)
   - `ErrorCard`: Error message display

2. **Integration Tests**:
   - Complete user flow: send message → tool call → display result
   - Image loading states
   - Carousel navigation

### Manual Testing Checklist

- [ ] `/generate-image dragon` produces 2 images
- [ ] Natural language "show me a castle" produces images
- [ ] "generate 3 images of a forest" produces 3 images
- [ ] "create 10 images" caps at 4 and shows warning
- [ ] Carousel navigation works (arrows, wrapping)
- [ ] Single image doesn't show arrows/counter
- [ ] Error handling displays friendly messages
- [ ] Images persist across page refresh
- [ ] Multiple image requests in same conversation work
- [ ] Loading spinner appears while generating

## Security Considerations

1. **Image Serving**:
   - Validate filename (no `..`, `/`, path traversal)
   - Only serve `.png` files from `chat_images` directory
   - No directory listing

2. **Rate Limiting**:
   - Max 10 image generation requests per minute per user (future enhancement)
   - Track requests by IP or session

3. **Content Policy**:
   - Gemini Imagen has built-in safety filters
   - Don't expose raw API errors (may contain sensitive info)
   - Log violations for monitoring

4. **Storage**:
   - Auto-cleanup: Delete images older than 7 days
   - Max 2MB per image (Gemini default)
   - Monitor disk usage

## Performance Considerations

1. **Async Execution**:
   - Image generation is async (10-30 seconds)
   - Frontend shows loading state immediately
   - Max 2 concurrent image generations per request

2. **Caching**:
   - Consider caching tool schemas (regenerated on every chat request)
   - Cache intent classification for 5 seconds (avoid re-analyzing same message)

3. **Image Optimization**:
   - Gemini Imagen returns compressed PNGs
   - Consider WebP conversion for smaller sizes (future enhancement)

## Future Enhancements

1. **Additional Tools**:
   - Scene generator tool
   - Actor/NPC lookup tool
   - Map asset search tool
   - Spell lookup tool

2. **Image Features**:
   - Image editing/regeneration
   - Style presets (oil painting, watercolor, etc.)
   - Aspect ratio control
   - Download images button

3. **System Improvements**:
   - Tool usage analytics
   - User preferences (default image count, style)
   - Tool enable/disable via UI
   - Streaming responses (text first, then images)

## Implementation Notes

### Dependencies

**Backend:**
- `google-generativeai>=0.4.0` (already installed)
- `Pillow>=10.0.0` (NEW - for image handling)
- `aiofiles>=23.0.0` (NEW - async file operations)

**Frontend:**
- No new dependencies needed

### Migration Path

1. Implement tool system core (base classes, registry)
2. Update Gemini service with function calling
3. Implement image generator tool
4. Update chat endpoint to use registry
5. Add image serving endpoint
6. Update frontend types
7. Implement ImageCarousel component
8. Update Message component
9. Test end-to-end
10. Deploy

### Rollback Plan

- Feature flag: `ENABLE_TOOL_SYSTEM=false` falls back to old chat logic
- Tools can be individually disabled via registry
- Frontend gracefully handles missing tool types

## Open Questions

None - design is complete and validated.

## Conclusion

This design provides a clean, modular tool system that makes adding new capabilities to the chat UI trivial. The use of Gemini's native function calling keeps the system simple and maintainable. Image generation serves as the first tool, with a clear path for adding scene generation, actor lookup, and other D&D-specific tools in the future.
