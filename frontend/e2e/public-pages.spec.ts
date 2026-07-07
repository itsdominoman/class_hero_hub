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
    heading: 'Clear school updates in one trusted place.',
    headingLevel: 'h1',
    expectedText: 'School notices',
    safeClickTarget: '/login'
  },
  {
    path: '/login',
    heading: 'Welcome to Class Hero Hub',
    headingLevel: 'h1',
    expectedText: 'Continue with Google',
    safeClickTarget: '/'
  },
  {
    path: '/privacy',
    heading: 'Privacy Policy',
    headingLevel: 'h1',
    expectedText: 'Copy TODO',
    safeClickTarget: '/terms'
  },
  {
    path: '/terms',
    heading: 'Terms of Service',
    headingLevel: 'h1',
    expectedText: 'Copy TODO',
    safeClickTarget: '/privacy'
  },
  {
    path: '/contact',
    heading: 'Contact Class Hero Hub',
    headingLevel: 'h1',
    expectedText: 'Email Support',
    safeClickTarget: '/faq'
  },
  {
    path: '/faq',
    heading: 'FAQ',
    headingLevel: 'h1',
    expectedText: 'Copy TODO',
    safeClickTarget: '/contact'
  },
  {
    path: '/safety-privacy',
    heading: 'Safety & Privacy',
    headingLevel: 'h1',
    expectedText: 'Copy TODO',
    safeClickTarget: '/contact'
  }
];

const SAFE_PUBLIC_PATHS = new Set([
  '/',
  '/login',
  '/privacy',
  '/terms',
  '/contact',
  '/faq',
  '/safety-privacy'
]);

async function assertPublicPage(page: Page, testCase: PageCase) {
  const tracker = createBrowserIssueTracker(page);
  tracker.ignoreConsoleErrorSnippet('the server responded with a status of 401');

  await page.route('**/api/me', async (route) => {
    await route.fulfill({
      status: 401,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'Not authenticated' })
    });
  });

  await page.goto(testCase.path, { waitUntil: 'networkidle' });
  await page.waitForTimeout(250);

  const links = await collectInternalLinks(page);
  expect(links.length, `${testCase.path} internal link inventory`).toBeGreaterThan(0);

  const safeLinks = links.filter((link) => SAFE_PUBLIC_PATHS.has(new URL(link.href, page.url()).pathname));
  expect(safeLinks.length, `${testCase.path} safe public links`).toBeGreaterThan(0);
  for (const link of safeLinks) {
    const resolved = new URL(link.href, page.url());
    const response = await page.request.get(resolved.toString());
    expect(response.ok(), `${testCase.path} internal link ${resolved.pathname}`).toBeTruthy();
  }

  const heading = page.locator(testCase.headingLevel ?? 'h1', { hasText: testCase.heading });
  await expect(heading).toBeVisible();

  if (testCase.expectedText) {
    await expect(page.getByText(testCase.expectedText, { exact: false }).first()).toBeVisible();
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
