# Foundry Chat Sidebar Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a sidebar tab to FoundryVTT that provides AI chat functionality via HTTP to the backend `/chat` endpoint.

**Architecture:** New sidebar tab registered via `renderSidebar` hook, lazy-initialized `TablewriteTab` class manages UI state and HTTP communication, chat service handles request/response to backend.

**Tech Stack:** TypeScript, FoundryVTT v11-v13, Vitest for testing, CSS with Foundry CSS variables

---

## Task 1: Add Localization Strings

**Files:**
- Modify: `foundry-module/tablewrite-assistant/lang/en.json`

**Step 1: Add the new localization strings**

Edit `lang/en.json` to add chat-related strings:

```json
{
  "TABLEWRITE_ASSISTANT.SettingsBackendUrl": "Backend URL",
  "TABLEWRITE_ASSISTANT.SettingsBackendUrlHint": "URL of your Tablewrite server (e.g., http://localhost:8000)",
  "TABLEWRITE_ASSISTANT.Connected": "Connected to Tablewrite",
  "TABLEWRITE_ASSISTANT.Disconnected": "Disconnected from Tablewrite",
  "TABLEWRITE_ASSISTANT.CreatedActor": "Created actor: {name}",
  "TABLEWRITE_ASSISTANT.CreatedJournal": "Created journal: {name}",
  "TABLEWRITE_ASSISTANT.CreatedScene": "Created scene: {name}",
  "TABLEWRITE_ASSISTANT.TabTooltip": "Tablewrite AI",
  "TABLEWRITE_ASSISTANT.Placeholder": "Ask me anything about D&D...",
  "TABLEWRITE_ASSISTANT.ChatError": "Failed to send message",
  "TABLEWRITE_ASSISTANT.Send": "Send"
}
```

**Step 2: Commit**

```bash
git add foundry-module/tablewrite-assistant/lang/en.json
git commit -m "feat: add chat sidebar localization strings"
```

---

## Task 2: Create Chat Service with Tests (TDD)

**Files:**
- Create: `foundry-module/tablewrite-assistant/src/ui/chat-service.ts`
- Create: `foundry-module/tablewrite-assistant/tests/ui/chat-service.test.ts`

**Step 1: Write the failing test**

Create `tests/ui/chat-service.test.ts`:

```typescript
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock fetch globally
const mockFetch = vi.fn();
globalThis.fetch = mockFetch;

// Mock getBackendUrl
vi.mock('../../src/settings.js', () => ({
  getBackendUrl: () => 'http://localhost:8000'
}));

describe('ChatService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.resetModules();
  });

  describe('send', () => {
    it('sends POST request to /api/chat with correct payload', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ message: 'Hello!', type: 'text' })
      });

      const { chatService } = await import('../../src/ui/chat-service');

      const history = [
        { role: 'user' as const, content: 'Hi', timestamp: new Date() },
        { role: 'assistant' as const, content: 'Hello', timestamp: new Date() }
      ];

      await chatService.send('How are you?', history);

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/chat',
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
        })
      );

      // Verify body structure
      const callArgs = mockFetch.mock.calls[0];
      const body = JSON.parse(callArgs[1].body);
      expect(body.message).toBe('How are you?');
      expect(body.context).toEqual({});
      expect(body.conversation_history).toHaveLength(2);
      expect(body.conversation_history[0].role).toBe('user');
      expect(body.conversation_history[0].content).toBe('Hi');
    });

    it('returns the message from response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ message: 'I am doing well!', type: 'text' })
      });

      const { chatService } = await import('../../src/ui/chat-service');

      const result = await chatService.send('Hello', []);

      expect(result).toBe('I am doing well!');
    });

    it('throws error when response is not ok', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500
      });

      const { chatService } = await import('../../src/ui/chat-service');

      await expect(chatService.send('Hello', [])).rejects.toThrow('Chat request failed: 500');
    });

    it('excludes current message from conversation history', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ message: 'Response', type: 'text' })
      });

      const { chatService } = await import('../../src/ui/chat-service');

      // History includes the current message (last item)
      const history = [
        { role: 'user' as const, content: 'First message', timestamp: new Date() },
        { role: 'assistant' as const, content: 'First response', timestamp: new Date() },
        { role: 'user' as const, content: 'Current message', timestamp: new Date() }
      ];

      await chatService.send('Current message', history);

      const callArgs = mockFetch.mock.calls[0];
      const body = JSON.parse(callArgs[1].body);
      // Should only include first 2 messages (excluding current)
      expect(body.conversation_history).toHaveLength(2);
      expect(body.conversation_history[1].content).toBe('First response');
    });
  });
});
```

