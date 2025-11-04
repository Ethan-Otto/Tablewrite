import { test, expect } from '@playwright/test';

/**
 * Real end-to-end test for image generation.
 *
 * This test DOES NOT mock the backend - it tests the actual integration
 * with the real Gemini API.
 *
 * Prerequisites:
 * - Backend running on http://localhost:8001
 * - Frontend running on http://localhost:5174
 * - Valid GEMINI_API_KEY in backend .env
 */

test.describe('Image Generation - Real Integration', () => {
  test('should generate and display real images from Gemini', async ({ page }) => {
    // Navigate to the app
    await page.goto('http://localhost:5174');

    // Wait for app to load
    await expect(page.getByRole('heading', { name: 'Module Assistant' })).toBeVisible();

    // Type image generation request
    const textarea = page.locator('textarea');
    await textarea.fill('generate an image of a dragon');

    // Send message
    await textarea.press('Enter');

    // Wait for the user message to appear
    await expect(page.locator('text=generate an image of a dragon')).toBeVisible();

    // Wait for the assistant response (with longer timeout for API call)
    // Should see "Generated 2 images" message
    await expect(page.locator('text=Generated 2 images')).toBeVisible({ timeout: 60000 });

    // Wait for ImageCarousel to appear
    const carousel = page.locator('[class*="border"]').filter({ hasText: 'Image 1 / 2' });
    await expect(carousel).toBeVisible({ timeout: 10000 });

    // Check that images are actually loaded
    const images = page.locator('img[src*="/api/images/"]');
    await expect(images.first()).toBeVisible({ timeout: 5000 });

    // Verify the image has actual content (not broken)
    const imgSrc = await images.first().getAttribute('src');
    expect(imgSrc).toMatch(/\/api\/images\/\d+_[a-f0-9]+\.png/);

    // Check that navigation controls are present (2 images = should have arrows)
    const prevButton = page.locator('button:has-text("◀")');
    const nextButton = page.locator('button:has-text("▶")');
    await expect(prevButton).toBeVisible();
    await expect(nextButton).toBeVisible();

    // Check image counter
    await expect(page.locator('text=Image 1 / 2')).toBeVisible();

    // Test navigation - click next
    await nextButton.click();
    await expect(page.locator('text=Image 2 / 2')).toBeVisible();

    // Verify second image is different
    const secondImgSrc = await images.first().getAttribute('src');
    expect(secondImgSrc).not.toBe(imgSrc);

    // Navigate back
    await prevButton.click();
    await expect(page.locator('text=Image 1 / 2')).toBeVisible();

    console.log('✅ Image generation test passed! Images were generated and displayed successfully.');
  });

  test('should handle custom image count', async ({ page }) => {
    await page.goto('http://localhost:5174');
    await expect(page.getByRole('heading', { name: 'Module Assistant' })).toBeVisible();

    const textarea = page.locator('textarea');
    await textarea.fill('generate 3 images of a castle');
    await textarea.press('Enter');

    // Wait for response
    await expect(page.locator('text=Generated 3 images')).toBeVisible({ timeout: 90000 });

    // Check for 3-image counter
    await expect(page.locator('text=Image 1 / 3')).toBeVisible({ timeout: 10000 });

    console.log('✅ Custom count test passed!');
  });
});
