# D&D Module Assistant - UI Design Specification

## Overview
Chat-based UI for D&D module generation with Gemini integration, inspired by Baldur's Gate 2 aesthetics.

## Design Decisions (from brainstorming session)

### Visual Design
- **Selected Variant:** Variant 1 - Wax Seal
- **Aesthetic:** Fantasy journal with medium aging/wear
- **Color Palette:** Parchment tones (browns, creams, golds)
- **Typography:**
  - Headers: UnifrakturMaguntia (blackletter)
  - Body: IM Fell DW Pica (classical serif)
  - UI Elements: Crimson Pro
- **Key Elements:**
  - Red wax seal send button with fleur-de-lis symbol
  - Pen icon (✒) for AI assistant
  - Parchment background with subtle texture
  - Ornate borders and decorative elements

### Technology Stack

#### Frontend
- **Framework:** React
- **Component Library:** shadcn/ui
- **Layout:** Traditional chat interface with input at bottom
- **Styling:** Tailwind CSS (via shadcn/ui)

#### Backend
- **Framework:** FastAPI
- **API Style:** REST API
- **AI Integration:** Google Gemini API
- **Deployment:** Local only

### Features

#### Chat Interface
- **Message Types:**
  - User messages (right-aligned)
  - Assistant messages (left-aligned)
  - System messages (centered)

- **Input Methods:**
  - Slash commands (primary): `/generate-scene`, `/list-scenes`, `/help`
  - Natural language (secondary)

- **Results Display:**
  - Inline scene cards in chat
  - Expandable/collapsible content
  - Generated images displayed in cards

#### Function Calling
- **Primary Function:** Scene generation
  - `/generate-scene [description]` - Generate scene with AI artwork
  - `/list-scenes [chapter]` - List all scenes in a chapter

- **Future Functions:**
  - Actor/NPC editing
  - Chapter navigation
  - Module content search

#### Context Awareness
The assistant should have access to:
- Current module content (XML)
- Available actors/NPCs
- Scene library
- Chapter structure

### User Experience Goals
- **Immersion:** Fantasy journal feel maintains D&D atmosphere
- **Practicality:** Clear, readable interface for actual work
- **Balance:** Medieval aesthetic without sacrificing usability

## Implementation Plan

### Phase 1: Frontend Setup
1. Initialize React project with Vite
2. Install shadcn/ui and configure Tailwind
3. Set up project structure
4. Import Google Fonts (UnifrakturMaguntia, IM Fell DW Pica, Crimson Pro)

### Phase 2: UI Components
1. Convert wax seal HTML/CSS to React components:
   - `<AppContainer>` - Main layout
   - `<Header>` - Title bar
   - `<ChatWindow>` - Scrollable message area
   - `<Message>` - Individual message bubble
   - `<SceneCard>` - Scene result display
   - `<InputArea>` - Text input with wax seal button

2. Implement shadcn/ui components:
   - Input field
   - Button (customized as wax seal)
   - Card (for scene results)
   - ScrollArea (for chat window)

### Phase 3: Backend Setup
1. Initialize FastAPI project
2. Set up Gemini API client
3. Create endpoints:
   - `POST /api/chat` - Main chat endpoint
   - `POST /api/generate-scene` - Scene generation
   - `GET /api/scenes` - List scenes
   - `GET /api/actors` - List actors
4. Integrate with existing module generation pipeline

### Phase 4: Integration
1. Connect frontend to backend API
2. Implement slash command parsing
3. Add message history management
4. Integrate Gemini streaming responses
5. Add scene image generation

### Phase 5: Polish
1. Add animations (fade-in for messages)
2. Implement loading states
3. Error handling and user feedback
4. Accessibility improvements
5. Performance optimization

## File Structure
```
dnd_module_gen/
├── ui/                          # New UI application
│   ├── frontend/                # React app
│   │   ├── src/
│   │   │   ├── components/
│   │   │   │   ├── AppContainer.tsx
│   │   │   │   ├── Header.tsx
│   │   │   │   ├── ChatWindow.tsx
│   │   │   │   ├── Message.tsx
│   │   │   │   ├── SceneCard.tsx
│   │   │   │   └── InputArea.tsx
│   │   │   ├── hooks/
│   │   │   │   ├── useChat.ts
│   │   │   │   └── useSlashCommands.ts
│   │   │   ├── lib/
│   │   │   │   └── api.ts
│   │   │   ├── App.tsx
│   │   │   └── main.tsx
│   │   ├── public/
│   │   └── package.json
│   │
│   └── backend/                 # FastAPI app
│       ├── app/
│       │   ├── main.py
│       │   ├── routers/
│       │   │   ├── chat.py
│       │   │   ├── scenes.py
│       │   │   └── actors.py
│       │   ├── services/
│       │   │   ├── gemini.py
│       │   │   └── module_integration.py
│       │   └── models/
│       │       ├── chat.py
│       │       └── scene.py
│       └── requirements.txt
│
└── ui_prototypes/               # HTML/CSS prototypes (reference only)
```

## API Specification

### Chat Endpoint
```
POST /api/chat
Request:
{
  "message": string,
  "context": {
    "module": string?,
    "chapter": string?,
    "conversation_history": Message[]
  }
}

Response:
{
  "message": string,
  "type": "text" | "scene" | "list",
  "data": any?,
  "scene": Scene?
}
```

### Scene Generation
```
POST /api/generate-scene
Request:
{
  "description": string,
  "style": string?,
  "chapter": string?
}

Response:
{
  "scene": {
    "name": string,
    "description": string,
    "image_url": string?,
    "section_path": string
  }
}
```

## Next Steps
1. Create React app structure
2. Set up FastAPI backend
3. Implement core chat functionality
4. Integrate with existing module generation pipeline
