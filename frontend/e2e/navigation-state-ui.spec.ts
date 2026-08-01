import { expect, test, type Page, type Route } from '@playwright/test';

const membership = {
  membership_id: 51,
  school_id: 7,
  school_name: 'State Test School',
  role: 'school_admin'
};

async function json(route: Route, body: unknown, status = 200) {
  await route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
}

function session() {
  return { id: 5, name: 'State Test Administrator', is_platform_admin: false, memberships: [membership] };
}

async function commonRoute(route: Route) {
  const path = new URL(route.request().url()).pathname;
  if (path === '/api/me' || path === '/api/me/v2') {
    await json(route, session());
    return true;
  }
  if (path.endsWith('/school/surveys/availability') || path.endsWith('/safeguarding/availability')) {
    await json(route, { available: false });
    return true;
  }
  if (path.endsWith('/messaging/unread-count')) {
    await json(route, { total: 0, conversations: 0 });
    return true;
  }
  return false;
}

async function mockReports(page: Page) {
  await page.route('**/api/**', async (route) => {
    if (await commonRoute(route)) return;
    const url = new URL(route.request().url());
    const path = url.pathname;
    if (path.endsWith('/school/grade-levels')) return json(route, [{ id: 2, name: 'Grade 4', status: 'active' }]);
    if (path.endsWith('/school/class-sections')) return json(route, [{ id: 12, name: '4A', grade_level_id: 2, status: 'active' }]);
    if (path.endsWith('/school/subjects')) return json(route, [{ id: 3, name: 'English', status: 'active' }]);
    if (path.endsWith('/school/behaviour/categories')) return json(route, { categories: [{ id: 8, label: 'Kindness', type: 'positive' }] });
    if (path.endsWith('/school/teachers')) return json(route, { teachers: [] });
    if (path.endsWith('/school/reports/behaviour/overview')) {
      return json(route, {
        metrics: {
          total_events: 3,
          positive_count: 3,
          needs_work_count: 0,
          positive_ratio: 1,
          active_students: 1,
          active_teachers: 1,
          signed_points_total: 3
        },
        filters: {
          date_from: url.searchParams.get('date_from') || '2026-07-01',
          date_to: url.searchParams.get('date_to') || '2026-07-31'
        }
      });
    }
    if (path.endsWith('/school/reports/behaviour/trends')) return json(route, { series: [] });
    if (path.endsWith('/school/reports/behaviour/breakdowns')) {
      return json(route, { classes: [], grades: [], subjects: [], duty_contexts: [], categories: [] });
    }
    if (path.endsWith('/school/reports/behaviour/students')) {
      return json(route, { repeated_needs_work: [], top_positive: [], improving: [], worsening: [] });
    }
    if (path.endsWith('/school/reports/behaviour/teachers')) return json(route, { teachers: [] });
    if (path.endsWith('/school/reports/behaviour/events')) {
      const offset = Number(url.searchParams.get('offset') || 0);
      return json(route, { events: [], pagination: { total: 50, offset } });
    }
    if (path.endsWith('/school/reports/behaviour/matrix')) {
      return json(route, {
        rows: [],
        truncation: { row_limit: 25, rows_truncated: false, columns_truncated: false, max_cells: 100, returned_rows: 0, returned_cells: 0 }
      });
    }
    await json(route, { detail: 'Not available in reports state test' }, 404);
  });
}

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
    shortlist_size: 3,
    certificate_title: 'Star of the Week',
    signatory_text: 'Head of School',
    needs_work_safeguard: { enabled: false, categories: [] }
  }
};

async function mockRecognition(page: Page) {
  await page.route('**/api/**', async (route) => {
    if (await commonRoute(route)) return;
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith('/school/recognition/options')) {
      return json(route, { branches: [], grades: [], classes: [], positive_categories: [], needs_work_categories: [] });
    }
    if (path.endsWith('/school/recognition/configs')) return json(route, { configs: [] });
    if (path.endsWith('/school/recognition/reviews/700')) {
      return json(route, {
        ...reviewSummary,
        candidates: [{
          id: 1,
          student_id: 91,
          student_name: 'Mariam Al Harthy',
          student_name_ar: 'مريم الحارثية',
          branch_name: 'Main',
          grade_name: 'Grade 4',
          class_name: '4A',
          positive_points_total: 3,
          positive_event_count: 3,
          category_totals: [{ id: 8, label: 'Kindness', points: 3, events: 3 }],
          rank: 1,
          is_excluded: false,
          safeguard_excluded: false,
          safeguard_counted_total: 0,
          safeguard_category_totals: [],
          safeguard_overridden: false,
          is_eligible: true
        }]
      });
    }
    if (path.endsWith('/school/recognition/reviews')) return json(route, { reviews: [reviewSummary] });
    await json(route, { detail: 'Not available in recognition state test' }, 404);
  });
}