**Step 2: Run test to verify it fails**

Run: `cd foundry-module/tablewrite-assistant && npm test -- tests/ui/chat-service.test.ts`
Expected: FAIL with "Cannot find module"

**Step 3: Create the chat service implementation**

Create `src/ui/chat-service.ts`:

```typescript
/**
 * Chat service for HTTP communication with backend.
 */

import { getBackendUrl } from '../settings.js';

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: Date;
}

interface ChatResponse {
  message: string;
  type: string;
  data?: Record<string, unknown>;
}

class ChatService {
  /**
   * Send a message to the backend chat endpoint.
   * @param message - The user's message
   * @param history - Full conversation history (current message is last item)
   * @returns The assistant's response message
   */
  async send(message: string, history: ChatMessage[]): Promise<string> {
    const url = `${getBackendUrl()}/api/chat`;

    // Exclude the current message from history (it's the last item)
    const conversationHistory = history.slice(0, -1).map(msg => ({
      role: msg.role,
      content: msg.content,
      timestamp: msg.timestamp?.toISOString() ?? new Date().toISOString()
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

**Step 4: Run test to verify it passes**

Run: `cd foundry-module/tablewrite-assistant && npm test -- tests/ui/chat-service.test.ts`
Expected: PASS (all 4 tests)

**Step 5: Commit**

```bash
git add foundry-module/tablewrite-assistant/src/ui/chat-service.ts foundry-module/tablewrite-assistant/tests/ui/chat-service.test.ts
git commit -m "feat: add chat service with HTTP client for backend communication"
```

---

## Task 3: Create TablewriteTab Class with Tests (TDD)

**Files:**
- Create: `foundry-module/tablewrite-assistant/src/ui/TablewriteTab.ts`
- Create: `foundry-module/tablewrite-assistant/tests/ui/TablewriteTab.test.ts`

**Step 1: Write the failing tests**

Create `tests/ui/TablewriteTab.test.ts`:

```typescript
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock chatService
const mockSend = vi.fn();
vi.mock('../../src/ui/chat-service.js', () => ({
  chatService: { send: mockSend }
}));

// Mock game.i18n
const mockI18n = {
  localize: vi.fn((key: string) => {
    const translations: Record<string, string> = {
      'TABLEWRITE_ASSISTANT.Placeholder': 'Ask me anything about D&D...',
      'TABLEWRITE_ASSISTANT.ChatError': 'Failed to send message'
    };
    return translations[key] ?? key;
  })
};

// Mock ui.notifications
const mockNotifications = {
  error: vi.fn()
};

// @ts-ignore
globalThis.game = { i18n: mockI18n };
// @ts-ignore
globalThis.ui = { notifications: mockNotifications };

