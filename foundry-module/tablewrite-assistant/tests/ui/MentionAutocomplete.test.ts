import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock Foundry globals with proper collection structure (using .contents)
const mockActorDocs = [
  { id: 'abc123', name: 'Goblin Scout', uuid: 'Actor.abc123' },
  { id: 'def456', name: 'Goblin Boss', uuid: 'Actor.def456' }
];
const mockJournalDocs = [
  { id: 'xyz789', name: 'Lost Mine of Phandelver', uuid: 'JournalEntry.xyz789' }
];
const mockItemDocs = [
  { id: 'item001', name: 'Longsword', uuid: 'Item.item001' }
];
const mockSceneDocs = [
  { id: 'scene001', name: 'Cragmaw Hideout', uuid: 'Scene.scene001' }
];

// @ts-ignore - Mock Foundry collection objects with .contents property
globalThis.game = {
  actors: { contents: mockActorDocs, map: <T>(fn: (doc: typeof mockActorDocs[0]) => T) => mockActorDocs.map(fn) },
  journal: { contents: mockJournalDocs, map: <T>(fn: (doc: typeof mockJournalDocs[0]) => T) => mockJournalDocs.map(fn) },
  items: { contents: mockItemDocs, map: <T>(fn: (doc: typeof mockItemDocs[0]) => T) => mockItemDocs.map(fn) },
  scenes: { contents: mockSceneDocs, map: <T>(fn: (doc: typeof mockSceneDocs[0]) => T) => mockSceneDocs.map(fn) }
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
