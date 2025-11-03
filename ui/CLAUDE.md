# UI - D&D Module Assistant

This directory contains the full-stack UI for the D&D Module Assistant - a chat interface for working with D&D module content, generating scenes, and managing actors.

## Architecture

### Stack Overview
- **Frontend**: React 19 + TypeScript + Vite
- **Backend**: FastAPI (Python) with Google Gemini API
- **Styling**: Tailwind CSS v3 with custom theme
- **Design**: Wax seal aesthetic with parchment textures

### Directory Structure
```
ui/
├── frontend/          # React + Vite frontend
│   ├── src/
│   │   ├── components/    # React components
│   │   │   ├── Header.tsx
│   │   │   ├── ChatWindow.tsx
│   │   │   ├── InputArea.tsx
│   │   │   └── Message.tsx
│   │   ├── hooks/         # React hooks
│   │   │   └── useChat.ts
│   │   ├── lib/           # Types and utilities
│   │   │   └── types.ts
│   │   ├── App.tsx        # Root component
│   │   └── index.css      # Global styles
│   └── package.json
└── backend/           # FastAPI backend
    ├── app/
    │   ├── main.py        # FastAPI app entry point
    │   ├── routers/       # API routes
    │   │   └── chat.py
    │   └── services/      # Business logic
    │       └── gemini_service.py
    └── requirements.txt
```

## Frontend

### Component Architecture

**Layout Flow** (fixed 96vh container):
```
App.tsx (h-screen, overflow-hidden)
└── Container (96vh, flex-col)
    ├── Header (py-3)
    ├── ChatWindow (flex-1, overflow-y-auto) ← Only scrollable element
    └── InputArea (pt-[25px], pb-0)
```

**Key Components**:

1. **Header.tsx**
   - Title with decorative flourishes (❦)
   - Gradient: `#b89d7d` → `#9d8565` (light to dark)
   - Font: `UnifrakturMaguntia` cursive
   - Minimal padding: `py-3`

2. **ChatWindow.tsx**
   - Main message display area
   - Only scrollable element in the UI
   - Parchment background with subtle grid overlay
   - Minimal padding: `pt-2`, `pb-2`
   - Auto-scrolls to bottom on new messages

3. **InputArea.tsx**
   - Text input with wax seal send button
   - Gradient: `#b89d7d` → `#9d8565` (light to dark, matches Header)
   - Padding: `pt-[25px]`, `pb-0` (no bottom padding)
   - Helper text: "Press Enter to send • Shift+Enter for new line"
   - **Wax Seal Button**: Red gradient with fleur-de-lis emblem, ribbon underneath

4. **Message.tsx**
   - Individual message bubbles
   - User messages: right-aligned, brown card
   - Assistant messages: left-aligned, parchment card with icon
   - Markdown rendering via `react-markdown`

### Styling Philosophy

**Color Palette**:
- Parchment light: `#f8f2e6` / `rgb(248, 242, 230)`
- Parchment medium: `#e4d4b9` / `rgb(228, 212, 185)`
- Parchment dark: `#b49d7d` / `rgb(180, 157, 125)`
- Brown accent: `#7d5a3d` / `rgb(125, 90, 61)`
- Dark brown: `#5c3d2e` / `rgb(92, 61, 46)`
- Wax red: `#8b1f1f` / `rgb(139, 31, 31)`

**Typography**:
- Headings: `UnifrakturMaguntia` (medieval blackletter)
- Body: `IM Fell DW Pica` (old-style serif)
- UI elements: `Crimson Pro` (modern serif)

**Spacing Strategy**:
- Maximize vertical space for chat (96vh container)
- Minimal padding throughout: Header (`py-3`), ChatWindow (`pt-2`, `pb-2`), InputArea (`pt-[25px]`, `pb-0`)
- Outer container: `p-2` (8px all sides)
- Page locked: `html, body` have `overflow: hidden` (no page scrolling)

**Visual Effects**:
- Double borders: `4px double #7d5a3d`
- Box shadows for depth: `0 30px 60px rgba(0, 0, 0, 0.4)`
- Parchment texture: Radial gradients with aging spots overlay
- Gradients: Light to dark (creates visual weight)

### Critical Implementation Details

1. **No Page Scrolling**:
   - `html, body`: `height: 100vh`, `overflow: hidden`
   - Outer container: `h-screen overflow-hidden`
   - Only ChatWindow scrolls: `overflow-y-auto`

2. **Gradient Consistency**:
   - Header and InputArea use same gradient direction (light→dark)
   - No overlay gradients (removed dark overlays that caused banding)
   - No inset shadows (caused visual artifacts)

3. **Markdown Rendering**:
   - Uses `react-markdown` with Tailwind prose classes
   - Custom code styling: `prose-code:text-sm prose-code:bg-[rgba(125,90,61,0.1)]`
   - Commands (like `/help`) rendered as inline code

4. **Chat State Management**:
   - `useChat` hook handles WebSocket/API communication
   - Messages stored in state array
   - Auto-scroll on new messages via `useEffect` + `scrollIntoView`

### Running the Frontend

```bash
cd ui/frontend
npm install
npm run dev  # Runs on http://localhost:5173
```