describe('TablewriteTab', () => {
  let container: HTMLElement;

  beforeEach(() => {
    vi.clearAllMocks();
    container = document.createElement('div');
    document.body.appendChild(container);
  });

  afterEach(() => {
    document.body.removeChild(container);
    vi.resetModules();
  });

  describe('render', () => {
    it('renders chat UI structure', async () => {
      const { TablewriteTab } = await import('../../src/ui/TablewriteTab');
      const tab = new TablewriteTab(container);

      tab.render();

      expect(container.querySelector('.tablewrite-chat')).toBeTruthy();
      expect(container.querySelector('.tablewrite-messages')).toBeTruthy();
      expect(container.querySelector('.tablewrite-input-form')).toBeTruthy();
      expect(container.querySelector('.tablewrite-input')).toBeTruthy();
      expect(container.querySelector('.tablewrite-send')).toBeTruthy();
    });

    it('sets placeholder text from localization', async () => {
      const { TablewriteTab } = await import('../../src/ui/TablewriteTab');
      const tab = new TablewriteTab(container);

      tab.render();

      const input = container.querySelector('.tablewrite-input') as HTMLTextAreaElement;
      expect(input.placeholder).toBe('Ask me anything about D&D...');
    });
  });

  describe('sendMessage', () => {
    it('adds user message to display', async () => {
      mockSend.mockResolvedValueOnce('Hello!');
      const { TablewriteTab } = await import('../../src/ui/TablewriteTab');
      const tab = new TablewriteTab(container);
      tab.render();

      await tab.sendMessage('Hi there');

      const messages = container.querySelectorAll('.tablewrite-message');
      expect(messages.length).toBeGreaterThanOrEqual(1);
      expect(container.querySelector('.tablewrite-message--user')).toBeTruthy();
    });

    it('adds assistant response to display', async () => {
      mockSend.mockResolvedValueOnce('Hello! How can I help?');
      const { TablewriteTab } = await import('../../src/ui/TablewriteTab');
      const tab = new TablewriteTab(container);
      tab.render();

      await tab.sendMessage('Hi there');

      const assistantMessage = container.querySelector('.tablewrite-message--assistant');
      expect(assistantMessage).toBeTruthy();
      expect(assistantMessage?.textContent).toContain('Hello! How can I help?');
    });

    it('does not send empty messages', async () => {
      const { TablewriteTab } = await import('../../src/ui/TablewriteTab');
      const tab = new TablewriteTab(container);
      tab.render();

      await tab.sendMessage('   ');

      expect(mockSend).not.toHaveBeenCalled();
    });

    it('shows error message on failure', async () => {
      mockSend.mockRejectedValueOnce(new Error('Network error'));
      const { TablewriteTab } = await import('../../src/ui/TablewriteTab');
      const tab = new TablewriteTab(container);
      tab.render();

      await tab.sendMessage('Hello');

      expect(mockNotifications.error).toHaveBeenCalled();
      const assistantMessage = container.querySelector('.tablewrite-message--assistant');
      expect(assistantMessage?.textContent).toContain('Error');
    });
  });

  describe('formatContent', () => {
    it('converts bold markdown to strong tags', async () => {
      mockSend.mockResolvedValueOnce('This is **bold** text');
      const { TablewriteTab } = await import('../../src/ui/TablewriteTab');
      const tab = new TablewriteTab(container);
      tab.render();

      await tab.sendMessage('test');

      const assistantMessage = container.querySelector('.tablewrite-message--assistant');
      expect(assistantMessage?.innerHTML).toContain('<strong>bold</strong>');
    });

    it('converts italic markdown to em tags', async () => {
      mockSend.mockResolvedValueOnce('This is *italic* text');
      const { TablewriteTab } = await import('../../src/ui/TablewriteTab');
      const tab = new TablewriteTab(container);
      tab.render();

      await tab.sendMessage('test');

      const assistantMessage = container.querySelector('.tablewrite-message--assistant');
      expect(assistantMessage?.innerHTML).toContain('<em>italic</em>');
    });

    it('converts inline code markdown to code tags', async () => {
      mockSend.mockResolvedValueOnce('Use the `command` here');
      const { TablewriteTab } = await import('../../src/ui/TablewriteTab');
      const tab = new TablewriteTab(container);
      tab.render();

      await tab.sendMessage('test');

      const assistantMessage = container.querySelector('.tablewrite-message--assistant');
      expect(assistantMessage?.innerHTML).toContain('<code>command</code>');
    });

    it('converts newlines to br tags', async () => {
      mockSend.mockResolvedValueOnce('Line 1\nLine 2');
      const { TablewriteTab } = await import('../../src/ui/TablewriteTab');
      const tab = new TablewriteTab(container);
      tab.render();

      await tab.sendMessage('test');

      const assistantMessage = container.querySelector('.tablewrite-message--assistant');
      expect(assistantMessage?.innerHTML).toContain('<br>');
    });
  });

  describe('keyboard handling', () => {
    it('submits on Enter key', async () => {
      mockSend.mockResolvedValueOnce('Response');
      const { TablewriteTab } = await import('../../src/ui/TablewriteTab');
      const tab = new TablewriteTab(container);
      tab.render();

      const input = container.querySelector('.tablewrite-input') as HTMLTextAreaElement;
      input.value = 'Hello';

      const event = new KeyboardEvent('keydown', { key: 'Enter', shiftKey: false });
      input.dispatchEvent(event);

      // Wait for async send
      await new Promise(resolve => setTimeout(resolve, 10));

      expect(mockSend).toHaveBeenCalledWith('Hello', expect.any(Array));
    });

    it('allows Shift+Enter for newline without submitting', async () => {
      const { TablewriteTab } = await import('../../src/ui/TablewriteTab');
      const tab = new TablewriteTab(container);
      tab.render();

      const input = container.querySelector('.tablewrite-input') as HTMLTextAreaElement;
      input.value = 'Hello';

      const event = new KeyboardEvent('keydown', { key: 'Enter', shiftKey: true });
      input.dispatchEvent(event);

      await new Promise(resolve => setTimeout(resolve, 10));

      expect(mockSend).not.toHaveBeenCalled();
    });
  });
});
```

**Step 2: Run test to verify it fails**

Run: `cd foundry-module/tablewrite-assistant && npm test -- tests/ui/TablewriteTab.test.ts`
Expected: FAIL with "Cannot find module"

**Step 3: Create the TablewriteTab implementation**

Create `src/ui/TablewriteTab.ts`:

```typescript
/**
 * Tablewrite sidebar tab - chat UI for AI assistant.
 */

