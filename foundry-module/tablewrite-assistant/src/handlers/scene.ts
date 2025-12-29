/**
 * Handle scene creation messages from backend.
 */

export async function handleSceneCreate(data: Record<string, unknown>): Promise<void> {
  try {
    const name = data.name as string;

    if (name) {
      const message = game.i18n.format('TABLEWRITE_ASSISTANT.CreatedScene', { name });
      ui.notifications?.info(message);
    }
  } catch (error) {
    console.error('[Tablewrite] Failed to handle scene create:', error);
    ui.notifications?.error(`Failed to create scene: ${error}`);
  }
}
