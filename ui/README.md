# D&D Module Assistant UI

A fantasy-themed chat interface for D&D module generation powered by Google Gemini AI. Features a wax seal aesthetic inspired by Baldur's Gate 2.

## Project Structure

```
ui/
├── backend/          # FastAPI backend
├── frontend/         # React + TypeScript frontend
└── README.md         # This file
```

## Quick Start

### 1. Start Backend Server

```bash
cd ui/backend
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

Backend runs on: http://localhost:8000

### 2. Start Frontend Dev Server

```bash
cd ui/frontend
npm install
npm run dev
```

Frontend runs on: http://localhost:5173

### 3. Open Application

Navigate to http://localhost:5173 in your browser.

## Features

- **Chat Interface**: Natural language and slash command support
- **Wax Seal Aesthetic**: Parchment colors, medieval fonts, fleur-de-lis flourishes
- **Slash Commands**:
  - `/help` - Show available commands
  - `/generate-scene [description]` - Generate D&D scene with AI
  - `/list-scenes [chapter]` - List all scenes
  - `/list-actors` - List all actors/NPCs
- **Scene Generation**: AI-generated scene descriptions with visual cards
- **Gemini Integration**: Real-time AI responses powered by Gemini 2.0 Flash
- **Auto-scroll**: Chat automatically scrolls to show latest messages

## Architecture

- **Frontend**: React 19 + TypeScript + Vite + shadcn/ui + Tailwind CSS
- **Backend**: FastAPI + Pydantic + Google Gemini API
- **Communication**: REST API with JSON payloads

## Environment Variables

Create `.env` in `ui/backend/`:

```
GeminiImageAPI=<your_gemini_api_key>
```

Create `.env.local` in `ui/frontend/`:

```
VITE_API_URL=http://localhost:8000
```

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

## Development

See individual README files:
- [Backend Documentation](./backend/README.md)
- [Frontend Documentation](./frontend/README.md)

## Design System

- **Colors**: Parchment tones (browns, creams, golds)
- **Fonts**:
  - Headers: UnifrakturMaguntia (blackletter)
  - Body: IM Fell DW Pica (classical serif)
  - UI Elements: Crimson Pro
- **Key Elements**:
  - Red wax seal send button with fleur-de-lis symbol
  - Pen icon (✒) for AI assistant
  - Parchment gradient backgrounds
  - Ornate borders and medieval styling

## Testing

The backend includes unit tests. Run them with:

```bash
cd ui/backend
uv run pytest
```

## Future Enhancements

- [ ] WebSocket support for streaming responses
- [ ] Scene image generation integration
- [ ] Actor/NPC editing interface
- [ ] Chapter navigation
- [ ] Module content search
- [ ] Persistent chat history
- [ ] Multiple module support

## License

Part of the dnd_module_gen project.
