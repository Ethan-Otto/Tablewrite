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
 * Handle update actor request - update an actor's data by UUID.
 *
 * Message format: {uuid: string, updates: Record<string, unknown>}
 * Updates can include nested paths like "system.abilities.str.value"
 */
export async function handleUpdateActor(data: {
  uuid: string;
  updates: Record<string, unknown>;
}): Promise<CreateResult> {
  try {
    const { uuid, updates } = data;

    if (!uuid || !updates) {
      return {
        success: false,
        error: 'Missing uuid or updates'
      };
    }

    // Get the actor
    const actor = await fromUuid(uuid) as FoundryDocument | null;
    if (!actor) {
      return {
        success: false,
        error: `Actor not found: ${uuid}`
      };
    }

    // Apply updates (cast to any to access update method)
    await (actor as any).update(updates);
    console.log('[Tablewrite] Updated actor:', actor.name, uuid, 'with:', updates);
    ui.notifications?.info(`Updated actor: ${actor.name}`);

    return {
      success: true,
      id: actor.id,
      uuid: uuid,
      name: actor.name ?? undefined
    };
  } catch (error) {
    console.error('[Tablewrite] Failed to update actor:', error);
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

/**
 * Add custom items (attacks, feats) to an existing actor.
 * Unlike handleGiveItems which pulls from compendiums, this creates new items.
 */
export async function handleAddCustomItems(data: {
  actor_uuid: string;
  items: Array<{
    name: string;
    type: 'weapon' | 'feat';
    description: string;
    damage_formula?: string;  // e.g., "2d6+3"
    damage_type?: string;     // e.g., "psychic"
    attack_bonus?: number;
    range?: number;
    activation?: string;      // "action", "bonus", "reaction", "passive"
    save_dc?: number;
    save_ability?: string;    // "dex", "con", "wis", etc.
    // AOE fields
    aoe_type?: string;        // "cone", "sphere", "line", "cube", "cylinder"
    aoe_size?: number;        // size in feet (e.g., 60 for 60-foot cone)
    on_save?: string;         // "half", "none" - what happens on successful save
  }>;
}): Promise<{ success: boolean; items_added?: number; error?: string }> {
  try {
    const { actor_uuid, items } = data;

    // Get the actor
    const actor = await fromUuid(actor_uuid) as FoundryDocument | null;
    if (!actor) {
      return {
        success: false,
        error: `Actor not found: ${actor_uuid}`
      };
    }

    const itemsToAdd: Record<string, unknown>[] = [];

    for (const itemDef of items) {
      // Generate unique ID for this item
      const itemId = foundry.utils.randomID(16);

      if (itemDef.type === 'weapon') {
        // Parse damage formula (e.g., "2d6+3" -> number=2, denomination=6, bonus=3)
        let damageNumber = 1;
        let damageDenom = 6;
        let damageBonus = "";

        if (itemDef.damage_formula) {
          const match = itemDef.damage_formula.match(/(\d+)?d(\d+)([+-]\d+)?/i);
          if (match) {
            damageNumber = parseInt(match[1] || "1");
            damageDenom = parseInt(match[2]);
            damageBonus = match[3] || "";
          }
        }

        // Create attack activity
        const activityId = foundry.utils.randomID(16);
        const activity = {
          _id: activityId,
          type: "attack",
          name: "",
          sort: 0,
          activation: {
            type: itemDef.activation || "action",
            value: null,
            override: false,
            condition: ""
          },
          attack: {
            ability: "",
            bonus: itemDef.attack_bonus ? String(itemDef.attack_bonus) : "",
            critical: { threshold: null },
            flat: false,
            type: { value: "melee", classification: "weapon" }
          },
          consumption: { targets: [], scaling: { allowed: false, max: "" }, spellSlot: true },
          damage: { critical: { bonus: "" }, includeBase: true, parts: [] },
          duration: { units: "inst", concentration: false, override: false },
          effects: [],
          range: { override: false },
          target: { template: { contiguous: false, type: "", size: "", units: "ft" }, affects: { count: "", type: "", choice: false, special: "" }, override: false },
          uses: { spent: 0, recovery: [], max: "" }
        };

        const weaponItem = {
          _id: itemId,
          name: itemDef.name,
          type: "weapon",
          img: "icons/skills/melee/hand-grip-sword-orange.webp",
          system: {
            description: { value: itemDef.description || "" },
            activities: { [activityId]: activity },
            damage: {
              base: {
                number: damageNumber,
                denomination: damageDenom,
                bonus: damageBonus.replace("+", ""),
                types: [itemDef.damage_type || "bludgeoning"],
                custom: { enabled: false, formula: "" },
                scaling: { mode: "", number: null, formula: "" }
              }
            },
            range: {
              value: itemDef.range || 5,
              long: null,
              reach: itemDef.range || 5,
              units: "ft"
            },
            type: { value: "natural", baseItem: "" },
            properties: [],
            uses: { spent: 0, recovery: [], max: "" }
          }
        };
        itemsToAdd.push(weaponItem);

      } else if (itemDef.type === 'feat') {
        // Create activity based on whether it's a save or utility
        const activityId = foundry.utils.randomID(16);
        let activity: Record<string, unknown>;

        if (itemDef.save_dc && itemDef.save_ability) {
          // Save-based feat (like breath weapon)
          // Determine if this is an AOE attack
          const isAoe = itemDef.aoe_type && itemDef.aoe_size;

          // For AOE attacks, range is "self" (originates from creature)
          // For non-AOE save abilities, use provided range or default
          const rangeConfig = isAoe
            ? { override: false, units: "self", special: "" }
            : { override: false, units: itemDef.range ? "ft" : "", value: itemDef.range || null };

          // Target template for AOE
          const targetTemplate = isAoe
            ? {
                contiguous: false,
                units: "ft",
                type: itemDef.aoe_type,
                size: String(itemDef.aoe_size),
                count: "",
                width: itemDef.aoe_type === "line" ? "5" : ""
              }
            : { contiguous: false, type: "", size: "", units: "ft" };

          activity = {
            _id: activityId,
            type: "save",
            name: "",
            sort: 0,
            activation: {
              type: itemDef.activation || "action",
              value: null,
              override: false,
              condition: ""
            },
            save: {
              ability: [itemDef.save_ability],
              dc: { calculation: "", formula: String(itemDef.save_dc) }
            },
            consumption: { targets: [], scaling: { allowed: false, max: "" }, spellSlot: true },
            damage: {
              critical: { bonus: "" },
              includeBase: true,
              parts: [],
              onSave: itemDef.on_save || "half"
            },
            duration: { units: "inst", concentration: false, override: false },
            effects: [],
            range: rangeConfig,
            target: {
              template: targetTemplate,
              affects: { count: "", type: "creature", choice: false, special: "" },
              override: false,
              prompt: true
            },
            uses: { spent: 0, recovery: [], max: "" }
          };

          // Add damage if specified
          if (itemDef.damage_formula) {
            // Parse damage formula for proper structure
            let damageNumber = 1;
            let damageDenom = 6;
            let damageBonus = "";

            const match = itemDef.damage_formula.match(/(\d+)?d(\d+)([+-]\d+)?/i);
            if (match) {
              damageNumber = parseInt(match[1] || "1");
              damageDenom = parseInt(match[2]);
              damageBonus = match[3]?.replace("+", "") || "";
            }

            (activity.damage as Record<string, unknown>).parts = [{
              number: damageNumber,
              denomination: damageDenom,
              bonus: damageBonus,
              types: [itemDef.damage_type || "fire"],
              custom: { enabled: false, formula: "" },
              scaling: { mode: "", number: 1 }
            }];
          }
        } else {
          // Utility/passive feat
          activity = {
            _id: activityId,
            type: "utility",
            name: "",
            sort: 0,
            activation: {
              type: itemDef.activation || "passive",
              value: null,
              override: false,
              condition: ""
            },
            consumption: { targets: [], scaling: { allowed: false, max: "" }, spellSlot: true },
            duration: { units: "inst", concentration: false, override: false },
            effects: [],
            range: { override: false },
            target: { template: { contiguous: false, type: "", size: "", units: "ft" }, affects: { count: "", type: "", choice: false, special: "" }, override: false },
            uses: { spent: 0, recovery: [], max: "" }
          };
        }

        const featItem = {
          _id: itemId,
          name: itemDef.name,
          type: "feat",
          img: "icons/magic/control/energy-stream-link-large-blue.webp",
          system: {
            description: { value: itemDef.description || "" },
            activities: { [activityId]: activity },
            activation: {
              type: itemDef.activation || "passive",
              value: null,
              condition: ""
            },
            uses: {}
          }
        };
        itemsToAdd.push(featItem);
      }
    }

    if (itemsToAdd.length === 0) {
      return {
        success: false,
        error: "No valid items to add"
      };
    }

    // Add items to actor
    const created = await actor.createEmbeddedDocuments('Item', itemsToAdd);
    const addedCount = created?.length ?? 0;

    console.log(`[Tablewrite] Added ${addedCount} custom items to actor ${actor.name}`);
    ui.notifications?.info(`Added ${addedCount} items to ${actor.name}`);

    return {
      success: true,
      items_added: addedCount
    };
  } catch (error) {
    console.error('[Tablewrite] Failed to add custom items:', error);
    return {
      success: false,
      error: String(error)
    };
  }
}
