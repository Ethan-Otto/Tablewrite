/**
 * Tests for main entry point (main.ts)
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock Foundry globals
const mockGame = {
  settings: {
    register: vi.fn(),
    get: vi.fn().mockReturnValue('http://localhost:8000'),
  },
};

// Track Hooks callbacks
const hookCallbacks: Record<string, ((...args: unknown[]) => void)[]> = {};

const mockHooks = {
  once: vi.fn((hookName: string, callback: (...args: unknown[]) => void) => {
    if (!hookCallbacks[hookName]) {
      hookCallbacks[hookName] = [];
    }
    hookCallbacks[hookName].push(callback);
  }),
  on: vi.fn((hookName: string, callback: (...args: unknown[]) => void) => {
    if (!hookCallbacks[hookName]) {
      hookCallbacks[hookName] = [];
    }
    hookCallbacks[hookName].push(callback);
  }),
};

// Mock ui.notifications
const mockNotifications = {
  info: vi.fn(),
  warn: vi.fn(),
  error: vi.fn(),
};

// Mock WebSocket
class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  readyState = MockWebSocket.OPEN;
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onerror: ((event: Error) => void) | null = null;

  constructor(public url: string) {
    // Simulate async connection
    setTimeout(() => this.onopen?.(), 0);
  }

  send = vi.fn();
  close = vi.fn();
}

// Set up globals before import
// @ts-ignore
globalThis.game = mockGame;
// @ts-ignore
globalThis.Hooks = mockHooks;
// @ts-ignore
globalThis.ui = { notifications: mockNotifications };
// @ts-ignore
globalThis.WebSocket = MockWebSocket;

describe('main.ts', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Clear hook callbacks
    Object.keys(hookCallbacks).forEach(key => {
      hookCallbacks[key] = [];
    });
    // Reset modules to allow fresh imports
    vi.resetModules();
  });

  afterEach(() => {
    vi.resetModules();
  });

  it('registers init hook', async () => {
    await import('../src/main');

    expect(mockHooks.once).toHaveBeenCalledWith('init', expect.any(Function));
  });

  it('registers ready hook', async () => {
    await import('../src/main');

    expect(mockHooks.once).toHaveBeenCalledWith('ready', expect.any(Function));
  });

  it('registers close hook', async () => {
    await import('../src/main');

    expect(mockHooks.once).toHaveBeenCalledWith('close', expect.any(Function));
  });

  it('init hook calls registerSettings', async () => {
    await import('../src/main');

    // Trigger the init hook
    const initCallback = hookCallbacks['init']?.[0];
    expect(initCallback).toBeDefined();

    initCallback?.();

    // Verify settings.register was called (from registerSettings)
    expect(mockGame.settings.register).toHaveBeenCalledWith(
      'tablewrite-assistant',
      'backendUrl',
      expect.any(Object)
    );
  });

  it('ready hook creates client and connects', async () => {
    const { client } = await import('../src/main');

    // Initially null
    expect(client).toBeNull();

    // Trigger ready hook
    const readyCallback = hookCallbacks['ready']?.[0];
    expect(readyCallback).toBeDefined();

    readyCallback?.();

    // Re-import to get updated client
    const { client: updatedClient } = await import('../src/main');

    // Client should be created and connected
    expect(updatedClient).not.toBeNull();
    expect(updatedClient?.isConnected()).toBe(true);
  });

  it('ready hook uses backendUrl from settings', async () => {
    mockGame.settings.get.mockReturnValue('http://custom:9000');

    await import('../src/main');

    // Trigger ready hook
    const readyCallback = hookCallbacks['ready']?.[0];
    readyCallback?.();

    // Verify settings.get was called
    expect(mockGame.settings.get).toHaveBeenCalledWith('tablewrite-assistant', 'backendUrl');

    // Re-import to get updated client
    const { client } = await import('../src/main');
    expect(client?.getWebSocketUrl()).toBe('ws://custom:9000/ws/foundry');
  });

  it('close hook disconnects client', async () => {
    await import('../src/main');

    // First connect via ready hook
    const readyCallback = hookCallbacks['ready']?.[0];
    readyCallback?.();

    // Then trigger close hook
    const closeCallback = hookCallbacks['close']?.[0];
    expect(closeCallback).toBeDefined();

    closeCallback?.();

    // Re-import to get updated client
    const { client } = await import('../src/main');

    // Client should be null after close
    expect(client).toBeNull();
  });

  it('renderSidebar hook adds tab with native DOM (v12 fallback)', async () => {
    // Create mock HTMLElement sidebar for v12 structure (a.item)
    const mockSidebar = document.createElement('div');
    mockSidebar.innerHTML = `
      <nav id="sidebar-tabs">
        <a class="item" data-tab="chat"><i class="fas fa-comments"></i></a>
      </nav>
    `;

    // Mock game.i18n
    // @ts-ignore
    globalThis.game.i18n = {
      localize: vi.fn().mockReturnValue('Tablewrite Assistant')
    };

    await import('../src/main');

    // Trigger renderSidebar hook with HTMLElement (not JQuery)
    const renderCallback = hookCallbacks['renderSidebar']?.[0];
    expect(renderCallback).toBeDefined();

    // Call with HTMLElement as v13 does
    renderCallback?.({}, mockSidebar, {}, {});

    // Verify tab was added (v12 fallback uses 'a' tag)
    const tabButton = mockSidebar.querySelector('[data-tab="tablewrite"]');
    expect(tabButton).not.toBeNull();
    expect(tabButton?.tagName).toBe('A');
    expect(tabButton?.classList.contains('item')).toBe(true);

    // Verify tab content container was added
    const tabContent = mockSidebar.querySelector('#tablewrite');
    expect(tabContent).not.toBeNull();
    expect(tabContent?.classList.contains('tab')).toBe(true);
  });

  it('renderSidebar hook adds tab with v13 button-in-li structure', async () => {
    // Create mock HTMLElement sidebar for v13 structure (button in li in menu)
    const mockSidebar = document.createElement('div');
    mockSidebar.innerHTML = `
      <nav id="sidebar-tabs">
        <menu class="flexcol">
          <li>
            <button type="button" class="ui-control plain icon fa-solid fa-comments" data-action="tab" data-tab="chat" role="tab"></button>
          </li>
        </menu>
      </nav>
    `;

    // Mock game.i18n
    // @ts-ignore
    globalThis.game.i18n = {
      localize: vi.fn().mockReturnValue('Tablewrite Assistant')
    };

    await import('../src/main');

    // Trigger renderSidebar hook
    const renderCallback = hookCallbacks['renderSidebar']?.[0];
    expect(renderCallback).toBeDefined();

    // v13 passes parts array including 'tabs'
    renderCallback?.({}, mockSidebar, {}, { parts: ['tabs', 'footer'] });

    // Verify tab was added (v13 uses 'button' tag in 'li' wrapper)
    const tabButton = mockSidebar.querySelector('button[data-tab="tablewrite"]');
    expect(tabButton).not.toBeNull();
    expect(tabButton?.tagName).toBe('BUTTON');
    expect(tabButton?.classList.contains('ui-control')).toBe(true);
    expect(tabButton?.getAttribute('role')).toBe('tab');

    // Verify li wrapper was created
    const tabLi = tabButton?.closest('li');
    expect(tabLi).not.toBeNull();

    // Verify tab content container was added with v13 attributes
    const tabContent = mockSidebar.querySelector('#tablewrite');
    expect(tabContent).not.toBeNull();
    expect(tabContent?.classList.contains('tab')).toBe(true);
    expect(tabContent?.dataset.group).toBe('primary');
  });
});
