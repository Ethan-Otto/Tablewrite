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

// Mock game.settings
const mockSettings = {
  get: vi.fn((moduleId: string, key: string) => {
    if (key === 'backendUrl') return 'http://localhost:8000';
    return undefined;
  })
};

// @ts-ignore
globalThis.game = { i18n: mockI18n, settings: mockSettings };
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
      // No send button - Enter key submits (like native Foundry chat)
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

    it('escapes HTML in message content to prevent XSS', async () => {
      mockSend.mockResolvedValueOnce('<script>alert("xss")</script>');
      const { TablewriteTab } = await import('../../src/ui/TablewriteTab');
      const tab = new TablewriteTab(container);
      tab.render();

      await tab.sendMessage('test');

      const assistantMessage = container.querySelector('.tablewrite-message--assistant');
      expect(assistantMessage?.innerHTML).toContain('&lt;script&gt;');
      expect(assistantMessage?.innerHTML).not.toContain('<script>');
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
