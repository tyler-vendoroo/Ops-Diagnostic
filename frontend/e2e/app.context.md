# Vendoroo Operations Diagnostic — Test Context

## What this application does
A sales diagnostic tool for property management companies evaluating Vendoroo's AI maintenance coordination platform. Two paths:
- **Quick diagnostic**: 5-step survey → scoring engine → results page → PDF report
- **Full diagnostic**: File uploads (work orders, lease, PMA, vendor directory) → background processing → results page → PDF report

## Core user flows

### Quick diagnostic flow
1. Land on `/` or `/diagnostic`
2. Fill lead capture form (name, email, company, phone, terms checkbox)
3. Choose "Quick Diagnostic" from path selector
4. Complete 5 survey steps:
   - Step 1 (Portfolio): company name, door count, property count, PMS platform, operational model, staff count
   - Step 2 (Vendors): active vendor count, select trades covered (12 tap-to-toggle buttons)
   - Step 3 (Policies & controls): emergency protocols yes/no/unsure, NTE yes/no/unsure, SLAs yes/no/unsure
   - Step 4 (Current performance): response time select, completion time select, after-hours method radio
   - Step 5 (Your goal): primary goal radio (scale/optimize/elevate), pain points checkboxes (max 3)
5. Submit → redirect to `/diagnostic/results/{id}`
6. Results page shows: score ring, category breakdown, key findings, impact table, gaps, tier recommendation, PDF download

### Full diagnostic flow
1. Lead capture (same as quick)
2. Choose "Full Diagnostic"
3. Step 1: company info form (door count, property count, PMS, operational model, staff count, primary goal)
4. Step 2: file uploads (work orders required, lease/PMA/vendor directory optional)
5. Submit → redirect to `/diagnostic/results/{id}`
6. Results page polls for completion, then renders same layout as quick

## Key selectors and patterns
- Lead form fields: `input[name="name"]`, `input[name="email"]`, `input[name="company"]`, `input[name="phone"]`
- Terms checkbox: `button[role="checkbox"]` inside the lead form
- Survey inputs: `input#co-name`, `input#doors`, `input#props`, `input#staff`, `input#vendors`
- PMS select: `[data-slot="select-trigger"]` within the survey form
- Trade buttons: `<button>` elements containing trade names like "Plumbing", "Electrical", "HVAC"
- Policy buttons: "Yes"/"No"/"Unsure" `<button>` elements (NOT radio inputs — they were converted to tappable buttons)
- Step navigation: `button:text("Next")`, `button:text("Back")`
- Submit: `button:text("Run diagnostic")`
- Results score: text matching `/\d+/` inside the score ring SVG text element
- PDF download: `a[href*="/pdf"]`
- Progress indicator: named steps "Portfolio", "Vendors", "Policies", "Operations", "Goals"

## Data flow
- Lead data persists in `localStorage` under key `vendoroo_ops_diagnostic_lead`
- Quick diagnostic results source stored in `sessionStorage` under `vendoroo_diagnostic_results_source`
- API base: `http://localhost:8000/api/v1`
- Quick diagnostic POST: `/diagnostic/quick`
- Get diagnostic: `/diagnostic/{id}`
- Get PDF: `/diagnostic/{id}/pdf`

## Important test considerations
- The quick diagnostic path has ZERO AI/Claude API calls — fully deterministic, always testable
- The full diagnostic path calls Claude API for document analysis — mark tests `test.skip` without ANTHROPIC_API_KEY
- Score ranges: best-case prospect (all trades, fast response, all policies) should score >= 60
- Struggling prospect (3 trades, slow response, no policies) should score < 60
- PDF download link only appears if PDF generation succeeded (check for `a[href*="/pdf"]` existence)
- Results page polls every 2.5 seconds when status is "processing" — wait for score to appear before asserting
- localStorage must be cleared between test runs to avoid stale lead data
- Trade selector is a 3-column grid of `<button>` elements — clicking toggles selection state
- Policy answers (Yes/No/Unsure) are `<button>` elements with `aria-pressed` attribute, not radio inputs

## Healer rules
- Always wait for `.animate-spin` to disappear before asserting results content
- Wait for score text (a number inside the SVG) before asserting any results page content
- Trade buttons may shift layout — use text-based locators (`button:has-text("Plumbing")`) not positional
- Policy buttons: use `button:has-text("Yes")` scoped to the relevant section
- Never auto-fix a test asserting score ranges (>= 60, < 60) — these validate scoring logic, not UI
- If PDF download test fails with 404, the issue is backend PDF generation, not a stale selector — report as app bug
- The results page has 7 sections in order: score header, category breakdown, key findings, projected impact, gaps, recommended plan, CTAs
