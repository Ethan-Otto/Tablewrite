import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock ui.notifications
const mockNotifications = {
  error: vi.fn(),
  info: vi.fn(),
};

// @ts-ignore
globalThis.ui = { notifications: mockNotifications };

// Mock game.i18n
const mockI18n = {
  localize: vi.fn((key: string) => {
    const translations: Record<string, string> = {
      'TABLEWRITE_ASSISTANT.BattleMapUpload.Title': 'Battle Map Upload',
      'TABLEWRITE_ASSISTANT.BattleMapUpload.SelectFile': 'Select battle map image',
      'TABLEWRITE_ASSISTANT.BattleMapUpload.SceneName': 'Scene Name',
      'TABLEWRITE_ASSISTANT.BattleMapUpload.GridSize': 'Grid Size',
      'TABLEWRITE_ASSISTANT.BattleMapUpload.SkipWalls': 'Skip wall detection',
      'TABLEWRITE_ASSISTANT.BattleMapUpload.CreateScene': 'Create Scene',
      'TABLEWRITE_ASSISTANT.BattleMapUpload.NoFileSelected': 'Please select a battle map image',
    };
    return translations[key] ?? key;
  }),
};

// @ts-ignore
globalThis.game = { i18n: mockI18n };

describe('BattleMapUpload', () => {
  let container: HTMLElement;

  beforeEach(() => {
    vi.clearAllMocks();
    container = document.createElement('div');
    document.body.appendChild(container);
  });

  afterEach(() => {
    document.body.removeChild(container);
    vi.resetModules();
  });

  it('renders upload form with all required elements', async () => {
    // Dynamic import to handle module not existing yet
    const { BattleMapUpload } = await import('../../src/ui/BattleMapUpload');

    const upload = new BattleMapUpload(container, 'http://localhost:8000');
    upload.render();

    expect(container.querySelector('#battlemap-file')).toBeTruthy();
    expect(container.querySelector('#scene-name')).toBeTruthy();
    expect(container.querySelector('#grid-size-mode')).toBeTruthy();
    expect(container.querySelector('#skip-walls')).toBeTruthy();
    expect(container.querySelector('#create-scene-btn')).toBeTruthy();
  });

  it('shows error notification when no file selected', async () => {
    const { BattleMapUpload } = await import('../../src/ui/BattleMapUpload');

    const upload = new BattleMapUpload(container, 'http://localhost:8000');
    upload.render();

    // Click create without selecting file
    const btn = container.querySelector('#create-scene-btn') as HTMLButtonElement;
    btn.click();

    expect(mockNotifications.error).toHaveBeenCalledWith(
      'Please select a battle map image'
    );
  });

  it('shows manual grid input when mode changed to manual', async () => {
    const { BattleMapUpload } = await import('../../src/ui/BattleMapUpload');

    const upload = new BattleMapUpload(container, 'http://localhost:8000');
    upload.render();

    const gridModeSelect = container.querySelector('#grid-size-mode') as HTMLSelectElement;
    const gridSizeInput = container.querySelector('#grid-size') as HTMLInputElement;

    // Initially hidden
    expect(gridSizeInput.style.display).toBe('none');

    // Change to manual
    gridModeSelect.value = 'manual';
    gridModeSelect.dispatchEvent(new Event('change'));

    // Should now be visible
    expect(gridSizeInput.style.display).toBe('block');
  });
});