import { chatService, ChatMessage } from './chat-service.js';

export class TablewriteTab {
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
        content: '**Error:** Could not reach backend. Is the server running?',
        timestamp: new Date()
      });
    }

    this.isLoading = false;
    this.renderMessages();
    this.updateLoadingState();
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

**Step 4: Run test to verify it passes**

Run: `cd foundry-module/tablewrite-assistant && npm test -- tests/ui/TablewriteTab.test.ts`
Expected: PASS (all tests)

**Step 5: Commit**

```bash
git add foundry-module/tablewrite-assistant/src/ui/TablewriteTab.ts foundry-module/tablewrite-assistant/tests/ui/TablewriteTab.test.ts
git commit -m "feat: add TablewriteTab class for sidebar chat UI"
```

---

## Task 4: Add CSS Styles

**Files:**
- Modify: `foundry-module/tablewrite-assistant/styles/module.css`

**Step 1: Add the chat sidebar styles**

Replace contents of `styles/module.css`:

```css
/* Tablewrite module styles */

/* Chat container fills sidebar tab */
.tablewrite-chat {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 0.5rem;
}

/* Messages area - scrollable */
.tablewrite-messages {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

/* Individual message bubble */
.tablewrite-message {
  padding: 0.5rem;
  border-radius: 4px;
  font-size: var(--font-size-12);
  line-height: 1.4;
}

/* User message - right aligned */
.tablewrite-message--user {
  background: rgba(0, 0, 0, 0.1);
  margin-left: 1rem;
}

/* Assistant message - left aligned with accent border */
.tablewrite-message--assistant {
  background: rgba(255, 255, 255, 0.1);
  border-left: 2px solid var(--color-border-highlight);
  margin-right: 1rem;
}

/* Input form - bottom of sidebar */
.tablewrite-input-form {
  display: flex;
  gap: 0.25rem;
}

/* Text input */
.tablewrite-input {
  flex: 1;
  resize: none;
  font-family: var(--font-primary);
  font-size: var(--font-size-12);
}

/* Send button */
.tablewrite-send {
  width: 2rem;
  padding: 0;
}

/* Loading state - disabled */
.tablewrite-send.loading {
  opacity: 0.5;
  pointer-events: none;
}

/* Code styling in messages */
.tablewrite-message-content code {
  background: rgba(0, 0, 0, 0.2);
  padding: 0.1rem 0.25rem;
  border-radius: 2px;
  font-family: var(--font-mono);
}
```

**Step 2: Verify CSS file is referenced in module.json**

Check `module.json` - it already has `"styles": ["styles/module.css"]` so no change needed.

**Step 3: Commit**

```bash
git add foundry-module/tablewrite-assistant/styles/module.css
git commit -m "feat: add CSS styles for chat sidebar"
```

---

## Task 5: Register Sidebar Tab Hook

**Files:**
- Modify: `foundry-module/tablewrite-assistant/src/main.ts`

**Step 1: Add the sidebar tab registration hook**

Update `src/main.ts` to add the renderSidebar hook:

```typescript
/**
 * Tablewrite Assistant - FoundryVTT Module
 * Create D&D content through natural language.
 */

import { registerSettings, getBackendUrl } from './settings.js';
import { TablewriteClient } from './websocket/client.js';
import { TablewriteTab } from './ui/TablewriteTab.js';

// Module-scoped client instance
export let client: TablewriteClient | null = null;

/**
 * Initialize module settings.
 */
Hooks.once('init', () => {
  console.log('[Tablewrite Assistant] Initializing...');
  registerSettings();
});

/**
 * Connect to backend when Foundry is ready.
 */
Hooks.once('ready', () => {
  console.log('[Tablewrite Assistant] Foundry ready, connecting to backend...');

  const backendUrl = getBackendUrl();
  client = new TablewriteClient(backendUrl);
  client.connect();
});

/**
 * Register sidebar tab for chat UI.
 */
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

/**
 * Disconnect on close.
 */
Hooks.once('close', () => {
  if (client) {
    client.disconnect();
    client = null;
  }
});
```

**Step 2: Commit**

