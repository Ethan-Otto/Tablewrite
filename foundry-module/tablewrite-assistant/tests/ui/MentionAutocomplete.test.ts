import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock Foundry globals
const mockActors = [
  { name: 'Goblin Scout', uuid: 'Actor.abc123' },
  { name: 'Goblin Boss', uuid: 'Actor.def456' }
];
const mockJournals = [
  { name: 'Lost Mine of Phandelver', uuid: 'JournalEntry.xyz789' }
];
const mockItems = [
  { name: 'Longsword', uuid: 'Item.item001' }
];
const mockScenes = [
  { name: 'Cragmaw Hideout', uuid: 'Scene.scene001' }
];

// @ts-ignore
globalThis.game = {
  actors: mockActors,
  journal: mockJournals,
  items: mockItems,
  scenes: mockScenes
};

describe('MentionAutocomplete', () => {
  let textarea: HTMLTextAreaElement;
  let container: HTMLElement;

  beforeEach(() => {
    container = document.createElement('div');
    textarea = document.createElement('textarea');
    container.appendChild(textarea);
    document.body.appendChild(container);
  });

  afterEach(() => {
    document.body.removeChild(container);
  });

  describe('constructor', () => {
    it('creates instance with textarea reference', async () => {
      const { MentionAutocomplete } = await import('../../src/ui/MentionAutocomplete');
      const autocomplete = new MentionAutocomplete(textarea);

      expect(autocomplete).toBeDefined();
      expect(autocomplete.isOpen).toBe(false);
    });
  });

  describe('getEntities', () => {
    it('returns all entity types from game object', async () => {
      const { MentionAutocomplete } = await import('../../src/ui/MentionAutocomplete');
      const autocomplete = new MentionAutocomplete(textarea);

      const entities = autocomplete.getEntities();

      expect(entities.actors).toHaveLength(2);
      expect(entities.journals).toHaveLength(1);
      expect(entities.items).toHaveLength(1);
      expect(entities.scenes).toHaveLength(1);
    });

    it('maps entities to standardized format', async () => {
      const { MentionAutocomplete } = await import('../../src/ui/MentionAutocomplete');
      const autocomplete = new MentionAutocomplete(textarea);

      const entities = autocomplete.getEntities();

      expect(entities.actors[0]).toEqual({
        name: 'Goblin Scout',
        uuid: 'Actor.abc123',
        type: 'Actor'
      });
    });
  });
});
