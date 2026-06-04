import { expect, test, type Locator, type Page } from '@playwright/test';
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
const PARENT_DESKTOP_VIEWPORTS = [1024];
const CHILD_VIEWPORTS = [320, 360, 375, 390, 430, 768];

const PUBLIC_CASES: VisualCase[] = [
  {
    path: '/',
    heading: 'Less nagging. Clearer routines. Rewards kids can actually earn.',
    headingLevel: 'h1',
    auth: 'public',
    screenshotName: 'home-public',
    ignoredConsoleErrorSnippets: ['the server responded with a status of 401']
  },
  {
    path: '/faq',
    heading: 'Clear answers for parents and children.',
    headingLevel: 'h1',
    auth: 'public',
    screenshotName: 'faq-public',
    ignoredConsoleErrorSnippets: ['the server responded with a status of 401']
  }
];

const PARENT_CASES: VisualCase[] = [
  {
    path: '/parent',
    heading: 'My Family',
    headingLevel: 'h1',
    auth: 'parent',
    screenshotName: 'parent-auth',
    extraChecks: async (page) => {
      await assertParentChildCardLayout(page);
    }
  },
  {
    path: '/parent/settings',
    heading: 'Parent settings',
    headingLevel: 'h1',
    auth: 'parent',
    screenshotName: 'parent-settings-auth',
    extraChecks: async (page) => {
      await expect(page.getByRole('heading', { name: 'Edit child names and avatars' })).toBeVisible();
      await expect(page.getByRole('heading', { name: 'Tools still opened from the parent dashboard' })).toBeVisible();
    }
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

type BoxMetrics = {
  x: number;
  y: number;
  width: number;
  height: number;
  right: number;
  bottom: number;
  clientWidth: number;
  scrollWidth: number;
  text: string;
};

async function readBox(locator: Locator): Promise<BoxMetrics> {
  return locator.first().evaluate((element) => {
    const rect = element.getBoundingClientRect();
    return {
      x: rect.x,
      y: rect.y,
      width: rect.width,
      height: rect.height,
      right: rect.right,
      bottom: rect.bottom,
      clientWidth: element.clientWidth,
      scrollWidth: element.scrollWidth,
      text: (element.textContent || '').replace(/\s+/g, ' ').trim()
    };
  });
}

async function assertRewardCardLayout(page: Page) {
  for (const rewardTitle of CHILD_REWARD_TITLES) {
    const title = page.getByRole('heading', { name: rewardTitle });
    const card = title.locator('xpath=ancestor::div[contains(@class,"rounded-[1.75rem]")][1]');
    const value = card.getByText(/^\s*\d+\s+points\b/i);
    const requestButton = card.getByRole('button', { name: 'Request' });

    await expect(title).toBeVisible();
    await expect(value).toBeVisible();
    await expect(requestButton).toBeVisible();

    const [cardBox, titleBox, valueBox, buttonBox] = await Promise.all([
      readBox(card),
      readBox(title),
      readBox(value),
      readBox(requestButton)
    ]);

    expect(
      titleBox.bottom,
      `reward title should sit above its value for "${titleBox.text}"`
    ).toBeLessThanOrEqual(valueBox.y + 2);
    expect(
      valueBox.right,
      `reward value should stay inside the card for "${titleBox.text}"`
    ).toBeLessThanOrEqual(cardBox.right + 2);
    expect(
      valueBox.scrollWidth,
      `reward value text should not be clipped for "${titleBox.text}"`
    ).toBeLessThanOrEqual(valueBox.clientWidth + 2);
    expect(
      valueBox.width,
      `reward value should have room below the title for "${titleBox.text}"`
    ).toBeGreaterThanOrEqual(92);
    expect(
      buttonBox.width,
      `reward request button should remain full width for "${titleBox.text}"`
    ).toBeGreaterThanOrEqual(cardBox.width - 44);
    expect(
      buttonBox.y,
      `reward request button should sit below the value for "${titleBox.text}"`
    ).toBeGreaterThanOrEqual(valueBox.bottom - 2);
  }
}

async function assertChildCustomRequestLayout(page: Page, viewport: number) {
  const form = page.locator('form').filter({ has: page.getByRole('textbox', { name: 'Request name' }) });
  const nameInput = form.getByRole('textbox', { name: 'Request name' });
  const pointsInput = form.getByRole('spinbutton', { name: 'Points' });
  const nameContainer = nameInput.locator('xpath=ancestor::*[contains(@class,"space-y-2")][1]');
  const pointsContainer = pointsInput.locator('xpath=ancestor::*[contains(@class,"space-y-2")][1]');
  const submitButton = form.locator('button[type="submit"]');
  const valueLabel = page.locator('[data-qa="child-custom-request-value"]');
  const conversionLabel = page.locator('[data-qa="child-custom-request-conversion"]');

  await expect(nameInput).toBeVisible();
  await expect(pointsInput).toBeVisible();
  await expect(submitButton).toBeVisible();
  await expect(valueLabel).toBeVisible();
  await expect(conversionLabel).toBeVisible();

  const [nameBox, pointsBox, submitBox, valueBox, nameContainerBox, pointsContainerBox] = await Promise.all([
    readBox(nameInput),
    readBox(pointsInput),
    readBox(submitButton),
    readBox(valueLabel),
    readBox(nameContainer),
    readBox(pointsContainer)
  ]);

  if (viewport < 768) {
    expect(Math.abs(nameBox.x - pointsBox.x), 'custom request fields should align on mobile').toBeLessThanOrEqual(6);
    expect(Math.abs(nameBox.x - submitBox.x), 'custom request button should align on mobile').toBeLessThanOrEqual(6);
    expect(pointsBox.y, 'custom request points field should sit below the name field on mobile').toBeGreaterThanOrEqual(nameBox.bottom - 2);
    expect(submitBox.y, 'custom request button should sit below the points field on mobile').toBeGreaterThanOrEqual(pointsBox.bottom - 2);
  } else {
    // Top alignment of inputs
    expect(Math.abs(nameBox.y - pointsBox.y), 'custom request inputs should align at top on desktop').toBeLessThanOrEqual(6);
    // Bottom alignment of inputs
    expect(Math.abs(nameBox.bottom - pointsBox.bottom), 'custom request inputs should align at bottom on desktop').toBeLessThanOrEqual(6);
    // Button alignment with input row
    expect(Math.abs(submitBox.bottom - nameBox.bottom), 'custom request button should align with input bottom on desktop').toBeLessThanOrEqual(6);
    // Container/Label alignment
    expect(Math.abs(nameContainerBox.y - pointsContainerBox.y), 'custom request form containers should align top on desktop').toBeLessThanOrEqual(6);
  }

  // Value text should be below the form grid
  const formBox = await readBox(form);
  expect(valueBox.y, 'custom request value text should sit below the form grid row').toBeGreaterThanOrEqual(formBox.bottom - 2);

  expect(valueBox.scrollWidth, 'custom request value should not be clipped').toBeLessThanOrEqual(valueBox.clientWidth + 2);
  expect(submitBox.width, 'custom request button should not be cramped').toBeGreaterThanOrEqual(100);
  expect(submitBox.height, 'custom request button should not wrap awkwardly').toBeLessThanOrEqual(64);
}

async function assertParentChildCardLayout(page: Page) {
  const jacksonTitle = page.getByRole('heading', { name: 'Jackson' });
  const leahTitle = page.getByRole('heading', { name: 'Leah' });
  await expect(jacksonTitle).toBeVisible();
  await expect(leahTitle).toBeVisible();

  for (const title of [jacksonTitle, leahTitle]) {
    const card = title.locator('xpath=ancestor::a[1]');
    const currentPointsLabel = card.getByText('Current points', { exact: true });
    const availableNowLabel = card.getByText('Available now', { exact: true });

    await expect(card).toBeVisible();
    await expect(currentPointsLabel).toBeVisible();
    await expect(availableNowLabel).toBeVisible();
    await expect(card, 'child launcher card should stay readable').toHaveText(/Open .* dashboard/i);
  }
}

async function assertParentChildCardAlignment(page: Page) {
  const jacksonTitle = page.getByRole('heading', { name: 'Jackson' });
  const leahTitle = page.getByRole('heading', { name: 'Leah' });
  const currentPointLabels: BoxMetrics[] = [];
  const availableNowLabels: BoxMetrics[] = [];

  for (const title of [jacksonTitle, leahTitle]) {
    const card = title.locator('xpath=ancestor::a[1]');
    const currentPointsLabel = card.getByText('Current points', { exact: true });
    const availableNowLabel = card.getByText('Available now', { exact: true });

    await expect(card).toBeVisible();
    await expect(currentPointsLabel).toBeVisible();
    await expect(availableNowLabel).toBeVisible();

    currentPointLabels.push(await readBox(currentPointsLabel));
    availableNowLabels.push(await readBox(availableNowLabel));
  }

  expect(
    Math.abs(currentPointLabels[0].y - currentPointLabels[1].y),
    'current point labels should align across cards'
  ).toBeLessThanOrEqual(10);
  expect(
    Math.abs(availableNowLabels[0].y - availableNowLabels[1].y),
    'available now labels should align across cards'
  ).toBeLessThanOrEqual(10);

  for (const box of [...currentPointLabels, ...availableNowLabels]) {
    expect(box.height, 'parent card stat labels should not wrap').toBeLessThanOrEqual(64);
    expect(box.width, 'parent card stat labels should remain wide enough').toBeGreaterThanOrEqual(100);
  }
}

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

  await page.setViewportSize({ width: viewport, height: 1600 });
  await page.goto(visualCase.path, { waitUntil: 'networkidle' });
  await page.waitForTimeout(200);

  const heading = page.locator(visualCase.headingLevel ?? 'h1', { hasText: visualCase.heading });
  await expect(heading, `${visualCase.path} heading`).toBeVisible();

  if (visualCase.extraChecks) {
    await visualCase.extraChecks(page);
  }

  if (visualCase.path === '/parent' && viewport >= 1024) {
    await assertParentChildCardAlignment(page);
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
  tracker.ignoreConsoleErrorSnippet('the server responded with a status of 401');
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

  await assertRewardCardLayout(page);
  await assertChildCustomRequestLayout(page, viewport);

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
      const viewports = visualCase.path === '/parent'
        ? [...STANDARD_VIEWPORTS, ...PARENT_DESKTOP_VIEWPORTS]
        : STANDARD_VIEWPORTS;

      for (const viewport of viewports) {
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
