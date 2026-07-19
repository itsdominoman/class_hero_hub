import { expect, test, type Page, type Route } from '@playwright/test';

async function json(route: Route, body: unknown) {
  await route.fulfill({
    contentType: 'application/json',
    body: JSON.stringify(body)
  });
}

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

test('native teacher shell keeps the safe-area header fixed and the last class above Android navigation', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await emulateAndroidShell(page);
  await mockTeacherDashboard(page);
  await page.goto('/teach');
  await page.addStyleTag({
    content: ':root { --safe-top: 24px !important; --safe-bottom: 48px !important; }'
  });

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
  expect((await logo.boundingBox())?.y).toBeGreaterThanOrEqual(24);
  await expect(menu).toBeVisible();
  const lastBox = await lastClass.boundingBox();
  expect((lastBox?.y || 0) + (lastBox?.height || 0)).toBeLessThanOrEqual(844 - 47);
});
