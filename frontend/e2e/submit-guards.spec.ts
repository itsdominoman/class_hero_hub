import { expect, test, type Page } from '@playwright/test';

type ChildSummary = {
  child: {
    id: number;
    display_name: string;
    avatar_name: string | null;
    active: boolean;
  };
  spending_balance: number;
  savings_balance: number;
  locked_savings: number;
  available_savings: number;
  available_spending: number;
  pending_redemptions: number;
  pet_progress: {
    current_stage: 'egg';
    lifetime_points: number;
  };
  savings_unlock_schedule: [];
};

type Preset = {
  id: number;
  family_id: number;
  parent_id: number;
  title: string;
  description: string;
  icon: string;
  points: number;
  is_active: boolean;
};

type Redemption = {
  id: number;
  child_id: number;
  child_name: string;
  points: number;
  title: string;
  description: string;
  status: 'pending' | 'approved' | 'rejected';
  parent_note: string | null;
  created_at: string;
  reviewed_at: string | null;
};

type DashboardFixture = {
  parent: Record<string, unknown>;
  children: ChildSummary[];
  presets: Preset[];
  redemptions: Redemption[];
  rewards: any[];
  familyMembers: any[];
  familyInvites: any[];
};

type Deferred<T> = {
  promise: Promise<T>;
  resolve: (value: T | PromiseLike<T>) => void;
};

function createDeferred<T>(): Deferred<T> {
  let resolve!: (value: T | PromiseLike<T>) => void;
  const promise = new Promise<T>((res) => {
    resolve = res;
  });
  return { promise, resolve };
}

async function fulfillJson(route: any, body: unknown, status = 200) {
  await route.fulfill({
    status,
    contentType: 'application/json',
    body: JSON.stringify(body)
  });
}

function createDashboardFixture(): DashboardFixture {
  return {
    parent: {
      id: 1,
      email: 'qa-parent@dev.familyherohub.com',
      name: 'QA Parent',
      is_admin: false,
      family_id: 1,
      created_at: '2026-06-15T00:00:00Z',
      last_login_at: '2026-06-15T00:00:00Z'
    },
    children: [
      {
        child: {
          id: 101,
          display_name: 'Jackson',
          avatar_name: null,
          active: true
        },
        spending_balance: 42,
        savings_balance: 0,
        locked_savings: 0,
        available_savings: 0,
        available_spending: 42,
        pending_redemptions: 1,
        pet_progress: {
          current_stage: 'egg',
          lifetime_points: 0
        },
        savings_unlock_schedule: []
      },
      {
        child: {
          id: 202,
          display_name: 'Leah',
          avatar_name: null,
          active: true
        },
        spending_balance: 30,
        savings_balance: 0,
        locked_savings: 0,
        available_savings: 0,
        available_spending: 30,
        pending_redemptions: 1,
        pet_progress: {
          current_stage: 'egg',
          lifetime_points: 0
        },
        savings_unlock_schedule: []
      }
    ],
    presets: [
      {
        id: 501,
        family_id: 1,
        parent_id: 1,
        title: 'Guard Brush Teeth',
        description: 'Preset used by the submit-guard browser test.',
        icon: '🪥',
        points: 5,
        is_active: true
      },
      {
        id: 502,
        family_id: 1,
        parent_id: 1,
        title: 'Guard Homework Star',
        description: 'Sibling preset used to confirm unrelated presets stay enabled.',
        icon: '⭐',
        points: 3,
        is_active: true
      }
    ],
    redemptions: [
      {
        id: 701,
        child_id: 101,
        child_name: 'Jackson',
        points: 5,
        title: 'Request Jackson One',
        description: 'First request used by the browser test.',
        status: 'pending',
        parent_note: null,
        created_at: '2026-06-15T09:00:00Z',
        reviewed_at: null
      },
      {
        id: 702,
        child_id: 202,
        child_name: 'Leah',
        points: 7,
        title: 'Request Leah Two',
        description: 'Second request used to verify unrelated rows stay enabled.',
        status: 'pending',
        parent_note: null,
        created_at: '2026-06-15T10:00:00Z',
        reviewed_at: null
      }
    ],
    rewards: [],
    familyMembers: [],
    familyInvites: []
  };
}

