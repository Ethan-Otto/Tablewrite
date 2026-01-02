import { test } from '@playwright/test';

test('take screenshot of UI', async ({ page }) => {
  await page.goto('/');
  await page.waitForTimeout(2000); // Wait for everything to load
  await page.screenshot({ path: 'ui-screenshot.png', fullPage: true });
});
