import { test, expect } from '@playwright/test';

test('debug image generation UI', async ({ page }) => {
  // Capture browser console
  page.on('console', msg => {
    console.log(`[BROWSER ${msg.type()}]:`, msg.text());
  });

  // Navigate to the app
  await page.goto('http://localhost:5174');

  // Wait for app to load
  await expect(page.getByRole('heading', { name: 'Module Assistant' })).toBeVisible();

  // Type image generation request
  const textarea = page.locator('textarea');
  await textarea.fill('generate an image of a dragon');
  await textarea.press('Enter');

  // Wait for user message to appear
  await expect(page.locator('text=generate an image of a dragon')).toBeVisible();
  console.log('✅ User message appeared');

  // Wait for any assistant response (60s timeout for image generation)
  await page.waitForTimeout(20000);

  // Take a screenshot
  await page.screenshot({ path: 'test-results/debug-ui.png', fullPage: true });
  console.log('📸 Screenshot saved to test-results/debug-ui.png');

  // Check what messages are in the chat
  const messages = await page.locator('[class*="flex gap"]').all();
  console.log(`Found ${messages.length} messages`);

  // Print all text content
  for (let i = 0; i < messages.length; i++) {
    const text = await messages[i].textContent();
    console.log(`Message ${i}: ${text}`);
  }

  // Check for ImageCarousel
  const carousel = page.locator('[class*="border"]').filter({ hasText: 'Image' });
  const carouselExists = await carousel.count();
  console.log(`ImageCarousel found: ${carouselExists > 0 ? 'YES' : 'NO'}`);

  // Check for images
  const images = page.locator('img[src*="/api/images/"]');
  const imageCount = await images.count();
  console.log(`Images with /api/images/ src: ${imageCount}`);


  // Wait a bit more
  await page.waitForTimeout(5000);

  // Final screenshot
  await page.screenshot({ path: 'test-results/debug-ui-final.png', fullPage: true });
});
