import { test } from '@playwright/test';

const backgrounds = [
  {
    name: '01_current_parchment',
    style: 'linear-gradient(135deg, #d4c4a8 0%, #c4b098 50%, #d4c4a8 100%)'
  },
  {
    name: '02_dark_leather',
    style: 'linear-gradient(135deg, #3d2817 0%, #2d1f15 50%, #3d2817 100%)'
  },
  {
    name: '03_burgundy_wax',
    style: 'linear-gradient(135deg, #5a1212 0%, #721818 50%, #5a1212 100%)'
  },
  {
    name: '04_aged_wood',
    style: 'linear-gradient(135deg, #4a3020 0%, #5c3d2e 50%, #4a3020 100%)'
  },
  {
    name: '05_textured_parchment',
    style: 'repeating-linear-gradient(45deg, transparent, transparent 35px, rgba(125, 90, 61, 0.03) 35px, rgba(125, 90, 61, 0.03) 70px), linear-gradient(135deg, #d4c4a8 0%, #c4b098 50%, #d4c4a8 100%)'
  },
  {
    name: '06_medieval_tapestry',
    style: 'radial-gradient(circle at 20% 50%, transparent 10px, rgba(125, 90, 61, 0.05) 11px, transparent 12px), radial-gradient(circle at 80% 50%, transparent 10px, rgba(125, 90, 61, 0.05) 11px, transparent 12px), linear-gradient(135deg, #8d6a4d 0%, #7d5a3d 100%)'
  },
  {
    name: '07_rich_velvet',
    style: 'radial-gradient(ellipse at center, #6d4d3e 0%, #4a3020 100%)'
  }
];

test.describe('Background Mockups', () => {
  for (const bg of backgrounds) {
    test(`Generate mockup: ${bg.name}`, async ({ page }) => {
      await page.goto('/');
      await page.waitForTimeout(2000);

      // Inject the background style
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
