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

declare const game: {
  actors?: Array<{ name: string; uuid: string }>;
  journal?: Array<{ name: string; uuid: string }>;
  items?: Array<{ name: string; uuid: string }>;
  scenes?: Array<{ name: string; uuid: string }>;
};

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
    return {
      actors: (game.actors ?? []).map((a: any) => ({
        name: a.name,
        uuid: a.uuid,
        type: 'Actor' as const
      })),
      journals: (game.journal ?? []).map((j: any) => ({
        name: j.name,
        uuid: j.uuid,
        type: 'JournalEntry' as const
      })),
      items: (game.items ?? []).map((i: any) => ({
        name: i.name,
        uuid: i.uuid,
        type: 'Item' as const
      })),
      scenes: (game.scenes ?? []).map((s: any) => ({
        name: s.name,
        uuid: s.uuid,
        type: 'Scene' as const
      }))
    };
  }
}
