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
}
