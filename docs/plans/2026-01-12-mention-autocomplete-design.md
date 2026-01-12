# @-Mention Autocomplete Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add @-mention autocomplete to the Tablewrite chat input for referencing Foundry VTT entities (Actors, Journals, Items, Scenes).

**Architecture:** Create a standalone `MentionAutocomplete` class that manages a dropdown UI. It listens for `@` character input, fetches entities from Foundry's `game` object, filters/scores them, and inserts formatted mentions. Integration is via event delegation from `TablewriteTab`.

**Tech Stack:** TypeScript, Vitest for testing, Foundry VTT API (`game.actors`, `game.journal`, etc.)

---

## Task 1: Create MentionAutocomplete Class Shell

**Files:**
- Create: `foundry-module/tablewrite-assistant/src/ui/MentionAutocomplete.ts`
- Test: `foundry-module/tablewrite-assistant/tests/ui/MentionAutocomplete.test.ts`

**Step 1: Write the failing test for class instantiation**

Create `foundry-module/tablewrite-assistant/tests/ui/MentionAutocomplete.test.ts`:

```typescript
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
});
```

**Step 2: Run test to verify it fails**

Run: `cd foundry-module/tablewrite-assistant && npm test -- tests/ui/MentionAutocomplete.test.ts`
Expected: FAIL with "Cannot find module" or similar

**Step 3: Write minimal implementation**

Create `foundry-module/tablewrite-assistant/src/ui/MentionAutocomplete.ts`:

```typescript
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
```

**Step 4: Run test to verify it passes**

Run: `cd foundry-module/tablewrite-assistant && npm test -- tests/ui/MentionAutocomplete.test.ts`
Expected: PASS

**Step 5: Commit**

```bash
git add foundry-module/tablewrite-assistant/src/ui/MentionAutocomplete.ts foundry-module/tablewrite-assistant/tests/ui/MentionAutocomplete.test.ts
git commit -m "feat(mention): add MentionAutocomplete class shell"
```

---

## Task 2: Implement Entity Fetching

**Files:**
- Modify: `foundry-module/tablewrite-assistant/src/ui/MentionAutocomplete.ts`
- Test: `foundry-module/tablewrite-assistant/tests/ui/MentionAutocomplete.test.ts`

**Step 1: Write the failing test for entity fetching**

Add to `tests/ui/MentionAutocomplete.test.ts`:

```typescript
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
```

**Step 2: Run test to verify it fails**

Run: `cd foundry-module/tablewrite-assistant && npm test -- tests/ui/MentionAutocomplete.test.ts`
Expected: FAIL with "getEntities is not a function"

**Step 3: Write minimal implementation**

Add to `MentionAutocomplete.ts`:

```typescript
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

// Inside class:
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
```

**Step 4: Run test to verify it passes**

Run: `cd foundry-module/tablewrite-assistant && npm test -- tests/ui/MentionAutocomplete.test.ts`
Expected: PASS

**Step 5: Commit**

```bash
git add foundry-module/tablewrite-assistant/src/ui/MentionAutocomplete.ts foundry-module/tablewrite-assistant/tests/ui/MentionAutocomplete.test.ts
git commit -m "feat(mention): add entity fetching from Foundry game object"
```

---

## Task 3: Implement Search/Filter Logic

**Files:**
- Modify: `foundry-module/tablewrite-assistant/src/ui/MentionAutocomplete.ts`
- Test: `foundry-module/tablewrite-assistant/tests/ui/MentionAutocomplete.test.ts`

**Step 1: Write the failing test for filtering**

Add to `tests/ui/MentionAutocomplete.test.ts`:

```typescript
  describe('filterEntities', () => {
    it('filters entities by case-insensitive substring match', async () => {
      const { MentionAutocomplete } = await import('../../src/ui/MentionAutocomplete');
      const autocomplete = new MentionAutocomplete(textarea);

      const results = autocomplete.filterEntities('gob');

      expect(results).toHaveLength(2);
      expect(results[0].name).toBe('Goblin Scout');
      expect(results[1].name).toBe('Goblin Boss');
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
      globalThis.game.actors = [
        { name: 'Goblin 1', uuid: 'Actor.1' },
        { name: 'Goblin 2', uuid: 'Actor.2' },
        { name: 'Goblin 3', uuid: 'Actor.3' },
        { name: 'Goblin 4', uuid: 'Actor.4' },
        { name: 'Goblin 5', uuid: 'Actor.5' },
        { name: 'Goblin 6', uuid: 'Actor.6' },
        { name: 'Goblin 7', uuid: 'Actor.7' },
        { name: 'Goblin 8', uuid: 'Actor.8' }
      ];

      const { MentionAutocomplete } = await import('../../src/ui/MentionAutocomplete');
      const autocomplete = new MentionAutocomplete(textarea);

      const results = autocomplete.filterEntities('goblin');

      expect(results.length).toBeLessThanOrEqual(6);
    });

    it('distributes results across entity types', async () => {
      // Reset mocks to have multiple matching types
      // @ts-ignore
      globalThis.game = {
        actors: [
          { name: 'Cave Bear', uuid: 'Actor.1' },
          { name: 'Cave Spider', uuid: 'Actor.2' }
        ],
        journal: [
          { name: 'Cave Notes', uuid: 'JournalEntry.1' }
        ],
        items: [
          { name: 'Cave Map', uuid: 'Item.1' }
        ],
        scenes: [
          { name: 'Cave Entrance', uuid: 'Scene.1' }
        ]
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
```

