import { test, expect, type Route } from '@playwright/test';

/**
 * E2E tests for the D&D Module Assistant chat UI tool system.
 *
 * Tests cover:
 * - Basic text chat
 * - Image generation tool (ImageCarousel)
 * - Error handling
 * - UI element rendering
 *
 * All backend responses are mocked using Playwright's route interception.
 */

test.describe('Chat UI Tool System', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');

    // Wait for the app to load (check for header specifically)
    await expect(page.getByRole('heading', { name: 'Module Assistant' })).toBeVisible();
  });

  test('should display header and input area on load', async ({ page }) => {
    // Check header
    await expect(page.getByRole('heading', { name: 'Module Assistant' })).toBeVisible();

    // Check input area
    const textarea = page.locator('textarea[placeholder*="generate-scene"]');
    await expect(textarea).toBeVisible();

    // Check send button (wax seal)
    const sendButton = page.getByRole('button', { name: 'Send message' });
    await expect(sendButton).toBeVisible();

    // Check helper text
    await expect(page.locator('text=Press Enter to send')).toBeVisible();
  });

  test('should send a basic text message and receive response', async ({ page }) => {
    // Mock the chat API response
    await page.route('**/api/chat', async (route: Route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          message: 'Hello! I am the Module Assistant. How can I help you with your D&D module today?',
          type: 'text',
          data: null,
          scene: null
        })
      });
    });

    // Type a message
    const textarea = page.locator('textarea[placeholder*="generate-scene"]');
    await textarea.fill('Hello');

    // Click send button
    const sendButton = page.locator('button[aria-label="Send message"]');
    await sendButton.click();

    // Wait for user message to appear
    await expect(page.locator('text=YOU').first()).toBeVisible();
    await expect(page.locator('text=Hello').first()).toBeVisible();

    // Wait for assistant response
    await expect(page.locator('text=ASSISTANT').first()).toBeVisible();
    await expect(page.locator('text=I am the Module Assistant')).toBeVisible();

    // Input should be cleared
    await expect(textarea).toHaveValue('');
  });

  test('should handle Enter key to send message', async ({ page }) => {
    // Mock the chat API response
    await page.route('**/api/chat', async (route: Route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          message: 'Response to keyboard input',
          type: 'text',
          data: null,
          scene: null
        })
      });
    });

    // Type a message and press Enter
    const textarea = page.locator('textarea[placeholder*="generate-scene"]');
    await textarea.fill('Test keyboard input');
    await textarea.press('Enter');

    // Wait for response
    await expect(page.locator('text=Response to keyboard input')).toBeVisible();
  });

  test('should handle error type responses', async ({ page }) => {
    // Mock an error response
    await page.route('**/api/chat', async (route: Route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          message: 'An error occurred while processing your request.',
          type: 'error',
          data: null,
          scene: null
        })
      });
    });

    // Send a message
    const textarea = page.locator('textarea[placeholder*="generate-scene"]');
    await textarea.fill('This will cause an error');
    await textarea.press('Enter');

    // Wait for error message in assistant response
    await expect(page.locator('text=An error occurred')).toBeVisible();
  });

  test('should handle API failure gracefully', async ({ page }) => {
    // Mock a failed API call
    await page.route('**/api/chat', async (route: Route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: 'Internal server error'
        })
      });
    });

    // Send a message
    const textarea = page.locator('textarea[placeholder*="generate-scene"]');
    await textarea.fill('This will fail');
    await textarea.press('Enter');

    // User message should still appear
    await expect(page.locator('text=This will fail')).toBeVisible();

    // System error message should appear (from useChat error handling)
    await expect(page.locator('text=Error').first()).toBeVisible({ timeout: 10000 });
  });

  test('should maintain conversation history', async ({ page }) => {
    let requestCount = 0;

    // Mock multiple chat responses
    await page.route('**/api/chat', async (route: Route) => {
      requestCount++;
      const request = route.request();
      const postData = request.postDataJSON();

      // Verify conversation history is sent
      if (requestCount === 2) {
        expect(postData.conversation_history).toBeDefined();
        expect(postData.conversation_history.length).toBeGreaterThan(0);
      }

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          message: `Response ${requestCount}`,
          type: 'text',
          data: null,
          scene: null
        })
      });
    });

    const textarea = page.locator('textarea[placeholder*="generate-scene"]');

    // Send first message
    await textarea.fill('First message');
    await textarea.press('Enter');
    await expect(page.locator('text=Response 1')).toBeVisible();

    // Send second message
    await textarea.fill('Second message');
    await textarea.press('Enter');
    await expect(page.locator('text=Response 2')).toBeVisible();

    // Both messages should be visible
    await expect(page.locator('text=First message')).toBeVisible();
    await expect(page.locator('text=Second message')).toBeVisible();
  });

  test('should render markdown in assistant responses', async ({ page }) => {
    // Mock response with markdown
    await page.route('**/api/chat', async (route: Route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          message: '**Bold text** and *italic text* with `code snippet`',
          type: 'text',
          data: null,
          scene: null
        })
      });
    });

    // Send a message
    const textarea = page.locator('textarea[placeholder*="generate-scene"]');
    await textarea.fill('Test markdown');
    await textarea.press('Enter');

    // Wait for response - check for markdown content instead
    await expect(page.locator('strong:has-text("Bold text")')).toBeVisible();
    await expect(page.locator('em:has-text("italic text")')).toBeVisible();
    await expect(page.locator('code:has-text("code snippet")')).toBeVisible();
  });

  test('should handle Shift+Enter for new line without sending', async ({ page }) => {
    const textarea = page.locator('textarea[placeholder*="generate-scene"]');

    // Type text and press Shift+Enter
    await textarea.fill('Line 1');
    await textarea.press('Shift+Enter');
    await textarea.type('Line 2');

    // Message should not be sent (no assistant response)
    await page.waitForTimeout(500);
    // Only the welcome system message should be visible, no user message
    const userMessages = page.locator('text=YOU');
    await expect(userMessages).not.toBeVisible();

    // Textarea should contain both lines
    const value = await textarea.inputValue();
    expect(value).toContain('Line 1');
    expect(value).toContain('Line 2');
  });

  test('should display correct avatar icons', async ({ page }) => {
    // Mock response
    await page.route('**/api/chat', async (route: Route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          message: 'Test avatars',
          type: 'text',
          data: null,
          scene: null
        })
      });
    });

    // Send a message
    const textarea = page.locator('textarea[placeholder*="generate-scene"]');
    await textarea.fill('Test');
    await textarea.press('Enter');

    // Wait for both messages
    await expect(page.locator('text=YOU')).toBeVisible();
    await expect(page.locator('text=Test avatars')).toBeVisible();

    // Check for avatars (wizard emoji for user, quill for assistant)
    // Note: These are decorative elements, so we just check they exist in the DOM
    const wizardEmoji = page.locator('span:has-text("🧙")').first();
    const quillEmoji = page.locator('span:has-text("✒")').first();

    await expect(wizardEmoji).toBeVisible();
    await expect(quillEmoji).toBeVisible();
  });

  test('should display welcome message on load', async ({ page }) => {
    // Check for welcome message (system message)
    await expect(page.locator('text=Welcome to the D&D Module Assistant')).toBeVisible();
  });
});
