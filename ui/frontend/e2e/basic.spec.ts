import { test, expect } from '@playwright/test';

test.describe('D&D Module Assistant UI', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should load the application', async ({ page }) => {
    await expect(page).toHaveTitle(/D&D Module Assistant/);
  });

  test('should display the header with correct title', async ({ page }) => {
    const header = page.locator('h1', { hasText: 'Module Assistant' });
    await expect(header).toBeVisible();
    
    // Check for fleur-de-lis flourishes
    const flourishes = page.locator('text=⚜');
    await expect(flourishes.first()).toBeVisible();
  });

  test('should display welcome message', async ({ page }) => {
    const welcomeMessage = page.getByText('Welcome to the D&D Module Assistant');
    await expect(welcomeMessage).toBeVisible();
  });

  test('should display input area with placeholder', async ({ page }) => {
    const textarea = page.locator('textarea');
    await expect(textarea).toBeVisible();
    await expect(textarea).toHaveAttribute('placeholder', /Type a message or use \/help/);
  });

  test('should display wax seal send button', async ({ page }) => {
    // Look for the button with fleur-de-lis symbol
    const sendButton = page.locator('button[aria-label="Send message"]');
    await expect(sendButton).toBeVisible();
    
    // Check for the fleur-de-lis symbol in the button
    const fleurDeLis = sendButton.locator('text=⚜');
    await expect(fleurDeLis).toBeVisible();
  });

  test('should send a message and receive response', async ({ page }) => {
    // Type a message
    const textarea = page.locator('textarea');
    await textarea.fill('Hello, can you help me?');
    
    // Click send button
    const sendButton = page.locator('button[aria-label="Send message"]');
    await sendButton.click();
    
    // Wait for user message to appear
    await expect(page.getByText('Hello, can you help me?')).toBeVisible();
    
    // Wait for assistant response (with timeout for API call)
    await expect(page.locator('text=Assistant').first()).toBeVisible({ timeout: 10000 });
    
    // Verify input was cleared
    await expect(textarea).toHaveValue('');
  });

  test('should send /help command', async ({ page }) => {
    const textarea = page.locator('textarea');
    await textarea.fill('/help');
    
    const sendButton = page.locator('button[aria-label="Send message"]');
    await sendButton.click();
    
    // Wait for help response
    await expect(page.getByText(/Available Commands/)).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/\/generate-scene/)).toBeVisible();
  });

  test('should disable send button when input is empty', async ({ page }) => {
    const sendButton = page.locator('button[aria-label="Send message"]');
    await expect(sendButton).toBeDisabled();
    
    // Type something
    const textarea = page.locator('textarea');
    await textarea.fill('test');
    
    // Button should be enabled
    await expect(sendButton).toBeEnabled();
    
    // Clear input
    await textarea.clear();
    
    // Button should be disabled again
    await expect(sendButton).toBeDisabled();
  });

  test('should auto-scroll to latest message', async ({ page }) => {
    // Send multiple messages to test scrolling
    const textarea = page.locator('textarea');
    const sendButton = page.locator('button[aria-label="Send message"]');
    
    for (let i = 1; i <= 3; i++) {
      await textarea.fill(`Test message ${i}`);
      await sendButton.click();
      // Wait a bit between messages
      await page.waitForTimeout(1000);
    }
    
    // The last message should be visible (meaning auto-scroll worked)
    await expect(page.getByText('Test message 3')).toBeVisible();
  });
});
