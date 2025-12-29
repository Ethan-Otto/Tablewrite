import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock Foundry globals
const mockGame = {
  settings: {
    register: vi.fn(),
    get: vi.fn(),
  },
};

// @ts-ignore - Mock global
globalThis.game = mockGame;

describe('Settings', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('registers backendUrl setting', async () => {
    const { registerSettings } = await import('../src/settings');

    registerSettings();

    expect(mockGame.settings.register).toHaveBeenCalledWith(
      'tablewrite-assistant',
      'backendUrl',
      expect.objectContaining({
        name: 'TABLEWRITE_ASSISTANT.SettingsBackendUrl',
        default: 'http://localhost:8000',
        type: String,
        config: true,
      })
    );
  });

  it('getBackendUrl returns configured URL', async () => {
    mockGame.settings.get.mockReturnValue('http://custom:9000');

    const { getBackendUrl } = await import('../src/settings');

    const url = getBackendUrl();

    expect(url).toBe('http://custom:9000');
    expect(mockGame.settings.get).toHaveBeenCalledWith('tablewrite-assistant', 'backendUrl');
  });
});
