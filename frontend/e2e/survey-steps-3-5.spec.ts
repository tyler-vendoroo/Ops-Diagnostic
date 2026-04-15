// spec: Survey steps 3–5 (Policies, Current Performance, Goals)
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

async function advanceToStep3(page: Page) {
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
  for (const t of ['Plumbing', 'Electrical', 'HVAC', 'Appliance Repair', 'Landscaping',
    'Pest Control', 'Roofing', 'Painting', 'Flooring', 'General Handyman', 'Pool/Spa', 'Locksmith']) {
    await page.locator('button').filter({ hasText: t }).click();
  }
  await page.click('button:has-text("Next")');
  await page.getByRole('heading', { name: /policies/i }).waitFor();
}

async function advanceToStep4(page: Page) {
  await advanceToStep3(page);
  const policyBtns = page.locator('button[aria-pressed]');
  await policyBtns.nth(0).click();
  await policyBtns.nth(3).click();
  await policyBtns.nth(6).click();
  await page.click('button:has-text("Next")');
  await page.getByRole('heading', { name: /current performance/i }).waitFor();
}

async function advanceToStep5(page: Page) {
  await advanceToStep4(page);
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
}

test.beforeEach(async ({ page }) => {
  await page.goto('/diagnostic/quick');
  await seedLead(page);
  await page.reload();
});

// ===========================================================================
// Step 3 — Policies
// ===========================================================================
test.describe('Step 3 — Policies', () => {
  test('renders correctly', async ({ page }) => {
    await advanceToStep3(page);

    await expect(page.getByRole('heading', { name: /policies & controls/i })).toBeVisible();
    await expect(page.locator('button[aria-pressed]')).toHaveCount(9);
    await expect(
      page.locator('label, span, div').filter({ hasText: /tiered/i }).first(),
    ).not.toBeVisible();
  });

  test('NTE tiered checkbox shows conditionally', async ({ page }) => {
    await advanceToStep3(page);

    const policyBtns = page.locator('button[aria-pressed]');
    await policyBtns.nth(3).click();
    await expect(
      page.locator('label, span, div, input').filter({ hasText: /tiered/i }).first(),
    ).toBeVisible();

    await policyBtns.nth(4).click();
    await expect(
      page.locator('label, span, div, input').filter({ hasText: /tiered/i }).first(),
    ).not.toBeVisible();
  });

  test('validation: unanswered policies', async ({ page }) => {
    await advanceToStep3(page);
    await page.click('button:has-text("Next")');

    const alert = page.locator('p[role="alert"]');
    await expect(alert).toBeVisible();
    await expect(alert).toContainText(/policy|answer/i);
  });

  test('policy button pressed state', async ({ page }) => {
    await advanceToStep3(page);
    const policyBtns = page.locator('button[aria-pressed]');
    await policyBtns.nth(0).click();
    await expect(policyBtns.nth(0)).toHaveAttribute('aria-pressed', 'true');
  });

  test('valid Step 3 advances to Step 4', async ({ page }) => {
    await advanceToStep3(page);
    const policyBtns = page.locator('button[aria-pressed]');
    await policyBtns.nth(0).click();
    await policyBtns.nth(3).click();
    await policyBtns.nth(6).click();
    await page.click('button:has-text("Next")');
    await expect(page.getByRole('heading', { name: /current performance/i })).toBeVisible();
  });
});

// ===========================================================================
// Step 4 — Current Performance
// ===========================================================================
test.describe('Step 4 — Current Performance', () => {
  test('renders correctly', async ({ page }) => {
    await advanceToStep4(page);

    await expect(page.getByRole('heading', { name: /current performance/i })).toBeVisible();
    await expect(page.locator('[data-slot="select-trigger"]')).toHaveCount(2);
    await expect(page.locator('[data-slot="radio-group-item"]')).toHaveCount(5);
  });

  test('validation: incomplete fields', async ({ page }) => {
    await advanceToStep4(page);
    await page.click('button:has-text("Next")');

    const alert = page.locator('p[role="alert"]');
    await expect(alert).toBeVisible();
    await expect(alert).toContainText(/operations|complete/i);
  });

  test('valid Step 4 advances to Step 5', async ({ page }) => {
    await advanceToStep4(page);

    const triggers = page.locator('[data-slot="select-trigger"]');
    await triggers.nth(0).click();
    await page.locator('[data-slot="select-item"]').filter({ hasText: 'Under 1 hour' }).click();
    await page.waitForTimeout(150);
    await triggers.nth(1).click();
    await page.locator('[data-slot="select-item"]').filter({ hasText: '1–3 days' }).click();
    await page.waitForTimeout(150);
    await page.locator('[data-slot="radio-group-item"]').nth(0).click({ force: true });
    await page.click('button:has-text("Next")');

    await expect(page.getByRole('heading', { name: /your goal/i })).toBeVisible();
  });
});

// ===========================================================================
// Step 5 — Goals
// ===========================================================================
test.describe('Step 5 — Goals', () => {
  test('renders correctly', async ({ page }) => {
    await advanceToStep5(page);

    await expect(page.getByRole('heading', { name: /your goal/i })).toBeVisible();
    await expect(page.locator('[data-slot="radio-group-item"]')).toHaveCount(3);
    await expect(page.getByText('0 of 3 selected')).toBeVisible();
    await expect(page.locator('button:has-text("Run diagnostic")')).toBeVisible();
  });

  test('pain points max 3 enforcement', async ({ page }) => {
    await advanceToStep5(page);

    await page.locator('label').filter({ hasText: 'Vendor reliability' }).click();
    await page.locator('label').filter({ hasText: 'Response times' }).click();
    await page.locator('label').filter({ hasText: 'Scaling the team' }).click();
    await expect(page.getByText('3 of 3 selected')).toBeVisible();

    await page.locator('label').filter({ hasText: 'Cost control' }).click({ force: true });
    await expect(page.getByText('3 of 3 selected')).toBeVisible();
  });

  test('validation: no primary goal', async ({ page }) => {
    await advanceToStep5(page);
    await page.locator('label').filter({ hasText: 'Vendor reliability' }).click();
    await page.click('button:has-text("Run diagnostic")');

    const alert = page.locator('p[role="alert"]');
    await expect(alert).toBeVisible();
    await expect(alert).toContainText(/goal/i);
  });

  test('validation: no pain points', async ({ page }) => {
    await advanceToStep5(page);
    await page.getByText('Scale', { exact: true }).click();
    await page.click('button:has-text("Run diagnostic")');

    const alert = page.locator('p[role="alert"]');
    await expect(alert).toBeVisible();
    await expect(alert).toContainText(/pain point|operational/i);
  });

  test('submit runs diagnostic and navigates to results', async ({ page }) => {
    await advanceToStep5(page);

    await page.getByText('Scale', { exact: true }).click();
    await page.locator('label').filter({ hasText: 'Vendor reliability' }).click();
    await page.locator('label').filter({ hasText: 'Response times' }).click();
    await page.locator('label').filter({ hasText: 'Scaling the team' }).click();
    await page.click('button:has-text("Run diagnostic")');

    await expect(page).toHaveURL(/\/diagnostic\/results\//, { timeout: 20_000 });
  });
});
