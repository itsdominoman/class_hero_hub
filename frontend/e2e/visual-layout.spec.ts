import { expect, test, type Page } from '@playwright/test';
import { mkdirSync } from 'node:fs';
import { join } from 'node:path';
import {
  assertNoHorizontalOverflow,
  createBrowserIssueTracker,
  findLayoutViolations,
  setupQaParentSession
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

const VIEWPORTS = [320, 375, 390, 430];

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
  },
  {
    path: '/parent',
    heading: 'My Family',
    headingLevel: 'h1',
    auth: 'parent',
    screenshotName: 'child-dashboard-parent-preview',
    ignoredConsoleErrorSnippets: ['Failed to load resource: the server responded with a status of 401 (Unauthorized)'],
    extraChecks: async (page) => {
      const childLink = page.locator('a[href^="/child/"]').first();
      await expect(childLink, 'child dashboard link').toBeVisible();
      await childLink.click();
      await expect(page).toHaveURL(/\/child\/\d+$/);
      await expect(page.getByRole('heading', { name: /Choose a reward/i })).toBeVisible();
      await expect(page.getByRole('heading', { name: /Ask to spend your points/i })).toBeVisible();
      await expect(page.getByRole('heading', { name: /Today’s schedule/i })).toBeVisible();
    }
  }
];

async function writeScreenshot(page: Page, screenshotName: string, viewport: number) {
  const outputDir = join(process.cwd(), '..', 'tmp', 'qa-runs', `${process.env.QA_RUN_ID || 'visual-layout'}`);
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

  const heading = page.locator(visualCase.headingLevel ?? 'h1', { hasText: visualCase.heading });

  await page.goto(visualCase.path, { waitUntil: 'networkidle' });
  await page.waitForTimeout(200);
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

test.describe('Europe dev visual layout checks', () => {
  test.describe('public pages', () => {
    for (const visualCase of PUBLIC_CASES) {
      for (const viewport of VIEWPORTS) {
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
      for (const viewport of VIEWPORTS) {
        test(`${visualCase.screenshotName} ${viewport}px`, async ({ page }) => {
          await assertVisualCase(page, visualCase, viewport);
        });
      }
    }
  });
});
