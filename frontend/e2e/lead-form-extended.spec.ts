// spec: Lead form — extended
// seed: e2e/lead-capture.spec.ts

import { test, expect, type Page } from '@playwright/test';

const LEAD_KEY = 'vendoroo_ops_diagnostic_lead';

async function clearLead(page: Page) {
  await page.goto('/diagnostic');
  await page.evaluate((key) => localStorage.removeItem(key), LEAD_KEY);
  await page.reload();
}

async function fillAndSubmitLead(
  page: Page,
  opts: { name?: string; email?: string; company?: string } = {},
) {
  const name    = opts.name    ?? 'Test QA User';
  const email   = opts.email   ?? 'qa@example.com';
  const company = opts.company ?? 'QA Property Management';

  await page.fill('input[name="name"]', name);
  await page.fill('input[name="email"]', email);
  await page.fill('input[name="company"]', company);
  await page.locator('form [data-slot="checkbox"]').click();
  await page.click('button[type="submit"]');
}

test.describe('Lead form — extended', () => {
  test('valid submission saves lead to localStorage', async ({ page }) => {
    await clearLead(page);
    await fillAndSubmitLead(page, {
      name: 'Test QA User',
      email: 'qa@example.com',
      company: 'QA Property Management',
    });

    await page.waitForFunction(
      (key) => localStorage.getItem(key) !== null,
      LEAD_KEY,
      { timeout: 10_000 },
    );

    const stored = await page.evaluate(
      (key) => JSON.parse(localStorage.getItem(key) ?? 'null'),
      LEAD_KEY,
    );
    expect(stored).not.toBeNull();
    expect(stored.name).toBe('Test QA User');
    expect(stored.email).toBe('qa@example.com');
    expect(stored.company).toBe('QA Property Management');
  });

  test('valid submission with ?next= redirects directly to survey', async ({ page }) => {
    await clearLead(page);
    await page.goto('/diagnostic?next=%2Fdiagnostic%2Fquick');

    await fillAndSubmitLead(page, {
      name: 'Test QA User',
      email: 'qa@example.com',
      company: 'QA Property Management',
    });

    await expect(page).toHaveURL('/diagnostic/quick', { timeout: 10_000 });
    await expect(page.getByRole('heading', { name: 'Your portfolio' })).toBeVisible();
  });

  test('path selector shows personalized greeting', async ({ page }) => {
    await clearLead(page);
    await fillAndSubmitLead(page, { name: 'Test QA User' });

    await expect(
      page.locator('p', { hasText: 'Test QA User' }),
    ).toBeVisible({ timeout: 10_000 });
  });

  test('path selector — Start full diagnostic navigates correctly', async ({ page }) => {
    await clearLead(page);
    await fillAndSubmitLead(page);

    await expect(
      page.getByRole('link', { name: 'Start full diagnostic' }),
    ).toBeVisible({ timeout: 10_000 });

    await page.getByRole('link', { name: 'Start full diagnostic' }).click();
    await expect(page).toHaveURL('/diagnostic/full', { timeout: 10_000 });
  });
});
