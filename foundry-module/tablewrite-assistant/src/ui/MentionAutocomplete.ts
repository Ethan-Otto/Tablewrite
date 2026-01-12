/**
 * @-mention autocomplete dropdown for Foundry VTT entities.
 * Triggers on '@' character, shows grouped suggestions for Actors, Journals, Items, Scenes.
 */
export class MentionAutocomplete {
  private textarea: HTMLTextAreaElement;
  private _isOpen: boolean = false;

  constructor(textarea: HTMLTextAreaElement) {
    this.textarea = textarea;
  }

  get isOpen(): boolean {
    return this._isOpen;
  }
}
