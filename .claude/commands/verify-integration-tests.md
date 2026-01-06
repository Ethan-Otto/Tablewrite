---
description: Verify integration tests exist and pass after feature implementation
---

# Integration Test Verification

Verify that integration tests were actually performed for the feature work in this conversation.

## Step 1: Environment Check

Before proceeding, verify the testing environment is operational:

1. **API Keys**: Check `.env` for required keys (`GeminiImageAPI`, `FOUNDRY_API_KEY`)
2. **Backend Server**: Verify backend is running on port 8000 - if not, start it
3. **Foundry Connection**: If Foundry tests needed, verify WebSocket connection - if not, run `python tests/foundry_init.py --force-refresh`

**Resolvable issues** (fix these automatically):
- Backend not running → Start it: `cd ui/backend && uvicorn app.main:app --reload --port 8000 &`
- Foundry not connected → Reconnect: `python tests/foundry_init.py --force-refresh`
- Test dependencies missing → Install them

**BLOCKING issues** (stop and alert user immediately):
```
🚫 TESTING BLOCKED: Missing GeminiImageAPI key in .env
   Cannot proceed - user must provide API key

🚫 TESTING BLOCKED: Missing FOUNDRY_API_KEY in .env
   Cannot proceed - user must provide API key

🚫 TESTING BLOCKED: FoundryVTT application not running and cannot be started
   Cannot proceed - user must start Foundry manually

🚫 TESTING BLOCKED: Required test data file not found and cannot be generated
   Cannot proceed - user must provide the file
```

If a blocking issue is encountered, STOP and wait for user to resolve it.

## Step 2: Identify What Needs Testing

Review the conversation to identify all features/changes that were implemented. For each:
- What functionality was added/modified?
- What external systems does it interact with? (Gemini API, FoundryVTT, database, filesystem)
- What would a round-trip test look like? (create → fetch → verify)

## Step 3: Check Existing Integration Tests

Search for integration tests covering these features:
- Look for `@pytest.mark.integration` decorators
- Check for real API calls (not mocked)
- Verify round-trip validation exists where applicable
- For Foundry resources: confirm `/tests` folder usage

## Step 4: Report Findings

**Format your report as follows:**

```
## Integration Test Coverage Report

### ✅ Tested
- [Feature]: [test file and what it validates]

### ❌ NOT TESTED - ACTION REQUIRED
- ❌ [Feature/Aspect]: [what test is missing]
- ❌ [Feature/Aspect]: [what test is missing]
- ❌ [Feature/Aspect]: [what test is missing]
```

## Step 5: Implement Missing Tests

**If there are ANY items in the "NOT TESTED" section, you MUST implement them now:**

1. Create integration test files following existing patterns in `tests/`
2. Tests MUST:
   - Use `@pytest.mark.integration` decorator
   - Use real data and real API calls (no mocks)
   - Include round-trip validation for resource creation (create → fetch → verify)
   - Store Foundry resources in `/tests` folder
   - For frontend: use Playwright with screenshot validation or backend state verification

3. Run each new test individually to verify it works: `pytest path/to/test.py -v`

4. Debug and fix any failures until all new tests pass

5. Update the report to show all items now have ✅

**Do not proceed to Step 6 until all items show ✅**

## Step 6: Run All Integration Tests

Execute: `pytest -m integration -x` (stops on first failure)

**If any test fails, you MUST fix it** - even if it appears to be a preexisting issue unrelated to the current feature work. Do not skip or ignore failing tests.

Only alert the user and stop if the fix is truly impossible (e.g., requires architectural decisions beyond scope, depends on external system changes, or needs credentials/access you don't have).

## Test Requirements

Per project CLAUDE.md:
- Every feature must have integration tests with real data
- Foundry resources must use `/tests` folder
- Round-trip tests required for resource creation (create → fetch → verify)
- Frontend changes need Playwright validation with screenshots or backend state verification
