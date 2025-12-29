// foundry-module/tablewrite-assistant/tests/handlers/actor.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock Foundry Actor class
const mockActor = {
  create: vi.fn().mockResolvedValue({ id: 'actor123', name: 'Test Actor' }),
};

// @ts-ignore
globalThis.Actor = mockActor;

// Mock ui.notifications
const mockNotifications = {
  info: vi.fn(),
  error: vi.fn(),
};

// @ts-ignore
globalThis.ui = { notifications: mockNotifications };

// Mock game.i18n
const mockI18n = {
  format: vi.fn((key: string, data: { name: string }) => `Created actor: ${data.name}`),
};

// @ts-ignore
globalThis.game = { i18n: mockI18n };

describe('handleActorCreate', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows notification on success', async () => {
    const { handleActorCreate } = await import('../../src/handlers/actor');

    await handleActorCreate({ name: 'Goblin', uuid: 'Actor.abc123' });

    expect(mockNotifications.info).toHaveBeenCalled();
  });

  it('shows notification with actor name', async () => {
    const { handleActorCreate } = await import('../../src/handlers/actor');

    await handleActorCreate({ name: 'Goblin', uuid: 'Actor.abc123' });

    expect(mockI18n.format).toHaveBeenCalledWith(
      'TABLEWRITE_ASSISTANT.CreatedActor',
      { name: 'Goblin' }
    );
  });
});
