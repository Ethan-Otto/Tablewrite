/**
 * WebSocket client for connecting to Tablewrite backend.
 */
import { handleMessage, TablewriteMessage } from '../handlers';

export class TablewriteClient {
  private ws: WebSocket | null = null;
  private backendUrl: string;
  private wsUrl: string;

  constructor(backendUrl: string) {
    this.backendUrl = backendUrl;
    this.wsUrl = this.convertToWsUrl(backendUrl);
  }

  /**
   * Convert HTTP(S) URL to WS(S) URL.
   */
  private convertToWsUrl(httpUrl: string): string {
    return httpUrl
      .replace(/^https:\/\//, 'wss://')
      .replace(/^http:\/\//, 'ws://')
      + '/ws/foundry';
  }

  /**
   * Get the WebSocket URL (for testing).
   */
  getWebSocketUrl(): string {
    return this.wsUrl;
  }

  /**
   * Connect to the backend.
   */
  connect(): void {
    if (this.ws) {
      this.disconnect();
    }

    this.ws = new WebSocket(this.wsUrl);

    this.ws.onopen = () => {
      ui.notifications?.info('TABLEWRITE_ASSISTANT.Connected', { localize: true });
    };

    this.ws.onclose = () => {
      ui.notifications?.warn('TABLEWRITE_ASSISTANT.Disconnected', { localize: true });
      this.ws = null;
    };

    this.ws.onerror = (error) => {
      console.error('[Tablewrite] WebSocket error:', error);
    };

    this.ws.onmessage = (event) => {
      this.handleMessage(event.data);
    };
  }

  /**
   * Disconnect from the backend.
   */
  disconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  /**
   * Check if connected.
   */
  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  /**
   * Handle incoming WebSocket message.
   */
  private async handleMessage(data: string): Promise<void> {
    try {
      const message: TablewriteMessage = JSON.parse(data);
      console.log('[Tablewrite] Received:', message.type);

      await handleMessage(message);
    } catch (e) {
      console.error('[Tablewrite] Failed to parse message:', e);
    }
  }
}
