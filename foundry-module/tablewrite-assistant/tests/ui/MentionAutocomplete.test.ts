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
    // Clean up any dropdowns
    document.querySelectorAll('.mention-dropdown').forEach(el => el.remove());
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

  describe('renderDropdown', () => {
    // Mock data for dropdown tests
    const mockActors = [
      { id: 'abc123', name: 'Goblin Scout', uuid: 'Actor.abc123' },
      { id: 'def456', name: 'Goblin Boss', uuid: 'Actor.def456' }
    ];
    const mockJournals = [
      { id: 'xyz789', name: 'Lost Mine of Phandelver', uuid: 'JournalEntry.xyz789' }
    ];
    const mockItems = [
      { id: 'item001', name: 'Longsword', uuid: 'Item.item001' }
    ];
    const mockScenes = [
      { id: 'scene001', name: 'Cragmaw Hideout', uuid: 'Scene.scene001' }
    ];

    beforeEach(() => {
      // Reset mocks
      // @ts-ignore
      globalThis.game = {
        actors: {
          contents: mockActors,
          map: function<T>(fn: (doc: any) => T): T[] { return this.contents.map(fn); }
        },
        journal: {
          contents: mockJournals,
          map: function<T>(fn: (doc: any) => T): T[] { return this.contents.map(fn); }
        },
        items: {
          contents: mockItems,
          map: function<T>(fn: (doc: any) => T): T[] { return this.contents.map(fn); }
        },
        scenes: {
          contents: mockScenes,
          map: function<T>(fn: (doc: any) => T): T[] { return this.contents.map(fn); }
        }
      };
    });

    it('creates dropdown element in DOM', async () => {
      const { MentionAutocomplete } = await import('../../src/ui/MentionAutocomplete');
      const autocomplete = new MentionAutocomplete(textarea);

      autocomplete.open('gob');

      const dropdown = document.querySelector('.mention-dropdown');
      expect(dropdown).toBeTruthy();
    });

    it('groups results by entity type with headers', async () => {
      const { MentionAutocomplete } = await import('../../src/ui/MentionAutocomplete');
      const autocomplete = new MentionAutocomplete(textarea);

      autocomplete.open('gob');

      const groups = document.querySelectorAll('.mention-group');
      expect(groups.length).toBeGreaterThan(0);

      const header = document.querySelector('.mention-group-header');
      expect(header?.textContent).toContain('Actors');
    });

    it('renders individual items with name', async () => {
      const { MentionAutocomplete } = await import('../../src/ui/MentionAutocomplete');
      const autocomplete = new MentionAutocomplete(textarea);

      autocomplete.open('gob');

      const items = document.querySelectorAll('.mention-item');
      expect(items.length).toBe(2);
    });

    it('highlights first item by default', async () => {
      const { MentionAutocomplete } = await import('../../src/ui/MentionAutocomplete');
      const autocomplete = new MentionAutocomplete(textarea);

      autocomplete.open('gob');

      const selected = document.querySelector('.mention-item--selected');
      expect(selected).toBeTruthy();
    });

    it('shows "No matches" when filter returns empty', async () => {
      const { MentionAutocomplete } = await import('../../src/ui/MentionAutocomplete');
      const autocomplete = new MentionAutocomplete(textarea);

      autocomplete.open('zzzzz');

      const dropdown = document.querySelector('.mention-dropdown');
      expect(dropdown?.textContent).toContain('No matches');
    });

    it('removes dropdown on close', async () => {
      const { MentionAutocomplete } = await import('../../src/ui/MentionAutocomplete');
      const autocomplete = new MentionAutocomplete(textarea);

      autocomplete.open('gob');
      autocomplete.close();

      const dropdown = document.querySelector('.mention-dropdown');
      expect(dropdown).toBeFalsy();
    });
  });

  describe('keyboard navigation', () => {
    // Mock data for keyboard navigation tests
    const mockActors = [
      { id: 'abc123', name: 'Goblin Boss', uuid: 'Actor.abc123' },
      { id: 'def456', name: 'Goblin Scout', uuid: 'Actor.def456' }
    ];
    const mockJournals = [
      { id: 'xyz789', name: 'Lost Mine of Phandelver', uuid: 'JournalEntry.xyz789' }
    ];
    const mockItems = [
      { id: 'item001', name: 'Longsword', uuid: 'Item.item001' }
    ];
    const mockScenes = [
      { id: 'scene001', name: 'Cragmaw Hideout', uuid: 'Scene.scene001' }
    ];

    beforeEach(() => {
      // @ts-ignore
      globalThis.game = {
        actors: {
          contents: mockActors,
          map: function<T>(fn: (doc: any) => T): T[] { return this.contents.map(fn); }
        },
        journal: {
          contents: mockJournals,
          map: function<T>(fn: (doc: any) => T): T[] { return this.contents.map(fn); }
        },
        items: {
          contents: mockItems,
          map: function<T>(fn: (doc: any) => T): T[] { return this.contents.map(fn); }
        },
        scenes: {
          contents: mockScenes,
          map: function<T>(fn: (doc: any) => T): T[] { return this.contents.map(fn); }
        }
      };
    });

    it('moves selection down on ArrowDown', async () => {
      const { MentionAutocomplete } = await import('../../src/ui/MentionAutocomplete');
      const autocomplete = new MentionAutocomplete(textarea);

      autocomplete.open('gob');
      autocomplete.handleKeyDown(new KeyboardEvent('keydown', { key: 'ArrowDown' }));

      const selected = document.querySelector('.mention-item--selected');
      expect(selected?.textContent).toContain('Goblin Scout');
    });

    it('wraps to top on ArrowDown at end', async () => {
      const { MentionAutocomplete } = await import('../../src/ui/MentionAutocomplete');
      const autocomplete = new MentionAutocomplete(textarea);

      autocomplete.open('gob');
      autocomplete.handleKeyDown(new KeyboardEvent('keydown', { key: 'ArrowDown' }));
      autocomplete.handleKeyDown(new KeyboardEvent('keydown', { key: 'ArrowDown' }));

      const selected = document.querySelector('.mention-item--selected');
      expect(selected?.textContent).toContain('Goblin Boss');
    });

    it('moves selection up on ArrowUp', async () => {
      const { MentionAutocomplete } = await import('../../src/ui/MentionAutocomplete');
      const autocomplete = new MentionAutocomplete(textarea);

      autocomplete.open('gob');
      autocomplete.handleKeyDown(new KeyboardEvent('keydown', { key: 'ArrowDown' }));
      autocomplete.handleKeyDown(new KeyboardEvent('keydown', { key: 'ArrowUp' }));

      const selected = document.querySelector('.mention-item--selected');
      expect(selected?.textContent).toContain('Goblin Boss');
    });

    it('wraps to bottom on ArrowUp at start', async () => {
      const { MentionAutocomplete } = await import('../../src/ui/MentionAutocomplete');
      const autocomplete = new MentionAutocomplete(textarea);

      autocomplete.open('gob');
      autocomplete.handleKeyDown(new KeyboardEvent('keydown', { key: 'ArrowUp' }));

      const selected = document.querySelector('.mention-item--selected');
      expect(selected?.textContent).toContain('Goblin Scout');
    });

    it('closes on Escape', async () => {
      const { MentionAutocomplete } = await import('../../src/ui/MentionAutocomplete');
      const autocomplete = new MentionAutocomplete(textarea);

      autocomplete.open('gob');
      autocomplete.handleKeyDown(new KeyboardEvent('keydown', { key: 'Escape' }));

      expect(autocomplete.isOpen).toBe(false);
      expect(document.querySelector('.mention-dropdown')).toBeFalsy();
    });

    it('returns true for handled keys to prevent default', async () => {
      const { MentionAutocomplete } = await import('../../src/ui/MentionAutocomplete');
      const autocomplete = new MentionAutocomplete(textarea);

      autocomplete.open('gob');
      expect(autocomplete.handleKeyDown(new KeyboardEvent('keydown', { key: 'ArrowDown' }))).toBe(true);
      expect(autocomplete.handleKeyDown(new KeyboardEvent('keydown', { key: 'ArrowUp' }))).toBe(true);

      // Tab closes dropdown, so reopen for next test
      expect(autocomplete.handleKeyDown(new KeyboardEvent('keydown', { key: 'Tab' }))).toBe(true);
      autocomplete.open('gob');

      // Enter closes dropdown, so reopen for next test
      expect(autocomplete.handleKeyDown(new KeyboardEvent('keydown', { key: 'Enter' }))).toBe(true);
      autocomplete.open('gob');

      // Escape closes dropdown
      expect(autocomplete.handleKeyDown(new KeyboardEvent('keydown', { key: 'Escape' }))).toBe(true);
    });

    it('returns false for unhandled keys', async () => {
      const { MentionAutocomplete } = await import('../../src/ui/MentionAutocomplete');
      const autocomplete = new MentionAutocomplete(textarea);

      autocomplete.open('gob');

      expect(autocomplete.handleKeyDown(new KeyboardEvent('keydown', { key: 'a' }))).toBe(false);
      expect(autocomplete.handleKeyDown(new KeyboardEvent('keydown', { key: 'Shift' }))).toBe(false);
    });
  });

  describe('insertSelected', () => {
    // Mock data for insertion tests
    const mockActors = [
      { id: 'abc123', name: 'Goblin Boss', uuid: 'Actor.abc123' },
      { id: 'def456', name: 'Goblin Scout', uuid: 'Actor.def456' }
    ];
    const mockJournals = [
      { id: 'xyz789', name: 'Lost Mine of Phandelver', uuid: 'JournalEntry.xyz789' }
    ];
    const mockItems = [
      { id: 'item001', name: 'Longsword', uuid: 'Item.item001' }
    ];
    const mockScenes = [
      { id: 'scene001', name: 'Cragmaw Hideout', uuid: 'Scene.scene001' }
    ];

    beforeEach(() => {
      // @ts-ignore
      globalThis.game = {
        actors: {
          contents: mockActors,
          map: function<T>(fn: (doc: any) => T): T[] { return this.contents.map(fn); }
        },
        journal: {
          contents: mockJournals,
          map: function<T>(fn: (doc: any) => T): T[] { return this.contents.map(fn); }
        },
        items: {
          contents: mockItems,
          map: function<T>(fn: (doc: any) => T): T[] { return this.contents.map(fn); }
        },
        scenes: {
          contents: mockScenes,
          map: function<T>(fn: (doc: any) => T): T[] { return this.contents.map(fn); }
        }
      };
    });

    it('inserts formatted mention at cursor position', async () => {
      const { MentionAutocomplete } = await import('../../src/ui/MentionAutocomplete');
      const autocomplete = new MentionAutocomplete(textarea);

      textarea.value = '@gob';
      textarea.selectionStart = 4;
      textarea.selectionEnd = 4;

      autocomplete.open('@gob'.substring(1)); // 'gob'

      // Wait for any async operations
      await new Promise(resolve => setTimeout(resolve, 10));

      autocomplete.insertSelected();

      // Should replace @gob with formatted mention
      expect(textarea.value).toMatch(/@\[.+\]\(.+\) /);
    });

    it('replaces @query text with mention', async () => {
      const { MentionAutocomplete } = await import('../../src/ui/MentionAutocomplete');
      const autocomplete = new MentionAutocomplete(textarea);

      textarea.value = 'Hello @test world';
      textarea.selectionStart = 11; // After @test
      textarea.selectionEnd = 11;

      // Update game mock with matching entity for 'test'
      // @ts-ignore
      globalThis.game.actors = {
        contents: [{ id: 'test1', name: 'Test Monster', uuid: 'Actor.test1' }],
        map: function<T>(fn: (doc: any) => T): T[] { return this.contents.map(fn); }
      };

      autocomplete.open('test');

      await new Promise(resolve => setTimeout(resolve, 10));

      autocomplete.insertSelected();

      expect(textarea.value).toContain('Hello @[');
      expect(textarea.value).toMatch(/\) +world/); // Trailing space from mention + existing space
      expect(textarea.value).not.toContain('@test ');
    });

    it('positions cursor after inserted mention', async () => {
      const { MentionAutocomplete } = await import('../../src/ui/MentionAutocomplete');
      const autocomplete = new MentionAutocomplete(textarea);

      textarea.value = '@gob';
      textarea.selectionStart = 4;
      textarea.selectionEnd = 4;

      autocomplete.open('gob');

      await new Promise(resolve => setTimeout(resolve, 10));

      autocomplete.insertSelected();

      // Cursor should be after the mention (after the trailing space)
      expect(textarea.selectionStart).toBeGreaterThan(4);
      expect(textarea.selectionStart).toBe(textarea.selectionEnd);
    });

    it('closes dropdown after insertion', async () => {
      const { MentionAutocomplete } = await import('../../src/ui/MentionAutocomplete');
      const autocomplete = new MentionAutocomplete(textarea);

      textarea.value = '@gob';
      textarea.selectionStart = 4;
      textarea.selectionEnd = 4;

      autocomplete.open('gob');

      await new Promise(resolve => setTimeout(resolve, 10));

      expect(autocomplete.isOpen).toBe(true);

      autocomplete.insertSelected();

      expect(autocomplete.isOpen).toBe(false);
    });

    it('does nothing when no results available', async () => {
      const { MentionAutocomplete } = await import('../../src/ui/MentionAutocomplete');
      const autocomplete = new MentionAutocomplete(textarea);

      textarea.value = '@xyz123nonexistent';
      textarea.selectionStart = 18;
      textarea.selectionEnd = 18;

      // Don't open - currentResults will be empty
      autocomplete.insertSelected();

      // Value should be unchanged
      expect(textarea.value).toBe('@xyz123nonexistent');
    });
  });

  describe('mouse click selection', () => {
    // Mock data for mouse interaction tests
    const mockActors = [
      { id: 'abc123', name: 'Goblin Boss', uuid: 'Actor.abc123' },
      { id: 'def456', name: 'Goblin Scout', uuid: 'Actor.def456' }
    ];
    const mockJournals = [
      { id: 'xyz789', name: 'Lost Mine of Phandelver', uuid: 'JournalEntry.xyz789' }
    ];
    const mockItems = [
      { id: 'item001', name: 'Longsword', uuid: 'Item.item001' }
    ];
    const mockScenes = [
      { id: 'scene001', name: 'Cragmaw Hideout', uuid: 'Scene.scene001' }
    ];

    beforeEach(() => {
      // @ts-ignore
      globalThis.game = {
        actors: {
          contents: mockActors,
          map: function<T>(fn: (doc: any) => T): T[] { return this.contents.map(fn); }
        },
        journal: {
          contents: mockJournals,
          map: function<T>(fn: (doc: any) => T): T[] { return this.contents.map(fn); }
        },
        items: {
          contents: mockItems,
          map: function<T>(fn: (doc: any) => T): T[] { return this.contents.map(fn); }
        },
        scenes: {
          contents: mockScenes,
          map: function<T>(fn: (doc: any) => T): T[] { return this.contents.map(fn); }
        }
      };
    });

    it('inserts mention when item is clicked', async () => {
      const { MentionAutocomplete } = await import('../../src/ui/MentionAutocomplete');
      const autocomplete = new MentionAutocomplete(textarea);

      textarea.value = '@gob';
      textarea.selectionStart = 4;
      textarea.selectionEnd = 4;

      autocomplete.open('gob');

      await new Promise(resolve => setTimeout(resolve, 10));

      // Find and click the first item
      const dropdown = document.querySelector('.mention-dropdown');
      const firstItem = dropdown?.querySelector('.mention-item');
      expect(firstItem).toBeTruthy();

      firstItem?.dispatchEvent(new MouseEvent('click', { bubbles: true }));

      // Should have inserted mention
      expect(textarea.value).toMatch(/@\[.+\]\(.+\) /);
      expect(autocomplete.isOpen).toBe(false);
    });

    it('updates selection on mouseenter', async () => {
      const { MentionAutocomplete } = await import('../../src/ui/MentionAutocomplete');
      const autocomplete = new MentionAutocomplete(textarea);

      textarea.value = '@g';
      textarea.selectionStart = 2;
      textarea.selectionEnd = 2;

      autocomplete.open('g');

      await new Promise(resolve => setTimeout(resolve, 10));

      const items = document.querySelectorAll('.mention-item');
      expect(items.length).toBeGreaterThan(1);

      // First item should be selected initially
      expect(items[0].classList.contains('mention-item--selected')).toBe(true);

      // Mouse over second item
      items[1].dispatchEvent(new MouseEvent('mouseenter', { bubbles: true }));

      // Second item should now be selected
      expect(items[0].classList.contains('mention-item--selected')).toBe(false);
      expect(items[1].classList.contains('mention-item--selected')).toBe(true);
    });
  });

  describe('handleInput', () => {
    // Mock data for handleInput tests
    const mockActors = [
      { id: 'abc123', name: 'Goblin Scout', uuid: 'Actor.abc123' },
      { id: 'def456', name: 'Goblin Boss', uuid: 'Actor.def456' }
    ];
    const mockJournals = [
      { id: 'xyz789', name: 'Lost Mine of Phandelver', uuid: 'JournalEntry.xyz789' }
    ];
    const mockItems = [
      { id: 'item001', name: 'Longsword', uuid: 'Item.item001' }
    ];
    const mockScenes = [
      { id: 'scene001', name: 'Cragmaw Hideout', uuid: 'Scene.scene001' }
    ];

    beforeEach(() => {
      // @ts-ignore
      globalThis.game = {
        actors: {
          contents: mockActors,
          map: function<T>(fn: (doc: any) => T): T[] { return this.contents.map(fn); }
        },
        journal: {
          contents: mockJournals,
          map: function<T>(fn: (doc: any) => T): T[] { return this.contents.map(fn); }
        },
        items: {
          contents: mockItems,
          map: function<T>(fn: (doc: any) => T): T[] { return this.contents.map(fn); }
        },
        scenes: {
          contents: mockScenes,
          map: function<T>(fn: (doc: any) => T): T[] { return this.contents.map(fn); }
        }
      };
    });

    it('opens autocomplete when @ is typed', async () => {
      const { MentionAutocomplete } = await import('../../src/ui/MentionAutocomplete');
      const autocomplete = new MentionAutocomplete(textarea);

      textarea.value = '@';
      textarea.selectionStart = 1;
      textarea.selectionEnd = 1;
      textarea.dispatchEvent(new Event('input'));

      expect(autocomplete.isOpen).toBe(true);
    });

    it('updates results as user types after @', async () => {
      const { MentionAutocomplete } = await import('../../src/ui/MentionAutocomplete');
      const autocomplete = new MentionAutocomplete(textarea);

      textarea.value = '@gob';
      textarea.selectionStart = 4;
      textarea.selectionEnd = 4;
      textarea.dispatchEvent(new Event('input'));

      expect(autocomplete.isOpen).toBe(true);
    });

    it('closes when @ is deleted', async () => {
      const { MentionAutocomplete } = await import('../../src/ui/MentionAutocomplete');
      const autocomplete = new MentionAutocomplete(textarea);

      // First open
      textarea.value = '@gob';
      textarea.selectionStart = 4;
      textarea.selectionEnd = 4;
      textarea.dispatchEvent(new Event('input'));

      expect(autocomplete.isOpen).toBe(true);

      // Then delete the @
      textarea.value = 'gob';
      textarea.selectionStart = 3;
      textarea.selectionEnd = 3;
      textarea.dispatchEvent(new Event('input'));

      expect(autocomplete.isOpen).toBe(false);
    });

    it('closes when space is typed after @query', async () => {
      const { MentionAutocomplete } = await import('../../src/ui/MentionAutocomplete');
      const autocomplete = new MentionAutocomplete(textarea);

      // First open
      textarea.value = '@gob';
      textarea.selectionStart = 4;
      textarea.selectionEnd = 4;
      textarea.dispatchEvent(new Event('input'));

      expect(autocomplete.isOpen).toBe(true);

      // Then type space
      textarea.value = '@gob ';
      textarea.selectionStart = 5;
      textarea.selectionEnd = 5;
      textarea.dispatchEvent(new Event('input'));

      expect(autocomplete.isOpen).toBe(false);
    });

    it('extracts query after @ for filtering', async () => {
      const { MentionAutocomplete } = await import('../../src/ui/MentionAutocomplete');
      const autocomplete = new MentionAutocomplete(textarea);

      textarea.value = 'Hello @gob';
      textarea.selectionStart = 10;
      textarea.selectionEnd = 10;
      textarea.dispatchEvent(new Event('input'));

      // Should filter with 'gob' query
      expect(autocomplete.isOpen).toBe(true);
    });

    it('does not trigger @ in middle of word', async () => {
      const { MentionAutocomplete } = await import('../../src/ui/MentionAutocomplete');
      const autocomplete = new MentionAutocomplete(textarea);

      textarea.value = 'test@email.com';
      textarea.selectionStart = 14;
      textarea.selectionEnd = 14;
      textarea.dispatchEvent(new Event('input'));

      expect(autocomplete.isOpen).toBe(false);
    });
  });
});
