import { expect, test } from '@playwright/test';
import { setupQaParentSession } from './qa-support';

test.describe('Europe dev authenticated QA login', () => {
  test('logs in through the dev-only QA helper and loads the placeholder dashboard', async ({ page }) => {
    await setupQaParentSession(page);

    await page.goto('/parent', { waitUntil: 'networkidle' });

    await expect(page.getByRole('heading', { name: 'No school role assigned yet' })).toBeVisible();
    await expect(page.getByText('You are signed in, but this account does not have a school role yet.')).toBeVisible();

    await page.goto('/');
    const dashboardLink = page.locator('nav.md\\:flex a').filter({ hasText: /Dashboard/i });
    await expect(dashboardLink).toBeVisible();
    await expect(page.getByRole('button', { name: /Logout/i })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Login' })).not.toBeVisible();
  });

  test('shows Admin link in header when user is admin', async ({ page }) => {
    await setupQaParentSession(page);

    await page.route('**/api/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 999,
          email: 'admin@example.com',
          name: 'Admin User',
          is_admin: true,
          school_roles: [],
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

    await page.goto('/');
    const adminLink = page.locator('nav.md\\:flex a').filter({ hasText: /^Admin$/i });
    await expect(adminLink).not.toBeVisible();
  });
});
