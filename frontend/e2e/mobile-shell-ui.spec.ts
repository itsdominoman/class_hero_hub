import { expect, test, type Locator, type Page, type Route } from '@playwright/test';

async function json(route: Route, body: unknown) {
  await route.fulfill({
    contentType: 'application/json',
    body: JSON.stringify(body)
  });
}

const BOUNDED_NATIVE_VIEWPORT_HEIGHT = 772;

async function emulateAndroidShell(page: Page) {
  await page.addInitScript(() => {
    Object.assign(window, { androidBridge: {} });
    Object.assign(globalThis, {
      Capacitor: {
        PluginHeaders: [
          {
            name: 'SecureStorage',
            methods: [
              { name: 'get', rtype: 'promise' },
              { name: 'set', rtype: 'promise' },
              { name: 'remove', rtype: 'promise' }
            ]
          },
          {
            name: 'App',
            methods: [
              { name: 'addListener', rtype: 'callback' },
              { name: 'removeListener', rtype: 'callback' },
              { name: 'exitApp', rtype: 'promise' }
            ]
          }
        ],
        nativePromise: async (plugin: string, method: string, options: { key?: string } = {}) => {
          if (plugin === 'SecureStorage' && method === 'get') {
            return { value: options.key === 'chh_access_token' ? 'playwright-native-token' : null };
          }
          return {};
        },
        nativeCallback: () => 'playwright-listener'
      }
    });
    localStorage.setItem('familyHeroHub.language', 'en');
  });
}

async function mockTeacherDashboard(page: Page) {
  const membership = {
    membership_id: 51,
    school_id: 7,
    school_name: 'Al Noor School',
    role: 'teacher'
  };
  await page.route('**/api/me', (route) => json(route, {
    id: 5,
    name: 'Teacher One',
    is_platform_admin: false,
    memberships: [membership]
  }));
  await page.route('**/api/me/v2', (route) => json(route, {
    id: 5,
    memberships: [membership]
  }));
  await page.route('**/api/messaging/unread-count', (route) => json(route, {
    total: 0,
    conversations: 0
  }));
  await page.route('**/api/teach/dashboard', (route) => json(route, {
    schools: [{ id: 7, name: 'Al Noor School' }],
    assignments: Array.from({ length: 18 }, (_, index) => ({
      id: index + 1,
      role: 'homeroom',
      target_type: 'class_section',
      school: { id: 7, name: 'Al Noor School' },
      class_section: { id: index + 20, name: `${index + 1}A`, code: `${index + 1}A` },
      subject_group: null,
      branch: { name: 'Main' },
      academic_year: { name: '2026/27' },
      grade_level: { name: `Grade ${index + 1}` },
      subject: null,
      valid_from: '2026-07-19'
    }))
  }));
  await page.route('**/api/teach/announcements**', (route) => json(route, { items: [] }));
}

test('native teacher shell stays fixed and scrolls terminal controls within its bounded viewport', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: BOUNDED_NATIVE_VIEWPORT_HEIGHT });
  await emulateAndroidShell(page);
  await mockTeacherDashboard(page);
  await page.goto('/teach');

  await expect(page.getByRole('heading', { name: 'My classes' })).toBeVisible();
  const header = page.locator('.app-header');
  const logo = header.getByRole('img', { name: 'Class Hero Hub' });
  const menu = header.getByRole('button', { name: 'Open menu' });
  const appMain = page.locator('.app-main');
  const lastClass = page.getByRole('link', { name: 'Grade 18 Home Room Main' });
  await expect(lastClass).toBeAttached();

  const beforeHeader = await header.boundingBox();
  const shellMetrics = await appMain.evaluate((element) => {
    const style = getComputedStyle(element);
    element.scrollTop = element.scrollHeight;
    element.dispatchEvent(new Event('scroll'));
    return {
      overflowY: style.overflowY,
      scrollTop: element.scrollTop,
      scrollHeight: element.scrollHeight,
      clientHeight: element.clientHeight,
      documentScroll: window.scrollY
    };
  });
  expect(shellMetrics.overflowY).toBe('auto');
  expect(shellMetrics.scrollHeight).toBeGreaterThan(shellMetrics.clientHeight);
  expect(shellMetrics.scrollTop).toBeGreaterThan(0);
  expect(shellMetrics.documentScroll).toBe(0);

  const afterHeader = await header.boundingBox();
  expect(afterHeader?.y).toBeCloseTo(beforeHeader?.y || 0, 0);
  expect((await logo.boundingBox())?.y).toBeGreaterThanOrEqual(0);
  await expect(menu).toBeVisible();
  const lastBox = await lastClass.boundingBox();
  expect((lastBox?.y || 0) + (lastBox?.height || 0)).toBeLessThanOrEqual(BOUNDED_NATIVE_VIEWPORT_HEIGHT - 12);

  await menu.click();
  const drawer = page.locator('#mobile-navigation');
  const logout = drawer.getByRole('button', { name: 'Logout' });
  const close = drawer.getByRole('button', { name: 'Close menu' });
  await drawer.evaluate((element) => { element.scrollTop = element.scrollHeight; });
  await expect(close).toBeAttached();
  await expect(logout).toBeVisible();
  const logoutBox = await logout.boundingBox();
  expect((logoutBox?.y || 0) + (logoutBox?.height || 0)).toBeLessThanOrEqual(BOUNDED_NATIVE_VIEWPORT_HEIGHT - 12);
});

