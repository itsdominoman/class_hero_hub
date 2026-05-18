import { expect, test, type Page } from '@playwright/test';
import { collectInternalLinks, createBrowserIssueTracker } from './qa-support';

type PageCase = {
  path: string;
  heading: string;
  headingLevel?: 'h1' | 'h2';
  expectedText?: string;
  safeClickTarget?: string;
};

const PUBLIC_CASES: PageCase[] = [
  {
    path: '/',
    heading: 'Less nagging. Clearer routines. Rewards kids can actually earn.',
    headingLevel: 'h1',
    expectedText: 'Family goals made simple',
    safeClickTarget: '/login'
  },
  {
    path: '/login',
    heading: 'Parent sign-in',
    headingLevel: 'h1',
    expectedText: 'Continue with Google',
    safeClickTarget: '/request-access'
  },
  {
    path: '/privacy',
    heading: 'Privacy Policy',
    headingLevel: 'h1',
    expectedText: 'Authentication & Security',
    safeClickTarget: '/terms'
  },
  {
    path: '/terms',
    heading: 'Terms of Service',
    headingLevel: 'h1',
    expectedText: 'Purpose of Service',
    safeClickTarget: '/privacy'
  },
  {
    path: '/contact',
    heading: 'Contact Us',
    headingLevel: 'h1',
    expectedText: 'Email Support',
    safeClickTarget: '/faq'
  },
  {
    path: '/request-access',
    heading: 'Request Access',
    headingLevel: 'h1',
    expectedText: 'Submit Request',
    safeClickTarget: '/login'
  },
  {
    path: '/faq',
    heading: 'Clear answers for parents and children.',
    headingLevel: 'h1',
    expectedText: 'Find quick help for sign-in',
    safeClickTarget: '/contact'
  },
  {
    path: '/calendar',
    heading: 'Calendar unavailable',
    headingLevel: 'h1',
    expectedText: 'Try again'
  }
];

const SAFE_PUBLIC_PATHS = new Set([
  '/',
  '/login',
  '/privacy',
  '/terms',
  '/contact',
  '/request-access',
  '/faq',
  '/calendar'
]);

async function assertPublicPage(page: Page, testCase: PageCase) {
  const tracker = createBrowserIssueTracker(page);

  await page.goto(testCase.path, { waitUntil: 'networkidle' });
  await page.waitForTimeout(250);

  const links = await collectInternalLinks(page);
  if (testCase.path !== '/calendar') {
    expect(links.length, `${testCase.path} internal link inventory`).toBeGreaterThan(0);
  }

  const safeLinks = links.filter((link) => SAFE_PUBLIC_PATHS.has(new URL(link.href, page.url()).pathname));
  if (testCase.path !== '/calendar') {
    expect(safeLinks.length, `${testCase.path} safe public links`).toBeGreaterThan(0);
  }
  for (const link of safeLinks) {
    const resolved = new URL(link.href, page.url());
    const response = await page.request.get(resolved.toString());
    expect(response.ok(), `${testCase.path} internal link ${resolved.pathname}`).toBeTruthy();
  }

  const heading = page.locator(testCase.headingLevel ?? 'h1', { hasText: testCase.heading });
  await expect(heading).toBeVisible();

  if (testCase.expectedText) {
    await expect(page.getByText(testCase.expectedText, { exact: false })).toBeVisible();
  }

  if (testCase.safeClickTarget) {
    const safeLink = page.locator(`a[href="${testCase.safeClickTarget}"]`).first();
    await expect(safeLink, `${testCase.path} safe link ${testCase.safeClickTarget}`).toBeVisible();
    await safeLink.click();
    await expect(page).toHaveURL(new RegExp(`${testCase.safeClickTarget.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}$`));
  }

  expect(tracker.issues.pageErrors, `${testCase.path} page errors`).toEqual([]);
  expect(tracker.issues.consoleErrors, `${testCase.path} console errors`).toEqual([]);
}

test.describe('Europe dev public pages', () => {
  for (const testCase of PUBLIC_CASES) {
    test(`${testCase.path} renders without browser errors`, async ({ page }) => {
      await assertPublicPage(page, testCase);
    });
  }
});
