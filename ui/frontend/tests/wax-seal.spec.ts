import { test, expect } from '@playwright/test';

test.describe('Wax Seal Button Visual Test', () => {
  test('should capture wax seal in normal and pressed states', async ({ page }) => {
    await page.goto('/');

    // Wait for the page to load
    await page.waitForLoadState('networkidle');

    // Type a message to enable the button
    const textarea = page.locator('textarea');
    await textarea.fill('Test message');

    // Get the wax seal button
    const sealButton = page.locator('button[aria-label="Send message"]');
    await expect(sealButton).toBeVisible();

    // Screenshot 1: Normal state
    await sealButton.screenshot({
      path: 'tests/screenshots/wax-seal-normal.png',
      animations: 'disabled'
    });

    // Screenshot 2: Pressed state (hold mouse down)
    await sealButton.hover();
    await page.mouse.down();
    await page.waitForTimeout(100); // Brief pause to ensure state change
    await sealButton.screenshot({
      path: 'tests/screenshots/wax-seal-pressed.png',
      animations: 'disabled'
    });
    await page.mouse.up();

    console.log('Screenshots saved to tests/screenshots/');
  });

  test('should verify full layout with helper text visible', async ({ page }) => {
    await page.goto('/');

    // Wait for the page to load
    await page.waitForLoadState('networkidle');

    // Type a message to enable the button
    const textarea = page.locator('textarea');
    await textarea.fill('Test message');

    // Take full page screenshot
    await page.screenshot({
      path: 'tests/screenshots/full-layout.png',
      fullPage: true
    });

    // Verify helper text is visible
    const helperText = page.locator('text=Press Enter to send • Shift+Enter for new line');
    await expect(helperText).toBeVisible();

    console.log('Full layout screenshot saved');
  });
});
