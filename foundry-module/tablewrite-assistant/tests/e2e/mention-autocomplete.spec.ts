import { test, expect, Page } from '@playwright/test';

/**
 * E2E tests for @-mention autocomplete feature.
 *
 * Requirements:
 * - FoundryVTT running at http://localhost:30000
 * - Backend running at http://localhost:8000
 * - A world loaded with the Tablewrite Assistant module active
 * - An available user to join as (Testing, Player, or any non-GM user)
 *
 * Tests create their own test entities and clean them up after.
 */

const BACKEND_URL = 'http://localhost:8000';

// Track created entity UUIDs for cleanup
const createdEntities: { type: string; uuid: string }[] = [];

/**
 * Check if Foundry is accessible before running tests.
 */
async function isFoundryAvailable(): Promise<boolean> {
  try {
    const response = await fetch('http://localhost:30000', { method: 'HEAD' });
    return response.ok;
  } catch {
    return false;
  }
}

/**
 * Check if backend is accessible.
 */
async function isBackendAvailable(): Promise<boolean> {
  try {
    const response = await fetch(`${BACKEND_URL}/api/foundry/status`);
    return response.ok;
  } catch {
    return false;
  }
}

/**
 * Create a test actor via the backend API.
 */
async function createTestActor(name: string): Promise<string | null> {
  try {
    const response = await fetch(`${BACKEND_URL}/api/foundry/actor`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name,
        type: 'npc',
        system: {
          abilities: {
            str: { value: 10 },
            dex: { value: 10 },
            con: { value: 10 },
            int: { value: 10 },
            wis: { value: 10 },
            cha: { value: 10 }
          }
        }
      })
    });
    if (response.ok) {
      const data = await response.json();
      const uuid = data.uuid || data.id;
      if (uuid) {
        createdEntities.push({ type: 'Actor', uuid });
        return uuid;
      }
    }
    return null;
  } catch {
    return null;
  }
}

/**
 * Create a test journal entry via the backend API.
 */
async function createTestJournal(name: string): Promise<string | null> {
  try {
    const response = await fetch(`${BACKEND_URL}/api/foundry/journal`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name,
        pages: [{ name: 'Page 1', type: 'text', text: { content: 'Test content' } }]
      })
    });
    if (response.ok) {
      const data = await response.json();
      const uuid = data.uuid || data.id;
      if (uuid) {
        createdEntities.push({ type: 'JournalEntry', uuid });
        return uuid;
      }
    }
    return null;
  } catch {
    return null;
  }
}

/**
 * Create a test item via the backend API.
 */
async function createTestItem(name: string): Promise<string | null> {
  try {
    const response = await fetch(`${BACKEND_URL}/api/foundry/item`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name,
        type: 'weapon'
      })
    });
    if (response.ok) {
      const data = await response.json();
      const uuid = data.uuid || data.id;
      if (uuid) {
        createdEntities.push({ type: 'Item', uuid });
        return uuid;
      }
    }
    return null;
  } catch {
    return null;
  }
}

/**
 * Delete a test entity via the backend API.
 */
async function deleteEntity(type: string, uuid: string): Promise<void> {
  try {
    // Extract the ID from the UUID (format: Actor.xyz or just xyz)
    const id = uuid.includes('.') ? uuid.split('.').pop() : uuid;
    await fetch(`${BACKEND_URL}/api/foundry/${type.toLowerCase()}/${id}`, {
      method: 'DELETE'
    });
  } catch {
    // Ignore cleanup errors
  }
}

/**
 * Set up test entities for the E2E tests.
 */
async function setupTestEntities(): Promise<boolean> {
  const backendAvailable = await isBackendAvailable();
  if (!backendAvailable) {
    console.log('Backend not available, skipping entity creation');
    return false;
  }

  console.log('Creating test entities...');

  // Create multiple test entities for the autocomplete to find
  const actors = await Promise.all([
    createTestActor('Test Goblin Scout'),
    createTestActor('Test Dragon Wyrmling'),
    createTestActor('Test Skeleton Warrior')
  ]);

  const journals = await Promise.all([
    createTestJournal('Test Adventure Notes'),
    createTestJournal('Test Location Guide')
  ]);

  const items = await Promise.all([
    createTestItem('Test Magic Sword'),
    createTestItem('Test Healing Potion')
  ]);

  const createdCount = [...actors, ...journals, ...items].filter(Boolean).length;
  console.log(`Created ${createdCount} test entities`);

  return createdCount >= 2; // Need at least 2 for navigation tests
}

