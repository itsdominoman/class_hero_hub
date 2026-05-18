import { expect, test, type Page } from '@playwright/test';
import { mkdirSync } from 'node:fs';
import { resolve } from 'node:path';
import { join } from 'node:path';
import {
  assertNoHorizontalOverflow,
  assertReadableElement,
  createBrowserIssueTracker,
  findLayoutViolations,
  setupQaChildSession,
  setupQaParentSession,
  type QaChildSession
} from './qa-support';

type VisualCase = {
  path: string;
  heading: string;
  headingLevel?: 'h1' | 'h2';
  auth: 'public' | 'parent';
  screenshotName: string;
  extraChecks?: (page: Page) => Promise<void>;
  ignoredConsoleErrorSnippets?: string[];
};

const STANDARD_VIEWPORTS = [320, 375, 390, 430];
const CHILD_VIEWPORTS = [320, 360, 375, 390, 430, 768];

const PUBLIC_CASES: VisualCase[] = [
  {
    path: '/',
    heading: 'Less nagging. Clearer routines. Rewards kids can actually earn.',
    headingLevel: 'h1',
    auth: 'public',
    screenshotName: 'home-public'
  },
  {
    path: '/faq',
    heading: 'Clear answers for parents and children.',
    headingLevel: 'h1',
    auth: 'public',
    screenshotName: 'faq-public'
  }
];

const PARENT_CASES: VisualCase[] = [
  {
    path: '/parent',
    heading: 'My Family',
    headingLevel: 'h1',
    auth: 'parent',
    screenshotName: 'parent-auth'
  },
  {
    path: '/allowance',
    heading: 'Allowance setup',
    headingLevel: 'h1',
    auth: 'parent',
    screenshotName: 'allowance-auth'
  },
  {
    path: '/calendar',
    heading: 'Plan the week with the family.',
    headingLevel: 'h1',
    auth: 'parent',
    screenshotName: 'calendar-auth'
  },
  {
    path: '/redemptions',
    heading: 'Reward Requests',
    headingLevel: 'h1',
    auth: 'parent',
    screenshotName: 'redemptions-auth'
  }
];

const CHILD_REWARD_TITLES = [
  'QA Reward Short',
  'QA Reward Very Long Name Designed To Stress Mobile Card Wrapping',
  'QA Reward Long Description Stress Case',
  'QA Reward Bonus'
];

const CHILD_REWARD_LONG_DESCRIPTION =
  'This reward description is intentionally long so the child reward cards, helper badges, and mobile spacing all get exercised together without needing a brittle pixel snapshot.';

async function writeScreenshot(page: Page, screenshotName: string, viewport: number) {
  const artifactRoot = process.env.QA_ARTIFACT_ROOT?.trim() || resolve(process.cwd(), '..', 'tmp', 'qa-runs');
  const outputDir = join(artifactRoot, process.env.QA_RUN_ID || 'visual-layout');
  mkdirSync(outputDir, { recursive: true });
  await page.screenshot({
    path: join(outputDir, `${screenshotName}-${viewport}.png`),
    fullPage: true
  });
}

async function assertVisualCase(page: Page, visualCase: VisualCase, viewport: number) {
  const tracker = createBrowserIssueTracker(page);
  for (const snippet of visualCase.ignoredConsoleErrorSnippets || []) {
    tracker.ignoreConsoleErrorSnippet(snippet);
  }

  await page.setViewportSize({ width: viewport, height: 1600 });
  await page.goto(visualCase.path, { waitUntil: 'networkidle' });
  await page.waitForTimeout(200);

  const heading = page.locator(visualCase.headingLevel ?? 'h1', { hasText: visualCase.heading });
  await expect(heading, `${visualCase.path} heading`).toBeVisible();

  if (visualCase.extraChecks) {
    await visualCase.extraChecks(page);
  }

  await assertNoHorizontalOverflow(page);
  const layoutViolations = await findLayoutViolations(page);

  await writeScreenshot(page, visualCase.screenshotName, viewport);

  expect(layoutViolations, `${visualCase.path} layout violations at ${viewport}px`).toEqual([]);
  expect(tracker.issues.pageErrors, `${visualCase.path} page errors at ${viewport}px`).toEqual([]);
  expect(tracker.issues.consoleErrors, `${visualCase.path} console errors at ${viewport}px`).toEqual([]);
}

