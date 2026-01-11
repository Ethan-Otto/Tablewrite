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
 * v13 compatible: handles new button-in-li sidebar structure.
 */
Hooks.on('renderSidebar', (app: Application, html: HTMLElement, context?: unknown, options?: { parts?: string[] }) => {
  // v13: Skip partial re-renders that don't include tabs
  // In v13, the initial render includes 'tabs' in parts array
  if (options?.parts && !options.parts.includes('tabs') && !options.parts.includes('sidebar')) {
    return;
  }

  const tabsContainer = html.querySelector('#sidebar-tabs');
  if (!tabsContainer) return;

  // Prevent duplicates (important for v13 re-renders)
  if (tabsContainer.querySelector('[data-tab="tablewrite"]')) return;

  // Find the chat tab button (v13 uses button elements inside li)
  const chatTabButton = tabsContainer.querySelector('button[data-tab="chat"]');

  if (chatTabButton) {
    // v13 structure: <li><button data-tab="chat">...</button></li>
    const chatLi = chatTabButton.closest('li');
    if (!chatLi) return;

    // Create new li wrapper
    const tabLi = document.createElement('li');

    // Create button matching v13 style
    const tabButton = document.createElement('button');
    tabButton.type = 'button';
    tabButton.className = 'ui-control plain icon fas fa-feather-alt';
    tabButton.dataset.action = 'tab';
    tabButton.dataset.tab = 'tablewrite';
    tabButton.setAttribute('role', 'tab');
    tabButton.setAttribute('aria-pressed', 'false');
    tabButton.dataset.group = 'primary';
    tabButton.setAttribute('aria-label', game.i18n.localize('TABLEWRITE_ASSISTANT.TabTooltip'));
    tabButton.dataset.tooltip = game.i18n.localize('TABLEWRITE_ASSISTANT.TabTooltip');

    tabLi.appendChild(tabButton);
    chatLi.after(tabLi);

    // Add tab content container
    const tabContent = document.createElement('section');
    tabContent.id = 'tablewrite';
    tabContent.className = 'tab sidebar-tab flexcol';
    tabContent.dataset.tab = 'tablewrite';
    tabContent.dataset.group = 'primary';
    html.appendChild(tabContent);

    // Initialize tab when clicked (lazy initialization)
    tabButton.addEventListener('click', () => {
      const container = document.getElementById('tablewrite');
      if (container && !container.dataset.initialized) {
        container.dataset.initialized = 'true';
        new TablewriteTab(container).render();
      }
    });
  } else {
    // Fallback for older Foundry versions (v12 and below)
    const chatTab = tabsContainer.querySelector('a[data-tab="chat"]');
    if (!chatTab) return;

    const tabButton = document.createElement('a');
    tabButton.className = 'item';
    tabButton.dataset.tab = 'tablewrite';
    tabButton.dataset.tooltip = game.i18n.localize('TABLEWRITE_ASSISTANT.TabTooltip');
    tabButton.innerHTML = '<i class="fas fa-feather-alt"></i>';
    chatTab.after(tabButton);

    // Add tab content container
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
  }
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
