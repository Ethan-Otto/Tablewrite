/**
 * Handle actor creation, retrieval, and deletion messages from backend.
 *
 * Message format for create: {actor: {...}, spell_uuids: [...], name: string, cr: number}
 * Message format for get: {uuid: string}
 * Message format for delete: {uuid: string}
 */

import type { CreateResult, GetResult, DeleteResult, ListResult } from './index.js';

export async function handleActorCreate(data: Record<string, unknown>): Promise<CreateResult> {
  try {
    // Extract the actor data from the message
    const actorData = data.actor as Record<string, unknown>;
    if (!actorData) {
      console.error('[Tablewrite] No actor data in message:', data);
      ui.notifications?.error('Failed to create actor: No actor data received');
      return {
        success: false,
        error: 'No actor data in message'
      };
    }

    const actor = await Actor.create(actorData);
    if (actor) {
      const message = game.i18n.format('TABLEWRITE_ASSISTANT.CreatedActor', { name: actor.name });
      ui.notifications?.info(message);
      console.log('[Tablewrite] Created actor:', actor.name, actor.id);

      return {
        success: true,
        id: actor.id,
        uuid: `Actor.${actor.id}`,
        name: actor.name ?? undefined
      };
    }

    return {
      success: false,
      error: 'Actor.create returned null'
    };
  } catch (error) {
    console.error('[Tablewrite] Failed to create actor:', error);
    ui.notifications?.error(`Failed to create actor: ${error}`);
    return {
      success: false,
      error: String(error)
    };
  }
}

/**
 * Handle get actor request - fetch an actor by UUID.
 */
export async function handleGetActor(uuid: string): Promise<GetResult> {
  try {
    // Use fromUuid to get the actor document
    const actor = await fromUuid(uuid);

    if (!actor) {
      console.error('[Tablewrite] Actor not found:', uuid);
      return {
        success: false,
        error: `Actor not found: ${uuid}`
      };
    }

    // Convert to plain object for transmission
    const actorData = actor.toObject();
    console.log('[Tablewrite] Fetched actor:', actorData.name, uuid);

    return {
      success: true,
      entity: actorData as Record<string, unknown>
    };
  } catch (error) {
    console.error('[Tablewrite] Failed to get actor:', error);
    return {
      success: false,
      error: String(error)
    };
  }
}

/**
 * Handle delete actor request - delete an actor by UUID.
 */
export async function handleDeleteActor(uuid: string): Promise<DeleteResult> {
  try {
    // Use fromUuid to get the actor document
    const actor = await fromUuid(uuid);

    if (!actor) {
      console.error('[Tablewrite] Actor not found:', uuid);
      return {
        success: false,
        error: `Actor not found: ${uuid}`
      };
    }

    const actorName = actor.name;

    // Delete the actor
    await actor.delete();
    console.log('[Tablewrite] Deleted actor:', actorName, uuid);
    ui.notifications?.info(`Deleted actor: ${actorName}`);

    return {
      success: true,
      uuid: uuid,
      name: actorName
    };
  } catch (error) {
    console.error('[Tablewrite] Failed to delete actor:', error);
    return {
      success: false,
      error: String(error)
    };
  }
}

/**
 * Handle list actors request - return all world actors (not compendium).
 */
export async function handleListActors(): Promise<ListResult> {
  try {
    // Get all world actors (game.actors is the world collection, not compendiums)
    const actors = game.actors;
    if (!actors) {
      return {
        success: false,
        error: 'No actors collection available'
      };
    }

    const actorList = actors.map((actor: FoundryDocument) => ({
      uuid: `Actor.${actor.id}`,
      id: actor.id,
      name: actor.name
    }));

    console.log('[Tablewrite] Listed', actorList.length, 'world actors');

    return {
      success: true,
      actors: actorList
    };
  } catch (error) {
    console.error('[Tablewrite] Failed to list actors:', error);
    return {
      success: false,
      error: String(error)
    };
  }
}
