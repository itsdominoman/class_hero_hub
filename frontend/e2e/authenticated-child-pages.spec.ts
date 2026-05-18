import { expect, test } from '@playwright/test';
import { setupQaChildSession } from './qa-support';

test.describe('Europe dev authenticated child QA', () => {
  test('loads the seeded child dashboard from the real child session helper', async ({ page }) => {
    const childSession = await setupQaChildSession(page);

    await page.goto(childSession.childRoute, { waitUntil: 'networkidle' });
    await page.waitForTimeout(200);

    await expect(page.getByRole('heading', { name: childSession.childName })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Choose a reward' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Ask to spend your points' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Points log' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Waiting requests' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Savings snapshot' })).toBeVisible();
    await expect(page.getByText('Your current points are worth', { exact: false })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'QA Reward Very Long Name Designed To Stress Mobile Card Wrapping' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'QA Reward Long Description Stress Case' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'QA Pending Request' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'QA Waiting Request' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'QA Task Pack Bag' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'QA Event Piano Lesson' })).toBeVisible();
    await expect(page.getByText('QA School Bag Pack', { exact: false })).toBeVisible();
    await expect(page.getByText('QA School Bag Piano', { exact: false })).toBeVisible();

    await expect(page.getByRole('heading', { name: /^QA Reward / })).toHaveCount(4);
    await expect(page.getByRole('button', { name: 'Mark done' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Request' }).first()).toBeVisible();
  });
});
