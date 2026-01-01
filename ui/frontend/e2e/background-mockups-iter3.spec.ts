import { test } from '@playwright/test';

const backgrounds = [
  {
    name: '15_soft_charcoal',
    style: 'radial-gradient(ellipse at center, #454545 0%, #2a2a2a 100%)'
  },
  {
    name: '16_midnight_blue',
    style: 'linear-gradient(135deg, #1a1f2e 0%, #0d1117 50%, #1a1f2e 100%)'
  },
  {
    name: '17_warm_brown_texture',
    style: 'repeating-linear-gradient(45deg, #5c3d2e 0px, #5c3d2e 10px, #4a3020 10px, #4a3020 20px), linear-gradient(135deg, #5c3d2e 0%, #4a3020 100%)'
  },
  {
    name: '18_olive_drab',
    style: 'linear-gradient(135deg, #3d3d2b 0%, #2b2b1f 50%, #3d3d2b 100%)'
  },
  {
    name: '19_deep_mahogany',
    style: 'radial-gradient(ellipse at center, #5d2e1a 0%, #3d1e10 100%)'
  },
  {
    name: '20_dusty_rose_parchment',
    style: 'linear-gradient(135deg, #c4a898 0%, #b89d8d 50%, #c4a898 100%)'
  }
];

test.describe('Background Mockups Iteration 3', () => {
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