async function mockAuthenticatedRouteAudit(page: Page) {
  const teacherMembership = {
    membership_id: 51,
    school_id: 7,
    school_name: 'Al Noor School',
    role: 'teacher'
  };
  const adminMembership = {
    membership_id: 52,
    school_id: 7,
    school_name: 'Al Noor School',
    role: 'school_admin'
  };
  const memberships = [teacherMembership, adminMembership];
  await page.route('**/api/**', async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname;
    if (path.endsWith('/api/me') || path.endsWith('/api/me/v2')) {
      await json(route, { id: 5, name: 'Teacher Admin', is_platform_admin: false, memberships });
      return;
    }
    if (path.endsWith('/messaging/unread-count')) {
      await json(route, { total: 0, conversations: 0 });
      return;
    }
    if (path.endsWith('/teach/dashboard')) {
      await json(route, {
        schools: [{ id: 7, name: 'Al Noor School' }],
        assignments: Array.from({ length: 18 }, (_, index) => ({
          id: index + 1,
          role: 'homeroom',
          target_type: 'class_section',
          school: { id: 7, name: 'Al Noor School' },
          class_section: { id: index + 20, name: `${index + 1}A`, code: `${index + 1}A` },
          subject_group: null,
          branch: { name: 'Main' },
          academic_year: { name: '2026/27' },
          grade_level: { name: `Grade ${index + 1}` },
          subject: null,
          valid_from: '2026-07-19'
        }))
      });
      return;
    }
    if (path.endsWith('/teach/assignments/77')) {
      await json(route, {
        assignment: {
          id: 77,
          role: 'homeroom',
          target_type: 'class_section',
          school: { id: 7, name: 'Al Noor School' },
          class_section: { id: 12, name: 'KG1A' },
          subject_group: null,
          subject: null,
          branch: { id: 1, name: 'Main' },
          academic_year: { id: 1, name: '2026/27' },
          grade_level: { id: 2, name: 'KG1' }
        },
        student_count: 30,
        students: Array.from({ length: 30 }, (_, index) => ({
          id: index + 1,
          first_name: `Student ${index + 1}`,
          last_name: 'Audit',
          display_name: `Student ${index + 1} Audit`,
          avatar_url_256: null,
          points_total: index
        }))
      });
      return;
    }
    if (path.endsWith('/teach/behaviour/quick-actions')) {
      await json(route, {
        quick_actions: { positive: [], needs_work: [] },
        other_actions: { positive: [], needs_work: [] }
      });
      return;
    }
    if (path.endsWith('/teach/homework')) {
      await json(route, { items: [] });
      return;
    }
    if (path.endsWith('/teach/announcements')) {
      await json(route, { items: [] });
      return;
    }
    if (path.endsWith('/school/settings')) {
      await json(route, { grade_level_label: 'Grade' });
      return;
    }
    if (path.endsWith('/school/feature-controls')) {
      await json(route, {
        voice_notes: {
          feature: 'voice_notes', enabled: false, control_version: 1,
          disclosure_version: '2026-07', acknowledgement_items: []
        }
      });
      return;
    }
    if (path.endsWith('/school/setup-checklist')) {
      await json(route, {
        complete: false,
        items: Array.from({ length: 24 }, (_, index) => ({
          key: `setup-${index + 1}`,
          label: `Setup card ${index + 1}`,
          count: index,
          complete: false,
          required: true
        }))
      });
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
    if (path.endsWith('/school/behaviour/categories')) {
      await json(route, { categories: [] });
      return;
    }
    if (path.includes('/school/reports/behaviour/overview')) {
      await json(route, {
        metrics: {
          total_events: 1, positive_count: 1, needs_work_count: 0,
          positive_ratio: 1, signed_points_total: 1, active_students: 1, active_teachers: 1
        },
        filters: {}
      });
      return;
    }
    if (path.includes('/school/reports/behaviour/trends')) {
      await json(route, { series: [] });
      return;
    }
    if (path.includes('/school/reports/behaviour/breakdowns')) {
      await json(route, { grades: [], classes: [], subjects: [], duty_contexts: [], categories: [] });
      return;
    }
    if (path.includes('/school/reports/behaviour/students')) {
      await json(route, { repeated_needs_work: [], top_positive: [], improving: [], worsening: [] });
      return;
    }
    if (path.includes('/school/reports/behaviour/teachers')) {
      await json(route, { teachers: [] });
      return;
    }
    if (
      path.endsWith('/school/branches') ||
      path.endsWith('/school/education-stages') ||
      path.endsWith('/school/academic-years') ||
      path.endsWith('/school/grade-levels') ||
      path.endsWith('/school/class-sections') ||
      path.endsWith('/school/subjects') ||
      path.endsWith('/school/subject-groups') ||
      path.endsWith('/school/default-subject-templates')
    ) {
      await json(route, []);
      return;
    }
    if (path.endsWith('/school/announcements')) {
      await json(route, { announcements: [] });
      return;
    }
    await route.fulfill({ status: 404, json: { detail: `Unmocked ${path}` } });
  });
}

