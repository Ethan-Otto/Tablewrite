# D&D Module Assistant - Backend API

FastAPI backend for D&D module generation and FoundryVTT integration.

## Project Structure

```
ui/
├── backend/          # FastAPI backend
│   ├── app/
│   │   ├── main.py           # FastAPI app entry point
│   │   ├── routers/          # API routes
│   │   ├── services/         # Business logic
│   │   ├── tools/            # Chat tools (actor creation, images)
│   │   └── websocket/        # Foundry WebSocket handlers
│   └── tests/
└── README.md         # This file
```

## Quick Start

```bash
cd ui/backend
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

Backend runs on: http://localhost:8000 (Swagger docs at /docs)

## Features

- **REST API**: Endpoints for actors, journals, scenes, files
- **WebSocket**: Real-time communication with FoundryVTT module
- **Gemini Integration**: AI-powered chat and content generation
- **Tool System**: Modular tools for actor creation, image generation

## Environment Variables

Create `.env` in project root or `ui/backend/`:

```
GeminiImageAPI=<your_gemini_api_key>
FOUNDRY_URL=http://localhost:30000
```

## Testing

```bash
cd ui/backend
uv run pytest
```

## FoundryVTT Integration

The backend communicates with the Tablewrite Assistant Foundry module via WebSocket.

See `foundry-module/tablewrite-assistant/` for the Foundry module.

## License

Part of the dnd_module_gen project.
