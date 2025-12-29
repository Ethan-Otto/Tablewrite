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

  it('calls Scene.create with the data', async () => {
    const { handleSceneCreate } = await import('../../src/handlers/scene');
    const sceneData = { name: 'Cave Entrance', background: { src: 'path/to/image.webp' }, grid: { size: 100 } };

    await handleSceneCreate(sceneData);

    expect(mockScene.create).toHaveBeenCalledWith(sceneData);
  });

  it('shows notification on success', async () => {
    const { handleSceneCreate } = await import('../../src/handlers/scene');

    await handleSceneCreate({ name: 'Cave Entrance', uuid: 'Scene.abc123' });

    expect(mockNotifications.info).toHaveBeenCalled();
  });

  it('shows notification with created scene name', async () => {
    mockScene.create.mockResolvedValue({ id: 'scene123', name: 'Cave Entrance' });
    const { handleSceneCreate } = await import('../../src/handlers/scene');

    await handleSceneCreate({ name: 'Cave Entrance', uuid: 'Scene.abc123' });

    expect(mockI18n.format).toHaveBeenCalledWith(
      'TABLEWRITE_ASSISTANT.CreatedScene',
      { name: 'Cave Entrance' }
    );
  });

  it('shows error notification when create fails', async () => {
    mockScene.create.mockRejectedValue(new Error('Permission denied'));
    const { handleSceneCreate } = await import('../../src/handlers/scene');

    await handleSceneCreate({ name: 'Cave Entrance' });

    expect(mockNotifications.error).toHaveBeenCalled();
  });

  it('does not show success notification when create returns null', async () => {
    mockScene.create.mockResolvedValue(null);
    const { handleSceneCreate } = await import('../../src/handlers/scene');

    await handleSceneCreate({ name: 'Cave Entrance' });

    expect(mockNotifications.info).not.toHaveBeenCalled();
  });
});
