/**
 * Handle actor creation messages from backend.
 */

export async function handleActorCreate(data: Record<string, unknown>): Promise<void> {
  try {
    const name = data.name as string;

    if (name) {
      const message = game.i18n.format('TABLEWRITE_ASSISTANT.CreatedActor', { name });
      ui.notifications?.info(message);
    }
  } catch (error) {
    console.error('[Tablewrite] Failed to handle actor create:', error);
    ui.notifications?.error(`Failed to create actor: ${error}`);
  }
}
