import { expect, test } from '@playwright/test';
import { setupQaParentSession } from './qa-support';

test.describe('Europe dev authenticated QA login', () => {
  test('legacy parent URL sends a signed-in account to the Family Hero Hub explanation', async ({ page }) => {
    await setupQaParentSession(page);

    await page.goto('/parent', { waitUntil: 'domcontentloaded' });

    await expect(page).toHaveURL(/\/family-connection$/);
    await expect(page.getByRole('heading', { name: 'School updates for families.' })).toBeVisible();
  });

  test('links a platform administrator to the platform dashboard', async ({ page }) => {
    await setupQaParentSession(page);

    await page.route('**/api/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          user: {
            id: 999,
            email: 'admin@example.com',
            name: 'Admin User',
            locale: 'en',
            status: 'active',
            created_at: '2026-05-18T00:00:00Z',
            last_login_at: '2026-05-18T00:00:00Z'
          },
          is_platform_admin: true,
          can_manage_school_entitlements: true,
          memberships: []
        })
      });
    });

    await page.goto('/', { waitUntil: 'domcontentloaded' });
    await expect(page.locator('a[href="/platform"]').filter({ hasText: 'Dashboard' }).first()).toBeVisible();
  });

  test('does not expose the platform dashboard to a signed-in non-admin', async ({ page }) => {
    await setupQaParentSession(page);
    await page.route('**/api/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          user: {
            id: 1000,
            email: 'staff@example.com',
            name: 'Staff User',
            locale: 'en',
            status: 'active',
            created_at: '2026-05-18T00:00:00Z',
            last_login_at: '2026-05-18T00:00:00Z'
          },
          is_platform_admin: false,
          can_manage_school_entitlements: false,
          memberships: []
        })
      });
    });

    await page.goto('/', { waitUntil: 'domcontentloaded' });
    await expect(page.locator('a[href="/platform"]')).toHaveCount(0);
    await expect(page.locator('a[href="/family-connection"]').filter({ hasText: 'Dashboard' }).first()).toBeVisible();
  });
});