async function installDashboardGetMocks(page: Page, fixture: DashboardFixture) {
  const allowanceSummary = {
    settings: {
      is_enabled: false,
      currency: 'USD',
      currency_exponent: 2,
      period: 'weekly',
      point_goal: 0,
      allowance_amount_minor: 0,
      allowance_enabled_at: null
    },
    allowance_enabled_at: null,
    point_value_display: '1 point = $0.01',
    period_start: '2026-06-15',
    period_end: '2026-06-22',
    next_reset_at: '2026-06-22',
    earned_points_period: 0,
    earned_allowance_minor_period: 0,
    spent_points_period: 0,
    spent_allowance_minor_period: 0,
    pending_points: 0,
    pending_allowance_minor: 0,
    carried_over_points: 0,
    carried_over_allowance_minor: 0,
    available_points: 0,
    available_allowance_minor: 0,
    saved_points: 0,
    saved_allowance_minor: 0,
    locked_saved_points: 0,
    locked_saved_allowance_minor: 0,
    progress_percent: 0,
    maxed_for_period: false,
    currency: 'USD',
    currency_exponent: 2
  };

  await page.route('**/api/me', async (route) => {
    await fulfillJson(route, fixture.parent);
  });
  await page.route('**/api/children/', async (route) => {
    await fulfillJson(route, fixture.children);
  });
  await page.route('**/api/redemptions', async (route) => {
    await fulfillJson(route, fixture.redemptions);
  });
  await page.route('**/api/rewards', async (route) => {
    await fulfillJson(route, fixture.rewards);
  });
  await page.route('**/api/presets/', async (route) => {
    await fulfillJson(route, fixture.presets);
  });
  await page.route('**/api/family/grownups', async (route) => {
    await fulfillJson(route, fixture.familyMembers);
  });
  await page.route('**/api/family/invites', async (route) => {
    await fulfillJson(route, fixture.familyInvites);
  });
  await page.route('**/api/family/settings', async (route) => {
    await fulfillJson(route, { week_start_day: 'sunday' });
  });
  await page.route('**/api/allowance/children/*/summary', async (route) => {
    await fulfillJson(route, allowanceSummary);
  });
  await page.route('**/api/school-items/summary', async (route) => {
    await fulfillJson(route, {
      configured: false,
      show_needed_today: false,
      show_pack_tomorrow: false,
      tile_count: 0,
      tile_mode: 'none',
      needed_today: [],
      pack_tomorrow: []
    });
  });
  await page.route('**/api/school-items/configured', async (route) => {
    await fulfillJson(route, { configured: false });
  });
  await page.route('**/api/calendar/summary', async (route) => {
    await fulfillJson(route, { configured: false, tile_count: 0, today: [], tomorrow: [] });
  });
  await page.route('**/api/children/*/ledger*', async (route) => {
    await fulfillJson(route, []);
  });
}

