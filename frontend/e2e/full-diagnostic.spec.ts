import { test, expect, type Page } from '@playwright/test';
import path from 'path';

const WO_CSV = path.join(__dirname, 'fixtures', 'work-orders.csv');

const LEAD = {
  name: 'Test User',
  email: 'test@playwright.com',
  company: 'Acme PM',
};

async function seedLead(page: Page) {
  await page.evaluate((lead) => {
    localStorage.setItem('vendoroo_ops_diagnostic_lead', JSON.stringify({
      ...lead,
      terms_accepted: true,
      lead_id: 'test-lead',
    }));
  }, LEAD);
}

/** Seed lead + prior quick-diagnostic results so the page auto-skips step 1. */
async function seedLeadWithResults(page: Page) {
  await page.evaluate((lead) => {
    localStorage.setItem('vendoroo_ops_diagnostic_lead', JSON.stringify({
      ...lead,
      terms_accepted: true,
      lead_id: 'test-lead',
    }));
    localStorage.setItem('vendoroo_diagnostic_results_source', JSON.stringify({
      door_count: 350,
      property_count: 14,
      pms_platform: 'AppFolio',
      operational_model: 'va',
      staff_count: 4,
      primary_goal: 'scale',
    }));
  }, LEAD);
}

async function fillStep1(page: Page) {
  await page.fill('#company', 'Test PM Co');
  await page.fill('#door-count', '300');
  await page.fill('#property-count', '12');
  await page.selectOption('#pms', 'AppFolio');
  await page.fill('#staff-count', '5');
  await page.getByText('VA Coordinators', { exact: true }).click();
  await page.getByText('Scale', { exact: true }).click();
}

async function uploadWorkOrders(page: Page) {
  // The work order dropzone is the first file input (sr-only hidden input)
  const fileInputs = page.locator('input[type="file"]');
  await fileInputs.nth(0).setInputFiles(WO_CSV);
  // Wait for file to appear as attached (dropzone switches to file-name display)
  await expect(page.locator('text=work-orders.csv')).toBeVisible();
}

async function waitForResults(page: Page) {
  await expect(page.locator('.animate-spin')).not.toBeVisible({ timeout: 60_000 });
  await expect(page.locator('svg text').first()).toBeVisible({ timeout: 60_000 });
}

// ─────────────────────────────────────────────────────────────────────────────
// Step 1 — Company info
// ─────────────────────────────────────────────────────────────────────────────

test.describe('Full diagnostic — step 1', () => {
  test('renders company info form', async ({ page }) => {
    await page.goto('/diagnostic/full');
    await seedLead(page);
    await page.reload();

    await expect(page.locator('#company')).toBeVisible();
    await expect(page.locator('#door-count')).toBeVisible();
    await expect(page.locator('#property-count')).toBeVisible();
    await expect(page.locator('#pms')).toBeVisible();
    await expect(page.locator('#staff-count')).toBeVisible();
    await expect(page.getByText('VA Coordinators', { exact: true })).toBeVisible();
    await expect(page.getByText('In-House Tech Team', { exact: true })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Continue to uploads', exact: true })).toBeVisible();
  });

  test('advances to step 2 after filling required fields', async ({ page }) => {
    await page.goto('/diagnostic/full');
    await seedLead(page);
    await page.reload();

    await fillStep1(page);
    await page.getByRole('button', { name: 'Continue to uploads', exact: true }).click();

    // Step 2 dropzones visible
    await expect(page.getByText('Work Order History')).toBeVisible();
    await expect(page.getByText('Lease Agreement')).toBeVisible();
    await expect(page.getByText('PMA')).toBeVisible();
    await expect(page.getByText('Vendor Directory')).toBeVisible();
  });

  test('auto-skips to step 2 when prior results are in localStorage', async ({ page }) => {
    await page.goto('/diagnostic/full');
    await seedLeadWithResults(page);
    await page.reload();

    // Should land directly on step 2 — no company form fields
    await expect(page.locator('#company')).not.toBeVisible();
    await expect(page.getByText('Work Order History')).toBeVisible();
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Step 2 — File uploads
// ─────────────────────────────────────────────────────────────────────────────

test.describe('Full diagnostic — step 2', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/diagnostic/full');
    await seedLeadWithResults(page);
    await page.reload();
    // Auto-skips to step 2
    await expect(page.getByText('Work Order History')).toBeVisible();
  });

  test('Run Full Diagnostic is disabled without a work order file', async ({ page }) => {
    const btn = page.getByRole('button', { name: 'Run Full Diagnostic', exact: true });
    await expect(btn).toBeDisabled();
  });

  test('Run Full Diagnostic enables after uploading work order file', async ({ page }) => {
    await uploadWorkOrders(page);
    const btn = page.getByRole('button', { name: 'Run Full Diagnostic', exact: true });
    await expect(btn).toBeEnabled();
  });

  test('back button returns to step 1', async ({ page }) => {
    await page.getByRole('button', { name: '← Back', exact: true }).click();
    await expect(page.locator('#company')).toBeVisible();
  });

  test('uploaded file shows name and can be removed', async ({ page }) => {
    await uploadWorkOrders(page);
    await expect(page.locator('text=work-orders.csv')).toBeVisible();

    // Remove the file
    await page.getByRole('button', { name: 'Remove', exact: true }).first().click();
    await expect(page.locator('text=work-orders.csv')).not.toBeVisible();

    // Button should be disabled again
    const btn = page.getByRole('button', { name: 'Run Full Diagnostic', exact: true });
    await expect(btn).toBeDisabled();
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Full flow
// ─────────────────────────────────────────────────────────────────────────────

test.describe('Full diagnostic — end-to-end flow', () => {
  test('completes full flow from step 1 and reaches results page', async ({ page }) => {
    await page.goto('/diagnostic/full');
    await seedLead(page);
    await page.reload();

    // Step 1
    await fillStep1(page);
    await page.getByRole('button', { name: 'Continue to uploads', exact: true }).click();

    // Step 2
    await expect(page.getByText('Work Order History')).toBeVisible();
    await uploadWorkOrders(page);
    await page.getByRole('button', { name: 'Run Full Diagnostic', exact: true }).click();

    // Navigate to results
    await expect(page).toHaveURL(/\/diagnostic\/results\//, { timeout: 30_000 });
    await waitForResults(page);

    // Results page shows key sections
    await expect(page.locator('svg text').first()).toBeVisible();
  });

  test('auto-skip + upload reaches results page', async ({ page }) => {
    await page.goto('/diagnostic/full');
    await seedLeadWithResults(page);
    await page.reload();

    // Step 2 directly
    await expect(page.getByText('Work Order History')).toBeVisible();
    await uploadWorkOrders(page);
    await page.getByRole('button', { name: 'Run Full Diagnostic', exact: true }).click();

    await expect(page).toHaveURL(/\/diagnostic\/results\//, { timeout: 30_000 });
    await waitForResults(page);
  });
});
