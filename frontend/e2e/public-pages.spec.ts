import { expect, test, type Page } from '@playwright/test';

type PageCase = {
  path: string;
  heading: string;
  headingLevel?: 'h1' | 'h2';
  expectedText?: string;
};

const PUBLIC_CASES: PageCase[] = [
  {
    path: '/',
    heading: 'Less nagging. Clearer routines. Rewards kids can actually earn.',
    headingLevel: 'h1',
    expectedText: 'Family goals made simple'
  },
  {
    path: '/login',
    heading: 'Parent sign-in',
    headingLevel: 'h1',
    expectedText: 'Continue with Google'
  },
  {
    path: '/privacy',
    heading: 'Privacy Policy',
    headingLevel: 'h1',
    expectedText: 'Authentication & Security'
  },
  {
    path: '/terms',
    heading: 'Terms of Service',
    headingLevel: 'h1',
    expectedText: 'Purpose of Service'
  },
  {
    path: '/contact',
    heading: 'Contact Us',
    headingLevel: 'h1',
    expectedText: 'Email Support'
  },
  {
    path: '/request-access',
    heading: 'Request Access',
    headingLevel: 'h1',
    expectedText: 'Submit Request'
  },
  {
    path: '/calendar',
    heading: 'Calendar unavailable',
    headingLevel: 'h1',
    expectedText: 'Try again'
  }
];

async function captureBrowserIssues(page: Page) {
  const consoleErrors: string[] = [];
  const pageErrors: string[] = [];

  page.on('console', (message) => {
    if (message.type() === 'error') {
      consoleErrors.push(message.text());
    }
  });

  page.on('pageerror', (error) => {
    pageErrors.push(error.message);
  });

  return { consoleErrors, pageErrors };
}

async function assertPublicPage(page: Page, testCase: PageCase) {
  const issues = await captureBrowserIssues(page);

  await page.goto(testCase.path, { waitUntil: 'networkidle' });
  await page.waitForTimeout(250);

  const heading = page.locator(testCase.headingLevel ?? 'h1', { hasText: testCase.heading });
  await expect(heading).toBeVisible();

  if (testCase.expectedText) {
    await expect(page.getByText(testCase.expectedText, { exact: false })).toBeVisible();
  }

  expect(issues.pageErrors, `${testCase.path} page errors`).toEqual([]);
  expect(issues.consoleErrors, `${testCase.path} console errors`).toEqual([]);
}

test.describe('Europe dev public pages', () => {
  for (const testCase of PUBLIC_CASES) {
    test(`${testCase.path} renders without browser errors`, async ({ page }) => {
      await assertPublicPage(page, testCase);
    });
  }
});
