// spec: Survey gate and Step 1 — Portfolio
// seed: e2e/lead-capture.spec.ts

import { test, expect, type Page } from '@playwright/test';

const LEAD = {
  name: 'Test QA User',
  email: 'qa@example.com',
  company: 'QA Property Management',
  terms_accepted: true,
  lead_id: 'test-lead',
};

async function seedLead(page: Page) {
  await page.evaluate((lead) => {
    localStorage.setItem('vendoroo_ops_diagnostic_lead', JSON.stringify(lead));
  }, LEAD);
}

async function gotoWithLead(page: Page) {
  await page.goto('/diagnostic/quick');
  await seedLead(page);
  await page.reload();
}

// ---------------------------------------------------------------------------
// Survey gate
// ---------------------------------------------------------------------------

test.describe('Survey gate', () => {
  test('RequireLeadGate redirects unauthenticated users', async ({ page }) => {
    await page.goto('/diagnostic/quick');
    await page.evaluate(() => localStorage.clear());
    await page.reload();

    await expect(page).toHaveURL(/\/diagnostic/);
    await expect(page.locator('input[name="name"]')).toBeVisible();
  });

  test('survey header renders correctly', async ({ page }) => {
    await gotoWithLead(page);

    await expect(page.locator('h1')).toContainText('Quick diagnostic');
    await expect(page.getByText('Five short steps', { exact: false })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Back to paths' })).toBeVisible();
  });

  test('progress indicator shows 5 steps', async ({ page }) => {
    await gotoWithLead(page);

    const nav = page.locator('nav[aria-label="Diagnostic progress"]');
    await expect(nav).toBeVisible();
    await expect(nav.getByText('Portfolio')).toBeVisible();
    await expect(nav.getByText('Vendors')).toBeVisible();
    await expect(nav.getByText('Policies')).toBeVisible();
    await expect(nav.getByText('Operations')).toBeVisible();
    await expect(nav.getByText('Goals')).toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// Step 1 — Portfolio
// ---------------------------------------------------------------------------

test.describe('Step 1 — Portfolio', () => {
  test('renders correctly with pre-filled company', async ({ page }) => {
    await gotoWithLead(page);

    await expect(page.getByText('Your portfolio')).toBeVisible();
    await expect(page.locator('#co-name')).toHaveValue('QA Property Management');
    await expect(page.locator('#doors')).toHaveValue('');
    await expect(page.locator('#props')).toHaveValue('');
    await expect(page.locator('#staff')).toHaveValue('');
  });

  test('validation: missing company name', async ({ page }) => {
    await gotoWithLead(page);
    await page.fill('#co-name', '');
    await page.click('button:has-text("Next")');
    await expect(page.locator('p[role="alert"]')).toContainText('Company name is required');
  });

  test('validation: invalid door count', async ({ page }) => {
    await gotoWithLead(page);
    await page.fill('#co-name', 'QA PM');
    await page.fill('#doors', 'abc');
    await page.click('button:has-text("Next")');
    await expect(page.locator('p[role="alert"]')).toContainText('valid number');
  });

  test('validation: no PMS platform selected', async ({ page }) => {
    await gotoWithLead(page);
    await page.fill('#co-name', 'QA PM');
    await page.fill('#doors', '100');
    await page.fill('#props', '10');
    await page.click('button:has-text("Next")');
    await expect(page.locator('p[role="alert"]')).toContainText(/PMS|platform/i);
  });

  test('PMS platform dropdown has 5 options', async ({ page }) => {
    await gotoWithLead(page);
    await page.locator('[data-slot="select-trigger"]').click();

    for (const opt of ['AppFolio', 'Buildium', 'RentVine', 'Rent Manager', 'Other']) {
      await expect(page.locator('[data-slot="select-item"]').filter({ hasText: opt })).toBeVisible();
    }
  });

  test('valid Step 1 advances to Step 2', async ({ page }) => {
    await gotoWithLead(page);

    await page.fill('#doors', '500');
    await page.fill('#props', '20');
    await page.locator('[data-slot="select-trigger"]').click();
    await page.locator('[data-slot="select-item"]').filter({ hasText: 'AppFolio' }).click();
    await page.keyboard.press('Escape');
    await page.locator('[data-slot="radio-group-item"]').nth(0).click({ force: true });
    await page.fill('#staff', '3');
    await page.click('button:has-text("Next")');

    await expect(page.getByText('Vendor network')).toBeVisible();
  });
});
