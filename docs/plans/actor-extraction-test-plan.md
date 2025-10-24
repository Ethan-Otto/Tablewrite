# Actor Extraction End-to-End Integration Test Plan

**Date:** 2025-10-24
**Feature:** Actor/NPC Extraction and FoundryVTT Creation
**Status:** Ready for Manual Testing

## Overview

This document outlines the manual integration tests required to verify the complete actor extraction workflow. These tests should be run with real PDFs and API calls to validate the full pipeline.

## Prerequisites

Before running these tests:
- [ ] Gemini API configured (`GeminiImageAPI` in `.env`)
- [ ] FoundryVTT REST API configured (relay server, API key, client ID)
- [ ] FoundryVTT instance running (local or The Forge)
- [ ] Test PDF available: `data/pdfs/Lost_Mine_of_Phandelver_test.pdf`
- [ ] All unit tests passing: `uv run pytest -m "not integration and not slow"`

## Test 1: Full Pipeline with Actor Processing

**Objective:** Verify complete workflow from PDF to FoundryVTT with actors

**Command:**
```bash
uv run python scripts/full_pipeline.py \
    --journal-name "Actor Test Module" \
    --pdf-path "data/pdfs/Lost_Mine_of_Phandelver_test.pdf"
```

**Expected Results:**
- [ ] Pipeline completes without errors
- [ ] XML files contain `<stat_block>` tags
- [ ] Stat blocks are extracted and parsed
- [ ] NPCs are identified from XML
- [ ] Creature actors created in FoundryVTT
- [ ] NPC actors created with biographies
- [ ] Journal uploaded to FoundryVTT successfully

**Verification Steps:**
1. Check console output for actor processing statistics:
   - `stat_blocks_found: X`
   - `stat_blocks_created: Y`
   - `npcs_found: Z`
   - `npcs_created: W`

2. Open FoundryVTT and verify:
   - Navigate to Actors tab
   - Locate newly created creature actors (e.g., "Goblin", "Bugbear")
   - Open creature actor sheets and verify:
     - AC, HP, CR values are correct
     - Abilities are populated (if available)
     - Biography contains raw stat block text

3. Verify NPC actors:
   - Locate NPC actors (e.g., "Klarg", "Sildar Hallwinter")
   - Open NPC actor sheets and verify:
     - Biography contains description and plot relevance
     - Biography contains @UUID link to creature stat block
     - Clicking @UUID link navigates to correct creature actor
     - No stats directly on NPC (stats are in linked creature)

**Success Criteria:**
- All steps complete without errors
- At least 1 creature actor created
- At least 1 NPC actor created
- @UUID links function correctly

---

## Test 2: Compendium Reuse

**Objective:** Verify actors are reused from compendium instead of creating duplicates

**Setup:**
Ensure FoundryVTT has standard compendiums loaded (dnd5e.monsters, etc.)

**Command:**
```bash
uv run python scripts/full_pipeline.py \
    --journal-name "Actor Test Module 2" \
    --pdf-path "data/pdfs/Lost_Mine_of_Phandelver_test.pdf"
```

**Expected Results:**
- [ ] Pipeline completes without errors
- [ ] Console shows "Found existing actor in compendium" messages
- [ ] `stat_blocks_reused > 0` in final statistics
- [ ] No duplicate actors created

**Verification Steps:**
1. Check console output for reuse messages:
   ```
   Found existing actor in compendium: Goblin
   ```

2. Check final statistics:
   - `stat_blocks_reused: X` (should be > 0)
   - Total actors in FoundryVTT should not double

3. Verify NPCs link to existing compendium actors:
   - Open NPC biography
   - @UUID should point to compendium entry, not newly created actor

**Success Criteria:**
- At least 1 actor reused from compendium
- No duplicate actors in actor list
- NPCs correctly link to compendium entries

---

## Test 3: Actors-Only Mode

**Objective:** Verify standalone actor processing without full pipeline

**Setup:**
Run full pipeline once to create a run directory, then run actors-only mode

**Commands:**
```bash
# First, create a run directory (if not already done in Test 1)
uv run python scripts/full_pipeline.py --skip-upload --skip-export --journal-name "Test"

# Then run actors-only mode
uv run python scripts/full_pipeline.py --actors-only
```

**Expected Results:**
- [ ] Script finds latest run directory automatically
- [ ] Actor processing runs successfully
- [ ] Actors created in FoundryVTT
- [ ] No XML generation or journal upload occurs

**Verification Steps:**
1. Check console output:
   - Should show "Running in actors-only mode"
   - Should show "Using latest run: <timestamp>"
   - Should NOT show PDF split or XML generation steps

2. Verify actors created:
   - Open FoundryVTT Actors tab
   - New actors should appear

**Success Criteria:**
- Actors-only mode completes successfully
- Only actor processing runs (no PDF/XML steps)
- Actors created in FoundryVTT

---

## Test 4: Actors-Only Mode with Specific Run Directory

**Objective:** Verify actors-only mode with --run-dir flag

**Command:**
```bash
uv run python scripts/full_pipeline.py \
    --actors-only \
    --run-dir output/runs/<specific-timestamp>
```

**Expected Results:**
- [ ] Script uses specified run directory
- [ ] Actor processing runs successfully

**Verification Steps:**
1. Check console output shows correct run directory
2. Verify actors created

**Success Criteria:**
- Script uses specified directory
- Actors created successfully

---

## Test 5: Skip Actors Mode

**Objective:** Verify --skip-actors flag works correctly

**Command:**
```bash
uv run python scripts/full_pipeline.py \
    --skip-actors \
    --journal-name "No Actors Test"
```

