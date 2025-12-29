/**
 * Tablewrite Assistant - FoundryVTT Module
 * Create D&D content through natural language.
 */

import { registerSettings, getBackendUrl } from './settings';
import { TablewriteClient } from './websocket/client';

// Module-scoped client instance
export let client: TablewriteClient | null = null;

/**
 * Initialize module settings.
 */
Hooks.once('init', () => {
  console.log('[Tablewrite Assistant] Initializing...');
  registerSettings();
});

/**
 * Connect to backend when Foundry is ready.
 */
Hooks.once('ready', () => {
  console.log('[Tablewrite Assistant] Foundry ready, connecting to backend...');

  const backendUrl = getBackendUrl();
  client = new TablewriteClient(backendUrl);
  client.connect();
});

/**
 * Disconnect on close.
 */
Hooks.once('close', () => {
  if (client) {
    client.disconnect();
    client = null;
  }
});