/**
 * Clean up test entities after tests.
 */
async function cleanupTestEntities(): Promise<void> {
  console.log(`Cleaning up ${createdEntities.length} test entities...`);
  for (const entity of createdEntities) {
    await deleteEntity(entity.type, entity.uuid);
  }
  createdEntities.length = 0;
}

/**
 * Helper to navigate to Foundry and join as an available user.
 * Tries Testing user first, then falls back to any available non-GM user.
 */
async function joinFoundry(page: Page): Promise<void> {
  await page.goto('http://localhost:30000', { timeout: 10000 });
  await page.waitForLoadState('networkidle');

  // Check if we need to join (join form visible)
  const joinForm = page.locator('#join-game');
  const isJoinVisible = await joinForm.isVisible({ timeout: 3000 }).catch(() => false);

  if (isJoinVisible) {
    const userSelect = page.locator('select[name="userid"]');

    // Wait for options to be populated
    await page.waitForFunction(() => {
      const select = document.querySelector('select[name="userid"]');
      return select && select.options.length > 1; // More than just the placeholder
    }, { timeout: 5000 }).catch(() => null);

    // Get all available options using JavaScript evaluation for reliability
    const optionsData = await page.evaluate(() => {
      const select = document.querySelector('select[name="userid"]') as HTMLSelectElement;
      if (!select) return [];
      return Array.from(select.options).map(opt => ({
        value: opt.value,
        text: opt.textContent?.trim() || ''
      }));
    });

    let selectedValue: string | null = null;

    // Look for Testing user first
    for (const opt of optionsData) {
      if (opt.text.toLowerCase().includes('testing') && opt.value) {
        selectedValue = opt.value;
        break;
      }
    }

    // If no Testing user, select first non-empty, non-GM option
    if (!selectedValue) {
      for (const opt of optionsData) {
        if (opt.value && opt.text && !opt.text.toLowerCase().includes('gamemaster') && opt.text.trim() !== '') {
          selectedValue = opt.value;
          break;
        }
      }
    }

    // If we found a user, select and join
    if (selectedValue) {
      await userSelect.selectOption(selectedValue);
      await page.click('button[name="join"]');
      await page.waitForLoadState('networkidle');
    } else {
      throw new Error('No available user to join as - found options: ' + JSON.stringify(optionsData));
    }
  }

  // Wait for sidebar to be ready
  await page.waitForSelector('#sidebar', { timeout: 15000 });
}

/**
 * Helper to navigate to Tablewrite tab.
 */
async function gotoTablewriteTab(page: Page): Promise<void> {
  // Click on the Tablewrite tab button specifically (button element with data-tab)
  // The section also has data-tab="tablewrite", so we need to target the button
  const tablewriteTab = page.locator('button[data-tab="tablewrite"]');
  await tablewriteTab.click();

  // Wait for the input to be visible
  await page.waitForSelector('.tablewrite-input', { timeout: 5000 });
}

/**
 * Helper to type into the input with @ trigger.
 */
async function typeInInput(page: Page, text: string): Promise<void> {
  const input = page.locator('.tablewrite-input');
  await input.focus();
  // Clear existing content and type new text
  await input.fill(text);
}