**Step 2: Run test to verify it fails**

Run: `cd foundry-module/tablewrite-assistant && npm test -- tests/ui/MentionAutocomplete.test.ts`
Expected: FAIL with "filterEntities is not a function"

**Step 3: Write minimal implementation**

Add to `MentionAutocomplete.ts`:

```typescript
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
```

**Step 4: Run test to verify it passes**

Run: `cd foundry-module/tablewrite-assistant && npm test -- tests/ui/MentionAutocomplete.test.ts`
Expected: PASS

**Step 5: Commit**

```bash
git add foundry-module/tablewrite-assistant/src/ui/MentionAutocomplete.ts foundry-module/tablewrite-assistant/tests/ui/MentionAutocomplete.test.ts
git commit -m "feat(mention): add entity filtering with scoring and distribution"
```

---

## Task 4: Implement Dropdown Rendering

**Files:**
- Modify: `foundry-module/tablewrite-assistant/src/ui/MentionAutocomplete.ts`
- Test: `foundry-module/tablewrite-assistant/tests/ui/MentionAutocomplete.test.ts`

**Step 1: Write the failing test for dropdown rendering**

Add to `tests/ui/MentionAutocomplete.test.ts`:

```typescript
  describe('renderDropdown', () => {
    beforeEach(() => {
      // Reset mocks
      // @ts-ignore
      globalThis.game = {
        actors: mockActors,
        journal: mockJournals,
        items: mockItems,
        scenes: mockScenes
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
      expect(items[0].textContent).toContain('Goblin Scout');
    });

    it('highlights first item by default', async () => {
      const { MentionAutocomplete } = await import('../../src/ui/MentionAutocomplete');
      const autocomplete = new MentionAutocomplete(textarea);

      autocomplete.open('gob');

      const selected = document.querySelector('.mention-item--selected');
      expect(selected).toBeTruthy();
      expect(selected?.textContent).toContain('Goblin Scout');
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
```

**Step 2: Run test to verify it fails**

Run: `cd foundry-module/tablewrite-assistant && npm test -- tests/ui/MentionAutocomplete.test.ts`
Expected: FAIL with "open is not a function"

**Step 3: Write minimal implementation**

Add to `MentionAutocomplete.ts`:

```typescript
  private dropdown: HTMLElement | null = null;
  private selectedIndex: number = 0;
  private currentResults: MentionEntity[] = [];
  private currentQuery: string = '';

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
      Actor: '🎭',
      JournalEntry: '📖',
      Item: '⚔️',
      Scene: '🗺️'
    };
    return icons[type] || '📄';
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
```

**Step 4: Run test to verify it passes**

Run: `cd foundry-module/tablewrite-assistant && npm test -- tests/ui/MentionAutocomplete.test.ts`
Expected: PASS

**Step 5: Commit**

```bash
git add foundry-module/tablewrite-assistant/src/ui/MentionAutocomplete.ts foundry-module/tablewrite-assistant/tests/ui/MentionAutocomplete.test.ts
git commit -m "feat(mention): add dropdown rendering with grouped results"
```

---

## Task 5: Implement Keyboard Navigation

**Files:**
- Modify: `foundry-module/tablewrite-assistant/src/ui/MentionAutocomplete.ts`
- Test: `foundry-module/tablewrite-assistant/tests/ui/MentionAutocomplete.test.ts`

**Step 1: Write the failing test for keyboard navigation**

Add to `tests/ui/MentionAutocomplete.test.ts`:

