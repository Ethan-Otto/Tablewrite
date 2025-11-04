# Debug Plan: Missing Items After FoundryVTT Upload

## Problem Statement
When uploading Pit Fiend actor with 4 weapons, items are randomly lost:
- Sometimes Bite is missing
- Sometimes Mace is missing
- Sometimes Bite + Tail are missing
- **Non-deterministic** - different items lost each run

## Hypotheses to Test

### Hypothesis 1: JSON Structure Issue
**Theory**: Our generated JSON has invalid fields that cause FoundryVTT to reject specific items

**Tests:**
1. [ ] Dump the exact JSON being sent to FoundryVTT (before upload)
2. [ ] Compare our weapon JSON against official Pit Fiend weapon JSON field-by-field
3. [ ] Try uploading the EXACT official Pit Fiend JSON via our API
4. [ ] Check if official JSON survives round-trip

### Hypothesis 2: Activity ID Collisions
**Theory**: Using `_generate_activity_id()` for activities might generate duplicate IDs

**Tests:**
1. [ ] Log all activity IDs being generated for all items
2. [ ] Check for duplicate activity IDs across items
3. [ ] Use deterministic IDs (e.g., `f"{attack.name}_{activity_type}"`) instead of random

### Hypothesis 3: API Request Size Limit
**Theory**: The API or FoundryVTT has a size limit that causes items to be truncated

**Tests:**
1. [ ] Upload actors with increasing weapon counts: 1, 2, 3, 4, 5
2. [ ] Measure JSON size for each
3. [ ] Check if there's a pattern in which items survive (first N items?)

### Hypothesis 4: Array Indexing Issue
**Theory**: Items need explicit array indices or sort orders

**Tests:**
1. [ ] Add `"sort": index * 100` to each item
2. [ ] Check if item order in array matters
3. [ ] Try reversing item order

### Hypothesis 5: Missing Required Fields
**Theory**: Items are missing required fields that cause silent failures

**Tests:**
1. [ ] Compare our minimal weapon against official weapon for ALL fields
2. [ ] Add every field from official JSON even if empty
3. [ ] Check FoundryVTT console logs for errors

### Hypothesis 6: Race Condition in create_actor
**Theory**: The create returns before all items are fully saved

**Tests:**
1. [ ] Add delay between upload and download
2. [ ] Check if immediate download vs delayed download shows different results
3. [ ] Test with single-threaded vs concurrent uploads

### Hypothesis 7: Name/Type Collision
**Theory**: FoundryVTT deduplicates by name+type combo

**Tests:**
1. [ ] Upload actor with weapons named: "Bite1", "Bite2", "Bite3", "Bite4"
2. [ ] Check if all survive
3. [ ] Try different types (weapon vs feat) with same name

## Debugging Steps

### Step 1: Capture Exact JSON
```python
# In create_actor, before sending:
with open('/tmp/uploaded.json', 'w') as f:
    json.dump(actor_data, f, indent=2)
```

### Step 2: Minimal Reproduction
Create minimal test cases:
- Actor with 2 simple weapons (no activities)
- Actor with 2 weapons with 1 activity each
- Actor with 2 weapons with 3 activities each

### Step 3: Compare Against Official
Load official Pit Fiend JSON and:
- Upload it via our API
- Check if it survives round-trip
- Compare field by field

### Step 4: Instrument the API
Add logging to `manager.py` to capture:
- Exact HTTP request payload
- Exact HTTP response
- Status codes
- Response timing

### Step 5: Check FoundryVTT Logs
- Open FoundryVTT console
- Check for JavaScript errors during actor creation
- Look for warnings about invalid data

## Implementation Order

1. **Start with Step 1**: Dump JSON before upload to see exactly what we're sending
2. **Then Step 3**: Test if official JSON survives round-trip via our API
3. **Then Step 2**: Minimal reproduction to isolate the issue
4. **Then systematic hypothesis testing** based on findings

## Expected Outcomes

If it's our JSON structure:
- Official JSON will survive round-trip
- We'll see specific fields missing/incorrect

If it's API/FoundryVTT bug:
- Official JSON will ALSO lose items
- Pattern will emerge (first N items, or specific positions)

If it's race condition:
- Delayed download will show different results
- Immediate download might be incomplete

## Success Criteria

- [ ] Identify root cause with evidence
- [ ] Create minimal reproduction case
- [ ] Implement fix
- [ ] All weapons survive round-trip 100% of the time
- [ ] All integration tests pass consistently
