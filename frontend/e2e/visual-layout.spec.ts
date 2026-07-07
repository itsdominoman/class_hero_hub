import { expect, test, type Page } from '@playwright/test';
import { mkdirSync } from 'node:fs';
import { join, resolve } from 'node:path';
import {
  assertNoHorizontalOverflow,
  createBrowserIssueTracker,
  findLayoutViolations,
  setupQaParentSession
} from './qa-support';

type VisualCase = {
  path: string;
  heading: string;
  auth: 'public' | 'parent';
  screenshotName: string;
  ignoredConsoleErrorSnippets?: string[];
};

const STANDARD_VIEWPORTS = [320, 375, 390, 430];

const CASES: VisualCase[] = [
  {
    path: '/',
    heading: 'Clear school updates in one trusted place.',
    auth: 'public',
    screenshotName: 'home-public',
    ignoredConsoleErrorSnippets: ['the server responded with a status of 401']
  },
  {
    path: '/faq',
    heading: 'FAQ',
    auth: 'public',
    screenshotName: 'faq-public',
    ignoredConsoleErrorSnippets: ['the server responded with a status of 401']
  },
  {
    path: '/parent',
    heading: 'No school role assigned yet',
    auth: 'parent',
    screenshotName: 'dashboard-placeholder'
  }
];

async function writeScreenshot(page: Page, screenshotName: string, viewport: number) {
  const artifactRoot = process.env.QA_ARTIFACT_ROOT?.trim() || resolve(process.cwd(), '..', 'tmp', 'qa-runs');
  const runId = process.env.QA_RUN_ID || `${new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)}-visual-layout`;
  const outputDir = join(artifactRoot, runId);
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

  if (visualCase.auth === 'parent') {
    await setupQaParentSession(page);
  }

  await page.setViewportSize({ width: viewport, height: 1600 });
  await page.goto(visualCase.path, { waitUntil: 'networkidle' });
  await page.waitForTimeout(200);

  await expect(page.getByRole('heading', { name: visualCase.heading })).toBeVisible();

  await assertNoHorizontalOverflow(page);
  const layoutViolations = await findLayoutViolations(page);

  await writeScreenshot(page, visualCase.screenshotName, viewport);

  expect(layoutViolations, `${visualCase.path} layout violations at ${viewport}px`).toEqual([]);
  expect(tracker.issues.pageErrors, `${visualCase.path} page errors at ${viewport}px`).toEqual([]);
  expect(tracker.issues.consoleErrors, `${visualCase.path} console errors at ${viewport}px`).toEqual([]);
}

test.describe('Europe dev visual layout checks', () => {
  for (const visualCase of CASES) {
    for (const viewport of STANDARD_VIEWPORTS) {
      test(`${visualCase.screenshotName} ${viewport}px`, async ({ page }) => {
        await assertVisualCase(page, visualCase, viewport);
      });
    }
  }
});