async function scrollShellToEnd(page: Page) {
  await page.locator('.app-main').evaluate((element) => {
    element.scrollTop = element.scrollHeight;
    element.dispatchEvent(new Event('scroll'));
  });
}

async function expectAboveNavigation(locator: Locator) {
  const box = await locator.boundingBox();
  expect(box).not.toBeNull();
  expect((box?.y || 0) + (box?.height || 0)).toBeLessThanOrEqual(BOUNDED_NATIVE_VIEWPORT_HEIGHT - 12);
}

test('bounded native route scroller keeps final class, student, setup, and Reporting controls reachable', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: BOUNDED_NATIVE_VIEWPORT_HEIGHT });
  await emulateAndroidShell(page);
  await mockAuthenticatedRouteAudit(page);

  await page.goto('/teach', { waitUntil: 'domcontentloaded' });
  await expect(page.getByRole('heading', { name: 'My classes' })).toBeVisible();
  const finalClass = page.locator('a[href="/teach/assignments/18"]').first();
  await expect(finalClass).toBeAttached();
  await scrollShellToEnd(page);
  await expectAboveNavigation(finalClass);

  await page.goto('/teach/assignments/77', { waitUntil: 'domcontentloaded' });
  const finalStudent = page.getByRole('button', { name: 'Award behaviour to Student 30 Audit' });
  await expect(finalStudent).toBeAttached();
  await scrollShellToEnd(page);
  await expectAboveNavigation(finalStudent);

  await page.goto('/school', { waitUntil: 'domcontentloaded' });
  const finalSetupCard = page.getByRole('heading', { name: 'Setup card 24' }).locator('..').locator('..');
  await expect(finalSetupCard).toBeAttached();
  await scrollShellToEnd(page);
  await expectAboveNavigation(finalSetupCard);

  await page.getByRole('button', { name: 'Settings' }).click();
  const finalSetupControl = page.getByRole('button', { name: 'Enable voice notes' });
  await expect(finalSetupControl).toBeAttached();
  await scrollShellToEnd(page);
  await expectAboveNavigation(finalSetupControl);

  await page.goto('/school/reports', { waitUntil: 'domcontentloaded' });
  const finalReportControl = page.locator('.report-launcher').last();
  await expect(finalReportControl).toBeAttached();
  await scrollShellToEnd(page);
  await expectAboveNavigation(finalReportControl);
});