**Expected Results:**
- [ ] Pipeline runs without actor processing
- [ ] No actor-related console output
- [ ] Journal uploaded normally
- [ ] No actors created

**Verification Steps:**
1. Check console output:
   - Should show "Skipping actor processing (--skip-actors)"
   - Should NOT show any actor statistics

2. Verify no new actors:
   - Count actors in FoundryVTT before and after
   - No new actors should appear

**Success Criteria:**
- Pipeline completes without actor processing
- No actors created
- Journal upload still works

---

## Test 6: Error Handling - No Stat Blocks in PDF

**Objective:** Verify graceful handling when no stat blocks found

**Setup:**
Create or use a test PDF with no stat blocks (plain text chapter)

**Expected Results:**
- [ ] Pipeline completes without crashing
- [ ] Console shows "No stat blocks found"
- [ ] `stat_blocks_found: 0` in statistics
- [ ] No creatures created
- [ ] NPCs may still be created (if narrative found)

**Success Criteria:**
- Pipeline doesn't crash
- Appropriate zero-stat messages logged

---

## Test 7: Stat Block Parsing Accuracy

**Objective:** Verify Gemini correctly parses stat blocks

**Verification Steps:**
1. After Test 1 completes, examine created creature actors
2. For each creature, verify:
   - [ ] Name matches stat block
   - [ ] AC value is correct
   - [ ] HP value is correct
   - [ ] CR value is correct (as decimal: 1/4 = 0.25, 1/2 = 0.5)
   - [ ] Abilities (STR, DEX, etc.) are correct if present
   - [ ] Raw stat block text is preserved in biography

**Reference:**
Compare against source PDF stat blocks

**Success Criteria:**
- All stat values match source PDF
- Raw text preserved accurately

---

## Test 8: NPC Identification Accuracy

**Objective:** Verify Gemini correctly identifies named NPCs

**Verification Steps:**
1. After Test 1 completes, examine created NPC actors
2. For each NPC, verify:
   - [ ] Name is correctly extracted
   - [ ] Description is relevant and accurate
   - [ ] Plot relevance makes sense
   - [ ] creature_stat_block_name matches actual creature
   - [ ] Location is accurate (if available)

**Manual Check:**
Read source PDF and identify NPCs manually, compare with created actors

**Success Criteria:**
- Major NPCs are identified (Klarg, Sildar, etc.)
- NPC metadata is accurate
- Creature links are correct

---

## Test 9: XML Stat Block Tagging

**Objective:** Verify Gemini tags stat blocks in XML during generation

**Command:**
```bash
uv run python scripts/full_pipeline.py --skip-upload --skip-export --skip-actors
```

**Verification Steps:**
1. After pipeline completes, examine XML files in `output/runs/<timestamp>/documents/`
2. Search for `<stat_block` tags
3. Verify:
   - [ ] Stat blocks are wrapped in `<stat_block name="...">` tags
   - [ ] Name attribute matches creature name
   - [ ] Complete stat block text is inside tags
   - [ ] No parsing or restructuring of stat block content

**Example Expected XML:**
```xml
<stat_block name="Goblin">
GOBLIN
Small humanoid (goblinoid), neutral evil

Armor Class 15 (leather armor, shield)
Hit Points 7 (2d6)
...
</stat_block>
```

**Success Criteria:**
- Stat blocks are tagged correctly
- Complete text preserved
- Name attribute matches creature

---

## Test 10: Performance and Reliability

**Objective:** Verify pipeline is performant and doesn't timeout

**Command:**
```bash
time uv run python scripts/full_pipeline.py --journal-name "Performance Test"
```

**Expected Results:**
- [ ] Pipeline completes in reasonable time (< 10 minutes for test PDF)
- [ ] No timeouts or API rate limit errors
- [ ] All API calls succeed

**Verification Steps:**
1. Monitor console for timing
2. Check for any timeout or rate limit messages
3. Verify all steps complete

**Success Criteria:**
- Completes in < 10 minutes
- No timeouts
- No rate limit errors

---

## Bug Tracking

If issues are found during testing, document them here:

### Issue 1: [Title]
- **Test:** Test #X
- **Description:** What went wrong
- **Expected:** What should happen
- **Actual:** What actually happened
- **Reproduction Steps:** How to reproduce
- **Status:** [Open/Fixed]

---

## Test Results Summary

**Date Tested:** _____________
**Tester:** _____________
**FoundryVTT Version:** _____________
**Test PDF:** _____________

| Test # | Test Name | Status | Notes |
|--------|-----------|--------|-------|
| 1 | Full Pipeline | ⬜ PASS / ⬜ FAIL | |
| 2 | Compendium Reuse | ⬜ PASS / ⬜ FAIL | |
| 3 | Actors-Only Mode | ⬜ PASS / ⬜ FAIL | |
| 4 | Actors-Only with --run-dir | ⬜ PASS / ⬜ FAIL | |
| 5 | Skip Actors Mode | ⬜ PASS / ⬜ FAIL | |
| 6 | No Stat Blocks | ⬜ PASS / ⬜ FAIL | |
| 7 | Stat Block Accuracy | ⬜ PASS / ⬜ FAIL | |
| 8 | NPC Identification | ⬜ PASS / ⬜ FAIL | |
| 9 | XML Tagging | ⬜ PASS / ⬜ FAIL | |
| 10 | Performance | ⬜ PASS / ⬜ FAIL | |

**Overall Status:** ⬜ PASS / ⬜ FAIL

**Notes:**
_____________________________________________________________________________
_____________________________________________________________________________
_____________________________________________________________________________

---

## Sign-Off

**Feature Ready for Merge:** ⬜ YES / ⬜ NO

**Approver:** _____________
**Date:** _____________
