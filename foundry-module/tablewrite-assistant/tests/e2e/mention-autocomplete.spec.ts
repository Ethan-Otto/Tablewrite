import { test, expect, Page } from '@playwright/test';

/**
 * E2E tests for @-mention autocomplete feature.
 *
 * Requirements:
 * - FoundryVTT running at http://localhost:30000
 * - A world loaded with the Tablewrite Assistant module active
 * - An available user to join as (Testing, Player, or any non-GM user)
 *
 * Tests skip gracefully if Foundry is not available.
 */

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
 * Helper to navigate to Foundry and join as an available user.
 * Tries Testing user first, then falls back to any available non-GM user.
 */
async function joinFoundry(page: Page): Promise<void> {
  await page.goto('http://localhost:30000', { timeout: 10000 });
  await page.waitForLoadState('networkidle');

  // Check if we need to join (join form visible)
  const userSelect = page.locator('select[name="userid"]');
  const isJoinVisible = await userSelect.isVisible({ timeout: 3000 }).catch(() => false);

  if (isJoinVisible) {
    // Get all available options
    const options = await userSelect.locator('option').all();
    let selectedValue: string | null = null;

    // Look for Testing user first
    for (const option of options) {
      const text = await option.textContent();
      const value = await option.getAttribute('value');
      if (text?.toLowerCase().includes('testing') && value) {
        selectedValue = value;
        break;
      }
    }

    // If no Testing user, select first non-empty, non-GM option
    if (!selectedValue) {
      for (const option of options) {
        const text = await option.textContent();
        const value = await option.getAttribute('value');
        if (value && text && !text.toLowerCase().includes('gamemaster') && text.trim() !== '') {
          selectedValue = value;
          break;
        }
      }
    }

    // If we found a user, select and join
    if (selectedValue) {
      await userSelect.selectOption({ value: selectedValue });
      await page.click('button[name="join"]');
      await page.waitForLoadState('networkidle');
    } else {
      throw new Error('No available user to join as');
    }
  }

  // Wait for sidebar to be ready
  await page.waitForSelector('#sidebar', { timeout: 15000 });
}

/**
 * Helper to navigate to Tablewrite tab.
 */
async function gotoTablewriteTab(page: Page): Promise<void> {
  // Click on the Tablewrite tab button (not the section)
  // Use role selector to get the tab button specifically
  const tablewriteTab = page.getByRole('tab', { name: 'Tablewrite' });
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
  // Skip all tests if Foundry is not available
  test.beforeAll(async () => {
    const available = await isFoundryAvailable();
    if (!available) {
      test.skip();
    }
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

    // Type @ to trigger dropdown
    await typeInInput(page, '@');

    // Wait for dropdown with items
    await expect(page.locator('.mention-dropdown')).toBeVisible({ timeout: 3000 });

    // Check if there are any items
    const itemCount = await page.locator('.mention-item').count();
    if (itemCount === 0) {
      // No entities in the world - skip the insertion test
      test.skip();
      return;
    }

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

    // Type @ to trigger dropdown
    await typeInInput(page, '@');

    // Wait for dropdown
    await expect(page.locator('.mention-dropdown')).toBeVisible({ timeout: 3000 });

    // Check we have at least 2 items
    const itemCount = await page.locator('.mention-item').count();
    if (itemCount < 2) {
      test.skip();
      return;
    }

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

    // Type @ to trigger dropdown
    await typeInInput(page, '@');

    // Wait for dropdown
    await expect(page.locator('.mention-dropdown')).toBeVisible({ timeout: 3000 });

    // Check we have at least 2 items
    const itemCount = await page.locator('.mention-item').count();
    if (itemCount < 2) {
      test.skip();
      return;
    }

    // Press ArrowUp (should wrap to last item)
    await input.press('ArrowUp');

    // Last item should be selected
    const lastItem = page.locator('.mention-item').last();
    await expect(lastItem).toHaveClass(/mention-item--selected/, { timeout: 2000 });
  });

  test('selects item on click', async ({ page }) => {
    const input = page.locator('.tablewrite-input');

    // Type @ to trigger dropdown
    await typeInInput(page, '@');

    // Wait for dropdown
    await expect(page.locator('.mention-dropdown')).toBeVisible({ timeout: 3000 });

    // Check if there are any items
    const itemCount = await page.locator('.mention-item').count();
    if (itemCount === 0) {
      test.skip();
      return;
    }

    // Click the first item
    await page.locator('.mention-item').first().click();

    // Verify mention was inserted
    const value = await input.inputValue();
    expect(value).toMatch(/@\[.+\]\(.+\)/);

    // Dropdown should be closed
    await expect(page.locator('.mention-dropdown')).not.toBeVisible({ timeout: 2000 });
  });

  test('updates selection on mouseenter', async ({ page }) => {
    // Type @ to trigger dropdown
    await typeInInput(page, '@');

    // Wait for dropdown
    await expect(page.locator('.mention-dropdown')).toBeVisible({ timeout: 3000 });

    // Check we have at least 2 items
    const itemCount = await page.locator('.mention-item').count();
    if (itemCount < 2) {
      test.skip();
      return;
    }

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

    // Type @ to trigger dropdown
    await typeInInput(page, '@');

    // Wait for dropdown with items
    await expect(page.locator('.mention-dropdown')).toBeVisible({ timeout: 3000 });

    // Check if there are any items
    const itemCount = await page.locator('.mention-item').count();
    if (itemCount === 0) {
      test.skip();
      return;
    }

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