**Common Issues**:
- Browser cache: Use Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows) for hard refresh
- Dev server crashes: `killall node && rm -rf .vite && npm run dev`
- Port conflicts: Check for other processes on port 5173

## Backend

### API Architecture

**Endpoints** (FastAPI):
- `POST /chat` - Main chat endpoint
  - Accepts: `{"message": str, "context": dict, "conversation_history": list}`
  - Returns: `{"message": str, "type": "text"}`
- `GET /health` - Health check

**Key Services**:

1. **GeminiService** (`app/services/gemini_service.py`)
   - Handles Google Gemini API calls
   - `generate_chat_response()` - Main chat generation
   - `_build_chat_prompt()` - Formats prompt with conversation history
   - Uses `gemini-2.5-pro` model

2. **Chat Router** (`app/routers/chat.py`)
   - Converts conversation history to dict format
   - Passes context and history to Gemini
   - Error handling for API failures

### Environment Configuration

Create `.env` in `ui/backend/`:
```
GEMINI_API_KEY=<your_api_key>
CORS_ORIGINS=http://localhost:5173
```

### Running the Backend

```bash
cd ui/backend
uv venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
uv pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Runs on http://localhost:8000

## Development Workflow

### Making UI Changes

1. **Styling Changes**:
   - Edit component inline styles or Tailwind classes
   - Changes hot-reload automatically via Vite HMR
   - If changes don't appear: hard refresh browser (Cmd+Shift+R)

2. **Component Changes**:
   - Edit `.tsx` files in `frontend/src/components/`
   - TypeScript errors show in terminal and browser
   - Use React DevTools for debugging state

3. **Backend Changes**:
   - Edit Python files in `backend/app/`
   - FastAPI auto-reloads with `--reload` flag
   - Test endpoints at http://localhost:8000/docs (Swagger UI)

### Testing Changes

**Frontend**:
```bash
# Build for production
npm run build

# Preview production build
npm run preview
```

**Backend**:
```bash
# Manual API testing
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "context": {}, "conversation_history": []}'
```

**Integration**:
- Open browser to http://localhost:5173
- Type messages and verify responses
- Check browser console for errors
- Check terminal for backend logs

## Design System

### Component Patterns

**Message Cards**:
- User: Right-aligned, `bg-[#d4c4a8]`, small icon
- Assistant: Left-aligned, parchment background, larger icon

**Buttons**:
- Wax seal: Circular red gradient with emblem
- Hover: `opacity: 0.95`
- Active: `opacity: 0.9`, `scale: 0.98`

**Input Fields**:
- Background: `rgba(245, 238, 225, 0.95)`
- Border: `2px solid #7d5a3d`
- Focus: Border color change + shadow ring
- Font: `IM Fell DW Pica` serif

### Spacing Scale

- Extra tight: `2px` (`pt-0.5`, `pb-0`)
- Tight: `8px` (`pt-2`, `pb-2`, `p-2`)
- Normal: `12px` (`py-3`)
- Loose: `25px` (`pt-[25px]`)
- Extra loose: `40px` (`px-10`)

### Accessibility Notes

- Text contrast meets WCAG AA standards
- Keyboard navigation: Enter to send, Shift+Enter for new line
- Screen readers: ARIA labels on interactive elements
- Focus indicators on all inputs

## Common Tasks

### Add a New Command

1. Update backend to handle command in `chat.py`
2. Add command documentation to system prompt
3. Update placeholder text if needed: `/generate-scene [description]`

### Change Theme Colors

1. Update color palette in `index.css` CSS variables
2. Update component inline styles to reference new colors
3. Test contrast ratios for accessibility

### Modify Message Rendering

1. Edit `Message.tsx` component
2. Adjust Tailwind prose classes for styling
3. Update `react-markdown` components prop if needed

### Debug Conversation History

1. Check browser DevTools Network tab for `/chat` requests
2. Verify `conversation_history` array in request payload
3. Check backend logs for prompt formatting
4. Test with simple messages first

## Known Issues & Solutions

**Issue**: Browser cache prevents changes from appearing
**Solution**: Hard refresh (Cmd+Shift+R) or clear cache in DevTools

**Issue**: Weird shadow/gradient artifacts on InputArea
**Solution**: Ensure no overlay gradients or inset shadows in styles

**Issue**: Page scrolls instead of ChatWindow
**Solution**: Verify `html, body` have `overflow: hidden`

**Issue**: Dev server crashes with CSS errors
**Solution**: `killall node && rm -rf .vite && npm run dev`

**Issue**: Conversation history not working
**Solution**: Check `conversation_history` parameter passed to Gemini API

## Future Enhancements

- [ ] Add loading states for long Gemini responses
- [ ] Implement command autocomplete
- [ ] Add image generation for scenes
- [ ] Support file uploads for module PDFs
- [ ] Add user authentication
- [ ] Persist chat history to database
- [ ] Add export chat functionality
- [ ] Implement typing indicators
- [ ] Add markdown syntax highlighting for code blocks
- [ ] Support for actor stat blocks in chat

## References

- React 19 docs: https://react.dev
- Tailwind CSS: https://tailwindcss.com
- FastAPI: https://fastapi.tiangolo.com
- Google Gemini API: https://ai.google.dev
- Vite: https://vitejs.dev