```typescript
  describe('keyboard navigation', () => {
    beforeEach(() => {
      // @ts-ignore
      globalThis.game = {
        actors: mockActors,
        journal: mockJournals,
        items: mockItems,
        scenes: mockScenes
      };
    });

    it('moves selection down on ArrowDown', async () => {
      const { MentionAutocomplete } = await import('../../src/ui/MentionAutocomplete');
      const autocomplete = new MentionAutocomplete(textarea);

      autocomplete.open('gob');
      autocomplete.handleKeyDown(new KeyboardEvent('keydown', { key: 'ArrowDown' }));

      const selected = document.querySelector('.mention-item--selected');
      expect(selected?.textContent).toContain('Goblin Boss');
    });

    it('wraps to top on ArrowDown at end', async () => {
      const { MentionAutocomplete } = await import('../../src/ui/MentionAutocomplete');
      const autocomplete = new MentionAutocomplete(textarea);

      autocomplete.open('gob');
      autocomplete.handleKeyDown(new KeyboardEvent('keydown', { key: 'ArrowDown' }));
      autocomplete.handleKeyDown(new KeyboardEvent('keydown', { key: 'ArrowDown' }));

      const selected = document.querySelector('.mention-item--selected');
      expect(selected?.textContent).toContain('Goblin Scout');
    });

    it('moves selection up on ArrowUp', async () => {
      const { MentionAutocomplete } = await import('../../src/ui/MentionAutocomplete');
      const autocomplete = new MentionAutocomplete(textarea);

      autocomplete.open('gob');
      autocomplete.handleKeyDown(new KeyboardEvent('keydown', { key: 'ArrowDown' }));
      autocomplete.handleKeyDown(new KeyboardEvent('keydown', { key: 'ArrowUp' }));

      const selected = document.querySelector('.mention-item--selected');
      expect(selected?.textContent).toContain('Goblin Scout');
    });

    it('wraps to bottom on ArrowUp at start', async () => {
      const { MentionAutocomplete } = await import('../../src/ui/MentionAutocomplete');
      const autocomplete = new MentionAutocomplete(textarea);

      autocomplete.open('gob');
      autocomplete.handleKeyDown(new KeyboardEvent('keydown', { key: 'ArrowUp' }));

      const selected = document.querySelector('.mention-item--selected');
      expect(selected?.textContent).toContain('Goblin Boss');
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
      expect(autocomplete.handleKeyDown(new KeyboardEvent('keydown', { key: 'Tab' }))).toBe(true);
      expect(autocomplete.handleKeyDown(new KeyboardEvent('keydown', { key: 'Enter' }))).toBe(true);
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
```

**Step 2: Run test to verify it fails**

Run: `cd foundry-module/tablewrite-assistant && npm test -- tests/ui/MentionAutocomplete.test.ts`
Expected: FAIL with "handleKeyDown is not a function"

**Step 3: Write minimal implementation**

Add to `MentionAutocomplete.ts`:

```typescript
  handleKeyDown(event: KeyboardEvent): boolean {
    if (!this._isOpen) return false;

    switch (event.key) {
      case 'ArrowDown':
        this.moveSelection(1);
        return true;
      case 'ArrowUp':
        this.moveSelection(-1);
        return true;
      case 'Tab':
      case 'Enter':
        this.insertSelected();
        return true;
      case 'Escape':
        this.close();
        return true;
      default:
        return false;
    }
  }

  private moveSelection(delta: number): void {
    if (this.currentResults.length === 0) return;

    this.selectedIndex += delta;
    if (this.selectedIndex < 0) {
      this.selectedIndex = this.currentResults.length - 1;
    } else if (this.selectedIndex >= this.currentResults.length) {
      this.selectedIndex = 0;
    }

    this.updateSelectionHighlight();
  }

  private updateSelectionHighlight(): void {
    if (!this.dropdown) return;

    const items = this.dropdown.querySelectorAll('.mention-item');
    items.forEach((item, index) => {
      item.classList.toggle('mention-item--selected', index === this.selectedIndex);
    });
  }

  private insertSelected(): void {
    // Placeholder - will be implemented in Task 6
    this.close();
  }
```

**Step 4: Run test to verify it passes**

Run: `cd foundry-module/tablewrite-assistant && npm test -- tests/ui/MentionAutocomplete.test.ts`
Expected: PASS

**Step 5: Commit**

```bash
git add foundry-module/tablewrite-assistant/src/ui/MentionAutocomplete.ts foundry-module/tablewrite-assistant/tests/ui/MentionAutocomplete.test.ts
git commit -m "feat(mention): add keyboard navigation for dropdown"
```

---

## Task 6: Implement Mention Insertion

**Files:**
- Modify: `foundry-module/tablewrite-assistant/src/ui/MentionAutocomplete.ts`
- Test: `foundry-module/tablewrite-assistant/tests/ui/MentionAutocomplete.test.ts`

**Step 1: Write the failing test for mention insertion**

Add to `tests/ui/MentionAutocomplete.test.ts`:

