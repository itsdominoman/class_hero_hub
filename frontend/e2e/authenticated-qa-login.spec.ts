import { expect, test } from '@playwright/test';
import { setupQaParentSession } from './qa-support';

test.describe('Europe dev authenticated QA login', () => {
  test('logs in through the dev-only QA helper and loads the parent dashboard', async ({ page }) => {
    await setupQaParentSession(page);
    await page.goto('/');

    await page.goto('/parent', { waitUntil: 'networkidle' });

    await expect(page.getByRole('heading', { name: 'My Family' })).toBeVisible();
    await expect(page.getByText('QA Parent', { exact: false })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Allowance setup' })).toBeVisible();

    await page.getByRole('link', { name: 'Allowance setup' }).click();
    await expect(page).toHaveURL(/\/allowance$/);
    await expect(page.getByRole('heading', { name: 'Allowance setup' })).toBeVisible();
    const main = page.locator('main');
    await expect(
      page.getByText('Allowance is optional. Pick a child, choose an amount, and set the point goal. Turning on allowance gives your child’s current points an allowance value. You can adjust their points before enabling allowance if needed. Rewards and custom requests spend the same available balance, and nothing is paid automatically.', {
        exact: true
      })
    ).toBeVisible();
    await expect(main).toContainText('Rewards and custom requests spend the same available balance');
    await expect(page.locator('#child-select')).toBeVisible();
    await expect(main).toContainText('Available allowance balance');
    await expect(main).toContainText('Turning on allowance gives your child’s current points an allowance value');
    await expect(main).toContainText('Enable allowance-linked points');
  });
});
