/**
 * Handle actor creation, retrieval, and deletion messages from backend.
 *
 * Message format for create: {actor: {...}, spell_uuids: [...], name: string, cr: number}
 * Message format for get: {uuid: string}
 * Message format for delete: {uuid: string}
 */

import type { CreateResult, GetResult, DeleteResult, ListResult, GiveResult } from './index.js';

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
      const actorUuid = `Actor.${actor.id}`;
      console.log('[Tablewrite] Created actor:', actor.name, actor.id);

      // Add spells if spell_uuids provided
      const spellUuids = data.spell_uuids as string[] | undefined;
      if (spellUuids && spellUuids.length > 0) {
        console.log('[Tablewrite] Adding', spellUuids.length, 'spells to actor...');
        const giveResult = await handleGiveItems({
          actor_uuid: actorUuid,
          item_uuids: spellUuids
        });
        if (giveResult.success) {
          console.log('[Tablewrite] Added', giveResult.items_added, 'spells to actor');
        } else {
          console.warn('[Tablewrite] Failed to add some spells:', giveResult.errors);
        }
      }

      const message = game.i18n.format('TABLEWRITE_ASSISTANT.CreatedActor', { name: actor.name });
      ui.notifications?.info(message);

      return {
        success: true,
        id: actor.id,
        uuid: actorUuid,
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

/**
 * Handle give items request - add compendium items to an actor.
 *
 * This fetches items from compendiums by UUID and adds them to the actor.
 * Used for adding spells to NPCs after actor creation.
 *
 * Message format: {actor_uuid: string, item_uuids: string[]}
 */
export async function handleGiveItems(data: {
  actor_uuid: string;
  item_uuids: string[];
}): Promise<GiveResult> {
  try {
    const { actor_uuid, item_uuids } = data;

    if (!actor_uuid || !item_uuids || item_uuids.length === 0) {
      return {
        success: false,
        error: 'Missing actor_uuid or item_uuids'
      };
    }

    // Get the actor
    const actor = await fromUuid(actor_uuid) as FoundryDocument | null;
    if (!actor) {
      return {
        success: false,
        error: `Actor not found: ${actor_uuid}`
      };
    }

    // Fetch all items from compendiums
    const itemsToAdd: Record<string, unknown>[] = [];
    const errors: string[] = [];

    for (const itemUuid of item_uuids) {
      try {
        const item = await fromUuid(itemUuid);
        if (item) {
          // Convert to plain object for embedding
          const itemData = item.toObject();
          // Remove _id so Foundry generates a new one
          delete itemData._id;
          itemsToAdd.push(itemData);
        } else {
          errors.push(`Item not found: ${itemUuid}`);
        }
      } catch (e) {
        errors.push(`Failed to fetch ${itemUuid}: ${e}`);
      }
    }

    if (itemsToAdd.length === 0) {
      return {
        success: false,
        error: `No items could be fetched. Errors: ${errors.join(', ')}`
      };
    }

    // Add items to actor
    const created = await actor.createEmbeddedDocuments('Item', itemsToAdd);
    const addedCount = created?.length ?? 0;

    console.log(`[Tablewrite] Added ${addedCount} items to actor ${actor.name}`);
    if (errors.length > 0) {
      console.warn('[Tablewrite] Some items failed:', errors);
    }

    ui.notifications?.info(`Added ${addedCount} items to ${actor.name}`);

    return {
      success: true,
      actor_uuid: actor_uuid,
      items_added: addedCount,
      errors: errors.length > 0 ? errors : undefined
    };
  } catch (error) {
    console.error('[Tablewrite] Failed to give items:', error);
    return {
      success: false,
      error: String(error)
    };
  }
}