const student = {
  id: 91,
  external_ref: 'STU-91',
  first_name: 'Mariam',
  last_name: 'Al Harthy',
  display_name: 'Mariam Al Harthy',
  name_ar: 'مريم الحارثية',
  status: 'active',
  current_class_section: { id: 12, code: '4A', name: '4A', status: 'active', branch_campus_id: 1, grade_level_id: 2 }
};

async function mockStudents(page: Page) {
  await page.route('**/api/**', async (route) => {
    if (await commonRoute(route)) return;
    const url = new URL(route.request().url());
    const path = url.pathname;
    if (path.endsWith('/school/branches')) return json(route, [{ id: 1, code: 'MAIN', name: 'Main', status: 'active' }]);
    if (path.endsWith('/school/academic-years')) return json(route, []);
    if (path.endsWith('/school/grade-levels')) return json(route, [{ id: 2, code: 'G4', name: 'Grade 4', status: 'active' }]);
    if (path.endsWith('/school/class-sections')) return json(route, [{ id: 12, code: '4A', name: '4A', status: 'active', branch_campus_id: 1, grade_level_id: 2 }]);
    if (path.endsWith('/school/students/91/enrolments')) return json(route, []);
    if (path.endsWith('/school/students/91/guardian-invites')) return json(route, { contacts: [], invites: [], links: [] });
    if (path.endsWith('/school/students/91/fhh-invites')) return json(route, { invites: [], link_status: 'none', link_history_count: 0, link_history: [] });
    if (path.endsWith('/school/students/91')) return json(route, student);
    if (path.endsWith('/school/students')) {
      const pageNumber = Number(url.searchParams.get('page') || 1);
      return json(route, { items: [student], page: pageNumber, page_size: 25, total: 30, pages: 2 });
    }
    await json(route, { detail: 'Not available in student state test' }, 404);
  });
}

test('Reports restores filters, open sections and browser history', async ({ page }) => {
  await mockReports(page);
  await page.goto('/school/reports?date_from=2026-07-01&category_type=positive&section=events&events_offset=25');

  await expect(page.getByLabel('From date')).toHaveValue('2026-07-01');
  await expect(page.getByLabel('Category type')).toHaveValue('positive');
  await expect(page.getByRole('heading', { name: 'Underlying events' })).toBeVisible();
  await page.reload();
  await expect(page.getByRole('heading', { name: 'Underlying events' })).toBeVisible();

  await page.getByRole('button', { name: 'Back to overview' }).click();
  await expect(page).not.toHaveURL(/section=/);
  await expect(page).toHaveURL(/category_type=positive/);
  await page.getByRole('button', { name: /Class comparison/ }).click();
  await expect(page).toHaveURL(/section=classes/);
  await page.goBack();
  await expect(page).not.toHaveURL(/section=/);
  await page.goForward();
  await expect(page.getByRole('heading', { name: 'Class comparison' })).toBeVisible();
});

test('Recognition review selection supports deep links, refresh and Back/Forward', async ({ page }) => {
  await mockRecognition(page);
  await page.goto('/school/recognition?review=700');

  const decision = page.locator('section[aria-labelledby="recognition-decision-title"]');
  await expect(decision).toBeVisible();
  await page.reload();
  await expect(decision).toBeVisible();
  await decision.getByRole('button', { name: /Recent reviews/ }).click();
  await expect(page).not.toHaveURL(/review=/);

  await page.getByRole('button', { name: /Open review/ }).click();
  await expect(page).toHaveURL(/review=700/);
  await page.goBack();
  await expect(decision).toHaveCount(0);
  await page.goForward();
  await expect(decision).toBeVisible();

  const handled = await page.evaluate(() =>
    !window.dispatchEvent(new CustomEvent('chh:native-back', { cancelable: true }))
  );
  expect(handled).toBe(true);
  await expect(decision).toHaveCount(0);
});

test('Student list and detail URL restore refresh, Back/Forward and Android Back context', async ({ page }) => {
  await mockStudents(page);
  await page.goto('/school/students?search=Mariam&page=2&student=91');

  await expect(page.getByRole('heading', { name: 'Mariam Al Harthy' })).toBeVisible();
  await page.reload();
  await expect(page.getByRole('heading', { name: 'Mariam Al Harthy' })).toBeVisible();
  await page.getByRole('button', { name: /Back to students/ }).click();
  await expect(page).toHaveURL(/search=Mariam/);
  await expect(page).toHaveURL(/page=2/);
  await expect(page).not.toHaveURL(/student=/);

  await page.getByRole('button', { name: /Mariam Al Harthy/ }).click();
  await expect(page).toHaveURL(/student=91/);
  await page.goBack();
  await expect(page).not.toHaveURL(/student=/);
  await page.goForward();
  await expect(page.getByRole('heading', { name: 'Mariam Al Harthy' })).toBeVisible();

  const handled = await page.evaluate(() =>
    !window.dispatchEvent(new CustomEvent('chh:native-back', { cancelable: true }))
  );
  expect(handled).toBe(true);
  await expect(page).not.toHaveURL(/student=/);
});
