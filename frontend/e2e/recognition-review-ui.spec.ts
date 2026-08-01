import { expect, test, type Page, type Route } from '@playwright/test';

const membership = {
  membership_id: 51,
  school_id: 7,
  school_name: 'Recognition Test School',
  role: 'school_admin'
};

const reviewSummary = {
  id: 700,
  config_id: 90,
  period_start: '2026-07-01',
  period_end: '2026-07-07',
  status: 'draft',
  generated_at: '2026-07-08T08:00:00Z',
  criteria: {
    recognition_name: 'Star of the Week',
    scope: { type: 'class', id: 12, name: '4A' },
    review_period_days: 7,
    minimum_positive_points: 1,
    shortlist_size: 50,
    certificate_title: 'Star of the Week',
    signatory_text: 'Head of School',
    needs_work_safeguard: { enabled: true, maximum_allowed_events: 0, categories: [] }
  }
};

const candidates = Array.from({ length: 50 }, (_, index) => ({
  id: index + 1,
  student_id: 100 + index,
  student_name: `Candidate ${String(index + 1).padStart(2, '0')}`,
  student_name_ar: `المرشح ${String(index + 1).padStart(2, '0')}`,
  branch_name: 'Main',
  grade_name: 'Grade 4',
  class_name: '4A',
  positive_points_total: index < 8 ? 20 : 19 - Math.floor(index / 5),
  positive_event_count: index < 8 ? 5 : 4,
  category_totals: [{ id: 8, label: 'Kindness', points: index < 8 ? 20 : 10, events: 4 }],
  rank: index < 8 ? 1 : index - 6,
  is_excluded: false,
  safeguard_excluded: index === 1,
  safeguard_counted_total: index === 1 ? 1 : 0,
  safeguard_category_totals: index === 1 ? [{ id: 9, label: 'Disruption', events: 1 }] : [],
  safeguard_overridden: false,
  is_eligible: index !== 1
}));

async function json(route: Route, body: unknown, status = 200) {
  await route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
}

async function mockRecognition(page: Page) {
  await page.route('**/api/**', async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path === '/api/me' || path === '/api/me/v2') {
      return json(route, { id: 5, name: 'Recognition Administrator', is_platform_admin: false, memberships: [membership] });
    }
    if (path.endsWith('/school/surveys/availability') || path.endsWith('/safeguarding/availability')) {
      return json(route, { available: false });
    }
    if (path.endsWith('/messaging/unread-count')) return json(route, { total: 0, conversations: 0 });
    if (path.endsWith('/school/recognition/options')) {
      return json(route, { branches: [], grades: [], classes: [], positive_categories: [], needs_work_categories: [] });
    }
    if (path.endsWith('/school/recognition/configs')) return json(route, { configs: [] });
    if (path.endsWith('/school/recognition/reviews/700')) {
      return json(route, { ...reviewSummary, candidates });
    }
    if (path.endsWith('/school/recognition/reviews')) return json(route, { reviews: [reviewSummary] });
    return json(route, { detail: 'Not available in recognition usability test' }, 404);
  });
}

const widths = [390, 768, 1024, 1280, 1440];
const locales = [
  { code: 'en', list: 'Recognition shortlist candidates', summary: 'Decision summary', selected: 'Selected recipient', confirm: 'Confirm selected recipient' },
  { code: 'ar', list: 'قائمة المرشحين للتقدير', summary: 'ملخص القرار', selected: 'المستلم المختار', confirm: 'تأكيد المستلم المحدد' }
] as const;

for (const width of widths) {
  for (const language of locales) {
    test(`large tied shortlist remains bounded and actionable in ${language.code.toUpperCase()} at ${width}px`, async ({ page }) => {
      const height = width <= 768 ? 844 : 900;
      await page.setViewportSize({ width, height });
      await page.addInitScript((code) => localStorage.setItem('familyHeroHub.language', code), language.code);
      await mockRecognition(page);
      await page.goto('/school/recognition?review=700');

      const decision = page.locator('section[aria-labelledby="recognition-decision-title"]');
      const list = page.getByRole('list', { name: language.list });
      const controls = decision.locator('.recognition-decision-controls');
      await expect(list.getByRole('listitem')).toHaveCount(50);
      await expect(controls.getByRole('heading', { name: language.summary })).toBeVisible();
      await expect(list.getByText(/shared rank 1|الترتيب المشترك 1/).first()).toBeVisible();

      const listBox = await list.boundingBox();
      const decisionBox = await decision.boundingBox();
      expect(listBox).not.toBeNull();
      expect(decisionBox).not.toBeNull();
      expect(listBox!.height).toBeLessThanOrEqual(Math.min(height * 0.65, 704) + 3);
      expect(decisionBox!.height).toBeLessThan(1500);

      await list.getByRole('listitem').first().getByText(/Positive and staff-only evidence|الأدلة الإيجابية والأدلة الخاصة بالموظفين/).click();
      await expect(list.getByText('Kindness: 20 / 4').first()).toBeVisible();

      await list.evaluate((element) => { element.scrollTop = element.scrollHeight; });
      const lastCandidate = list.getByRole('listitem').last();
      await lastCandidate.getByRole('radio').check();
      await expect(controls.getByText(language.selected, { exact: true })).toBeVisible();
      await expect(controls.getByText(language.code === 'ar' ? 'المرشح 50' : 'Candidate 50')).toBeVisible();
      await expect(controls.getByRole('button', { name: language.confirm })).toBeEnabled();

      if (width >= 1280) {
        await expect.poll(() => controls.evaluate((element) => getComputedStyle(element).position)).toBe('sticky');
      }
      expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(1);
      await expect(page.locator('html')).toHaveAttribute('dir', language.code === 'ar' ? 'rtl' : 'ltr');
    });
  }
}
