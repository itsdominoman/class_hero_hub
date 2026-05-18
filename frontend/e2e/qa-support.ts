import { expect, type Page } from '@playwright/test';

const DEFAULT_QA_LOGIN_BASE_URL = process.env.QA_LOGIN_API_BASE_URL?.trim() || 'http://127.0.0.1:8000';

type BrowserIssues = {
  consoleErrors: string[];
  pageErrors: string[];
};

type LayoutViolation = {
  selector: string;
  text: string;
  reason: string;
};

type InternalLink = {
  href: string;
  text: string;
};

const DEFAULT_LAYOUT_SELECTORS = [
  'main h1',
  'main h2',
  'main h3',
  'main h4',
  'main button',
  'main a',
  'main [role="button"]',
  'main label',
  'main span'
].join(', ');

export function createBrowserIssueTracker(page: Page) {
  const ignoredConsoleErrorSnippets: string[] = [];
  const issues: BrowserIssues = {
    consoleErrors: [],
    pageErrors: []
  };

  page.on('console', (message) => {
    if (message.type() === 'error') {
      const text = message.text();
      if (ignoredConsoleErrorSnippets.some((snippet) => text.includes(snippet))) {
        return;
      }
      issues.consoleErrors.push(text);
    }
  });

  page.on('pageerror', (error) => {
    issues.pageErrors.push(error.message);
  });

  return {
    issues,
    ignoreConsoleErrorSnippet(snippet: string) {
      ignoredConsoleErrorSnippets.push(snippet);
    },
    clear() {
      issues.consoleErrors.length = 0;
      issues.pageErrors.length = 0;
    }
  };
}

export async function setupQaParentSession(page: Page) {
  const qaToken = process.env.QA_LOGIN_TOKEN?.trim();
  if (!qaToken) {
    throw new Error('QA_LOGIN_TOKEN is required for authenticated browser QA');
  }

  const loginUrl = new URL('/api/dev/qa-login', DEFAULT_QA_LOGIN_BASE_URL);
  const loginResponse = await page.request.post(loginUrl.toString(), {
    data: { token: qaToken }
  });

  expect(loginResponse.status()).toBe(200);
  const loginBody = await loginResponse.text();
  expect(loginBody).toContain('"status":"ok"');
  expect(loginBody).toContain('"email":"qa-parent@dev.familyherohub.com"');

  const loginCookies = loginResponse
    .headersArray()
    .filter((header) => header.name.toLowerCase() === 'set-cookie')
    .map((header) => header.value)
    .map((cookieHeader) => cookieHeader.split(';', 1)[0])
    .map((cookiePair) => {
      const separatorIndex = cookiePair.indexOf('=');
      return {
        name: cookiePair.slice(0, separatorIndex),
        value: cookiePair.slice(separatorIndex + 1)
      };
    });

  await page.context().addCookies(
    loginCookies.map((cookie) => ({
      ...cookie,
      url: DEFAULT_QA_LOGIN_BASE_URL
    }))
  );

  await page.route('**/api/**', async (route) => {
    const requestUrl = new URL(route.request().url());
    const backendUrl = new URL(`${requestUrl.pathname}${requestUrl.search}`, DEFAULT_QA_LOGIN_BASE_URL);
    const backendResponse = await route.fetch({ url: backendUrl.toString() });
    await route.fulfill({ response: backendResponse });
  });
}

export async function collectInternalLinks(page: Page): Promise<InternalLink[]> {
  return page.locator('a[href]').evaluateAll((anchors) => {
    const links: InternalLink[] = [];
    for (const anchor of anchors) {
      const element = anchor as HTMLAnchorElement;
      const rawHref = element.getAttribute('href');
      if (!rawHref) continue;
      try {
        const resolved = new URL(rawHref, window.location.href);
        if (resolved.origin !== window.location.origin) continue;
        links.push({
          href: `${resolved.pathname}${resolved.search}${resolved.hash}`,
          text: (element.textContent || '').replace(/\s+/g, ' ').trim()
        });
      } catch {
        continue;
      }
    }
    return links;
  });
}

