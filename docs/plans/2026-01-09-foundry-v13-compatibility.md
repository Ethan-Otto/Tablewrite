# FoundryVTT v13 Compatibility Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Update the Tablewrite Assistant module to be compatible with FoundryVTT v13 and dnd5e 5.0+.

**Architecture:** Convert jQuery DOM manipulation to native DOM APIs in `main.ts`, update module compatibility metadata, and verify activity schemas work with dnd5e 5.0+. The module already uses native DOM in most places (TablewriteTab.ts, etc.) - only the sidebar injection in main.ts needs conversion.

**Tech Stack:** TypeScript, FoundryVTT v13 API, dnd5e 5.0+, Vitest

---

## Background

- **FoundryVTT v13** deprecated jQuery - AppV2 applications pass `HTMLElement` not `JQuery` to render hooks
- **dnd5e 5.0+** removed compatibility shims for pre-activity systems (PR #5399)
- Current module: minimum v11, verified v12 - needs update to minimum v12, verified v13
- `main.ts` lines 35-66 use jQuery (`html.find()`, `.after()`, `.append()`, `.on()`)
- `TablewriteTab.ts` already uses native DOM - no changes needed

## References

- [FoundryVTT v13 Release Notes](https://foundryvtt.com/releases/13.341)
- [dnd5e 5.0 Release](https://github.com/foundryvtt/dnd5e/releases/tag/release-5.0.0)
- [V13 Sidebar API](https://foundryvtt.com/api/v13/classes/foundry.applications.sidebar.Sidebar.html)

---

### Task 1: Update module.json Compatibility

**Files:**
- Modify: `foundry-module/tablewrite-assistant/module.json:6-9`

**Step 1: Update the compatibility field**

```json
"compatibility": {
  "minimum": "12",
  "verified": "13"
}
```

**Step 2: Verify JSON is valid**

Run: `cd foundry-module/tablewrite-assistant && cat module.json | python3 -m json.tool > /dev/null && echo "Valid JSON"`
Expected: "Valid JSON"

**Step 3: Commit**

```bash
git add foundry-module/tablewrite-assistant/module.json
git commit -m "chore: update module compatibility to v12-v13"
```

---

### Task 2: Write Test for Native DOM Sidebar Injection

**Files:**
- Modify: `foundry-module/tablewrite-assistant/tests/main.test.ts`

**Step 1: Add test for renderSidebar hook with HTMLElement**

Add this test case to the existing `describe('main.ts')` block:

```typescript
it('renderSidebar hook adds tab with native DOM (v13 compatible)', async () => {
  // Create mock HTMLElement sidebar
  const mockSidebar = document.createElement('div');
  mockSidebar.innerHTML = `
    <nav id="sidebar-tabs">
      <a class="item" data-tab="chat"><i class="fas fa-comments"></i></a>
    </nav>
  `;

  // Mock game.i18n
  // @ts-ignore
  globalThis.game.i18n = {
    localize: vi.fn().mockReturnValue('Tablewrite Assistant')
  };

  await import('../src/main');

  // Trigger renderSidebar hook with HTMLElement (not JQuery)
  const renderCallback = hookCallbacks['renderSidebar']?.[0];
  expect(renderCallback).toBeDefined();

  // Call with HTMLElement as v13 does
  renderCallback?.({}, mockSidebar, {}, {});

  // Verify tab was added
  const tabButton = mockSidebar.querySelector('[data-tab="tablewrite"]');
  expect(tabButton).not.toBeNull();
  expect(tabButton?.tagName).toBe('A');
  expect(tabButton?.classList.contains('item')).toBe(true);

  // Verify tab content container was added
  const tabContent = mockSidebar.querySelector('#tablewrite');
  expect(tabContent).not.toBeNull();
  expect(tabContent?.classList.contains('tab')).toBe(true);
});
```

**Step 2: Run test to verify it fails**

Run: `cd foundry-module/tablewrite-assistant && npm test -- --run tests/main.test.ts`
Expected: FAIL - jQuery methods won't work on HTMLElement

**Step 3: Commit failing test**

```bash
git add foundry-module/tablewrite-assistant/tests/main.test.ts
git commit -m "test: add native DOM test for renderSidebar (failing)"
```

---

### Task 3: Convert jQuery to Native DOM in main.ts

**Files:**
- Modify: `foundry-module/tablewrite-assistant/src/main.ts:35-66`

**Step 1: Replace jQuery with native DOM**

Replace the entire `renderSidebar` hook (lines 35-66) with:

```typescript
/**
 * Register sidebar tab for chat UI.
 * v13 compatible: uses native DOM instead of jQuery.
 */
Hooks.on('renderSidebar', (app: Application, html: HTMLElement, context?: unknown, options?: { parts?: string[] }) => {
  // v13: Skip partial re-renders
  if (options?.parts && !options.parts.includes('sidebar')) return;

  const tabsContainer = html.querySelector('#sidebar-tabs');
  if (!tabsContainer) return;

  // Prevent duplicates (important for v13 re-renders)
  if (tabsContainer.querySelector('[data-tab="tablewrite"]')) return;

  // Add tab button right after the chat tab
  const chatTab = tabsContainer.querySelector('[data-tab="chat"]');
  if (!chatTab) return;

  const tabButton = document.createElement('a');
  tabButton.className = 'item';
  tabButton.dataset.tab = 'tablewrite';
  tabButton.dataset.tooltip = game.i18n.localize('TABLEWRITE_ASSISTANT.TabTooltip');
  tabButton.innerHTML = '<i class="fas fa-feather-alt"></i>';
  chatTab.after(tabButton);

  // Add tab content container
  // Must include 'tab' class for Foundry's tab switching to work
  const tabContent = document.createElement('section');
  tabContent.id = 'tablewrite';
  tabContent.className = 'tab sidebar-tab flexcol';
  tabContent.dataset.tab = 'tablewrite';
  html.appendChild(tabContent);

  // Initialize tab when clicked (lazy initialization)
  tabButton.addEventListener('click', () => {
    const container = document.getElementById('tablewrite');
    if (container && !container.dataset.initialized) {
      container.dataset.initialized = 'true';
      new TablewriteTab(container).render();
    }
  });
});
```

**Step 2: Run test to verify it passes**

Run: `cd foundry-module/tablewrite-assistant && npm test -- --run tests/main.test.ts`
Expected: PASS

**Step 3: Run full test suite**

Run: `cd foundry-module/tablewrite-assistant && npm test`
Expected: All tests PASS

**Step 4: Commit**

```bash
git add foundry-module/tablewrite-assistant/src/main.ts
git commit -m "refactor: convert jQuery to native DOM for v13 compatibility"
```

---

### Task 4: Build and Verify Module Loads

**Files:**
- None (build verification)

**Step 1: Build the module**

Run: `cd foundry-module/tablewrite-assistant && npm run build`
Expected: Build completes without errors

**Step 2: Verify dist/main.js exists and has no jQuery references**

Run: `grep -c "\\$(" foundry-module/tablewrite-assistant/dist/main.js || echo "No jQuery found (good)"`
Expected: "No jQuery found (good)" or count of 0

**Step 3: Commit (if any build changes)**

Build artifacts are gitignored, so no commit needed.

---

### Task 5: Manual Verification in FoundryVTT v13

**Files:**
- None (manual testing)

This task requires a running FoundryVTT v13 instance with dnd5e 5.0+.

**Step 1: Install module in v13**

Copy `foundry-module/tablewrite-assistant/` to Foundry v13's `Data/modules/` directory.

**Step 2: Enable module and check console**

1. Launch Foundry v13
2. Enable "Tablewrite" module in game settings
3. Open browser console (F12)
4. Verify no errors on load
5. Verify `[Tablewrite Assistant] Initializing...` appears

**Step 3: Test sidebar tab**

1. Click the feather icon in the sidebar tabs
2. Verify the Tablewrite tab renders correctly
3. Verify chat input is functional

**Step 4: Test actor creation with activities**

Use the chat to create an actor:
```
Create a goblin with a scimitar attack
```

1. Verify actor appears in world
2. Open actor sheet
3. Verify scimitar item exists
4. Verify attack activity is configured correctly
5. Roll the attack to verify it works

**Step 5: Test feat with save activity**

Use the chat to create:
```
Create a young red dragon with fire breath (60-foot cone, DC 17 Dex, 16d6 fire, half on save)
```

1. Verify breath weapon feat exists
2. Verify save activity is configured with:
   - DC 17 Dexterity save
   - 60-foot cone template
   - 16d6 fire damage
   - Half damage on successful save
3. Use the ability to verify template and damage roll

---

### Task 6: Activity Schema Verification (if issues found)

**Files:**
- Potentially modify: `foundry-module/tablewrite-assistant/src/handlers/actor.ts`

**Note:** Only perform this task if Task 5 reveals issues with activities.

**Step 1: Compare activity structure with dnd5e 5.0 examples**

If activities don't work in v13/dnd5e 5.0:
1. Create a weapon manually in Foundry v13
2. Export it to JSON
3. Compare structure with what `handleAddCustomItems` generates
4. Identify field differences

**Step 2: Update activity structure if needed**

Common potential changes (based on dnd5e 5.0 release notes):
- Activity type values may have changed
- Field names may be renamed
- New required fields may exist

Document specific changes here after investigation.

**Step 3: Write integration test with real Foundry**

```typescript
// Add to tests/handlers/actor.test.ts
it('creates weapon with attack activity compatible with dnd5e 5.0', async () => {
  // This test would require Foundry connection
  // Mark as @integration
});
```

**Step 4: Commit fixes**

```bash
git add foundry-module/tablewrite-assistant/src/handlers/actor.ts
git add foundry-module/tablewrite-assistant/tests/handlers/actor.test.ts
git commit -m "fix: update activity schema for dnd5e 5.0 compatibility"
```

---

### Task 7: Final Verification and PR

**Files:**
- None (verification)

**Step 1: Run full Python test suite**

Run: `cd /Users/ethanotto/Documents/Projects/dnd_module_gen && uv run pytest --full -x`
Expected: All tests PASS

**Step 2: Run TypeScript tests**

Run: `cd foundry-module/tablewrite-assistant && npm test`
Expected: All tests PASS

**Step 3: Create PR**

```bash
git push -u origin v13
gh pr create --title "feat: FoundryVTT v13 and dnd5e 5.0+ compatibility" --body "$(cat <<'EOF'
## Summary
- Update module compatibility to minimum v12, verified v13
- Convert jQuery DOM manipulation to native DOM in main.ts
- Verify activity schemas work with dnd5e 5.0+

## Changes
- `module.json`: Updated compatibility field
- `src/main.ts`: Replaced jQuery with native DOM APIs
- `tests/main.test.ts`: Added native DOM test coverage

## Test Plan
- [x] TypeScript unit tests pass
- [x] Python integration tests pass
- [x] Manual verification in Foundry v13
- [x] Actor creation with activities works
- [x] Sidebar tab renders correctly

## Breaking Changes
- Drops support for FoundryVTT v11 (minimum now v12)

Generated with Claude Code
EOF
)"
```

---

## Out of Scope

- Migrating `TablewriteTab.ts` (already uses native DOM)
- Full ApplicationV2 conversion (not needed for sidebar injection)
- v11 support (dropping to minimum v12)
