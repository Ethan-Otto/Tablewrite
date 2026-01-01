/**
 * Handle item search messages from backend.
 */

import type { SearchResult, SearchResultItem } from './index.js';

/**
 * Search for items in compendiums by query and optional filters.
 */
export async function handleSearchItems(data: {
  query: string;
  documentType?: string;
  subType?: string;
}): Promise<SearchResult> {
  try {
    const { query, documentType, subType } = data;
    const results: SearchResultItem[] = [];

    // Get all Item compendiums
    const packs = game.packs.filter(
      (p: Compendium) => p.documentName === (documentType || 'Item')
    );

    for (const pack of packs) {
      // Get or build index
      const index = await pack.getIndex({ fields: ['name', 'type', 'img'] });

      for (const entry of index.contents) {
        // Filter by subType if provided
        if (subType && entry.type !== subType) {
          continue;
        }

        // Filter by query (case-insensitive contains)
        if (query && !entry.name.toLowerCase().includes(query.toLowerCase())) {
          continue;
        }

        results.push({
          uuid: entry.uuid,
          id: entry._id,
          name: entry.name,
          type: entry.type,
          img: entry.img,
          pack: pack.metadata.label
        });
      }
    }

    console.log('[Tablewrite] Search returned', results.length, 'items for query:', query);

    return {
      success: true,
      results: results.slice(0, 200)  // Match relay server's 200-result limit
    };
  } catch (error) {
    console.error('[Tablewrite] Failed to search items:', error);
    return {
      success: false,
      error: String(error)
    };
  }
}

/**
 * Get full item data by UUID.
 */
export async function handleGetItem(uuid: string): Promise<{
  success: boolean;
  item?: Record<string, unknown>;
  error?: string;
}> {
  try {
    const item = await fromUuid(uuid);
    if (!item) {
      return { success: false, error: `Item not found: ${uuid}` };
    }
    return {
      success: true,
      item: item.toObject() as Record<string, unknown>
    };
  } catch (error) {
    return { success: false, error: String(error) };
  }
}

/**
 * List ALL items of a specific subtype from all compendiums.
 * Much more efficient than multiple search queries.
 */
export async function handleListCompendiumItems(data: {
  documentType?: string;
  subType?: string;
}): Promise<SearchResult> {
  try {
    const { documentType, subType } = data;
    const results: SearchResultItem[] = [];

    // Get all compendiums of the requested document type
    const packs = game.packs.filter(
      (p: Compendium) => p.documentName === (documentType || 'Item')
    );

    console.log(`[Tablewrite] Listing all ${subType || 'items'} from ${packs.length} compendiums...`);

    for (const pack of packs) {
      // Get or build index with needed fields
      // Include system.level for spells (needed by SpellCache)
      const index = await pack.getIndex({ fields: ['name', 'type', 'img', 'system.level', 'system.school'] });

      for (const entry of index.contents) {
        // Filter by subType if provided
        if (subType && entry.type !== subType) {
          continue;
        }

        const item: SearchResultItem = {
          uuid: entry.uuid,
          id: entry._id,
          name: entry.name,
          type: entry.type,
          img: entry.img,
          pack: pack.metadata.label
        };

        // Include system data if available (for spells)
        // Cast to any since getIndex with custom fields returns extended data
        const entryAny = entry as any;
        if (entryAny.system) {
          item.system = {
            level: entryAny.system.level,
            school: entryAny.system.school
          };
        }

        results.push(item);
      }
    }

    console.log(`[Tablewrite] Found ${results.length} ${subType || 'items'} in compendiums`);

    return {
      success: true,
      results  // No limit - return all items
    };
  } catch (error) {
    console.error('[Tablewrite] Failed to list compendium items:', error);
    return {
      success: false,
      error: String(error)
    };
  }
}
