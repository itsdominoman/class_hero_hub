import { expect, test, type Page, type Route } from '@playwright/test';

async function json(route: Route, body: unknown) {
  await route.fulfill({ contentType: 'application/json', body: JSON.stringify(body) });
}

async function mockSchoolSetup(page: Page, mixedRole = false, locale = 'en') {
  await page.addInitScript((language) => {
    localStorage.setItem('familyHeroHub.language', language);
  }, locale);

  const memberships = [
    { membership_id: 102, school_id: 7, school_name: 'Menu Test School', role: 'school_admin' },
    ...(mixedRole
      ? [
          { membership_id: 101, school_id: 7, school_name: 'Menu Test School', role: 'guardian' },
          { membership_id: 103, school_id: 7, school_name: 'Menu Test School', role: 'teacher' }
        ]
      : [])
  ];

  await page.route('**/api/**', async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith('/api/me') || path.endsWith('/api/me/v2')) {
      await json(route, { id: 5, name: 'Menu Test User', is_platform_admin: mixedRole, memberships });
      return;
    }
    if (path.endsWith('/safeguarding/availability') || path.endsWith('/school/surveys/availability')) {
      await json(route, { available: true });
      return;
    }
    if (path.endsWith('/messaging/unread-count')) {
      await json(route, { total: 0, conversations: 0 });
      return;
    }
    if (path.endsWith('/school/settings')) {
      await json(route, { grade_level_label: 'Grade' });
      return;
    }
    if (path.endsWith('/school/feature-controls')) {
      await json(route, {});
      return;
    }
    if (path.endsWith('/school/setup-checklist')) {
      await json(route, { items: [], complete: false });
      return;
    }
    if (path.endsWith('/school/teachers/assignments')) {
      await json(route, {});
      return;
    }
    if (path.endsWith('/school/teachers')) {
      await json(route, { teachers: [], pending_invites: [] });
      return;
    }
    if (path.endsWith('/school/announcements')) {
      await json(route, { announcements: [] });
      return;
    }
    if (path.endsWith('/school/messaging-policy')) {
      await json(route, {
        enabled: true,
        guardian_replies_enabled: true,
        delivery_receipts_visible: true,
        read_receipts_visible: true,
        allow_staff_out_of_hours_opt_in: false,
        teachers_may_mark_urgent: false,
        contact_hours_enabled: false,
        notification_delay_mode: 'delay_notifications_only',
        notification_preview_mode: 'generic',
        retention_days: 365,
        email_mode: 'off',
        policy_version: 1
      });
      return;
    }
    if (path.endsWith('/school/messaging-contact-hours')) {
      await json(route, {
        school_id: 7,
        school_timezone: 'Asia/Muscat',
        policy_version: 1,
        enabled: false,
        notification_delay_mode: 'delay_notifications_only',
        allow_staff_out_of_hours_opt_in: false,
        teachers_may_mark_urgent: false,
        weekly_windows: [],
        exceptions: []
      });
      return;
    }
    if (path.endsWith('/school/points-notification-policy')) {
      await json(route, {
        school_id: 7,
        school_timezone: 'Asia/Muscat',
        mode: 'off',
        daily_enabled: false,
        weekly_enabled: false,
        monthly_enabled: false,
        week_starts_on: 1,
        week_ends_on: 7,
        weekly_summary_day: 7,
        daily_summary_time: '15:00:00',
        weekly_summary_time: '15:00:00',
        monthly_summary_time: '15:00:00',
        policy_version: 1
      });
      return;
    }
    await json(route, []);
  });
}

test('school administrator sees the grouped desktop hierarchy and one active item', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await mockSchoolSetup(page);
  await page.goto('/school');

  const navigation = page.locator('nav[aria-label="School setup navigation"]:visible');
  await expect(navigation).toBeVisible({ timeout: 15_000 });
  for (const group of [
    'School structure',
    'Teaching setup',
    'Students',
    'Communication',
    'Behaviour & insights',
    'System'
  ]) {
    await expect(navigation.getByRole('heading', { name: group, exact: true })).toBeVisible();
  }
  await expect(navigation.getByRole('button', { name: 'Checklist', exact: true })).toHaveAttribute('aria-current', 'page');
  await expect(navigation.locator('[aria-current="page"]')).toHaveCount(1);
  await expect(navigation.getByText('Shortcut', { exact: true })).toHaveCount(3);
  await expect(navigation.getByRole('link', { name: 'Reports Shortcut', exact: true })).toHaveAttribute('href', '/school/reports');
  await expect(navigation.getByRole('link', { name: 'Positive recognition Shortcut', exact: true })).toHaveAttribute('href', '/school/recognition');
  await expect(navigation.getByRole('link', { name: 'System & compliance Shortcut', exact: true })).toHaveAttribute('href', '/school/administration');
});

