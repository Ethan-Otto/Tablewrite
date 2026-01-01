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

  it('calls Actor.create with the actor data from message', async () => {
    const { handleActorCreate } = await import('../../src/handlers/actor');
    const actorData = { name: 'Goblin', type: 'npc', system: { hp: { value: 7, max: 7 } } };
    // New message format wraps actor data
    const message = { actor: actorData, name: 'Goblin', cr: 0.25 };

    const result = await handleActorCreate(message);

    expect(mockActor.create).toHaveBeenCalledWith(actorData);
    expect(result.success).toBe(true);
  });

  it('returns success result with uuid on success', async () => {
    mockActor.create.mockResolvedValue({ id: 'actor456', name: 'Goblin' });
    const { handleActorCreate } = await import('../../src/handlers/actor');

    const result = await handleActorCreate({ actor: { name: 'Goblin', type: 'npc' }, name: 'Goblin' });

    expect(result.success).toBe(true);
    expect(result.uuid).toBe('Actor.actor456');
    expect(result.id).toBe('actor456');
    expect(result.name).toBe('Goblin');
  });

  it('shows notification on success', async () => {
    const { handleActorCreate } = await import('../../src/handlers/actor');

    await handleActorCreate({ actor: { name: 'Goblin', type: 'npc' }, name: 'Goblin' });

    expect(mockNotifications.info).toHaveBeenCalled();
  });

  it('shows notification with created actor name', async () => {
    mockActor.create.mockResolvedValue({ id: 'actor123', name: 'Goblin' });
    const { handleActorCreate } = await import('../../src/handlers/actor');

    await handleActorCreate({ actor: { name: 'Goblin', type: 'npc' }, name: 'Goblin' });

    expect(mockI18n.format).toHaveBeenCalledWith(
      'TABLEWRITE_ASSISTANT.CreatedActor',
      { name: 'Goblin' }
    );
  });

  it('returns error result when create fails', async () => {
    mockActor.create.mockRejectedValue(new Error('Permission denied'));
    const { handleActorCreate } = await import('../../src/handlers/actor');

    const result = await handleActorCreate({ actor: { name: 'Goblin' }, name: 'Goblin' });

    expect(result.success).toBe(false);
    expect(result.error).toContain('Permission denied');
    expect(mockNotifications.error).toHaveBeenCalled();
  });

  it('returns error when no actor data in message', async () => {
    const { handleActorCreate } = await import('../../src/handlers/actor');

    const result = await handleActorCreate({ name: 'Goblin' }); // Missing 'actor' property

    expect(result.success).toBe(false);
    expect(result.error).toBe('No actor data in message');
    expect(mockNotifications.error).toHaveBeenCalled();
    expect(mockActor.create).not.toHaveBeenCalled();
  });
});
