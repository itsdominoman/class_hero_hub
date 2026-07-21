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

const health = {
  jobs: { pending: 2, dead: 0 },
  notification_outbox: { pending: 1, dead: 0 },
  oldest_notification_age_seconds: 20,
  worker_heartbeats: [{ worker: 'worker-1', last_seen_at: '2026-07-21T08:00:00Z' }],
  archive_disk_used_percent: 76,
  backup_marker_age_seconds: 3600,
  alerts: {
    dead_jobs: false,
    dead_notifications: false,
    worker_stale: false,
    notification_backlog_old: false,
    archive_disk_high: false,
    database_pool_high: false,
    backup_marker_stale_or_missing: false
  }
};

async function mockApis(page: Page, membership: typeof adminMembership | typeof teacherMembership, isOwner = false) {
  await page.route('**/api/**', async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname === '/api/me') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ user: { id: 1, name: 'User' }, is_platform_admin: false, memberships: [membership] }) });
    }
    if (url.pathname === '/api/school/governance') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(governance(isOwner)) });
    }
    if (url.pathname === '/api/school/operations') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ health }) });
    }
    if (url.pathname === '/api/school/operations/advanced') {
      if (!isOwner) return route.fulfill({ status: 403, contentType: 'application/json', body: JSON.stringify({ detail: 'Current System Owner authority is required' }) });
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          health,
          active_retention_policy: { version: 3, effective_at: '2026-07-20T08:00:00Z', rules: { message_days: 2557, export_artifact_minutes: 30, delete_hot_after_verified_archive: true } },
          jobs: [{ id: 'job-1', job_type: 'retention_preview', state: 'succeeded', attempt_count: 1, created_at: '2026-07-21T08:00:00Z', progress: { messages: 4, message_body_bytes: 1024, preview_sha256: 'a'.repeat(64) } }],
          failed_notifications: []
        })
      });
    }
    return route.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ detail: 'Not available in UI test' }) });
  });
}

test('teacher does not see Administration while an ordinary administrator sees only authorised cards', async ({ page }) => {
  await mockApis(page, teacherMembership);
  await page.goto('/');
  await expect(page.getByRole('link', { name: 'Administration' })).not.toBeVisible();

  await page.unroute('**/api/**');
  await mockApis(page, adminMembership, false);
  await page.goto('/school/administration');
  await expect(page.getByRole('link', { name: 'Administration' }).first()).toBeVisible();
  await expect(page.getByRole('heading', { name: 'System status' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Compliance / Feature controls' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Advanced operations' })).not.toBeVisible();
  await expect(page.getByRole('heading', { name: 'System Owner' })).not.toBeVisible();
});

test('System Owner sees Governance and Advanced operations without raw payloads on System status', async ({ page }) => {
  await mockApis(page, adminMembership, true);
  await page.goto('/school/administration');
  await expect(page.getByRole('heading', { name: 'System Owner' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Advanced operations' })).toBeVisible();

  await page.goto('/school/operations');
  await expect(page.getByRole('heading', { name: 'System status' })).toBeVisible();
  await expect(page.getByText('Archive storage is 76.0% full')).toBeVisible();
  await expect(page.locator('pre')).toHaveCount(0);
  await expect(page.getByText('preview_sha256')).toHaveCount(0);
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

test('Advanced operations keeps technical JSON behind disclosures and actions deliberate at 360px', async ({ page }) => {
  await mockApis(page, adminMembership, true);
  await page.setViewportSize({ width: 360, height: 800 });
  await page.goto('/school/operations/advanced');
  await expect(page.getByRole('heading', { name: 'Advanced operations' })).toBeVisible();
  await expect(page.getByText('preview_sha256')).not.toBeVisible();
  await expect(page.getByRole('button', { name: 'Execute confirmed preview' })).not.toBeVisible();
  await page.getByText('Advanced actions', { exact: true }).click();
  const execute = page.getByRole('button', { name: 'Execute confirmed preview' });
  await expect(execute).toBeDisabled();
  await page.getByLabel('Operator reason').fill('Verified maintenance window');
  await page.getByText('I understand this action may change retained data or operational queue state.').click();
  await expect(execute).toBeEnabled();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});
