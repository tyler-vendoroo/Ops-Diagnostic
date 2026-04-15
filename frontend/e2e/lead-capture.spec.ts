import { test, expect } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.goto('/diagnostic');
  await page.evaluate(() => localStorage.clear());
  await page.reload();
});

test.describe('Lead capture form', () => {
  test('renders all fields', async ({ page }) => {
    await expect(page.locator('input[name="name"]')).toBeVisible();
    await expect(page.locator('input[name="email"]')).toBeVisible();
    await expect(page.locator('input[name="company"]')).toBeVisible();
    await expect(page.locator('input[name="phone"]')).toBeVisible();
  });

  test('does not submit with empty required fields', async ({ page }) => {
    // HTML required attributes block submission; verify form stays visible
    await page.click('button[type="submit"]');
    await expect(page.locator('input[name="name"]')).toBeVisible();
    await expect(page).toHaveURL('/diagnostic');
  });

  test('shows error when terms not accepted', async ({ page }) => {
    await page.fill('input[name="name"]', 'Test User');
    await page.fill('input[name="email"]', 'test@example.com');
    await page.fill('input[name="company"]', 'Acme PM');
    await page.click('button[type="submit"]');
    await expect(page.locator('p[role="alert"]')).toContainText('terms');
  });

  test('shows path selector after valid submit', async ({ page }) => {
    await page.fill('input[name="name"]', 'Test User');
    await page.fill('input[name="email"]', 'test@example.com');
    await page.fill('input[name="company"]', 'Acme PM');
    await page.locator('form [data-slot="checkbox"]').click();
    await page.click('button[type="submit"]');
    await expect(page.getByText('Quick Diagnostic', { exact: true })).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText('Full Diagnostic', { exact: true })).toBeVisible();
  });

  test('navigates to quick diagnostic after path selection', async ({ page }) => {
    await page.fill('input[name="name"]', 'Test User');
    await page.fill('input[name="email"]', 'test@example.com');
    await page.fill('input[name="company"]', 'Acme PM');
    await page.locator('form [data-slot="checkbox"]').click();
    await page.click('button[type="submit"]');
    await expect(page.getByText('Quick Diagnostic', { exact: true })).toBeVisible({ timeout: 10_000 });
    await page.getByRole('link', { name: 'Start quick diagnostic' }).click();
    await expect(page).toHaveURL('/diagnostic/quick');
  });
});
