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
    // Reset the mock return value to default
    mockActor.create.mockResolvedValue({ id: 'actor123', name: 'Test Actor' });
  });

  it('calls Actor.create with the data', async () => {
    const { handleActorCreate } = await import('../../src/handlers/actor');
    const actorData = { name: 'Goblin', type: 'npc', system: { hp: { value: 7, max: 7 } } };

    await handleActorCreate(actorData);

    expect(mockActor.create).toHaveBeenCalledWith(actorData);
  });

  it('shows notification on success', async () => {
    const { handleActorCreate } = await import('../../src/handlers/actor');

    await handleActorCreate({ name: 'Goblin', uuid: 'Actor.abc123' });

    expect(mockNotifications.info).toHaveBeenCalled();
  });

  it('shows notification with created actor name', async () => {
    mockActor.create.mockResolvedValue({ id: 'actor123', name: 'Goblin' });
    const { handleActorCreate } = await import('../../src/handlers/actor');

    await handleActorCreate({ name: 'Goblin', uuid: 'Actor.abc123' });

    expect(mockI18n.format).toHaveBeenCalledWith(
      'TABLEWRITE_ASSISTANT.CreatedActor',
      { name: 'Goblin' }
    );
  });

  it('shows error notification when create fails', async () => {
    mockActor.create.mockRejectedValue(new Error('Permission denied'));
    const { handleActorCreate } = await import('../../src/handlers/actor');

    await handleActorCreate({ name: 'Goblin' });

    expect(mockNotifications.error).toHaveBeenCalled();
  });

  it('does not show success notification when create returns null', async () => {
    mockActor.create.mockResolvedValue(null);
    const { handleActorCreate } = await import('../../src/handlers/actor');

    await handleActorCreate({ name: 'Goblin' });

    expect(mockNotifications.info).not.toHaveBeenCalled();
  });
});
