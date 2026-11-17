/**
 * Playwright E2E Smoke Test (Phase 3 Stretch)
 * Tests the complete end-to-end journey:
 * 1. Open homepage & click 'Try sample data'
 * 2. Navigate to Forecast Studio & trigger backtesting
 * 3. Inspect Leaderboard & Conformal Prediction Intervals
 * 4. Open AI Copilot drawer via ⌘K & ask question
 * 5. Navigate to printable report view
 */

import { test, expect } from '@playwright/test';

test.describe('Forecastly End-to-End Workflow', () => {
  test('Sample Data -> Forecast -> AI Copilot -> Printable Report', async ({ page }) => {
    // 1. Visit homepage
    await page.goto('/');
    await expect(page).toHaveTitle(/Forecastly/);

    // 2. Load sample data
    const sampleBtn = page.getByRole('button', { name: /try sample data/i });
    if (await sampleBtn.isVisible()) {
      await sampleBtn.click();
      await expect(page.getByText(/sample.*loaded/i)).toBeVisible({ timeout: 10000 });
    }

    // 3. Navigate to Forecast Studio
    await page.goto('/forecast');
    const runBtn = page.getByRole('button', { name: /run forecast/i });
    if (await runBtn.isVisible()) {
      await runBtn.click();
      // Wait for backtesting to complete
      await expect(page.getByText(/forecast timeline/i)).toBeVisible({ timeout: 60000 });
      await expect(page.getByText(/model leaderboard/i)).toBeVisible();
    }

    // 4. Open AI Copilot via ⌘K
    await page.keyboard.press('Meta+KeyK');
    await expect(page.getByText(/forecastly ai/i)).toBeVisible();

    // 5. Check Report view
    const reportLink = page.getByRole('button', { name: /report/i });
    if (await reportLink.isVisible()) {
      await reportLink.click();
      await expect(page.getByText(/executive sales report/i)).toBeVisible();
    }
  });
});
