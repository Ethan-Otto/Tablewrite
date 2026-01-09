# FoundryVTT v13 Compatibility

## Overview

Update the Tablewrite Assistant module to be compatible with FoundryVTT v13 and dnd5e 5.0+.

## Current State

- `module.json`: minimum v11, verified v12
- `main.ts`: Uses jQuery for sidebar tab injection via `renderSidebar` hook
- `src/handlers/actor.ts`: Creates activity structures for weapons/feats
- Already has partial v13 support (lines 36-43 in main.ts handle AppV2 partial re-renders)

## Changes Required

### 1. module.json

Update compatibility field:

```json
"compatibility": {
  "minimum": "12",
  "verified": "13"
}
```

**Rationale:** dnd5e 5.0+ requires v13, so minimum v12 is reasonable. Users on v11 can stay on older module version.

### 2. main.ts - Convert jQuery to Native DOM

**File:** `foundry-module/tablewrite-assistant/src/main.ts`

**Current (lines 35-66):**
```typescript
Hooks.on('renderSidebar', (app: Application, html: JQuery, context?: unknown, options?: { parts?: string[] }) => {
  if (options?.parts && !options.parts.includes('sidebar')) return;

  const tabsContainer = html.find('#sidebar-tabs');
  // ... uses jQuery methods: .find(), .length, .after(), .append(), .on()
});
```

**Change to:**
```typescript
Hooks.on('renderSidebar', (app: Application, html: HTMLElement, context?: unknown, options?: { parts?: string[] }) => {
  if (options?.parts && !options.parts.includes('sidebar')) return;

  const tabsContainer = html.querySelector('#sidebar-tabs');
  // ... use native DOM: querySelector, querySelectorAll, append, insertAdjacentHTML, addEventListener
});
```

**Why:** jQuery is deprecated starting v13. While it still works, AppV2 applications pass `HTMLElement` not `JQuery` to render hooks.

### 3. Verify Activity Structures with dnd5e 5.0+

**File:** `foundry-module/tablewrite-assistant/src/handlers/actor.ts`

The `handleAddCustomItems` function creates activity objects for weapons and feats (lines 346-549). dnd5e 5.0 refactored the activities system and removed compatibility shims.

**Verification needed:**
- Create a weapon with attack activity
- Create a feat with save activity (like breath weapon)
- Create a feat with utility activity (passive)
- Confirm all render correctly in actor sheet

**Potential issues:**
- Activity field names may have changed
- Activity type values may be different
- Damage structure may need updates

This requires testing with actual v13 + dnd5e 5.0+ instance.

## Testing Plan

1. **Build module:** `cd foundry-module/tablewrite-assistant && npm run build`
2. **Install in v13:** Copy to Foundry v13 Data/modules/
3. **Enable module:** Verify no console errors on load
4. **Test sidebar tab:** Click Tablewrite tab, verify renders correctly
5. **Test actor creation:** Create an actor via chat, verify appears in world
6. **Test weapon/feat creation:** Create actor with attacks, verify activities work
7. **Test scene creation:** Create scene with walls, verify walls display

## Out of Scope

- Migrating TablewriteTab.ts (already uses native DOM)
- Updating to full ApplicationV2 patterns (not needed for sidebar injection)
- Supporting v11 (dropping to minimum v12)

## References

- [FoundryVTT v13 Release Notes](https://foundryvtt.com/releases/13.341)
- [V13 Sidebar API](https://foundryvtt.com/api/v13/classes/foundry.applications.sidebar.Sidebar.html)
- [dnd5e 5.0 Release](https://github.com/foundryvtt/dnd5e/releases/tag/release-5.0.0)
- [renderApplicationV2 Hook](https://foundryvtt.com/api/functions/hookEvents.renderApplicationV2.html)
