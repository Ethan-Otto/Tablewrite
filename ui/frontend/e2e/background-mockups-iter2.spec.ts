import { test } from '@playwright/test';

const backgrounds = [
  {
    name: '08_lighter_wood',
    style: 'linear-gradient(135deg, #6d4d3e 0%, #5c3d2e 50%, #6d4d3e 100%)'
  },
  {
    name: '09_forest_green',
    style: 'linear-gradient(135deg, #2d3a2e 0%, #1f2b20 50%, #2d3a2e 100%)'
  },
  {
    name: '10_slate_stone',
    style: 'linear-gradient(135deg, #4a4a52 0%, #35353d 50%, #4a4a52 100%)'
  },
  {
    name: '11_warm_terracotta',
    style: 'linear-gradient(135deg, #8b5a3c 0%, #7d4a2e 50%, #8b5a3c 100%)'
  },
  {
    name: '12_deep_navy',
    style: 'linear-gradient(135deg, #1a2332 0%, #0f1824 50%, #1a2332 100%)'
  },
  {
    name: '13_subtle_wood_grain',
    style: 'repeating-linear-gradient(90deg, #4a3020 0px, #4a3020 2px, #5c3d2e 2px, #5c3d2e 4px), linear-gradient(135deg, #5c3d2e 0%, #4a3020 100%)'
  },
  {
    name: '14_aged_parchment_dark',
    style: 'linear-gradient(135deg, #b89d7d 0%, #9d8565 50%, #b89d7d 100%)'
  }
];

test.describe('Background Mockups Iteration 2', () => {
  for (const bg of backgrounds) {
    test(`Generate mockup: ${bg.name}`, async ({ page }) => {
      await page.goto('/');
      await page.waitForTimeout(2000);

      await page.evaluate((bgStyle) => {
        const container = document.querySelector('.min-h-screen');
        if (container) {
          (container as HTMLElement).style.background = bgStyle;
        }
      }, bg.style);

      await page.waitForTimeout(500);

      await page.screenshot({
        path: `background-mockups/${bg.name}.png`,
        fullPage: true
      });
    });
  }
});
