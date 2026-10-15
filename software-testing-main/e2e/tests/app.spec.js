import { test, expect } from '@playwright/test';

test('end-to-end security runner workflow', async ({ page }) => {
  // 1. Log in
  await page.goto('/');
  await page.fill('input[type="text"]', 'admin');
  await page.fill('input[type="password"]', 'secret');
  await page.click('button:has-text("Sign In")');

  // 2. Dashboard
  await expect(page.locator('h1')).toContainText('SecRunner Dashboard');

  // 3. New Run
  await page.click('text=New Run');
  await expect(page).toHaveURL(/.*\/run/);
  await expect(page.locator('h1')).toContainText('Execute Command');

  // Ensure select exists and button is ready
  const startButton = page.locator('button', { hasText: 'Start Scan' });
  await expect(startButton).toBeEnabled();
  
  // Click Start
  await startButton.click();
  
  // Validate Status changes
  await expect(page.locator('text=Status: Running')).toBeVisible();
  
  // Wait for the mock output line
  await expect(page.locator('.font-mono')).toContainText('hello from mock');
  
  // Wait for completion
  await expect(page.locator('text=Status: Pass')).toBeVisible({ timeout: 10000 });
  await expect(page.locator('.font-mono')).toContainText('done');
});
