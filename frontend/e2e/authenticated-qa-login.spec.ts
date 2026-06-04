import { expect, test } from '@playwright/test';
import { setupQaParentSession } from './qa-support';

test.describe('Europe dev authenticated QA login', () => {
  test('logs in through the dev-only QA helper and loads the parent dashboard', async ({ page }) => {
    await setupQaParentSession(page);
    await page.goto('/');

    await page.goto('/parent', { waitUntil: 'networkidle' });

    await expect(page.getByRole('heading', { name: 'My Family' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Settings', exact: true })).toBeVisible();
    await expect(page.getByRole('link', { name: /Dashboard/i }).first()).toBeVisible();

    // Check header
    const desktopParentDashboardLink = page.locator('nav.md\\:flex a').filter({ hasText: /Parent Dashboard/i });
    await expect(desktopParentDashboardLink).toBeVisible();
    await expect(page.getByRole('button', { name: /Logout/i })).toBeVisible();

    await page.getByRole('link', { name: 'Parent settings' }).click();
    await expect(page).toHaveURL(/\/parent\/settings$/);
    await expect(page.getByRole('heading', { name: 'Parent settings' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Allowance setup' })).toBeVisible();

    await page.getByRole('link', { name: 'Allowance setup' }).click();
    await expect(page).toHaveURL(/\/allowance$/);
    await expect(page.getByRole('heading', { name: 'Allowance setup' })).toBeVisible();
    const main = page.locator('main');
    await expect(main).toContainText('Allowance is optional');
    await expect(main).toContainText('Rewards and custom requests use the same available points and allowance value');
    await expect(page.locator('#child-select')).toBeVisible();
    await expect(main).toContainText('Available allowance balance');
    await expect(main).toContainText('Turning on allowance gives your child’s current points');
    await expect(main).toContainText('Enable allowance-linked points');

    // Go back to homepage and verify header still shows Parent Dashboard
    await page.goto('/');
    const homeParentDashboardLink = page.locator('nav.md\\:flex a').filter({ hasText: /Parent Dashboard/i });
    await expect(homeParentDashboardLink).toBeVisible();
    await expect(page.getByRole('button', { name: /Logout/i })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Login' })).not.toBeVisible();
  });

  test('shows Admin link in header when user is admin', async ({ page }) => {
    await setupQaParentSession(page);

    // Mock /api/me to return an admin.
    await page.route('**/api/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 999,
          email: 'admin@example.com',
          name: 'Admin User',
          is_admin: true,
          family_id: 1,
          created_at: '2026-05-18T00:00:00Z',
          last_login_at: '2026-05-18T00:00:00Z'
        })
      });
    });

    await page.goto('/');
    const adminLink = page.locator('nav.md\\:flex a').filter({ hasText: /^Admin$/i });
    await expect(adminLink).toBeVisible();
  });

  test('does NOT show Admin link in header when user is NOT admin', async ({ page }) => {
    await setupQaParentSession(page);

    // Default QA parent is NOT admin
    await page.goto('/');
    const adminLink = page.locator('nav.md\\:flex a').filter({ hasText: /^Admin$/i });
    await expect(adminLink).not.toBeVisible();
  });
});
