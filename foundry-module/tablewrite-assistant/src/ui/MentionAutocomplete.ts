/**
 * @-mention autocomplete dropdown for Foundry VTT entities.
 * Triggers on '@' character, shows grouped suggestions for Actors, Journals, Items, Scenes.
 */

export interface MentionEntity {
  name: string;
  uuid: string;
  type: 'Actor' | 'JournalEntry' | 'Item' | 'Scene';
}

export interface EntityGroups {
  actors: MentionEntity[];
  journals: MentionEntity[];
  items: MentionEntity[];
  scenes: MentionEntity[];
}

export class MentionAutocomplete {
  private textarea: HTMLTextAreaElement;
  private _isOpen: boolean = false;

  constructor(textarea: HTMLTextAreaElement) {
    this.textarea = textarea;
  }

  get isOpen(): boolean {
    return this._isOpen;
  }

  getEntities(): EntityGroups {
    // Access collections using .contents pattern consistent with the codebase
    const actorContents = game.actors?.contents ?? [];
    const journalContents = game.journal?.contents ?? [];
    const itemContents = game.items?.contents ?? [];
    const sceneContents = game.scenes?.contents ?? [];

    return {
      actors: actorContents.map((doc: FoundryDocument) => ({
        name: doc.name,
        uuid: doc.uuid,
        type: 'Actor' as const
      })),
      journals: journalContents.map((doc: FoundryDocument) => ({
        name: doc.name,
        uuid: doc.uuid,
        type: 'JournalEntry' as const
      })),
      items: itemContents.map((doc: FoundryDocument) => ({
        name: doc.name,
        uuid: doc.uuid,
        type: 'Item' as const
      })),
      scenes: sceneContents.map((doc: FoundryDocument) => ({
        name: doc.name,
        uuid: doc.uuid,
        type: 'Scene' as const
      }))
    };
  }

  filterEntities(query: string, maxResults: number = 6): MentionEntity[] {
    if (!query) return [];

    const lowerQuery = query.toLowerCase();
    const entities = this.getEntities();

    // Score function: prefix match = 2, contains = 1
    const score = (name: string): number => {
      const lowerName = name.toLowerCase();
      if (lowerName.startsWith(lowerQuery)) return 2;
      if (lowerName.includes(lowerQuery)) return 1;
      return 0;
    };

    // Filter and score each type
    const scored: { entity: MentionEntity; score: number }[] = [];

    for (const entity of entities.actors) {
      const s = score(entity.name);
      if (s > 0) scored.push({ entity, score: s });
    }
    for (const entity of entities.journals) {
      const s = score(entity.name);
      if (s > 0) scored.push({ entity, score: s });
    }
    for (const entity of entities.items) {
      const s = score(entity.name);
      if (s > 0) scored.push({ entity, score: s });
    }
    for (const entity of entities.scenes) {
      const s = score(entity.name);
      if (s > 0) scored.push({ entity, score: s });
    }

    // Sort by score (descending), then alphabetically
    scored.sort((a, b) => {
      if (b.score !== a.score) return b.score - a.score;
      return a.entity.name.localeCompare(b.entity.name);
    });

    // Distribute results: try to get ~2 per type, cap at maxResults
    const result: MentionEntity[] = [];
    const typeCounts: Record<string, number> = {};
    const maxPerType = Math.ceil(maxResults / 4);

    // First pass: up to maxPerType per category
    for (const { entity } of scored) {
      const count = typeCounts[entity.type] || 0;
      if (count < maxPerType && result.length < maxResults) {
        result.push(entity);
        typeCounts[entity.type] = count + 1;
      }
    }

    // Second pass: fill remaining slots
    for (const { entity } of scored) {
      if (result.length >= maxResults) break;
      if (!result.includes(entity)) {
        result.push(entity);
      }
    }

    return result;
  }
}