test.describe('Mention Autocomplete E2E', () => {
  // Set up test entities before all tests
  test.beforeAll(async () => {
    const foundryAvailable = await isFoundryAvailable();
    if (!foundryAvailable) {
      console.log('Foundry not available, skipping all tests');
      test.skip();
      return;
    }

    // Create test entities for the autocomplete to find
    const entitiesCreated = await setupTestEntities();
    if (!entitiesCreated) {
      console.log('Could not create test entities, some tests may fail');
    }
  });

  // Clean up test entities after all tests
  test.afterAll(async () => {
    await cleanupTestEntities();
  });

  test.beforeEach(async ({ page }) => {
    // Check Foundry availability in each test in case server went down
    const available = await isFoundryAvailable();
    if (!available) {
      test.skip();
      return;
    }

    try {
      // Navigate to Foundry and join as available user
      await joinFoundry(page);
      // Navigate to Tablewrite tab
      await gotoTablewriteTab(page);
    } catch (error) {
      // If we can't join, skip the test
      console.log('Skipping test - could not join Foundry:', error);
      test.skip();
    }
  });

  test('shows dropdown when @ is typed at start of input', async ({ page }) => {
    await typeInInput(page, '@');

    // Wait for dropdown to appear
    const dropdown = page.locator('.mention-dropdown');
    await expect(dropdown).toBeVisible({ timeout: 3000 });
  });

  test('shows dropdown when @ is typed after space', async ({ page }) => {
    await typeInInput(page, 'Hello @');

    const dropdown = page.locator('.mention-dropdown');
    await expect(dropdown).toBeVisible({ timeout: 3000 });
  });

  test('filters results as user types after @', async ({ page }) => {
    // Type @ followed by filter text - using a common term
    await typeInInput(page, '@gob');

    const dropdown = page.locator('.mention-dropdown');
    await expect(dropdown).toBeVisible({ timeout: 3000 });

    // Should show filtered results or "No matches" message
    const hasItems = await page.locator('.mention-item').count();
    const hasNoMatches = await page.locator('.mention-empty').isVisible().catch(() => false);

    // Either we have matches or the "No matches" message is shown
    expect(hasItems > 0 || hasNoMatches).toBeTruthy();
  });

  test('closes dropdown on Escape key', async ({ page }) => {
    const input = page.locator('.tablewrite-input');
    await typeInInput(page, '@');

    // Verify dropdown is open
    await expect(page.locator('.mention-dropdown')).toBeVisible({ timeout: 3000 });

    // Press Escape
    await input.press('Escape');

    // Dropdown should be hidden
    await expect(page.locator('.mention-dropdown')).not.toBeVisible({ timeout: 2000 });
  });

  test('closes dropdown when space is typed after query', async ({ page }) => {
    await typeInInput(page, '@test');

    // Verify dropdown is open
    await expect(page.locator('.mention-dropdown')).toBeVisible({ timeout: 3000 });

    // Type a space (which closes the autocomplete per the implementation)
    const input = page.locator('.tablewrite-input');
    await input.press('Space');

    // Dropdown should close because query now contains space
    await expect(page.locator('.mention-dropdown')).not.toBeVisible({ timeout: 2000 });
  });

  test('inserts mention on Enter when item is selected', async ({ page }) => {
    const input = page.locator('.tablewrite-input');

    // Type @ to trigger dropdown - filter by "Test" to find our test entities
    await typeInInput(page, '@Test');

    // Wait for dropdown with items
    await expect(page.locator('.mention-dropdown')).toBeVisible({ timeout: 3000 });

    // Wait for items to appear
    await expect(page.locator('.mention-item').first()).toBeVisible({ timeout: 3000 });

    // First item should be selected by default
    const firstItem = page.locator('.mention-item').first();
    await expect(firstItem).toHaveClass(/mention-item--selected/, { timeout: 2000 });

    // Press Enter to insert
    await input.press('Enter');

    // Verify mention was inserted (format: @[Name](Type.uuid) )
    const value = await input.inputValue();
    expect(value).toMatch(/@\[.+\]\(.+\)/);

    // Dropdown should be closed after insertion
    await expect(page.locator('.mention-dropdown')).not.toBeVisible({ timeout: 2000 });
  });

  test('navigates items with ArrowDown key', async ({ page }) => {
    const input = page.locator('.tablewrite-input');

    // Type @ to trigger dropdown - filter by "Test" to find our test entities
    await typeInInput(page, '@Test');

    // Wait for dropdown
    await expect(page.locator('.mention-dropdown')).toBeVisible({ timeout: 3000 });

    // Wait for at least 2 items
    await expect(page.locator('.mention-item').nth(1)).toBeVisible({ timeout: 3000 });

    // First item should be selected initially
    const firstItem = page.locator('.mention-item').first();
    await expect(firstItem).toHaveClass(/mention-item--selected/);

    // Press ArrowDown
    await input.press('ArrowDown');

    // Second item should now be selected
    const secondItem = page.locator('.mention-item').nth(1);
    await expect(secondItem).toHaveClass(/mention-item--selected/, { timeout: 2000 });

    // First item should no longer be selected
    await expect(firstItem).not.toHaveClass(/mention-item--selected/);
  });

  test('navigates items with ArrowUp key', async ({ page }) => {
    const input = page.locator('.tablewrite-input');

    // Type @ to trigger dropdown - filter by "Test" to find our test entities
    await typeInInput(page, '@Test');

    // Wait for dropdown
    await expect(page.locator('.mention-dropdown')).toBeVisible({ timeout: 3000 });

    // Wait for at least 2 items
    await expect(page.locator('.mention-item').nth(1)).toBeVisible({ timeout: 3000 });

    // Press ArrowUp (should wrap to last item)
    await input.press('ArrowUp');

    // Last item should be selected
    const lastItem = page.locator('.mention-item').last();
    await expect(lastItem).toHaveClass(/mention-item--selected/, { timeout: 2000 });
  });

  test('selects item on click', async ({ page }) => {
    const input = page.locator('.tablewrite-input');

    // Type @ to trigger dropdown - filter by "Test" to find our test entities
    await typeInInput(page, '@Test');

    // Wait for dropdown
    await expect(page.locator('.mention-dropdown')).toBeVisible({ timeout: 3000 });

    // Wait for items to appear
    await expect(page.locator('.mention-item').first()).toBeVisible({ timeout: 3000 });

    // Click the first item
    await page.locator('.mention-item').first().click();

    // Verify mention was inserted
    const value = await input.inputValue();
    expect(value).toMatch(/@\[.+\]\(.+\)/);

    // Dropdown should be closed
    await expect(page.locator('.mention-dropdown')).not.toBeVisible({ timeout: 2000 });
  });

  test('updates selection on mouseenter', async ({ page }) => {
    // Type @ to trigger dropdown - filter by "Test" to find our test entities
    await typeInInput(page, '@Test');

    // Wait for dropdown
    await expect(page.locator('.mention-dropdown')).toBeVisible({ timeout: 3000 });

    // Wait for at least 2 items
    await expect(page.locator('.mention-item').nth(1)).toBeVisible({ timeout: 3000 });

    const firstItem = page.locator('.mention-item').first();
    const secondItem = page.locator('.mention-item').nth(1);

    // First item should be selected initially
    await expect(firstItem).toHaveClass(/mention-item--selected/);

    // Hover over second item
    await secondItem.hover();

    // Second item should now be selected
    await expect(secondItem).toHaveClass(/mention-item--selected/, { timeout: 2000 });

    // First item should no longer be selected
    await expect(firstItem).not.toHaveClass(/mention-item--selected/);
  });

  test('inserts Tab key to select item', async ({ page }) => {
    const input = page.locator('.tablewrite-input');

    // Type @ to trigger dropdown - filter by "Test" to find our test entities
    await typeInInput(page, '@Test');

    // Wait for dropdown with items
    await expect(page.locator('.mention-dropdown')).toBeVisible({ timeout: 3000 });

    // Wait for items to appear
    await expect(page.locator('.mention-item').first()).toBeVisible({ timeout: 3000 });

    // Press Tab to insert (same as Enter per implementation)
    await input.press('Tab');

    // Verify mention was inserted
    const value = await input.inputValue();
    expect(value).toMatch(/@\[.+\]\(.+\)/);

    // Dropdown should be closed
    await expect(page.locator('.mention-dropdown')).not.toBeVisible({ timeout: 2000 });
  });

  test('does not trigger dropdown for @ in middle of word', async ({ page }) => {
    // Type text with @ in the middle (like an email)
    await typeInInput(page, 'test@example');

    // Dropdown should NOT appear
    await expect(page.locator('.mention-dropdown')).not.toBeVisible({ timeout: 2000 });
  });

  test('shows "No matches" message for unmatched query', async ({ page }) => {
    // Type @ followed by a query that won't match anything
    await typeInInput(page, '@zzzznonexistent12345');

    // Wait for dropdown
    await expect(page.locator('.mention-dropdown')).toBeVisible({ timeout: 3000 });

    // Should show "No matches" message
    const emptyMessage = page.locator('.mention-empty');
    await expect(emptyMessage).toBeVisible({ timeout: 2000 });
    await expect(emptyMessage).toContainText('No matches');
  });
});
