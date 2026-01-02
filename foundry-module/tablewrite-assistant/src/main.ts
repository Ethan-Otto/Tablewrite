/**
 * Tablewrite Assistant - FoundryVTT Module
 * Create D&D content through natural language.
 */

import { registerSettings, getBackendUrl } from './settings.js';
import { TablewriteClient } from './websocket/client.js';
import { TablewriteTab } from './ui/TablewriteTab.js';

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
 * Register sidebar tab for chat UI.
 */
Hooks.on('renderSidebar', (app: Application, html: JQuery, context?: unknown, options?: { parts?: string[] }) => {
  // v13: Skip partial re-renders
  if (options?.parts && !options.parts.includes('sidebar')) return;

  const tabsContainer = html.find('#sidebar-tabs');
  if (!tabsContainer.length) return;

  // Prevent duplicates (important for v13 re-renders)
  if (tabsContainer.find('[data-tab="tablewrite"]').length) return;

  // Add tab button
  const tabButton = $(`
    <a class="item" data-tab="tablewrite" data-tooltip="${game.i18n.localize('TABLEWRITE_ASSISTANT.TabTooltip')}">
      <i class="fas fa-hat-wizard"></i>
    </a>
  `);
  tabsContainer.append(tabButton);

  // Add tab content container (html IS the sidebar element)
  html.append('<section id="tablewrite" class="sidebar-tab" data-tab="tablewrite"></section>');

  // Initialize tab when clicked (lazy initialization)
  tabButton.on('click', () => {
    const container = document.getElementById('tablewrite');
    if (container && !container.dataset.initialized) {
      container.dataset.initialized = 'true';
      new TablewriteTab(container).render();
    }
  });
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
