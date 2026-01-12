import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock fetch globally
const mockFetch = vi.fn();
globalThis.fetch = mockFetch;

// Mock game object with system info and settings
(globalThis as any).game = {
  system: {
    id: 'dnd5e',
    title: 'DnD5e'
  },
  settings: {
    get: (module: string, key: string) => {
      if (module === 'dnd5e' && key === 'rulesVersion') {
        return 'legacy';  // 2014 rules
      }
      return undefined;
    }
  }
};

// Mock settings functions
vi.mock('../../src/settings.js', () => ({
  getBackendUrl: () => 'http://localhost:8000',
  isTokenArtEnabled: () => true,
  getArtStyle: () => 'watercolor'
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
      expect(body.context).toEqual({
        settings: {
          tokenArtEnabled: true,
          artStyle: 'watercolor'
        },
        gameSystem: {
          id: 'dnd5e',
          title: 'DnD5e',
          rulesVersion: 'legacy'
        }
      });
      expect(body.conversation_history).toHaveLength(2);
      expect(body.conversation_history[0].role).toBe('user');
      expect(body.conversation_history[0].content).toBe('Hi');
    });

    it('returns the full ChatResponse object', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ message: 'I am doing well!', type: 'text' })
      });

      const { chatService } = await import('../../src/ui/chat-service');

      const result = await chatService.send('Hello', []);

      expect(result).toEqual({ message: 'I am doing well!', type: 'text' });
    });

    it('throws error when response is not ok', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500
      });

      const { chatService } = await import('../../src/ui/chat-service');

      await expect(chatService.send('Hello', [])).rejects.toThrow('Chat request failed: 500');
    });

    it('passes history through unchanged (caller excludes current message)', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ message: 'Response', type: 'text' })
      });

      const { chatService } = await import('../../src/ui/chat-service');

      // History should NOT include the current message (per API contract)
      const history = [
        { role: 'user' as const, content: 'First message', timestamp: new Date() },
        { role: 'assistant' as const, content: 'First response', timestamp: new Date() }
      ];

      await chatService.send('Current message', history);

      const callArgs = mockFetch.mock.calls[0];
      const body = JSON.parse(callArgs[1].body);
      // History passed through as-is
      expect(body.conversation_history).toHaveLength(2);
      expect(body.conversation_history[0].content).toBe('First message');
      expect(body.conversation_history[1].content).toBe('First response');
    });
  });
});
