/**
 * Handle actor creation messages from backend.
 */

export async function handleActorCreate(data: Record<string, unknown>): Promise<void> {
  try {
    const actor = await Actor.create(data);
    if (actor) {
      const message = game.i18n.format('TABLEWRITE_ASSISTANT.CreatedActor', { name: actor.name });
      ui.notifications?.info(message);
    }
  } catch (error) {
    console.error('[Tablewrite] Failed to create actor:', error);
    ui.notifications?.error(`Failed to create actor: ${error}`);
  }
}
