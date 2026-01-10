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
 * v13 compatible: uses native DOM instead of jQuery.
 */
Hooks.on('renderSidebar', (app: Application, html: HTMLElement, context?: unknown, options?: { parts?: string[] }) => {
  // v13: Skip partial re-renders
  if (options?.parts && !options.parts.includes('sidebar')) return;

  const tabsContainer = html.querySelector('#sidebar-tabs');
  if (!tabsContainer) return;

  // Prevent duplicates (important for v13 re-renders)
  if (tabsContainer.querySelector('[data-tab="tablewrite"]')) return;

  // Add tab button right after the chat tab
  const chatTab = tabsContainer.querySelector('[data-tab="chat"]');
  if (!chatTab) return;

  const tabButton = document.createElement('a');
  tabButton.className = 'item';
  tabButton.dataset.tab = 'tablewrite';
  tabButton.dataset.tooltip = game.i18n.localize('TABLEWRITE_ASSISTANT.TabTooltip');
  tabButton.innerHTML = '<i class="fas fa-feather-alt"></i>';
  chatTab.after(tabButton);

  // Add tab content container
  // Must include 'tab' class for Foundry's tab switching to work
  const tabContent = document.createElement('section');
  tabContent.id = 'tablewrite';
  tabContent.className = 'tab sidebar-tab flexcol';
  tabContent.dataset.tab = 'tablewrite';
  html.appendChild(tabContent);

  // Initialize tab when clicked (lazy initialization)
  tabButton.addEventListener('click', () => {
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
