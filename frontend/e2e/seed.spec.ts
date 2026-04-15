import { test, expect } from '@playwright/test';

test('diagnostic landing page loads', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('h1')).toBeVisible();
  await expect(page.getByRole('link', { name: 'Start your diagnostic' }).first()).toBeVisible();
});

test('diagnostic entry page loads', async ({ page }) => {
  await page.goto('/diagnostic');
  await expect(page.locator('h1')).toBeVisible();
  await expect(page.locator('text=Operations diagnostic')).toBeVisible();
});
