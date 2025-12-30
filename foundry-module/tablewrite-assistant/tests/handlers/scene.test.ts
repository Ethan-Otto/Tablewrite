// foundry-module/tablewrite-assistant/tests/handlers/scene.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock Foundry Scene class
const mockScene = {
  create: vi.fn().mockResolvedValue({ id: 'scene123', name: 'Test Scene' }),
};

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
  format: vi.fn((key: string, data: { name: string }) => `Created scene: ${data.name}`),
};

// @ts-ignore
globalThis.game = { i18n: mockI18n };

describe('handleSceneCreate', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset the mock return value to default
    mockScene.create.mockResolvedValue({ id: 'scene123', name: 'Test Scene' });
  });

  it('calls Scene.create with the scene data from message', async () => {
    const { handleSceneCreate } = await import('../../src/handlers/scene');
    const sceneData = { name: 'Cave Entrance', background: { src: 'path/to/image.webp' }, grid: { size: 100 } };
    // New message format wraps scene data
    const message = { scene: sceneData, name: 'Cave Entrance', background_image: 'path/to/image.webp' };

    const result = await handleSceneCreate(message);

    expect(mockScene.create).toHaveBeenCalledWith(sceneData);
    expect(result.success).toBe(true);
  });

  it('returns success result with uuid on success', async () => {
    mockScene.create.mockResolvedValue({ id: 'scene456', name: 'Cave Entrance' });
    const { handleSceneCreate } = await import('../../src/handlers/scene');

    const result = await handleSceneCreate({ scene: { name: 'Cave Entrance' }, name: 'Cave Entrance' });

    expect(result.success).toBe(true);
    expect(result.uuid).toBe('Scene.scene456');
    expect(result.id).toBe('scene456');
    expect(result.name).toBe('Cave Entrance');
  });

  it('shows notification on success', async () => {
    const { handleSceneCreate } = await import('../../src/handlers/scene');

    await handleSceneCreate({ scene: { name: 'Cave Entrance' }, name: 'Cave Entrance' });

    expect(mockNotifications.info).toHaveBeenCalled();
  });

  it('shows notification with created scene name', async () => {
    mockScene.create.mockResolvedValue({ id: 'scene123', name: 'Cave Entrance' });
    const { handleSceneCreate } = await import('../../src/handlers/scene');

    await handleSceneCreate({ scene: { name: 'Cave Entrance' }, name: 'Cave Entrance' });

    expect(mockI18n.format).toHaveBeenCalledWith(
      'TABLEWRITE_ASSISTANT.CreatedScene',
      { name: 'Cave Entrance' }
    );
  });

  it('returns error result when create fails', async () => {
    mockScene.create.mockRejectedValue(new Error('Permission denied'));
    const { handleSceneCreate } = await import('../../src/handlers/scene');

    const result = await handleSceneCreate({ scene: { name: 'Cave Entrance' }, name: 'Cave Entrance' });

    expect(result.success).toBe(false);
    expect(result.error).toContain('Permission denied');
    expect(mockNotifications.error).toHaveBeenCalled();
  });

  it('returns error when no scene data in message', async () => {
    const { handleSceneCreate } = await import('../../src/handlers/scene');

    const result = await handleSceneCreate({ name: 'Cave Entrance' }); // Missing 'scene' property

    expect(result.success).toBe(false);
    expect(result.error).toBe('No scene data in message');
    expect(mockNotifications.error).toHaveBeenCalled();
    expect(mockScene.create).not.toHaveBeenCalled();
  });
});
