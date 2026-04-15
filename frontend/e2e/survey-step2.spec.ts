// spec: Step 2 — Vendor network
// seed: e2e/lead-capture.spec.ts

import { test, expect, type Page } from '@playwright/test';

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

async function advanceToStep2(page: Page) {
  await page.goto('/diagnostic/quick');
  await seedLead(page);
  await page.reload();

  await page.fill('#doors', '500');
  await page.fill('#props', '20');
  await page.locator('[data-slot="select-trigger"]').click();
  await page.locator('[data-slot="select-item"]').filter({ hasText: 'AppFolio' }).click();
  await page.keyboard.press('Escape');
  await page.locator('[data-slot="radio-group-item"]').nth(0).click({ force: true });
  await page.fill('#staff', '3');
  await page.click('button:has-text("Next")');
}

const ALL_TRADES = [
  'Plumbing', 'Electrical', 'HVAC', 'Appliance Repair', 'Landscaping',
  'Pest Control', 'Roofing', 'Painting', 'Flooring', 'General Handyman',
  'Pool/Spa', 'Locksmith',
] as const;

test.describe('Step 2 — Vendor network', () => {
  test('renders correctly', async ({ page }) => {
    await advanceToStep2(page);

    await expect(page.getByText('Vendor network')).toBeVisible();
    await expect(page.locator('#vendors')).toBeVisible();
    await expect(page.getByText('0 of 12 required trades')).toBeVisible();

    for (const trade of ALL_TRADES) {
      await expect(page.locator('button').filter({ hasText: trade })).toBeVisible();
    }
  });

  test('validation: invalid vendor count', async ({ page }) => {
    await advanceToStep2(page);
    await page.fill('#vendors', 'abc');
    await page.click('button:has-text("Next")');
    await expect(page.locator('p[role="alert"]')).toContainText('valid number');
  });

  test('trade toggle — select and deselect', async ({ page }) => {
    await advanceToStep2(page);

    await page.locator('button').filter({ hasText: 'Plumbing' }).click();
    await expect(page.getByText('1 of 12 required trades')).toBeVisible();

    await page.locator('button').filter({ hasText: 'Plumbing' }).click();
    await expect(page.getByText('0 of 12 required trades')).toBeVisible();
  });

  test('all 12 trades selected shows full coverage and advances to Step 3', async ({ page }) => {
    await advanceToStep2(page);
    await page.fill('#vendors', '30');

    for (const trade of ALL_TRADES) {
      await page.locator('button').filter({ hasText: trade }).click();
    }

    await expect(page.getByText('12 of 12 required trades')).toBeVisible();
    await expect(page.getByText('Full coverage across all required trades')).toBeVisible();

    await page.click('button:has-text("Next")');
    await expect(page.getByText('Policies & controls')).toBeVisible();
  });
});
