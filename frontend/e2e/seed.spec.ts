import { test, expect } from '@playwright/test';

test('diagnostic landing page loads', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('h1')).toBeVisible();
  await expect(page.locator('text=Operations diagnostic')).toBeVisible();
});
