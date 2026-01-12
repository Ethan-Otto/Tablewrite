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

  describe('filterEntities', () => {
    it('filters entities by case-insensitive substring match', async () => {
      const { MentionAutocomplete } = await import('../../src/ui/MentionAutocomplete');
      const autocomplete = new MentionAutocomplete(textarea);

      const results = autocomplete.filterEntities('gob');

      expect(results).toHaveLength(2);
      // Results sorted alphabetically within same score tier
      expect(results[0].name).toBe('Goblin Boss');
      expect(results[1].name).toBe('Goblin Scout');
    });

    it('returns empty array for no matches', async () => {
      const { MentionAutocomplete } = await import('../../src/ui/MentionAutocomplete');
      const autocomplete = new MentionAutocomplete(textarea);

      const results = autocomplete.filterEntities('zzz');

      expect(results).toHaveLength(0);
    });

    it('prioritizes exact prefix matches over contains', async () => {
      const { MentionAutocomplete } = await import('../../src/ui/MentionAutocomplete');
      const autocomplete = new MentionAutocomplete(textarea);

      const results = autocomplete.filterEntities('lost');

      expect(results[0].name).toBe('Lost Mine of Phandelver');
    });

    it('limits results to 6 total', async () => {
      // Add more mock actors
      // @ts-ignore
      globalThis.game.actors = {
        contents: [
          { id: '1', name: 'Goblin 1', uuid: 'Actor.1' },
          { id: '2', name: 'Goblin 2', uuid: 'Actor.2' },
          { id: '3', name: 'Goblin 3', uuid: 'Actor.3' },
          { id: '4', name: 'Goblin 4', uuid: 'Actor.4' },
          { id: '5', name: 'Goblin 5', uuid: 'Actor.5' },
          { id: '6', name: 'Goblin 6', uuid: 'Actor.6' },
          { id: '7', name: 'Goblin 7', uuid: 'Actor.7' },
          { id: '8', name: 'Goblin 8', uuid: 'Actor.8' }
        ],
        map: function<T>(fn: (doc: any) => T): T[] { return this.contents.map(fn); }
      };

      const { MentionAutocomplete } = await import('../../src/ui/MentionAutocomplete');
      const autocomplete = new MentionAutocomplete(textarea);

      const results = autocomplete.filterEntities('goblin');

      expect(results.length).toBeLessThanOrEqual(6);
    });

    it('distributes results across entity types', async () => {
      // Reset mocks to have multiple matching types
      // @ts-ignore
      globalThis.game = {
        actors: {
          contents: [
            { id: '1', name: 'Cave Bear', uuid: 'Actor.1' },
            { id: '2', name: 'Cave Spider', uuid: 'Actor.2' }
          ],
          map: function<T>(fn: (doc: any) => T): T[] { return this.contents.map(fn); }
        },
        journal: {
          contents: [{ id: '1', name: 'Cave Notes', uuid: 'JournalEntry.1' }],
          map: function<T>(fn: (doc: any) => T): T[] { return this.contents.map(fn); }
        },
        items: {
          contents: [{ id: '1', name: 'Cave Map', uuid: 'Item.1' }],
          map: function<T>(fn: (doc: any) => T): T[] { return this.contents.map(fn); }
        },
        scenes: {
          contents: [{ id: '1', name: 'Cave Entrance', uuid: 'Scene.1' }],
          map: function<T>(fn: (doc: any) => T): T[] { return this.contents.map(fn); }
        }
      };

      const { MentionAutocomplete } = await import('../../src/ui/MentionAutocomplete');
      const autocomplete = new MentionAutocomplete(textarea);

      const results = autocomplete.filterEntities('cave');

      // Should have at least one from each type
      const types = results.map(r => r.type);
      expect(types).toContain('Actor');
      expect(types).toContain('JournalEntry');
      expect(types).toContain('Item');
      expect(types).toContain('Scene');
    });
  });
});