async function openJacksonPointsModal(page: Page) {
  await page.getByRole('button', { name: /Open point actions for Jackson/i }).click();
  await expect(page.getByRole('heading', { name: 'Jackson' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Points', exact: true })).toBeVisible();
}

async function openJacksonRequests(page: Page) {
  await openJacksonPointsModal(page);
  await page.getByRole('button', { name: /^Requests$/i }).click();
}

test.describe('submit guards', () => {
  test('preset activation is single-flight and scoped to child plus preset', async ({ page }) => {
    const fixture = createDashboardFixture();
    await installDashboardGetMocks(page, fixture);

    await page.goto('/parent', { waitUntil: 'networkidle' });
    await openJacksonPointsModal(page);

    const jacksonPreset = page.getByRole('button', { name: /Guard Brush Teeth/i });
    const jacksonSiblingPreset = page.getByRole('button', { name: /Guard Homework Star/i });
    const leahCard = page.getByRole('button', { name: /Open point actions for Leah/i });
    const awardDeferred = createDeferred<void>();
    let awardCalls = 0;

    await page.route('**/api/children/*/award', async (route) => {
      if (route.request().method() !== 'POST') {
        await route.fallback();
        return;
      }
      awardCalls += 1;
      await awardDeferred.promise;
      await fulfillJson(route, {
        id: 900 + awardCalls,
        points: Number(JSON.parse(route.request().postData() || '{}').points || 0)
      });
    });

    await jacksonPreset.evaluate((button) => {
      const el = button as HTMLButtonElement;
      el.click();
      el.click();
    });

    await expect.poll(() => awardCalls).toBe(1);
    await expect(jacksonPreset).toBeDisabled();
    await expect(jacksonSiblingPreset).toBeEnabled();

    await jacksonSiblingPreset.click();
    await expect.poll(() => awardCalls).toBe(2);

    await page.getByRole('button', { name: /^Close$/i }).click();
    await leahCard.click();

    const leahPreset = page.getByRole('button', { name: /Guard Brush Teeth/i });
    await expect(leahPreset).toBeEnabled();
    await leahPreset.click();
    await expect.poll(() => awardCalls).toBe(3);

    awardDeferred.resolve();
    await expect(jacksonPreset).toBeEnabled({ timeout: 5000 });
    await expect(jacksonSiblingPreset).toBeEnabled();
    await expect(leahPreset).toBeEnabled();
  });

  test('failed preset request releases the guard', async ({ page }) => {
    const fixture = createDashboardFixture();
    await installDashboardGetMocks(page, fixture);

    await page.goto('/parent', { waitUntil: 'networkidle' });
    await openJacksonPointsModal(page);

    const presetButton = page.getByRole('button', { name: /Guard Brush Teeth/i });
    const presetDeferred = createDeferred<void>();
    let dialogMessage = '';

    page.once('dialog', async (dialog) => {
      dialogMessage = dialog.message();
      await dialog.accept();
    });

    await page.route('**/api/children/*/award', async (route) => {
      if (route.request().method() !== 'POST') {
        await route.fallback();
        return;
      }
      await presetDeferred.promise;
      await fulfillJson(route, { detail: 'boom' }, 500);
    });

    await presetButton.click();
    await expect(presetButton).toBeDisabled();
    presetDeferred.resolve();
    await expect(presetButton).toBeEnabled({ timeout: 5000 });
    expect(dialogMessage).toContain('Failed to apply preset');
  });

  test('custom point submission blocks rapid resubmits and restores controls', async ({ page }) => {
    const fixture = createDashboardFixture();
    await installDashboardGetMocks(page, fixture);

    await page.goto('/parent', { waitUntil: 'networkidle' });
    await openJacksonPointsModal(page);

    await page.getByRole('button', { name: /^Custom$/i }).click();
    await page.getByLabel('Points').fill('7');

    const addButton = page.getByRole('button', { name: /^Add points$/i });
    const removeButton = page.getByRole('button', { name: /^Remove points$/i });
    const awardDeferred = createDeferred<void>();
    let awardCalls = 0;

    await page.route('**/api/children/*/award', async (route) => {
      if (route.request().method() !== 'POST') {
        await route.fallback();
        return;
      }
      awardCalls += 1;
      await awardDeferred.promise;
      await fulfillJson(route, {
        id: 910 + awardCalls,
        points: Number(JSON.parse(route.request().postData() || '{}').points || 0)
      });
    });

    await addButton.evaluate((button) => {
      const el = button as HTMLButtonElement;
      el.click();
      el.click();
    });

    await expect.poll(() => awardCalls).toBe(1);
    await expect(addButton).toBeDisabled();
    await expect(removeButton).toBeDisabled();

    awardDeferred.resolve();
    await expect(addButton).toBeEnabled({ timeout: 5000 });
    await expect(removeButton).toBeEnabled();
  });

  test('parent requests row processing is single-flight and recovers after failure', async ({ page }) => {
    const fixture = createDashboardFixture();
    await installDashboardGetMocks(page, fixture);

    await page.goto('/parent', { waitUntil: 'networkidle' });
    await openJacksonRequests(page);

    const jacksonCard = page.getByRole('heading', { name: 'Request Jackson One' }).locator('xpath=ancestor::div[contains(@class,"rounded-[1.5rem]")][1]');
    const jacksonApprove = jacksonCard.getByRole('button', { name: /^Approve$/i });
    const jacksonReject = jacksonCard.getByRole('button', { name: /^Reject$/i });
    const reviewDeferred = createDeferred<void>();
    let approveCalls = 0;

    await page.route('**/api/redemptions/*/approve', async (route) => {
      if (route.request().method() !== 'POST') {
        await route.fallback();
        return;
      }
      approveCalls += 1;
      await reviewDeferred.promise;
      await fulfillJson(route, {
        id: 701,
        child_id: 101,
        points: 5,
        title: 'Request Jackson One',
        description: 'First request used by the browser test.',
        status: 'approved',
        parent_note: null,
        created_at: '2026-06-15T09:00:00Z',
        reviewed_at: '2026-06-15T10:00:00Z'
      });
    });

    await jacksonApprove.evaluate((button) => {
      const el = button as HTMLButtonElement;
      el.click();
      el.click();
    });

    await expect.poll(() => approveCalls).toBe(1);
    await expect(jacksonApprove).toBeDisabled();
    await expect(jacksonReject).toBeDisabled();

    reviewDeferred.resolve();
    await expect(jacksonApprove).toBeEnabled({ timeout: 5000 });
    await expect(jacksonReject).toBeEnabled();
  });

  test('rejection cancel does not lock the row and failure restores controls', async ({ page }) => {
    const fixture = createDashboardFixture();
    await installDashboardGetMocks(page, fixture);

    await page.addInitScript(() => {
      window.prompt = () => null;
    });

    await page.goto('/redemptions', { waitUntil: 'networkidle' });

    const card = page.getByRole('heading', { name: 'Request Jackson One' }).locator('xpath=ancestor::div[contains(concat(" ", normalize-space(@class), " "), " card ")][1]');
    const approveButton = card.getByRole('button', { name: /^Approve$/i });
    const rejectButton = card.getByRole('button', { name: /^Reject$/i });

    await rejectButton.click();
    await expect(approveButton).toBeEnabled();
    await expect(rejectButton).toBeEnabled();

    const approveDeferred = createDeferred<void>();
    let dialogMessage = '';

    page.once('dialog', async (dialog) => {
      dialogMessage = dialog.message();
      await dialog.accept();
    });

    await page.route('**/api/redemptions/*/approve', async (route) => {
      if (route.request().method() !== 'POST') {
        await route.fallback();
        return;
      }
      await approveDeferred.promise;
      await fulfillJson(route, { detail: 'boom' }, 500);
    });

    await approveButton.click();
    await expect(approveButton).toBeDisabled();
    await expect(rejectButton).toBeDisabled();
    approveDeferred.resolve();
    await expect(approveButton).toBeEnabled({ timeout: 5000 });
    await expect(rejectButton).toBeEnabled();
    expect(dialogMessage).toContain('Action failed');
  });
});
