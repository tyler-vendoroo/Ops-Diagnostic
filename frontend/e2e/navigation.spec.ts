// spec: Navigation and global elements
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

test.describe('Header', () => {
  test('visible on landing page', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('header a[href="/"]')).toBeVisible();
    await expect(page.locator('header').getByText('Vendoroo.ai', { exact: false })).toBeVisible();
  });

  test('visible on diagnostic entry page', async ({ page }) => {
    await page.goto('/diagnostic');
    await expect(page.locator('header a[href="/"]')).toBeVisible();
  });

  test('visible on survey page', async ({ page }) => {
    await gotoWithLead(page);
    await expect(page.locator('header a[href="/"]')).toBeVisible();
  });
});

test.describe('Footer', () => {
  test('visible on landing page', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('footer').getByText('2026')).toBeVisible();
    await expect(page.locator('footer').getByText(/Privacy/i)).toBeVisible();
  });

  test('visible on diagnostic entry page', async ({ page }) => {
    await page.goto('/diagnostic');
    await expect(page.locator('footer').getByText('2026')).toBeVisible();
  });
});

test.describe('Back to paths link', () => {
  test('navigates to /diagnostic', async ({ page }) => {
    await gotoWithLead(page);

    const backLink = page.getByRole('link', { name: 'Back to paths' });
    await expect(backLink).toBeVisible();
    await backLink.click();

    await expect(page).toHaveURL('/diagnostic');
    await expect(page.getByText('Operations diagnostic')).toBeVisible();
  });
});

test.describe('Back button preserves Step 1 data', () => {
  test('Step 1 values restored after navigating back from Step 2', async ({ page }) => {
    await gotoWithLead(page);

    // Fill and submit Step 1
    await page.fill('#doors', '500');
    await page.fill('#props', '20');
    await page.locator('[data-slot="select-trigger"]').click();
    await page.locator('[data-slot="select-item"]').filter({ hasText: 'AppFolio' }).click();
    await page.keyboard.press('Escape');
    await page.locator('[data-slot="radio-group-item"]').nth(0).click({ force: true });
    await page.fill('#staff', '3');
    await page.click('button:has-text("Next")');

    // Now on Step 2 — go back
    await page.click('button:has-text("Back")');

    // Step 1 should be visible with restored values
    await expect(page.getByText('Your portfolio')).toBeVisible();
    await expect(page.locator('#doors')).toHaveValue('500');
    await expect(page.locator('#props')).toHaveValue('20');
    await expect(page.locator('#staff')).toHaveValue('3');
  });
});

test.describe('Progress indicator', () => {
  test('updates to step 2 after completing Step 1', async ({ page }) => {
    await gotoWithLead(page);

    const nav = page.locator('nav[aria-label="Diagnostic progress"]');
    await expect(nav).toBeVisible();

    // Fill and submit Step 1
    await page.fill('#doors', '500');
    await page.fill('#props', '20');
    await page.locator('[data-slot="select-trigger"]').click();
    await page.locator('[data-slot="select-item"]').filter({ hasText: 'AppFolio' }).click();
    await page.keyboard.press('Escape');
    await page.locator('[data-slot="radio-group-item"]').nth(0).click({ force: true });
    await page.fill('#staff', '3');
    await page.click('button:has-text("Next")');

    // Step 2 (Vendors) should now be active
    await expect(page.getByText('Vendor network')).toBeVisible();
  });
});
