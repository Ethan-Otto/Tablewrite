# Foundry Chat Sidebar Design

## Overview

Add a new sidebar tab to FoundryVTT that provides AI chat functionality identical to the web UI. Primary goal: convenience (no browser tab switching).

## Key Decisions

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| Location | New sidebar tab | Discoverable, follows Foundry conventions |
| Styling | Foundry-native | Uses CSS variables, adapts to themes |
| Communication | HTTP to `/chat` | Simple, request/response fits HTTP |
| Entity operations | Existing WebSocket | Unchanged, tools still work |
| Persistence | None | Fresh conversation each session |
| Features | Full parity | Same backend, same capabilities |
| Pop-out support | No | Sidebar-only is sufficient |
| Compatibility | v11-v13 | Render hook works on all versions |

## Architecture

### Data Flow

```
User types message in Foundry sidebar
    ↓
TablewriteTab.sendMessage()
    ↓
chat-service.ts → HTTP POST /chat (with conversation history)
    ↓
Backend → Gemini (tools execute via existing WebSocket if needed)
    ↓
HTTP response → TablewriteTab updates UI
```

### Component Structure

```
foundry-module/tablewrite-assistant/
├── src/
│   ├── main.ts                    # MODIFY - add tab registration hook
│   ├── ui/
│   │   ├── TablewriteTab.ts       # NEW - chat UI class
│   │   └── chat-service.ts        # NEW - HTTP client
├── styles/
│   └── tablewrite-tab.css         # NEW - Foundry-native styles
├── lang/
│   └── en.json                    # MODIFY - add new strings
├── module.json                    # MODIFY - add CSS file
└── tests/
    └── ui/
        ├── chat-service.test.ts   # NEW - unit tests
        └── chat-integration.test.ts # NEW - integration test
```

## Implementation Details

### Tab Registration (v12/v13 Compatible)

```typescript
// main.ts
Hooks.on('renderSidebar', (app: Application, html: JQuery, context?: unknown, options?: { parts?: string[] }) => {
  // v13: Skip partial re-renders
  if (options?.parts && !options.parts.includes('sidebar')) return;

  const tabsContainer = html.find('.sidebar-tabs');
  if (!tabsContainer.length) return;

  // Prevent duplicates (important for v13 re-renders)
  if (tabsContainer.find('[data-tab="tablewrite"]').length) return;

  // Add tab button
  const tabButton = $(`
    <a class="item" data-tab="tablewrite" data-tooltip="${game.i18n.localize('TABLEWRITE_ASSISTANT.TabTooltip')}">
      <i class="fas fa-hat-wizard"></i>
    </a>
  `);
  tabsContainer.append(tabButton);

  // Add tab content container
  const sidebar = html.find('#sidebar');
  sidebar.append('<section id="tablewrite" class="sidebar-tab" data-tab="tablewrite"></section>');

  // Initialize tab when clicked (lazy initialization)
  tabButton.on('click', () => {
    const container = document.getElementById('tablewrite');
    if (container && !container.dataset.initialized) {
      container.dataset.initialized = 'true';
      new TablewriteTab(container).render();
    }
  });
});
```

### TablewriteTab Class

```typescript
// src/ui/TablewriteTab.ts

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

class TablewriteTab {
  private container: HTMLElement;
  private messages: ChatMessage[] = [];
  private isLoading: boolean = false;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  render(): void {
    this.container.innerHTML = `
      <div class="tablewrite-chat">
        <div class="tablewrite-messages"></div>
        <form class="tablewrite-input-form">
          <textarea
            class="tablewrite-input"
            placeholder="${game.i18n.localize('TABLEWRITE_ASSISTANT.Placeholder')}"
            rows="2"
          ></textarea>
          <button type="submit" class="tablewrite-send">
            <i class="fas fa-paper-plane"></i>
          </button>
        </form>
      </div>
    `;
    this.activateListeners();
  }

  private activateListeners(): void {
    const form = this.container.querySelector('.tablewrite-input-form');
    const input = this.container.querySelector('.tablewrite-input') as HTMLTextAreaElement;

    form?.addEventListener('submit', (e) => {
      e.preventDefault();
      this.sendMessage(input.value);
      input.value = '';
    });

    // Enter to send, Shift+Enter for newline
    input?.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        form?.dispatchEvent(new Event('submit'));
      }
    });
  }

  async sendMessage(content: string): Promise<void> {
    if (!content.trim() || this.isLoading) return;

    // Add user message
    this.messages.push({ role: 'user', content, timestamp: new Date() });
    this.renderMessages();

    // Send to backend
    this.isLoading = true;
    this.updateLoadingState();

    try {
      const response = await chatService.send(content, this.messages);
      this.messages.push({ role: 'assistant', content: response, timestamp: new Date() });
    } catch (error) {
      ui.notifications?.error(game.i18n.localize('TABLEWRITE_ASSISTANT.ChatError'));
      this.messages.push({
        role: 'assistant',
        content: `**Error:** Could not reach backend. Is the server running?`,
        timestamp: new Date()
      });
    }

    this.isLoading = false;
    this.renderMessages();
  }

  private renderMessages(): void {
    const container = this.container.querySelector('.tablewrite-messages');
    if (!container) return;

    container.innerHTML = this.messages.map(msg => `
      <div class="tablewrite-message tablewrite-message--${msg.role}">
        <div class="tablewrite-message-content">${this.formatContent(msg.content)}</div>
      </div>
    `).join('');

    container.scrollTop = container.scrollHeight;
  }

  private formatContent(content: string): string {
    // Basic markdown: **bold**, *italic*, `code`
    return content
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/`(.*?)`/g, '<code>$1</code>')
      .replace(/\n/g, '<br>');
  }

  private updateLoadingState(): void {
    const btn = this.container.querySelector('.tablewrite-send');
    btn?.classList.toggle('loading', this.isLoading);
  }
}
```

