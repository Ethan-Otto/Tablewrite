/**
 * Handle scene creation, retrieval, and deletion messages from backend.
 *
 * Message format for create: {scene: {...}, name: string, background_image: string|null}
 * Message format for get: {uuid: string}
 * Message format for delete: {uuid: string}
 */

import type { CreateResult, GetResult, DeleteResult } from './index.js';

export async function handleSceneCreate(data: Record<string, unknown>): Promise<CreateResult> {
  try {
    // The data IS the scene data directly (not wrapped in {scene: ...})
    // This matches the WebSocket message format: {type: "scene", data: scene_data}
    const sceneData = data;
    if (!sceneData || !sceneData.name) {
      console.error('[Tablewrite] Invalid scene data in message:', data);
      ui.notifications?.error('Failed to create scene: Invalid scene data received');
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

/**
 * Handle get scene request - fetch a scene by UUID.
 */
export async function handleGetScene(uuid: string): Promise<GetResult> {
  try {
    // Use fromUuid to get the scene document
    const scene = await fromUuid(uuid);

    if (!scene) {
      console.error('[Tablewrite] Scene not found:', uuid);
      return {
        success: false,
        error: `Scene not found: ${uuid}`
      };
    }

    // Convert to plain object for transmission
    const sceneData = scene.toObject();
    console.log('[Tablewrite] Fetched scene:', sceneData.name, uuid);

    return {
      success: true,
      entity: sceneData as Record<string, unknown>
    };
  } catch (error) {
    console.error('[Tablewrite] Failed to get scene:', error);
    return {
      success: false,
      error: String(error)
    };
  }
}

/**
 * Handle delete scene request - delete a scene by UUID.
 */
export async function handleDeleteScene(uuid: string): Promise<DeleteResult> {
  try {
    // Use fromUuid to get the scene document
    const scene = await fromUuid(uuid);

    if (!scene) {
      console.error('[Tablewrite] Scene not found:', uuid);
      return {
        success: false,
        error: `Scene not found: ${uuid}`
      };
    }

    const sceneName = scene.name;

    // Delete the scene
    await scene.delete();
    console.log('[Tablewrite] Deleted scene:', sceneName, uuid);
    ui.notifications?.info(`Deleted scene: ${sceneName}`);

    return {
      success: true,
      uuid: uuid,
      name: sceneName
    };
  } catch (error) {
    console.error('[Tablewrite] Failed to delete scene:', error);
    return {
      success: false,
      error: String(error)
    };
  }
}