export async function assertNoHorizontalOverflow(page: Page, tolerance = 2) {
  const overflow = await page.evaluate(() => {
    const doc = document.documentElement;
    const body = document.body;
    const viewportWidth = window.innerWidth;
    const scrollWidth = Math.max(doc.scrollWidth, body?.scrollWidth ?? 0);
    return {
      viewportWidth,
      scrollWidth,
      overflow: scrollWidth - viewportWidth
    };
  });

  expect(
    overflow.overflow,
    `horizontal overflow detected: scrollWidth=${overflow.scrollWidth}, viewportWidth=${overflow.viewportWidth}`
  ).toBeLessThanOrEqual(tolerance);
}

export async function findLayoutViolations(page: Page, selectors = DEFAULT_LAYOUT_SELECTORS) {
  return page.evaluate((selectorList) => {
    const violations: LayoutViolation[] = [];
    const elements = Array.from(document.querySelectorAll(selectorList));
    const viewportWidth = window.innerWidth;
    const tolerance = 2;

    const isVisible = (element: Element) => {
      const style = window.getComputedStyle(element);
      if (style.display === 'none' || style.visibility === 'hidden' || Number.parseFloat(style.opacity || '1') === 0) {
        return false;
      }

      const rect = element.getBoundingClientRect();
      return rect.width > 0 && rect.height > 0;
    };

    for (const element of elements) {
      if (!isVisible(element)) continue;

      const rect = element.getBoundingClientRect();
      const text = (element.textContent || '').replace(/\s+/g, ' ').trim();
      if (!text) continue;

      const style = window.getComputedStyle(element);
      const lineHeight = Number.parseFloat(style.lineHeight);
      const fontSize = Number.parseFloat(style.fontSize);
      const effectiveLineHeight = Number.isFinite(lineHeight) ? lineHeight : (Number.isFinite(fontSize) ? fontSize * 1.2 : 16);
      const estimatedLines = Math.max(1, rect.height / Math.max(1, effectiveLineHeight));
      const charsPerLine = text.length / estimatedLines;
      const className = typeof element.className === 'string' ? element.className : '';
      const tagName = element.tagName.toLowerCase();
      const looksLikeChip = /rounded|uppercase|tracking|text-xs|text-\[10px\]|whitespace-nowrap|badge|pill|chip/i.test(className);
      const isInteractive = tagName === 'button' || tagName === 'a' || element.getAttribute('role') === 'button' || tagName === 'label';
      const shouldInspect = tagName.startsWith('h') || isInteractive || looksLikeChip || tagName === 'span';

      if (!shouldInspect) continue;

      const parentRect = element.parentElement?.getBoundingClientRect();
      if (parentRect) {
        const overflowRight = rect.right - parentRect.right;
        const overflowLeft = parentRect.left - rect.left;
        if (overflowRight > tolerance || overflowLeft > tolerance) {
          violations.push({
            selector: tagName,
            text,
            reason: `overflows parent container by ${Math.max(overflowRight, overflowLeft).toFixed(1)}px`
          });
          continue;
        }
      }

      if (rect.width < 120 && rect.height > 60 && estimatedLines >= 4 && charsPerLine <= 4.5) {
        violations.push({
          selector: tagName,
          text,
          reason: `looks crushed: width=${rect.width.toFixed(1)} height=${rect.height.toFixed(1)} lines=${estimatedLines.toFixed(1)}`
        });
        continue;
      }

      if (isInteractive && text.length >= 8 && rect.width < 140 && rect.height > 52 && estimatedLines >= 3 && charsPerLine <= 5.5) {
        violations.push({
          selector: tagName,
          text,
          reason: `interactive text is too narrow: width=${rect.width.toFixed(1)} height=${rect.height.toFixed(1)} lines=${estimatedLines.toFixed(1)}`
        });
        continue;
      }

      if (looksLikeChip && text.length >= 14 && rect.width > viewportWidth + tolerance) {
        violations.push({
          selector: tagName,
          text,
          reason: `chip wider than viewport: width=${rect.width.toFixed(1)} viewport=${viewportWidth}`
        });
      }
    }

    return violations;
  }, selectors);
}

export function routeSlug(route: string) {
  if (route === '/') return 'home';
  return route
    .replace(/^\/+|\/+$/g, '')
    .replace(/\[(.+?)\]/g, '$1')
    .replace(/\//g, '-')
    .replace(/[^a-zA-Z0-9-]+/g, '-')
    .replace(/-+/g, '-')
    .toLowerCase();
}

export function authLabel(authType: 'public' | 'parent' | 'child' | 'admin' | 'dev-only' | 'unknown') {
  return authType === 'parent' ? 'parent' : authType;
}