### Chat Service

```typescript
// src/ui/chat-service.ts

import { getBackendUrl } from '../settings';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

interface ChatResponse {
  message: string;
  type: string;
}

class ChatService {
  private getUrl(): string {
    return getBackendUrl();
  }

  async send(message: string, history: ChatMessage[]): Promise<string> {
    const url = `${this.getUrl()}/chat`;

    // Format history for backend (matches web UI format)
    const conversationHistory = history.slice(0, -1).map(msg => ({
      role: msg.role,
      content: msg.content
    }));

    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message,
        context: {},
        conversation_history: conversationHistory
      })
    });

    if (!response.ok) {
      throw new Error(`Chat request failed: ${response.status}`);
    }

    const data: ChatResponse = await response.json();
    return data.message;
  }
}

export const chatService = new ChatService();
```

### Styling (Foundry-Native)

```css
/* styles/tablewrite-tab.css */

.tablewrite-chat {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 0.5rem;
}

.tablewrite-messages {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.tablewrite-message {
  padding: 0.5rem;
  border-radius: 4px;
  font-size: var(--font-size-12);
  line-height: 1.4;
}

.tablewrite-message--user {
  background: rgba(0, 0, 0, 0.1);
  margin-left: 1rem;
}

.tablewrite-message--assistant {
  background: rgba(255, 255, 255, 0.1);
  border-left: 2px solid var(--color-border-highlight);
  margin-right: 1rem;
}

.tablewrite-input-form {
  display: flex;
  gap: 0.25rem;
}

.tablewrite-input {
  flex: 1;
  resize: none;
  font-family: var(--font-primary);
  font-size: var(--font-size-12);
}

.tablewrite-send {
  width: 2rem;
  padding: 0;
}

.tablewrite-send.loading {
  opacity: 0.5;
  pointer-events: none;
}

.tablewrite-message-content code {
  background: rgba(0, 0, 0, 0.2);
  padding: 0.1rem 0.25rem;
  border-radius: 2px;
  font-family: var(--font-mono);
}
```

### Localization

```json
{
  "TABLEWRITE_ASSISTANT.TabTooltip": "Tablewrite AI",
  "TABLEWRITE_ASSISTANT.Placeholder": "Ask me anything about D&D...",
  "TABLEWRITE_ASSISTANT.ChatError": "Failed to send message",
  "TABLEWRITE_ASSISTANT.Send": "Send"
}
```

## Error Handling

| Scenario | Handling |
|----------|----------|
| Backend not running | Inline error message + notification toast |
| Network failure | Same as above |
| Empty message | Silently ignored |
| Double-submit | `isLoading` flag prevents |
| Long response (30s+) | No timeout, loading state shown |

## Testing Strategy

### Unit Tests
- ChatService payload format
- ChatService error handling
- Message formatting

### Integration Test
- Send message to real backend, verify response

### Manual Checklist
- Tab appears in sidebar
- Click opens chat UI
- Send/receive messages work
- Enter sends, Shift+Enter newlines
- Loading state visible
- Error handling works
- Works after Foundry reload

## Not In Scope

- Streaming responses (future enhancement)
- Conversation persistence
- Pop-out window support
- Foundry-specific commands (token selection, etc.)