```bash
git add foundry-module/tablewrite-assistant/src/main.ts
git commit -m "feat: register sidebar tab for chat UI"
```

---

## Task 6: Build and Manual Test

**Files:**
- No file changes - verification only

**Step 1: Build the TypeScript**

Run: `cd foundry-module/tablewrite-assistant && npm run build`
Expected: No TypeScript errors, `dist/` folder updated

**Step 2: Restart Foundry (if running)**

Refresh Foundry browser tab or restart Foundry to load updated module.

**Step 3: Manual verification checklist**

1. Tab appears in sidebar with hat-wizard icon
2. Click tab opens chat UI
3. Input field shows placeholder text
4. Type message and press Enter - sends message
5. User message appears on right
6. Assistant response appears on left (after backend responds)
7. Loading state visible during request
8. Error message appears if backend not running
9. Shift+Enter creates newline without sending
10. Works after Foundry reload

**Step 4: Commit verification**

```bash
git add -A
git commit -m "chore: verify build and manual testing complete"
```

---

## Task 7: Add Integration Test

**Files:**
- Create: `foundry-module/tablewrite-assistant/tests/ui/chat-integration.test.ts`

**Step 1: Write the integration test**

Create `tests/ui/chat-integration.test.ts`:

```typescript
import { describe, it, expect, beforeAll, afterAll } from 'vitest';

/**
 * Integration test - requires backend running at localhost:8000
 *
 * Run with: npm test -- tests/ui/chat-integration.test.ts
 *
 * Prerequisites:
 * 1. Start backend: cd ui/backend && uvicorn app.main:app --reload --port 8000
 */
describe('Chat Integration', () => {
  const BACKEND_URL = 'http://localhost:8000';

  // Check if backend is available
  let backendAvailable = false;

  beforeAll(async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/health`);
      backendAvailable = response.ok;
    } catch {
      backendAvailable = false;
    }
  });

  it('can send message to /api/chat and receive response', async () => {
    if (!backendAvailable) {
      console.warn('Backend not available - skipping integration test');
      return;
    }

    const response = await fetch(`${BACKEND_URL}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: '/help',
        context: {},
        conversation_history: []
      })
    });

    expect(response.ok).toBe(true);

    const data = await response.json();
    expect(data.message).toBeTruthy();
    expect(data.type).toBe('text');
    expect(data.message).toContain('Available Commands');
  });

  it('handles conversation history correctly', async () => {
    if (!backendAvailable) {
      console.warn('Backend not available - skipping integration test');
      return;
    }

    const response = await fetch(`${BACKEND_URL}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: 'What did I just ask?',
        context: {},
        conversation_history: [
          { role: 'user', content: 'What is a goblin?', timestamp: new Date().toISOString() },
          { role: 'assistant', content: 'A goblin is a small humanoid creature...', timestamp: new Date().toISOString() }
        ]
      })
    });

    expect(response.ok).toBe(true);

    const data = await response.json();
    expect(data.message).toBeTruthy();
    // Response should reference the previous question about goblins
    // (exact content depends on Gemini but it should acknowledge context)
  });
});
```

**Step 2: Run integration test (with backend running)**

Prerequisites:
```bash
# Terminal 1: Start backend
cd ui/backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000
```

Run: `cd foundry-module/tablewrite-assistant && npm test -- tests/ui/chat-integration.test.ts`
Expected: PASS (2 tests) if backend running, or skip messages if not

**Step 3: Commit**

```bash
git add foundry-module/tablewrite-assistant/tests/ui/chat-integration.test.ts
git commit -m "test: add integration test for chat HTTP communication"
```

---

## Task 8: Run Full Test Suite

**Files:**
- No file changes - verification only

**Step 1: Run all module tests**

Run: `cd foundry-module/tablewrite-assistant && npm test`
Expected: All tests pass (existing + new tests)

**Step 2: Fix any failing tests**

If any tests fail, investigate and fix before proceeding.

**Step 3: Final commit if needed**

```bash
git add -A
git commit -m "test: ensure all tests pass"
```

---

## Summary

This plan adds a chat sidebar to the FoundryVTT module in 8 tasks:

1. **Localization** - Add UI strings
2. **Chat Service** - HTTP client with TDD
3. **TablewriteTab** - UI class with TDD
4. **CSS Styles** - Foundry-native styling
5. **Hook Registration** - Sidebar tab integration
6. **Build & Manual Test** - Verification
7. **Integration Test** - Backend communication
8. **Full Test Suite** - Ensure nothing broken

Each task is ~5-15 minutes with TDD pattern (test first, implement, verify, commit).
