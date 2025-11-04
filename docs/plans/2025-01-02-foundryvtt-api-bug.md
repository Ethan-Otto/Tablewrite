# FoundryVTT API Bug: Items Being Replaced During create_actor

## Summary

FoundryVTT's `create_actor` API has a bug where **spell items duplicate and replace weapon items** when both types are present in the same actor creation payload.

## Reproduction

### Test 1: Weapons Only (4 items)
**Result**: ✅ **ALL ITEMS SURVIVE**
- Uploaded: 4 weapons
- Downloaded: 4 weapons
- No losses, no duplicates

### Test 2: Weapons + Spells (9 items)
**Result**: ❌ **2 WEAPONS LOST, 2 SPELLS DUPLICATED**
- Uploaded: 4 weapons + 1 feat + 4 spells = 9 items
  - Weapons: Bite, Claw, Mace, Tail
  - Spells: Detect Magic, Fireball, Hold Monster, Wall of Fire
- Downloaded: 2 weapons + 1 feat + 6 spells = 9 items
  - Weapons: Bite, Tail (LOST: Claw, Mace)
  - Spells: Detect Magic, Fireball, Hold Monster, Wall of Fire, Hold Monster, Wall of Fire (DUPLICATED: Hold Monster, Wall of Fire)

### Test 3: Weapons + Spells WITHOUT UUIDs (9 items)
**Result**: ❌ **3 WEAPONS LOST, 3 SPELLS DUPLICATED** (EVEN WORSE!)
- Uploaded: 4 weapons + 1 feat + 4 spells = 9 items
- Downloaded: 1 weapon + 1 feat + 7 spells = 9 items
  - Weapons: Claw (LOST: Bite, Mace, Tail)
  - Spells: Detect Magic, Fireball, Hold Monster, Wall of Fire, Fireball, Hold Monster, Wall of Fire (DUPLICATED: Fireball, Hold Monster, Wall of Fire)

### Test 4: Full Pit Fiend (13 items)
**Result**: ❌ **1 WEAPON LOST, 1 SPELL DUPLICATED**
- Uploaded: 4 weapons + 5 feats + 4 spells = 13 items
- Downloaded: 3 weapons + 5 feats + 5 spells = 13 items
  - Lost: Claw
  - Duplicated: Wall of Fire

## Pattern Analysis

1. **Item count is preserved** - total count stays the same (9 → 9, 13 → 13)
2. **Weapons are replaced by duplicate spells** - for every N weapons lost, N spells are duplicated
3. **The bug is WORSE without spell UUIDs** - UUIDs may provide some protection
4. **The bug only happens with mixed item types** - weapons-only works fine
5. **Non-deterministic** - different items lost on different runs

## Root Cause

This is a **FoundryVTT server-side bug** or **REST API relay bug**, NOT an issue with our JSON structure.

Evidence:
- Our JSON is valid (verified by direct function testing)
- Weapons-only uploads work perfectly
- The damage.parts fix is working correctly
- Item losses only happen when spells are present

## Workarounds

### Option 1: Create Actor, Then Add Items Separately ✅ **RECOMMENDED**

Instead of sending all items in the create payload:
1. Create actor with empty items array
2. Add weapons using `/items/create` endpoint
3. Add feats using `/items/create` endpoint
4. Add spells using `/items/create` endpoint

This avoids the mixed-item-types bug entirely.

### Option 2: Report Bug to FoundryVTT Team

File bug report with:
- Minimal reproduction case (4 weapons + 4 spells)
- Evidence showing items array is valid but gets corrupted
- Link to test scripts

### Option 3: Wait for Foundry to Fix

Not viable - users need working actors now.

## Implementation Plan

1. ✅ **Root cause identified**: FoundryVTT API bug with mixed item types
2. ⏳ **Implement workaround**: Split item creation into separate API calls
3. ⏳ **Update tests**: Verify all items survive round-trip
4. ⏳ **Document limitation**: Note that this is a FoundryVTT bug, not ours

## Next Steps

Implement Option 1 workaround by:
1. Adding `create_item()` method to `ActorManager` class
2. Updating `convert_to_foundry()` to return items separately or
3. Updating `create_actor()` to accept items as separate parameter and create them individually