```typescript
  describe('insertSelected', () => {
    beforeEach(() => {
      // @ts-ignore
      globalThis.game = {
        actors: mockActors,
        journal: mockJournals,
        items: mockItems,
        scenes: mockScenes
      };
    });

    it('inserts formatted mention at cursor position', async () => {
      const { MentionAutocomplete } = await import('../../src/ui/MentionAutocomplete');
      const autocomplete = new MentionAutocomplete(textarea);

      textarea.value = 'Hello @gob';
      textarea.selectionStart = 10;
      textarea.selectionEnd = 10;

      autocomplete.open('gob');
      autocomplete.handleKeyDown(new KeyboardEvent('keydown', { key: 'Enter' }));

      expect(textarea.value).toBe('Hello @[Goblin Scout](Actor.abc123) ');
    });

    it('replaces query text with mention', async () => {
      const { MentionAutocomplete } = await import('../../src/ui/MentionAutocomplete');
      const autocomplete = new MentionAutocomplete(textarea);

      textarea.value = 'Attack @goblin and run';
      textarea.selectionStart = 14;
      textarea.selectionEnd = 14;

      autocomplete.open('goblin');
      autocomplete.handleKeyDown(new KeyboardEvent('keydown', { key: 'Tab' }));

      expect(textarea.value).toBe('Attack @[Goblin Scout](Actor.abc123)  and run');
    });

    it('positions cursor after inserted mention', async () => {
      const { MentionAutocomplete } = await import('../../src/ui/MentionAutocomplete');
      const autocomplete = new MentionAutocomplete(textarea);

      textarea.value = '@gob';
      textarea.selectionStart = 4;
      textarea.selectionEnd = 4;

      autocomplete.open('gob');
      autocomplete.handleKeyDown(new KeyboardEvent('keydown', { key: 'Enter' }));

      const expectedEnd = '@[Goblin Scout](Actor.abc123) '.length;
      expect(textarea.selectionStart).toBe(expectedEnd);
      expect(textarea.selectionEnd).toBe(expectedEnd);
    });

    it('closes dropdown after insertion', async () => {
      const { MentionAutocomplete } = await import('../../src/ui/MentionAutocomplete');
      const autocomplete = new MentionAutocomplete(textarea);

      textarea.value = '@gob';
      textarea.selectionStart = 4;

      autocomplete.open('gob');
      autocomplete.handleKeyDown(new KeyboardEvent('keydown', { key: 'Enter' }));

      expect(autocomplete.isOpen).toBe(false);
    });
  });
```

**Step 2: Run test to verify it fails**

