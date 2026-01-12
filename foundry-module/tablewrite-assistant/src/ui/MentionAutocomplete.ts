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
  private dropdown: HTMLElement | null = null;
  private selectedIndex: number = 0;
  private currentResults: MentionEntity[] = [];
  private currentQuery: string = '';

  constructor(textarea: HTMLTextAreaElement) {
    this.textarea = textarea;
  }

  get isOpen(): boolean {
    return this._isOpen;
  }

  open(query: string): void {
    this.currentQuery = query;
    this.currentResults = this.filterEntities(query);
    this.selectedIndex = 0;
    this._isOpen = true;
    this.renderDropdown();
  }

  close(): void {
    this._isOpen = false;
    if (this.dropdown) {
      this.dropdown.remove();
      this.dropdown = null;
    }
  }

  private renderDropdown(): void {
    // Remove existing dropdown
    if (this.dropdown) {
      this.dropdown.remove();
    }

    this.dropdown = document.createElement('div');
    this.dropdown.className = 'mention-dropdown';

    if (this.currentResults.length === 0) {
      this.dropdown.innerHTML = '<div class="mention-empty">No matches</div>';
    } else {
      // Group by type
      const grouped = this.groupByType(this.currentResults);
      let itemIndex = 0;

      for (const [type, entities] of Object.entries(grouped)) {
        if (entities.length === 0) continue;

        const group = document.createElement('div');
        group.className = 'mention-group';

        const header = document.createElement('div');
        header.className = 'mention-group-header';
        header.innerHTML = `${this.getTypeIcon(type)} ${this.getTypeLabel(type)}`;
        group.appendChild(header);

        for (const entity of entities) {
          const item = document.createElement('div');
          item.className = 'mention-item';
          if (itemIndex === this.selectedIndex) {
            item.classList.add('mention-item--selected');
          }
          item.textContent = entity.name;
          item.dataset.index = String(itemIndex);
          item.dataset.uuid = entity.uuid;
          item.dataset.type = entity.type;
          item.dataset.name = entity.name;
          group.appendChild(item);
          itemIndex++;
        }

        this.dropdown.appendChild(group);
      }
    }

    // Position dropdown above textarea
    this.positionDropdown();
    document.body.appendChild(this.dropdown);
  }

  private groupByType(entities: MentionEntity[]): Record<string, MentionEntity[]> {
    const groups: Record<string, MentionEntity[]> = {
      JournalEntry: [],
      Actor: [],
      Item: [],
      Scene: []
    };
    for (const entity of entities) {
      groups[entity.type].push(entity);
    }
    return groups;
  }

  private getTypeIcon(type: string): string {
    const icons: Record<string, string> = {
      Actor: '\uD83C\uDFAD',
      JournalEntry: '\uD83D\uDCD6',
      Item: '\u2694\uFE0F',
      Scene: '\uD83D\uDDFA\uFE0F'
    };
    return icons[type] || '\uD83D\uDCC4';
  }

  private getTypeLabel(type: string): string {
    const labels: Record<string, string> = {
      Actor: 'Actors',
      JournalEntry: 'Journals',
      Item: 'Items',
      Scene: 'Scenes'
    };
    return labels[type] || type;
  }

  private positionDropdown(): void {
    if (!this.dropdown) return;

    const rect = this.textarea.getBoundingClientRect();
    this.dropdown.style.position = 'fixed';
    this.dropdown.style.left = `${rect.left}px`;
    this.dropdown.style.bottom = `${window.innerHeight - rect.top + 4}px`;
    this.dropdown.style.minWidth = `${rect.width}px`;
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
