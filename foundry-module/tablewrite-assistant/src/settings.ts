/**
 * Module settings registration and accessors.
 */

const MODULE_ID = 'tablewrite-assistant';

/**
 * Register all module settings with Foundry.
 * Call this in the 'init' hook.
 */
export function registerSettings(): void {
  game.settings.register(MODULE_ID, 'backendUrl', {
    name: 'TABLEWRITE_ASSISTANT.SettingsBackendUrl',
    hint: 'TABLEWRITE_ASSISTANT.SettingsBackendUrlHint',
    default: 'http://localhost:8000',
    type: String,
    config: true,
    scope: 'world',
  });
}

/**
 * Get the configured backend URL.
 */
export function getBackendUrl(): string {
  return game.settings.get(MODULE_ID, 'backendUrl') as string;
}