Run: `cd foundry-module/tablewrite-assistant && npm test -- tests/ui/MentionAutocomplete.test.ts`
Expected: FAIL (insertSelected doesn't modify textarea)

**Step 3: Write minimal implementation**

Update `insertSelected` in `MentionAutocomplete.ts`:

```typescript
  private insertSelected(): void {
    if (this.currentResults.length === 0) {
      this.close();
      return;
    }

    const selected = this.currentResults[this.selectedIndex];
    const mention = `@[${selected.name}](${selected.uuid}) `;

    // Find the @ that triggered this autocomplete
    const cursorPos = this.textarea.selectionStart;
    const textBeforeCursor = this.textarea.value.substring(0, cursorPos);
    const atIndex = textBeforeCursor.lastIndexOf('@');

    if (atIndex === -1) {
      this.close();
      return;
    }

    // Replace @query with @[Name](uuid)
    const beforeAt = this.textarea.value.substring(0, atIndex);
    const afterCursor = this.textarea.value.substring(cursorPos);

    this.textarea.value = beforeAt + mention + afterCursor;

    // Position cursor after mention
    const newCursorPos = atIndex + mention.length;
    this.textarea.selectionStart = newCursorPos;
    this.textarea.selectionEnd = newCursorPos;

    this.close();
  }
```

**Step 4: Run test to verify it passes**

Run: `cd foundry-module/tablewrite-assistant && npm test -- tests/ui/MentionAutocomplete.test.ts`
Expected: PASS

**Step 5: Commit**

```bash
git add foundry-module/tablewrite-assistant/src/ui/MentionAutocomplete.ts foundry-module/tablewrite-assistant/tests/ui/MentionAutocomplete.test.ts
git commit -m "feat(mention): add mention insertion into textarea"
```

---

## Task 7: Implement @ Detection Logic

**Files:**
- Modify: `foundry-module/tablewrite-assistant/src/ui/MentionAutocomplete.ts`
- Test: `foundry-module/tablewrite-assistant/tests/ui/MentionAutocomplete.test.ts`

**Step 1: Write the failing test for @ detection**

Add to `tests/ui/MentionAutocomplete.test.ts`:

```typescript
  describe('detectMention', () => {
    it('detects @ at start of input', async () => {
      const { MentionAutocomplete } = await import('../../src/ui/MentionAutocomplete');
      const autocomplete = new MentionAutocomplete(textarea);

      textarea.value = '@gob';
      textarea.selectionStart = 4;

      const result = autocomplete.detectMention();

      expect(result).toEqual({ active: true, query: 'gob' });
    });

    it('detects @ after space', async () => {
      const { MentionAutocomplete } = await import('../../src/ui/MentionAutocomplete');
      const autocomplete = new MentionAutocomplete(textarea);

      textarea.value = 'Hello @world';
      textarea.selectionStart = 12;

      const result = autocomplete.detectMention();

      expect(result).toEqual({ active: true, query: 'world' });
    });

    it('returns inactive for @ in middle of word', async () => {
      const { MentionAutocomplete } = await import('../../src/ui/MentionAutocomplete');
      const autocomplete = new MentionAutocomplete(textarea);

      textarea.value = 'email@example.com';
      textarea.selectionStart = 17;

      const result = autocomplete.detectMention();

      expect(result).toEqual({ active: false, query: '' });
    });

    it('returns inactive for no @', async () => {
      const { MentionAutocomplete } = await import('../../src/ui/MentionAutocomplete');
      const autocomplete = new MentionAutocomplete(textarea);

      textarea.value = 'Hello world';
      textarea.selectionStart = 11;

      const result = autocomplete.detectMention();

      expect(result).toEqual({ active: false, query: '' });
    });

    it('returns empty query for just @', async () => {
      const { MentionAutocomplete } = await import('../../src/ui/MentionAutocomplete');
      const autocomplete = new MentionAutocomplete(textarea);

      textarea.value = 'Hello @';
      textarea.selectionStart = 7;

      const result = autocomplete.detectMention();

      expect(result).toEqual({ active: true, query: '' });
    });

    it('stops at space after @', async () => {
      const { MentionAutocomplete } = await import('../../src/ui/MentionAutocomplete');
      const autocomplete = new MentionAutocomplete(textarea);

      textarea.value = '@gob and more';
      textarea.selectionStart = 4;

      const result = autocomplete.detectMention();

      expect(result).toEqual({ active: true, query: 'gob' });
    });
  });
```

**Step 2: Run test to verify it fails**

Run: `cd foundry-module/tablewrite-assistant && npm test -- tests/ui/MentionAutocomplete.test.ts`
Expected: FAIL with "detectMention is not a function"

**Step 3: Write minimal implementation**

Add to `MentionAutocomplete.ts`:

```typescript
  detectMention(): { active: boolean; query: string } {
    const cursorPos = this.textarea.selectionStart;
    const textBeforeCursor = this.textarea.value.substring(0, cursorPos);

    // Find the last @ before cursor
    const atIndex = textBeforeCursor.lastIndexOf('@');

    if (atIndex === -1) {
      return { active: false, query: '' };
    }

    // Check if @ is at start or preceded by whitespace
    if (atIndex > 0) {
      const charBefore = textBeforeCursor[atIndex - 1];
      if (!/\s/.test(charBefore)) {
        return { active: false, query: '' };
      }
    }

    // Extract query: text between @ and cursor (no spaces)
    const query = textBeforeCursor.substring(atIndex + 1);

    // If query contains space, mention is no longer active
    if (query.includes(' ')) {
      return { active: false, query: '' };
    }

    return { active: true, query };
  }
```

**Step 4: Run test to verify it passes**

Run: `cd foundry-module/tablewrite-assistant && npm test -- tests/ui/MentionAutocomplete.test.ts`
Expected: PASS

**Step 5: Commit**

```bash
git add foundry-module/tablewrite-assistant/src/ui/MentionAutocomplete.ts foundry-module/tablewrite-assistant/tests/ui/MentionAutocomplete.test.ts
git commit -m "feat(mention): add @ detection logic"
```

---

## Task 8: Add CSS Styles

**Files:**
- Modify: `foundry-module/tablewrite-assistant/styles/module.css`

**Step 1: No unit test needed for CSS (manual verification)**

**Step 2: Add dropdown styles**

Add to the end of `foundry-module/tablewrite-assistant/styles/module.css`:

```css
/* ========================================
   @-Mention Autocomplete Styles
   ======================================== */

.mention-dropdown {
  background: #2a2a2a;
  border: 1px solid #555;
  border-radius: 6px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
  max-height: 300px;
  overflow-y: auto;
  z-index: 10000;
  min-width: 200px;
  max-width: 350px;
}

.mention-group {
  border-bottom: 1px solid #444;
}

.mention-group:last-child {
  border-bottom: none;
}

.mention-group-header {
  padding: 6px 10px;
  font-size: 11px;
  font-weight: 600;
  color: #888;
  background: #333;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.mention-item {
  padding: 8px 12px;
  font-size: 13px;
  color: #ddd;
  cursor: pointer;
  transition: background 0.1s ease;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.mention-item:hover {
  background: #3a3a3a;
}

.mention-item--selected {
  background: rgba(122, 170, 68, 0.3);
  color: #fff;
}

.mention-item--selected:hover {
  background: rgba(122, 170, 68, 0.4);
}

.mention-empty {
  padding: 12px;
  text-align: center;
  color: #888;
  font-size: 12px;
  font-style: italic;
}
```

**Step 3: Verify styles render correctly (manual test)**

Build and test in Foundry manually.

**Step 4: Commit**

```bash
git add foundry-module/tablewrite-assistant/styles/module.css
git commit -m "style(mention): add autocomplete dropdown CSS"
```

---

## Task 9: Integrate with TablewriteTab

**Files:**
- Modify: `foundry-module/tablewrite-assistant/src/ui/TablewriteTab.ts`
- Test: `foundry-module/tablewrite-assistant/tests/ui/TablewriteTab.test.ts`

**Step 1: Write the failing test for integration**

Add to `tests/ui/TablewriteTab.test.ts`:

```typescript
  describe('mention autocomplete integration', () => {
    beforeEach(() => {
      // @ts-ignore
      globalThis.game = {
        i18n: mockI18n,
        settings: mockSettings,
        actors: [
          { name: 'Goblin Scout', uuid: 'Actor.abc123' }
        ],
        journal: [],
        items: [],
        scenes: []
      };
    });

    it('opens autocomplete when @ is typed', async () => {
      const { TablewriteTab } = await import('../../src/ui/TablewriteTab');
      const tab = new TablewriteTab(container);
      tab.render();

      const input = container.querySelector('.tablewrite-input') as HTMLTextAreaElement;
      input.value = '@gob';
      input.selectionStart = 4;
      input.dispatchEvent(new Event('input', { bubbles: true }));

      await new Promise(resolve => setTimeout(resolve, 10));

      const dropdown = document.querySelector('.mention-dropdown');
      expect(dropdown).toBeTruthy();
    });

    it('intercepts keyboard events when autocomplete is open', async () => {
      const { TablewriteTab } = await import('../../src/ui/TablewriteTab');
      const tab = new TablewriteTab(container);
      tab.render();

      const input = container.querySelector('.tablewrite-input') as HTMLTextAreaElement;
      input.value = '@gob';
      input.selectionStart = 4;
      input.dispatchEvent(new Event('input', { bubbles: true }));

      await new Promise(resolve => setTimeout(resolve, 10));

      // Press Enter - should insert mention, not submit form
      const event = new KeyboardEvent('keydown', { key: 'Enter', cancelable: true });
      input.dispatchEvent(event);

      expect(mockSend).not.toHaveBeenCalled();
      expect(input.value).toContain('@[Goblin Scout]');
    });

    it('submits form on Enter when autocomplete is closed', async () => {
      mockSend.mockResolvedValueOnce({ message: 'Response', type: 'text' });
      const { TablewriteTab } = await import('../../src/ui/TablewriteTab');
      const tab = new TablewriteTab(container);
      tab.render();

      const input = container.querySelector('.tablewrite-input') as HTMLTextAreaElement;
      input.value = 'Hello world';

      const event = new KeyboardEvent('keydown', { key: 'Enter', cancelable: true });
      input.dispatchEvent(event);

      await new Promise(resolve => setTimeout(resolve, 10));

      expect(mockSend).toHaveBeenCalled();
    });
  });
```

**Step 2: Run test to verify it fails**

Run: `cd foundry-module/tablewrite-assistant && npm test -- tests/ui/TablewriteTab.test.ts`
Expected: FAIL (autocomplete not integrated)

**Step 3: Write minimal implementation**

Modify `foundry-module/tablewrite-assistant/src/ui/TablewriteTab.ts`:

Add import at top:
```typescript
import { MentionAutocomplete } from './MentionAutocomplete.js';
```

Add property:
```typescript
  private mentionAutocomplete: MentionAutocomplete | null = null;
```

Modify `activateListeners()`:
```typescript
  private activateListeners(): void {
    const form = this.container.querySelector('.tablewrite-input-form');
    const input = this.container.querySelector('.tablewrite-input') as HTMLTextAreaElement;

    // Initialize mention autocomplete
    if (input) {
      this.mentionAutocomplete = new MentionAutocomplete(input);
    }

    form?.addEventListener('submit', (e) => {
      e.preventDefault();
      this.sendMessage(input.value);
      input.value = '';
    });

    // Handle input for @ detection
    input?.addEventListener('input', () => {
      if (!this.mentionAutocomplete) return;

      const { active, query } = this.mentionAutocomplete.detectMention();

      if (active) {
        this.mentionAutocomplete.open(query);
      } else {
        this.mentionAutocomplete.close();
      }
    });

    // Enter to send, Shift+Enter for new line
    // But first check if autocomplete wants the key
    input?.addEventListener('keydown', (e) => {
      // Let autocomplete handle keys when open
      if (this.mentionAutocomplete?.isOpen) {
        if (this.mentionAutocomplete.handleKeyDown(e)) {
          e.preventDefault();
          return;
        }
      }

      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        form?.dispatchEvent(new Event('submit'));
      }
    });

    // Drag and drop support (unchanged)
    input?.addEventListener('dragover', (e) => {
      e.preventDefault();
      input.classList.add('dragover');
    });

    input?.addEventListener('dragleave', () => {
      input.classList.remove('dragover');
    });

    input?.addEventListener('drop', (e) => {
      e.preventDefault();
      input.classList.remove('dragover');
      const files = e.dataTransfer?.files;
      if (files && files.length > 0) {
        ui.notifications?.info(`File upload coming soon: ${files[0].name}`);
      }
    });
  }
```

**Step 4: Run test to verify it passes**

Run: `cd foundry-module/tablewrite-assistant && npm test -- tests/ui/TablewriteTab.test.ts`
Expected: PASS

**Step 5: Commit**

```bash
git add foundry-module/tablewrite-assistant/src/ui/TablewriteTab.ts foundry-module/tablewrite-assistant/tests/ui/TablewriteTab.test.ts
git commit -m "feat(mention): integrate autocomplete with TablewriteTab"
```

---

## Task 10: Add Mouse Click Selection

**Files:**
- Modify: `foundry-module/tablewrite-assistant/src/ui/MentionAutocomplete.ts`
- Test: `foundry-module/tablewrite-assistant/tests/ui/MentionAutocomplete.test.ts`

**Step 1: Write the failing test for click selection**

Add to `tests/ui/MentionAutocomplete.test.ts`:

```typescript
  describe('mouse interaction', () => {
    beforeEach(() => {
      // @ts-ignore
      globalThis.game = {
        actors: mockActors,
        journal: mockJournals,
        items: mockItems,
        scenes: mockScenes
      };
    });

    it('selects item on click', async () => {
      const { MentionAutocomplete } = await import('../../src/ui/MentionAutocomplete');
      const autocomplete = new MentionAutocomplete(textarea);

      textarea.value = '@gob';
      textarea.selectionStart = 4;

      autocomplete.open('gob');

      const secondItem = document.querySelectorAll('.mention-item')[1] as HTMLElement;
      secondItem.click();

      expect(textarea.value).toBe('@[Goblin Boss](Actor.def456) ');
      expect(autocomplete.isOpen).toBe(false);
    });

    it('highlights item on hover', async () => {
      const { MentionAutocomplete } = await import('../../src/ui/MentionAutocomplete');
      const autocomplete = new MentionAutocomplete(textarea);

      autocomplete.open('gob');

      const secondItem = document.querySelectorAll('.mention-item')[1] as HTMLElement;
      secondItem.dispatchEvent(new MouseEvent('mouseenter', { bubbles: true }));

      expect(secondItem.classList.contains('mention-item--selected')).toBe(true);
    });
  });
```

**Step 2: Run test to verify it fails**

Run: `cd foundry-module/tablewrite-assistant && npm test -- tests/ui/MentionAutocomplete.test.ts`
Expected: FAIL (click/hover not implemented)

**Step 3: Write minimal implementation**

Add event listeners in `renderDropdown()` after creating items:

```typescript
  private renderDropdown(): void {
    // ... existing code ...

    for (const [type, entities] of Object.entries(grouped)) {
      // ... existing code ...

      for (const entity of entities) {
        const item = document.createElement('div');
        // ... existing code ...

        // Add click handler
        item.addEventListener('click', () => {
          this.selectedIndex = itemIndex;
          this.insertSelected();
        });

        // Add hover handler
        item.addEventListener('mouseenter', () => {
          this.selectedIndex = parseInt(item.dataset.index || '0');
          this.updateSelectionHighlight();
        });

        group.appendChild(item);
        itemIndex++;
      }

      this.dropdown.appendChild(group);
    }

    // ... rest of existing code ...
  }
```

Note: The `itemIndex` reference in the click handler will need to be captured correctly. Update the loop:

```typescript
        // Capture index for closure
        const currentIndex = itemIndex;

        // Add click handler
        item.addEventListener('click', () => {
          this.selectedIndex = currentIndex;
          this.insertSelected();
        });
```

**Step 4: Run test to verify it passes**

Run: `cd foundry-module/tablewrite-assistant && npm test -- tests/ui/MentionAutocomplete.test.ts`
Expected: PASS

**Step 5: Commit**

```bash
git add foundry-module/tablewrite-assistant/src/ui/MentionAutocomplete.ts foundry-module/tablewrite-assistant/tests/ui/MentionAutocomplete.test.ts
git commit -m "feat(mention): add mouse click and hover selection"
```

---

## Task 11: E2E Test with Playwright

**Files:**
- Create: `tests/e2e/test_mention_autocomplete.py`

**Step 1: Write the E2E test**

Create `tests/e2e/test_mention_autocomplete.py`:

```python
"""E2E test for @-mention autocomplete in Tablewrite chat."""

import pytest
import sys
from pathlib import Path

# Add helper to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "foundry-module/tablewrite-assistant/scripts/feedback"))

pytest.importorskip("playwright", reason="playwright not installed")


@pytest.mark.playwright
@pytest.mark.integration
class TestMentionAutocomplete:
    """Test @-mention autocomplete functionality in Foundry."""

    def test_mention_dropdown_appears_on_at_symbol(self):
        """Typing @ should show autocomplete dropdown."""
        from foundry_helper import FoundrySession

        with FoundrySession(headless=True, user="Testing") as session:
            session.goto_tablewrite()

            # Type @ in the input
            input_selector = ".tablewrite-input"
            session.page.fill(input_selector, "@")

            # Wait for dropdown
            session.page.wait_for_selector(".mention-dropdown", timeout=3000)

            dropdown = session.page.query_selector(".mention-dropdown")
            assert dropdown is not None, "Dropdown should appear when @ is typed"

    def test_mention_filters_on_typing(self):
        """Typing after @ should filter results."""
        from foundry_helper import FoundrySession

        with FoundrySession(headless=True, user="Testing") as session:
            session.goto_tablewrite()

            # Type @gob in the input
            input_selector = ".tablewrite-input"
            session.page.fill(input_selector, "@gob")

            # Wait for filtered dropdown
            session.page.wait_for_selector(".mention-dropdown", timeout=3000)

            # Check that items are filtered (should only show goblins if they exist)
            items = session.page.query_selector_all(".mention-item")
            # At minimum, should have some items or "No matches" message
            dropdown = session.page.query_selector(".mention-dropdown")
            assert dropdown is not None

    def test_mention_keyboard_navigation(self):
        """Arrow keys should navigate dropdown."""
        from foundry_helper import FoundrySession

        with FoundrySession(headless=True, user="Testing") as session:
            session.goto_tablewrite()

            input_selector = ".tablewrite-input"
            session.page.fill(input_selector, "@")

            session.page.wait_for_selector(".mention-dropdown", timeout=3000)

            # Press down arrow
            session.page.keyboard.press("ArrowDown")

            # Check selection moved
            selected = session.page.query_selector(".mention-item--selected")
            assert selected is not None, "Should have a selected item after arrow down"

    def test_mention_escape_closes_dropdown(self):
        """Escape should close dropdown."""
        from foundry_helper import FoundrySession

        with FoundrySession(headless=True, user="Testing") as session:
            session.goto_tablewrite()

            input_selector = ".tablewrite-input"
            session.page.fill(input_selector, "@")

            session.page.wait_for_selector(".mention-dropdown", timeout=3000)

            # Press escape
            session.page.keyboard.press("Escape")

            # Dropdown should be gone
            dropdown = session.page.query_selector(".mention-dropdown")
            assert dropdown is None, "Dropdown should close on Escape"

    def test_mention_insert_on_enter(self):
        """Enter should insert selected mention."""
        from foundry_helper import FoundrySession

        with FoundrySession(headless=True, user="Testing") as session:
            session.goto_tablewrite()

            input_selector = ".tablewrite-input"
            session.page.fill(input_selector, "@")

            session.page.wait_for_selector(".mention-dropdown", timeout=3000)

            # Press enter to select first item
            session.page.keyboard.press("Enter")

            # Check input contains mention format
            input_value = session.page.input_value(input_selector)
            assert "@[" in input_value, f"Should insert mention format, got: {input_value}"
            assert "](" in input_value, f"Should have UUID format, got: {input_value}"
```

**Step 2: Run E2E test to verify it works**

Run: `pytest tests/e2e/test_mention_autocomplete.py -v --playwright`

Note: Requires Foundry to be running with test data.

**Step 3: Commit**

```bash
git add tests/e2e/test_mention_autocomplete.py
git commit -m "test(mention): add E2E tests for autocomplete"
```

---

## Task 12: Build and Manual Verification

**Files:** None (verification only)

**Step 1: Build the module**

```bash
cd foundry-module/tablewrite-assistant && npm run build
```

**Step 2: Restart Foundry and verify**

Manual verification checklist:
- [ ] Type `@` at start of message → dropdown appears
- [ ] Type `@` after space → dropdown appears
- [ ] Type query text → results filter
- [ ] Arrow Down/Up → selection moves
- [ ] Enter/Tab → inserts `@[Name](Type.uuid)` format
- [ ] Escape → closes dropdown, keeps text
- [ ] Click on item → inserts and closes
- [ ] Hover over item → highlights it
- [ ] No matches → shows "No matches" message
- [ ] Multiple mentions in one message work

**Step 3: Run full test suite**

```bash
cd foundry-module/tablewrite-assistant && npm test
pytest --full -x
```

**Step 4: Final commit**

```bash
git add -A
git commit -m "feat(mention): complete @-mention autocomplete implementation"
```

---

## Summary

| Task | Description | Estimated Lines |
|------|-------------|-----------------|
| 1 | Class shell | ~20 |
| 2 | Entity fetching | ~30 |
| 3 | Filter/score logic | ~50 |
| 4 | Dropdown rendering | ~80 |
| 5 | Keyboard navigation | ~40 |
| 6 | Mention insertion | ~30 |
| 7 | @ detection | ~25 |
| 8 | CSS styles | ~50 |
| 9 | TablewriteTab integration | ~30 |
| 10 | Mouse interaction | ~15 |
| 11 | E2E tests | ~80 |
| 12 | Build & verify | N/A |

**Total:** ~450 lines new code (TypeScript + CSS + tests)
