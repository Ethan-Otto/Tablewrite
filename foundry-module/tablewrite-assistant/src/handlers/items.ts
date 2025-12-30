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