async function assertChildVisualCase(page: Page, childSession: QaChildSession, viewport: number) {
  const tracker = createBrowserIssueTracker(page);
  await page.setViewportSize({ width: viewport, height: 1600 });
  await page.goto(childSession.childRoute, { waitUntil: 'networkidle' });
  await page.waitForTimeout(250);

  await expect(page.getByRole('heading', { name: childSession.childName })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Choose a reward' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Ask to spend your points' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Points log' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Today’s schedule' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Waiting requests' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Savings snapshot' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Tasks today' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Events today' })).toBeVisible();
  await expect(page.getByText('Your current points are worth', { exact: false })).toBeVisible();

  await expect(page.getByRole('heading', { name: /^QA Reward / })).toHaveCount(4);
  await expect(page.getByRole('heading', { name: 'QA Pending Request' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'QA Waiting Request' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'QA Task Pack Bag' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'QA Event Piano Lesson' })).toBeVisible();
  await expect(page.getByText('QA School Bag Pack', { exact: false })).toBeVisible();
  await expect(page.getByText('QA School Bag Piano', { exact: false })).toBeVisible();

  await assertReadableElement(page.getByRole('textbox', { name: 'Request name' }), {
    label: 'custom request name input',
    minWidth: 160,
    maxHeight: 72,
    maxLines: 1,
    minCharsPerLine: 1
  });

  await assertReadableElement(page.getByRole('spinbutton', { name: 'Points' }), {
    label: 'custom request points input',
    minWidth: 90,
    maxHeight: 72,
    maxLines: 1,
    minCharsPerLine: 1
  });

  await expect(page.locator('form button[type="submit"]')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Mark done' })).toBeVisible();

  for (const rewardTitle of CHILD_REWARD_TITLES) {
    await assertReadableElement(page.getByRole('heading', { name: rewardTitle }), {
      label: `reward title ${rewardTitle}`,
      minWidth: rewardTitle.length > 40 ? 50 : 20,
      maxHeight: rewardTitle.length > 40 ? 400 : 220,
      maxLines: rewardTitle.length > 40 ? 12 : 6,
      minCharsPerLine: rewardTitle.length > 40 ? 4 : 3
    });
  }

  await assertReadableElement(
    page.getByText(CHILD_REWARD_LONG_DESCRIPTION, { exact: false }),
    {
      label: 'long reward description',
      minWidth: 120,
      maxHeight: 180,
      maxLines: 5,
      minCharsPerLine: 9
    }
  );

  await assertReadableElement(page.getByRole('button', { name: 'Request' }).first(), {
    label: 'reward request button',
    minWidth: 90,
    maxHeight: 90,
    maxLines: 3,
    minCharsPerLine: 4
  });

  await assertReadableElement(page.locator('form button[type="submit"]'), {
    label: 'custom request submit button',
    minWidth: 90,
    maxHeight: 90,
    maxLines: 3,
    minCharsPerLine: 4
  });

  await assertReadableElement(page.getByRole('heading', { name: 'QA Task Pack Bag' }), {
    label: 'task title QA Task Pack Bag',
    minWidth: 100,
    maxHeight: 150,
    maxLines: 4,
    minCharsPerLine: 5
  });

  await assertReadableElement(page.getByRole('heading', { name: 'QA Event Piano Lesson' }), {
    label: 'event title QA Event Piano Lesson',
    minWidth: 100,
    maxHeight: 150,
    maxLines: 4,
    minCharsPerLine: 5
  });

  await assertReadableElement(page.getByRole('heading', { name: 'QA Pending Request' }), {
    label: 'pending request title',
    minWidth: 100,
    maxHeight: 150,
    maxLines: 4,
    minCharsPerLine: 5
  });

  await assertReadableElement(page.getByRole('heading', { name: 'QA Waiting Request' }), {
    label: 'waiting request title',
    minWidth: 100,
    maxHeight: 150,
    maxLines: 4,
    minCharsPerLine: 5
  });

  await assertReadableElement(page.getByText('QA School Bag Pack', { exact: false }), {
    label: 'school bag pack item',
    minWidth: 100,
    maxHeight: 120,
    maxLines: 4,
    minCharsPerLine: 4
  });

  await assertReadableElement(page.getByText('QA School Bag Piano', { exact: false }), {
    label: 'school bag piano item',
    minWidth: 100,
    maxHeight: 120,
    maxLines: 4,
    minCharsPerLine: 4
  });

  await assertNoHorizontalOverflow(page);
  const layoutViolations = await findLayoutViolations(page);

  await writeScreenshot(page, 'child-dashboard-real-child-seeded-rewards', viewport);

  expect(layoutViolations, `real child dashboard layout violations at ${viewport}px`).toEqual([]);
  expect(tracker.issues.pageErrors, `real child dashboard page errors at ${viewport}px`).toEqual([]);
  expect(tracker.issues.consoleErrors, `real child dashboard console errors at ${viewport}px`).toEqual([]);
}

test.describe('Europe dev visual layout checks', () => {
  test.describe('public pages', () => {
    for (const visualCase of PUBLIC_CASES) {
      for (const viewport of STANDARD_VIEWPORTS) {
        test(`${visualCase.screenshotName} ${viewport}px`, async ({ page }) => {
          await assertVisualCase(page, visualCase, viewport);
        });
      }
    }
  });

  test.describe('authenticated parent pages', () => {
    test.beforeEach(async ({ page }) => {
      await setupQaParentSession(page);
    });

    for (const visualCase of PARENT_CASES) {
      for (const viewport of STANDARD_VIEWPORTS) {
        test(`${visualCase.screenshotName} ${viewport}px`, async ({ page }) => {
          await assertVisualCase(page, visualCase, viewport);
        });
      }
    }
  });

  test.describe('authenticated child pages', () => {
    let childSession!: QaChildSession;

    test.beforeEach(async ({ page }) => {
      childSession = await setupQaChildSession(page);
    });

    for (const viewport of CHILD_VIEWPORTS) {
      test(`child-dashboard-real-child-seeded-rewards ${viewport}px`, async ({ page }) => {
        await assertChildVisualCase(page, childSession, viewport);
      });
    }
  });
});
