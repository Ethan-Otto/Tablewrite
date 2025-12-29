// foundry-module/tablewrite-assistant/tests/handlers/index.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock ui.notifications
const mockNotifications = {
  info: vi.fn(),
  error: vi.fn(),
};

// @ts-ignore
globalThis.ui = { notifications: mockNotifications };

// Mock game.i18n
const mockI18n = {
  format: vi.fn((key: string, data: { name: string }) => `Created: ${data.name}`),
};

// @ts-ignore
globalThis.game = { i18n: mockI18n };

// Spy on console methods
const consoleSpy = vi.spyOn(console, 'log').mockImplementation(() => {});
const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

describe('handleMessage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('routes actor messages to handleActorCreate', async () => {
    const { handleMessage } = await import('../../src/handlers/index');

    await handleMessage({ type: 'actor', data: { name: 'Goblin' } });

    expect(mockNotifications.info).toHaveBeenCalled();
    expect(mockI18n.format).toHaveBeenCalledWith(
      'TABLEWRITE_ASSISTANT.CreatedActor',
      { name: 'Goblin' }
    );
  });

  it('routes journal messages to handleJournalCreate', async () => {
    const { handleMessage } = await import('../../src/handlers/index');

    await handleMessage({ type: 'journal', data: { name: 'Chapter 1' } });

    expect(mockNotifications.info).toHaveBeenCalled();
    expect(mockI18n.format).toHaveBeenCalledWith(
      'TABLEWRITE_ASSISTANT.CreatedJournal',
      { name: 'Chapter 1' }
    );
  });

  it('routes scene messages to handleSceneCreate', async () => {
    const { handleMessage } = await import('../../src/handlers/index');

    await handleMessage({ type: 'scene', data: { name: 'Cave' } });

    expect(mockNotifications.info).toHaveBeenCalled();
    expect(mockI18n.format).toHaveBeenCalledWith(
      'TABLEWRITE_ASSISTANT.CreatedScene',
      { name: 'Cave' }
    );
  });

  it('logs connected message with client_id', async () => {
    const { handleMessage } = await import('../../src/handlers/index');

    await handleMessage({ type: 'connected', client_id: 'test-client-123' });

    expect(consoleSpy).toHaveBeenCalledWith(
      '[Tablewrite] Connected with client_id:',
      'test-client-123'
    );
  });

  it('handles pong silently', async () => {
    const { handleMessage } = await import('../../src/handlers/index');

    // Should not throw
    await handleMessage({ type: 'pong' });

    // Should not trigger any notifications
    expect(mockNotifications.info).not.toHaveBeenCalled();
  });

  it('warns on unknown message type', async () => {
    const { handleMessage } = await import('../../src/handlers/index');

    // @ts-ignore - testing unknown type
    await handleMessage({ type: 'unknown_type' });

    expect(consoleWarnSpy).toHaveBeenCalledWith(
      '[Tablewrite] Unknown message type:',
      'unknown_type'
    );
  });
});
