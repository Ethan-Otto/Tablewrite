import { test } from '@playwright/test';

test('check for errors', async ({ page }) => {
  const errors: string[] = [];
  
  page.on('console', msg => {
    if (msg.type() === 'error') {
      console.log('Browser error:', msg.text());
      errors.push(msg.text());
    }
  });

  page.on('pageerror', err => {
    console.log('Page error:', err.message);
    errors.push(err.message);
  });

  await page.goto('/');
  await page.waitForTimeout(3000);
  
  console.log('Total errors:', errors.length);
  if (errors.length > 0) {
    console.log('Errors:', errors);
  }
  
  const html = await page.content();
  console.log('Page has content:', html.length, 'bytes');
});
