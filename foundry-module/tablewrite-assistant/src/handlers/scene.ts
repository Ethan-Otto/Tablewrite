/**
 * Handle scene creation messages from backend.
 *
 * Message format: {scene: {...}, name: string, background_image: string|null}
 */

import type { CreateResult } from './index.js';

export async function handleSceneCreate(data: Record<string, unknown>): Promise<CreateResult> {
  try {
    // Extract the scene data from the message
    const sceneData = data.scene as Record<string, unknown>;
    if (!sceneData) {
      console.error('[Tablewrite] No scene data in message:', data);
      ui.notifications?.error('Failed to create scene: No scene data received');
      return {
        success: false,
        error: 'No scene data in message'
      };
    }

    const scene = await Scene.create(sceneData);
    if (scene) {
      const message = game.i18n.format('TABLEWRITE_ASSISTANT.CreatedScene', { name: scene.name });
      ui.notifications?.info(message);
      console.log('[Tablewrite] Created scene:', scene.name, scene.id);

      return {
        success: true,
        id: scene.id,
        uuid: `Scene.${scene.id}`,
        name: scene.name ?? undefined
      };
    }

    return {
      success: false,
      error: 'Scene.create returned null'
    };
  } catch (error) {
    console.error('[Tablewrite] Failed to create scene:', error);
    ui.notifications?.error(`Failed to create scene: ${error}`);
    return {
      success: false,
      error: String(error)
    };
  }
}
