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

  // Token art generation toggle
  game.settings.register(MODULE_ID, 'tokenArtEnabled', {
    name: 'TABLEWRITE_ASSISTANT.SettingsTokenArtEnabled',
    hint: 'TABLEWRITE_ASSISTANT.SettingsTokenArtEnabledHint',
    default: true,
    type: Boolean,
    config: false,  // Not in Foundry settings menu - use our custom UI
    scope: 'client',
  });

  // Art style selection
  game.settings.register(MODULE_ID, 'artStyle', {
    name: 'TABLEWRITE_ASSISTANT.SettingsArtStyle',
    hint: 'TABLEWRITE_ASSISTANT.SettingsArtStyleHint',
    default: 'watercolor',
    type: String,
    config: false,  // Not in Foundry settings menu - use our custom UI
    scope: 'client',
    choices: {
      'watercolor': 'TABLEWRITE_ASSISTANT.StyleWatercolor',
      'oil': 'TABLEWRITE_ASSISTANT.StyleOil',
    }
  });
}

/**
 * Get the configured backend URL.
 */
export function getBackendUrl(): string {
  return game.settings.get(MODULE_ID, 'backendUrl') as string;
}

/**
 * Get whether token art generation is enabled.
 */
export function isTokenArtEnabled(): boolean {
  return game.settings.get(MODULE_ID, 'tokenArtEnabled') as boolean;
}

/**
 * Set token art generation enabled state.
 */
export async function setTokenArtEnabled(enabled: boolean): Promise<boolean> {
  await game.settings.set(MODULE_ID, 'tokenArtEnabled', enabled);
  return enabled;
}

/**
 * Get the selected art style.
 */
export function getArtStyle(): string {
  return game.settings.get(MODULE_ID, 'artStyle') as string;
}

/**
 * Set the art style.
 */
export async function setArtStyle(style: string): Promise<string> {
  await game.settings.set(MODULE_ID, 'artStyle', style);
  return style;
}
