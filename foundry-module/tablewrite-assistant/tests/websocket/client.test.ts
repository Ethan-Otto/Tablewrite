// foundry-module/tablewrite-assistant/tests/websocket/client.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest';

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

// @ts-ignore
globalThis.WebSocket = MockWebSocket;

// Mock ui.notifications
const mockNotifications = {
  info: vi.fn(),
  warn: vi.fn(),
  error: vi.fn(),
};

// @ts-ignore
globalThis.ui = { notifications: mockNotifications };

describe('TablewriteClient', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('connects to backend WebSocket URL', async () => {
    const { TablewriteClient } = await import('../../src/websocket/client');

    const client = new TablewriteClient('http://localhost:8000');
    client.connect();

    expect(client.isConnected()).toBe(true);
  });

  it('converts http URL to ws URL', async () => {
    const { TablewriteClient } = await import('../../src/websocket/client');

    const client = new TablewriteClient('http://localhost:8000');
    client.connect();

    // Check the WebSocket was created with ws:// URL
    expect(client.getWebSocketUrl()).toBe('ws://localhost:8000/ws/foundry');
  });

  it('converts https URL to wss URL', async () => {
    const { TablewriteClient } = await import('../../src/websocket/client');

    const client = new TablewriteClient('https://example.com');
    client.connect();

    expect(client.getWebSocketUrl()).toBe('wss://example.com/ws/foundry');
  });

  it('disconnect closes WebSocket', async () => {
    const { TablewriteClient } = await import('../../src/websocket/client');

    const client = new TablewriteClient('http://localhost:8000');
    client.connect();
    client.disconnect();

    expect(client.isConnected()).toBe(false);
  });
});
