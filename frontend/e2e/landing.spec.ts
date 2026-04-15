// spec: Landing page
// seed: e2e/lead-capture.spec.ts

import { test, expect } from '@playwright/test';

test.describe('Landing page', () => {
  test('renders all sections', async ({ page }) => {
    await page.goto('/');

    await expect(page).toHaveTitle('Vendoroo Ops Diagnostic');

    // Header
    const logoLink = page.locator('header a[href="/"]');
    await expect(logoLink).toBeVisible();
    await expect(page.locator('header nav a[href="https://vendoroo.ai"]')).toBeVisible();

    // Hero
    await expect(page.getByText('Vendoroo · AI Diagnostics')).toBeVisible();
    const h1 = page.locator('h1');
    await expect(h1).toContainText('Every operation has a score.');
    await expect(h1).toContainText("What's yours?");
    const heroCta = page.getByRole('link', { name: 'Start your diagnostic' }).first();
    await expect(heroCta).toBeVisible();
    await expect(heroCta).toHaveAttribute('href', '/diagnostic');

    // Social proof
    await expect(page.getByText('12,000+ work orders analyzed')).toBeVisible();
    await expect(page.getByText('200+ portfolios scored')).toBeVisible();
    await expect(page.getByText('Avg. score: 54/100')).toBeVisible();

    // How it works
    await page.getByRole('heading', { name: 'How it works' }).scrollIntoViewIfNeeded();
    await expect(page.getByRole('heading', { name: 'Tell us about your operation' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'We run the diagnostics' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Get your prescription' })).toBeVisible();

    // Choose your depth
    await page.getByRole('heading', { name: 'Choose your depth' }).scrollIntoViewIfNeeded();
    await expect(page.getByText('Most popular')).toBeVisible();
    const quickCta = page.getByRole('link', { name: 'Start quick diagnostic' });
    await expect(quickCta).toBeVisible();
    await expect(quickCta).toHaveAttribute('href', '/diagnostic/quick');
    const fullCta = page.getByRole('link', { name: 'Start full diagnostic' });
    await expect(fullCta).toBeVisible();
    await expect(fullCta).toHaveAttribute('href', '/diagnostic/full');

    // What's in your report
    await page.getByRole('heading', { name: "What's in your diagnostic report" }).scrollIntoViewIfNeeded();
    await expect(page.getByText(/SAMPLE PREVIEW/i)).toBeVisible();

    // Final CTA
    await page.getByText('Every operation has a number.', { exact: false }).scrollIntoViewIfNeeded();
    await expect(page.getByText('Every operation has a number.', { exact: false })).toBeVisible();

    // Footer
    await expect(page.locator('footer a[href="https://vendoroo.ai"]')).toBeVisible();
    await expect(page.locator('footer').getByText('2026')).toBeVisible();
    await expect(page.locator('footer').getByText(/Privacy/i)).toBeVisible();
  });

  test('hero CTA navigates to diagnostic entry', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('link', { name: 'Start your diagnostic' }).first().click();
    await expect(page).toHaveURL('/diagnostic');
    await expect(page.getByText('Operations diagnostic')).toBeVisible();
  });

  test('quick card CTA redirects to lead gate when no lead captured', async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
    await page.goto('/diagnostic/quick');
    await expect(page).toHaveURL(/\/diagnostic(\?next=%2Fdiagnostic%2Fquick)?$/);
    await expect(page.getByText('Operations diagnostic')).toBeVisible();
  });
});
