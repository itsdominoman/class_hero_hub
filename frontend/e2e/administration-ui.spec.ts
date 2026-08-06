import { expect, test, type Page } from '@playwright/test';

const adminMembership = { school_id: 1, membership_id: 10, school_name: 'Test School', role: 'school_admin' };
const teacherMembership = { school_id: 1, membership_id: 20, school_name: 'Test School', role: 'teacher' };

const governance = (isOwner: boolean) => ({
  is_current_owner: isOwner,
  recovery_required: false,
  owner_version: 2,
  owner: { membership_id: 10, display_name: 'Amina Owner', display_name_ar: 'أمينة المالكة', role: 'school_admin', membership_status: 'active' },
  staff: [
    { membership_id: 10, display_name: 'Amina Owner', display_name_ar: 'أمينة المالكة', role: 'school_admin', membership_status: 'active' },
    { membership_id: 11, display_name: 'Bilal Admin', display_name_ar: 'بلال المسؤول', role: 'school_admin', membership_status: 'active' },
    { membership_id: 20, display_name: 'Carol Teacher', display_name_ar: 'كارول المعلمة', role: 'teacher', membership_status: 'inactive' }
  ]
});

async function mockApis(page: Page, membership: typeof adminMembership | typeof teacherMembership, isOwner = false) {
  await page.route('**/api/**', async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname === '/api/me') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ user: { id: 1, name: 'User' }, is_platform_admin: false, memberships: [membership] }) });
    }
    if (url.pathname === '/api/school/governance') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(governance(isOwner)) });
    }
    return route.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ detail: 'Not available in UI test' }) });
  });
}

test('teacher does not see specialist administration while an ordinary administrator sees only compliance controls', async ({ page }) => {
  await mockApis(page, teacherMembership);
  await page.goto('/');
  await expect(page.getByRole('link', { name: 'System & compliance' })).not.toBeVisible();

  await page.unroute('**/api/**');
  await mockApis(page, adminMembership, false);
  await page.goto('/school/administration');
  await expect(page.getByRole('link', { name: /Compliance \/ Feature controls/ })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Compliance / Feature controls' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'System status' })).not.toBeVisible();
  await expect(page.getByRole('heading', { name: 'Advanced operations' })).not.toBeVisible();
  await expect(page.getByRole('heading', { name: 'System Owner' })).not.toBeVisible();
});

test('System Owner sees Governance while infrastructure panels remain absent', async ({ page }) => {
  await mockApis(page, adminMembership, true);
  await page.goto('/school/administration');
  await expect(page.getByRole('heading', { name: 'System Owner' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'System status' })).not.toBeVisible();
  await expect(page.getByRole('heading', { name: 'Advanced operations' })).not.toBeVisible();
});

test('Governance uses one locale, filters the School staff roster, and fits 360px', async ({ page }) => {
  await mockApis(page, adminMembership, true);
  await page.setViewportSize({ width: 360, height: 800 });
  await page.addInitScript(() => localStorage.setItem('familyHeroHub.language', 'ar'));
  await page.goto('/school/governance');

  await expect(page.locator('html')).toHaveAttribute('dir', 'rtl');
  await expect(page.getByRole('heading', { name: 'مالك النظام', exact: true })).toBeVisible();
  await expect(page.getByText('System Owner', { exact: true })).toHaveCount(0);
  await expect(page.getByRole('heading', { name: 'سجل موظفي المدرسة' })).toBeVisible();

  const roster = page.getByRole('heading', { name: 'سجل موظفي المدرسة' }).locator('..');
  await page.getByPlaceholder('البحث بالاسم').fill('كارول');
  await expect(roster.getByText('كارول المعلمة')).toBeVisible();
  await expect(roster.getByText('أمينة المالكة')).not.toBeVisible();
  await page.getByRole('combobox', { name: 'الحالة' }).selectOption('active');
  await expect(page.getByText('لا يوجد موظفون مطابقون لهذه عوامل التصفية.')).toBeVisible();

  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});

test('retired infrastructure routes remain unavailable to the System Owner', async ({ page }) => {
  await mockApis(page, adminMembership, true);
  await page.setViewportSize({ width: 360, height: 800 });
  await page.goto('/school/operations');
  await expect(page.getByRole('heading', { name: '404' })).toBeVisible();
  await page.goto('/school/operations/advanced');
  await expect(page.getByRole('heading', { name: '404' })).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});