test('mobile School setup uses contained group accordions', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await mockSchoolSetup(page);
  await page.goto('/school');

  const navigation = page.locator('nav[aria-label="School setup navigation"]:visible');
  await expect(navigation).toBeVisible({ timeout: 15_000 });
  await expect(navigation.locator('details')).toHaveCount(6);
  await expect(navigation.getByRole('button', { name: 'Checklist', exact: true })).toBeVisible();
  await navigation.getByText('Behaviour & insights', { exact: true }).click();
  await expect(navigation.getByRole('link', { name: 'Reports Shortcut', exact: true })).toBeVisible();
  await expect(page.locator('html')).toHaveAttribute('dir', 'ltr');
  expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(1);
});

test('Arabic mobile hierarchy preserves RTL labels and destinations', async ({ page }) => {
  await page.setViewportSize({ width: 768, height: 900 });
  await mockSchoolSetup(page, false, 'ar');
  await page.goto('/school');

  const navigation = page.locator('nav[aria-label="تنقل إعداد المدرسة"]:visible');
  await expect(navigation).toBeVisible({ timeout: 15_000 });
  await expect(page.locator('html')).toHaveAttribute('dir', 'rtl');
  await navigation.getByText('السلوك والرؤى', { exact: true }).click();
  await expect(navigation.getByRole('link', { name: 'التقارير اختصار', exact: true })).toHaveAttribute('href', '/school/reports');
  await expect(navigation.getByRole('link', { name: 'التقدير الإيجابي اختصار', exact: true })).toHaveAttribute('href', '/school/recognition');
  expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(1);
});

test('mixed-role administrator retains the same School setup hierarchy', async ({ page }) => {
  await page.setViewportSize({ width: 1024, height: 900 });
  await mockSchoolSetup(page, true);
  await page.goto('/school?tab=behaviour');

  const navigation = page.locator('nav[aria-label="School setup navigation"]:visible');
  await expect(navigation).toBeVisible({ timeout: 15_000 });
  await expect(navigation.getByRole('button', { name: 'Behaviour & points', exact: true })).toHaveAttribute('aria-current', 'page');
  await expect(page.getByRole('link', { name: 'Open reports →', exact: true })).toHaveAttribute('href', '/school/reports');
  await expect(navigation.locator('a')).toHaveCount(5);
  expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(1);
});

for (const width of [390, 768, 1024, 1280, 1440]) {
  for (const locale of ['en', 'ar']) {
    test(`School setup restores a ${locale.toUpperCase()} tab deep link at ${width}px`, async ({ page }) => {
      await page.setViewportSize({ width, height: 900 });
      await mockSchoolSetup(page, true, locale);
      await page.goto('/school?tab=teachers');

      const navigation = page.locator('nav[aria-label]:visible').filter({
        has: page.getByRole('button', {
          name: locale === 'ar' ? 'الموظفون وتكليفات التدريس' : 'Staff & teaching assignments',
          exact: true
        })
      });
      await expect(navigation.getByRole('button', {
        name: locale === 'ar' ? 'الموظفون وتكليفات التدريس' : 'Staff & teaching assignments',
        exact: true
      })).toHaveAttribute('aria-current', 'page');
      await page.reload();
      await expect(page).toHaveURL(/tab=teachers/);
      await expect(page.locator('html')).toHaveAttribute('dir', locale === 'ar' ? 'rtl' : 'ltr');
      expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(1);
    });
  }
}

test('School setup tab changes support browser and Android Back hierarchy', async ({ page }) => {
  await page.setViewportSize({ width: 1024, height: 900 });
  await mockSchoolSetup(page, true);
  await page.goto('/school');

  const navigation = page.locator('nav[aria-label="School setup navigation"]:visible');
  await navigation.getByText('Behaviour & insights', { exact: true }).click();
  await navigation.getByRole('button', { name: 'Behaviour & points', exact: true }).click();
  await expect(page).toHaveURL(/tab=behaviour/);
  await page.goBack();
  await expect(page).not.toHaveURL(/tab=/);
  await expect(navigation.getByRole('button', { name: 'Checklist', exact: true })).toHaveAttribute('aria-current', 'page');
  await page.goForward();
  await expect(page).toHaveURL(/tab=behaviour/);

  const handled = await page.evaluate(() =>
    !window.dispatchEvent(new CustomEvent('chh:native-back', { cancelable: true }))
  );
  expect(handled).toBe(true);
  await expect(page).not.toHaveURL(/tab=behaviour/);
});
