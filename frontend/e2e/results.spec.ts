// spec: Diagnostic results page
// seed: e2e/lead-capture.spec.ts

import { test, expect, type Page } from '@playwright/test';

test.setTimeout(60_000);

async function seedLead(page: Page) {
  await page.evaluate(() =>
    localStorage.setItem(
      'vendoroo_ops_diagnostic_lead',
      JSON.stringify({
        name: 'Test QA User',
        email: 'qa@example.com',
        company: 'QA Property Management',
        terms_accepted: true,
        lead_id: 'test-lead',
      }),
    ),
  );
}

async function runFullDiagnostic(page: Page) {
  await page.goto('/diagnostic/quick');
  await seedLead(page);
  await page.reload();

  // Step 1
  await page.fill('#doors', '500');
  await page.fill('#props', '20');
  await page.locator('[data-slot="select-trigger"]').click();
  await page.locator('[data-slot="select-item"]').filter({ hasText: 'AppFolio' }).click();
  await page.keyboard.press('Escape');
  await page.locator('[data-slot="radio-group-item"]').nth(0).click({ force: true });
  await page.fill('#staff', '3');
  await page.click('button:has-text("Next")');
  await page.getByRole('heading', { name: /vendor network/i }).waitFor();

  // Step 2
  await page.fill('#vendors', '30');
  for (const trade of ['Plumbing', 'Electrical', 'HVAC', 'Appliance Repair', 'Landscaping',
    'Pest Control', 'Roofing', 'Painting', 'Flooring', 'General Handyman', 'Pool/Spa', 'Locksmith']) {
    await page.locator('button').filter({ hasText: trade }).click();
  }
  await page.click('button:has-text("Next")');
  await page.getByRole('heading', { name: /policies/i }).waitFor();

  // Step 3 — all Yes (indices 0, 3, 6 in the aria-pressed buttons)
  const policyBtns = page.locator('button[aria-pressed]');
  await policyBtns.nth(0).click();
  await policyBtns.nth(3).click();
  await policyBtns.nth(6).click();
  await page.click('button:has-text("Next")');
  await page.getByRole('heading', { name: /current performance/i }).waitFor();

  // Step 4
  const triggers = page.locator('[data-slot="select-trigger"]');
  await triggers.nth(0).click();
  await page.locator('[data-slot="select-item"]').filter({ hasText: 'Under 1 hour' }).click();
  await page.waitForTimeout(150);
  await triggers.nth(1).click();
  await page.locator('[data-slot="select-item"]').filter({ hasText: '1–3 days' }).click();
  await page.waitForTimeout(150);
  await page.locator('[data-slot="radio-group-item"]').nth(0).click({ force: true });
  await page.click('button:has-text("Next")');
  await page.getByRole('heading', { name: /your goal/i }).waitFor();

  // Step 5
  await page.getByText('Scale', { exact: true }).click();
  await page.locator('label').filter({ hasText: 'Vendor reliability' }).click();
  await page.locator('label').filter({ hasText: 'Response times' }).click();
  await page.locator('label').filter({ hasText: 'Scaling the team' }).click();
  await page.click('button:has-text("Run diagnostic")');

  await expect(page).toHaveURL(/\/diagnostic\/results\//, { timeout: 20_000 });
  await page.waitForFunction(() => !document.querySelector('.animate-spin'), { timeout: 30_000 });
}

test.describe('Results page', () => {
  test('shows score rings with Current and With Vendoroo labels', async ({ page }) => {
    await runFullDiagnostic(page);

    await expect(page.getByText('Current', { exact: true }).first()).toBeVisible();
    await expect(page.getByText('With Vendoroo', { exact: true }).first()).toBeVisible();
  });

  test('shows category breakdown section', async ({ page }) => {
    await runFullDiagnostic(page);

    await expect(page.getByText('Category breakdown')).toBeVisible();
  });

  test('shows key findings section', async ({ page }) => {
    await runFullDiagnostic(page);

    await expect(page.getByText('Key findings')).toBeVisible();
  });

  test('shows gaps to address section', async ({ page }) => {
    await runFullDiagnostic(page);

    await expect(page.getByText('Gaps to address')).toBeVisible();
  });

  test('shows recommended plan section with pricing', async ({ page }) => {
    await runFullDiagnostic(page);

    await expect(page.getByText('Recommended plan')).toBeVisible();
    await expect(page.getByText(/\$\d+.*\/door\/mo/i).first()).toBeVisible();
  });

  test('shows upsell CTA when source is quick', async ({ page }) => {
    await runFullDiagnostic(page);

    // sessionStorage source is set to 'quick' by the survey submission
    const upsellLink = page.getByRole('link', { name: /full data-driven analysis/i });
    await expect(upsellLink).toBeVisible();
    await expect(upsellLink).toHaveAttribute('href', '/diagnostic/full');
  });

  test('shows Book a call CTA', async ({ page }) => {
    await runFullDiagnostic(page);

    await expect(page.getByRole('link', { name: /Book a call/i })).toBeVisible();
  });

  test('hides upsell CTA when source is not quick', async ({ page }) => {
    await runFullDiagnostic(page);

    // Clear the source flag and reload
    await page.evaluate(() => sessionStorage.removeItem('vendoroo_diagnostic_results_source'));
    await page.reload();
    await page.waitForFunction(() => !document.querySelector('.animate-spin'), { timeout: 30_000 });

    await expect(page.getByRole('link', { name: /full data-driven analysis/i })).not.toBeVisible();
  });
});
