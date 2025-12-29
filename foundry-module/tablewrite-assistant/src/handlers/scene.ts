/**
 * Handle scene creation messages from backend.
 */

export async function handleSceneCreate(data: Record<string, unknown>): Promise<void> {
  try {
    const scene = await Scene.create(data);
    if (scene) {
      const message = game.i18n.format('TABLEWRITE_ASSISTANT.CreatedScene', { name: scene.name });
      ui.notifications?.info(message);
    }
  } catch (error) {
    console.error('[Tablewrite] Failed to create scene:', error);
    ui.notifications?.error(`Failed to create scene: ${error}`);
  }
}
