// foundry-module/tablewrite-assistant/tests/handlers/index.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock Foundry Document classes
const mockActor = {
  create: vi.fn().mockResolvedValue({ id: 'actor123', name: 'Goblin' }),
};

const mockJournalEntry = {
  create: vi.fn().mockResolvedValue({ id: 'journal123', name: 'Chapter 1' }),
};

const mockScene = {
  create: vi.fn().mockResolvedValue({ id: 'scene123', name: 'Cave' }),
};

// @ts-ignore
globalThis.Actor = mockActor;
// @ts-ignore
globalThis.JournalEntry = mockJournalEntry;
// @ts-ignore
globalThis.Scene = mockScene;

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

  it('routes actor messages to handleActorCreate and returns result', async () => {
    const { handleMessage } = await import('../../src/handlers/index');
    // New message format: data contains wrapped actor data
    const result = await handleMessage({
      type: 'actor',
      data: { actor: { name: 'Goblin', type: 'npc' }, name: 'Goblin', cr: 0.25 },
      request_id: 'test-request-123'
    });

    expect(mockNotifications.info).toHaveBeenCalled();
    expect(result).not.toBeNull();
    expect(result?.responseType).toBe('actor_created');
    expect(result?.request_id).toBe('test-request-123');
    expect(result?.data?.uuid).toBe('Actor.actor123');
  });

  it('routes journal messages to handleJournalCreate and returns result', async () => {
    const { handleMessage } = await import('../../src/handlers/index');
    // New message format: data contains wrapped journal data
    const result = await handleMessage({
      type: 'journal',
      data: { journal: { name: 'Chapter 1' }, name: 'Chapter 1' },
      request_id: 'test-request-456'
    });

    expect(mockNotifications.info).toHaveBeenCalled();
    expect(result).not.toBeNull();
    expect(result?.responseType).toBe('journal_created');
    expect(result?.request_id).toBe('test-request-456');
    expect(result?.data?.uuid).toBe('JournalEntry.journal123');
  });

  it('routes scene messages to handleSceneCreate and returns result', async () => {
    const { handleMessage } = await import('../../src/handlers/index');
    // New message format: data contains wrapped scene data
    const result = await handleMessage({
      type: 'scene',
      data: { scene: { name: 'Cave' }, name: 'Cave' },
      request_id: 'test-request-789'
    });

    expect(mockNotifications.info).toHaveBeenCalled();
    expect(result).not.toBeNull();
    expect(result?.responseType).toBe('scene_created');
    expect(result?.request_id).toBe('test-request-789');
    expect(result?.data?.uuid).toBe('Scene.scene123');
  });

  it('logs connected message with client_id and returns null', async () => {
    const { handleMessage } = await import('../../src/handlers/index');

    const result = await handleMessage({ type: 'connected', client_id: 'test-client-123' });

    expect(consoleSpy).toHaveBeenCalledWith(
      '[Tablewrite] Connected with client_id:',
      'test-client-123'
    );
    expect(result).toBeNull();
  });

  it('handles pong silently and returns null', async () => {
    const { handleMessage } = await import('../../src/handlers/index');

    const result = await handleMessage({ type: 'pong' });

    // Should not trigger any notifications
    expect(mockNotifications.info).not.toHaveBeenCalled();
    expect(result).toBeNull();
  });

  it('warns on unknown message type and returns null', async () => {
    const { handleMessage } = await import('../../src/handlers/index');

    // @ts-ignore - testing unknown type
    const result = await handleMessage({ type: 'unknown_type' });

    expect(consoleWarnSpy).toHaveBeenCalledWith(
      '[Tablewrite] Unknown message type:',
      'unknown_type'
    );
    expect(result).toBeNull();
  });

  it('returns error response type when creation fails', async () => {
    mockActor.create.mockRejectedValueOnce(new Error('Permission denied'));
    const { handleMessage } = await import('../../src/handlers/index');

    const result = await handleMessage({
      type: 'actor',
      data: { actor: { name: 'Goblin' }, name: 'Goblin' },
      request_id: 'test-error-request'
    });

    expect(result).not.toBeNull();
    expect(result?.responseType).toBe('actor_error');
    expect(result?.request_id).toBe('test-error-request');
    expect(result?.error).toContain('Permission denied');
  });
});
