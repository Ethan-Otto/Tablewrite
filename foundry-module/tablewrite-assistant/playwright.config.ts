import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright configuration for Tablewrite Assistant E2E tests.
 *
 * These tests require FoundryVTT to be running at http://localhost:30000.
 * Tests will skip gracefully if Foundry is not available.
 */
export default defineConfig({
  testDir: './tests/e2e',
  /* Run tests in files in parallel */
  fullyParallel: false,
  /* Fail the build on CI if you accidentally left test.only in the source code. */
  forbidOnly: !!process.env.CI,
  /* Retry on CI only */
  retries: process.env.CI ? 2 : 0,
  /* Single worker since tests interact with the same Foundry instance */
  workers: 1,
  /* Reporter to use */
  reporter: [['list'], ['html', { open: 'never' }]],
  /* Shared settings for all the projects below */
  use: {
    /* Base URL to use in actions like `await page.goto('/')` */
    baseURL: 'http://localhost:30000',

    /* Collect trace when retrying the failed test */
    trace: 'on-first-retry',

    /* Take screenshot on failure */
    screenshot: 'only-on-failure',
  },

  /* Configure projects for major browsers */
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  /* Timeout settings */
  timeout: 30000,
  expect: {
    timeout: 5000,
  },
});
