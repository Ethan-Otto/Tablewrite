// foundry-module/tablewrite-assistant/tests/handlers/scene.test.ts
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
  format: vi.fn((key: string, data: { name: string }) => `Created scene: ${data.name}`),
};

// @ts-ignore
globalThis.game = { i18n: mockI18n };

describe('handleSceneCreate', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows notification on success', async () => {
    const { handleSceneCreate } = await import('../../src/handlers/scene');

    await handleSceneCreate({ name: 'Cave Entrance', uuid: 'Scene.abc123' });

    expect(mockNotifications.info).toHaveBeenCalled();
  });

  it('shows notification with scene name', async () => {
    const { handleSceneCreate } = await import('../../src/handlers/scene');

    await handleSceneCreate({ name: 'Cave Entrance', uuid: 'Scene.abc123' });

    expect(mockI18n.format).toHaveBeenCalledWith(
      'TABLEWRITE_ASSISTANT.CreatedScene',
      { name: 'Cave Entrance' }
    );
  });
});
