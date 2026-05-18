import { expect, type Locator, type Page } from '@playwright/test';

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

type QaLoginKind = 'parent' | 'child';

type ReadableElementOptions = {
  label: string;
  minWidth?: number;
  maxHeight?: number;
  maxLines?: number;
  minCharsPerLine?: number;
};

export type QaChildSession = {
  childId: number;
  childName: string;
  childRoute: string;
  familyId: number;
  reused: boolean;
  parentEmail: string;
};

type QaChildLoginResponse = {
  status: string;
  parent_email: string;
  family_id: number;
  child_id: number;
  child_name: string;
  child_route: string;
  reused: boolean;
};

const DEFAULT_LAYOUT_SELECTORS = [
  'main h1',
  'main h2',
  'main h3',
  'main h4',
  'main button',
  'main a',
  'main [role="button"]',
  'main span',
  'main input',
  'main textarea',
  'main select'
].join(', ');

const ROUTED_PAGES = new WeakSet<Page>();

function resolveQaLoginToken(kind: QaLoginKind) {
  if (kind === 'child') {
    return (process.env.QA_CHILD_LOGIN_TOKEN?.trim() || process.env.QA_LOGIN_TOKEN?.trim() || '');
  }
  return process.env.QA_LOGIN_TOKEN?.trim() || '';
}

function resolveQaLoginBaseUrl() {
  return process.env.QA_LOGIN_API_BASE_URL?.trim() || 'http://127.0.0.1:8000';
}

function resolveFrontendBaseUrl() {
  return process.env.PLAYWRIGHT_BASE_URL?.trim() || 'http://127.0.0.1:5173';
}

async function routeBackendApis(page: Page) {
  if (ROUTED_PAGES.has(page)) {
    return;
  }

  const backendBaseUrl = resolveQaLoginBaseUrl();
  await page.route('**/api/**', async (route) => {
    const requestUrl = new URL(route.request().url());
    const backendUrl = new URL(`${requestUrl.pathname}${requestUrl.search}`, backendBaseUrl);
    try {
      const backendResponse = await route.fetch({ url: backendUrl.toString() });
      await route.fulfill({ response: backendResponse });
    } catch (e) {
      // Catch "Fetch response has been disposed" if navigation happens during fetch
      if (!route.request().isNavigationRequest()) {
        try { await route.abort(); } catch { /* ignore */ }
      }
    }
  });
  ROUTED_PAGES.add(page);
}

function extractCookies(headersArray: Array<{ name: string; value: string }>) {
  return headersArray
    .filter((header) => header.name.toLowerCase() === 'set-cookie')
    .map((header) => {
      const cookieHeader = header.value;
      const parts = cookieHeader.split(';').map(p => p.trim());
      const [nameValue, ...attributes] = parts;
      const [name, value] = nameValue.split('=');

      const cookie: any = { name, value };

      for (const attr of attributes) {
        const [attrName] = attr.split('=');
        if (attrName.toLowerCase() === 'httponly') {
          cookie.httpOnly = true;
        }
      }

      return cookie;
    });
}

async function applySessionCookies(page: Page, loginResponse: { headersArray: () => Array<{ name: string; value: string }> }) {
  const loginCookies = extractCookies(loginResponse.headersArray());
  if (loginCookies.length === 0) {
    return;
  }

  const cookieUrls = Array.from(new Set([resolveQaLoginBaseUrl(), resolveFrontendBaseUrl()]));

  await page.context().addCookies(
    cookieUrls.flatMap((url) =>
      loginCookies.map((cookie) => ({
        ...cookie,
        url
      }))
    )
  );
}

async function assertElementReadable(locator: Locator, options: ReadableElementOptions) {
  const target = locator.first();
  await expect(target, `${options.label} visible`).toBeVisible();

  const metrics = await target.evaluate((element) => {
    const rect = element.getBoundingClientRect();
    const computed = window.getComputedStyle(element);
    const lineHeight = Number.parseFloat(computed.lineHeight);
    const fontSize = Number.parseFloat(computed.fontSize);
    const effectiveLineHeight = Number.isFinite(lineHeight) ? lineHeight : (Number.isFinite(fontSize) ? fontSize * 1.2 : 16);
    const text = (element.textContent || '').replace(/\s+/g, ' ').trim();
    const estimatedLines = Math.max(1, rect.height / Math.max(1, effectiveLineHeight));
    const charsPerLine = text.length / estimatedLines;

    return {
      tagName: element.tagName.toLowerCase(),
      width: rect.width,
      height: rect.height,
      text,
      estimatedLines,
      charsPerLine
    };
  });

  const minWidth = options.minWidth ?? 80;
  const maxHeight = options.maxHeight ?? 220;
  const maxLines = options.maxLines ?? 4;
  const minCharsPerLine = options.minCharsPerLine ?? 4;
  const isFormControl = ['input', 'textarea', 'select'].includes(metrics.tagName);

  expect(metrics.width, `${options.label} width`).toBeGreaterThanOrEqual(minWidth);
  expect(metrics.height, `${options.label} height`).toBeLessThanOrEqual(maxHeight);
  if (!isFormControl && metrics.text.length > 0) {
    expect(metrics.estimatedLines, `${options.label} line count`).toBeLessThanOrEqual(maxLines);
  }
  if (!isFormControl && metrics.text.length >= 10) {
    expect(metrics.charsPerLine, `${options.label} chars per line`).toBeGreaterThanOrEqual(minCharsPerLine);
  }
}

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
  const qaToken = resolveQaLoginToken('parent');
  if (!qaToken) {
    throw new Error('QA_LOGIN_TOKEN is required for authenticated browser QA');
  }

  const loginUrl = new URL('/api/dev/qa-login', resolveQaLoginBaseUrl());
  const loginResponse = await page.request.post(loginUrl.toString(), {
    data: { token: qaToken }
  });

  expect(loginResponse.status()).toBe(200);
  const loginBody = await loginResponse.text();
  expect(loginBody).toContain('"status":"ok"');
  expect(loginBody).toContain('"email":"qa-parent@dev.familyherohub.com"');

  await applySessionCookies(page, loginResponse);
  await routeBackendApis(page);
}

export async function setupQaChildSession(page: Page): Promise<QaChildSession> {
  const qaToken = resolveQaLoginToken('child');
  if (!qaToken) {
    throw new Error('QA_CHILD_LOGIN_TOKEN or QA_LOGIN_TOKEN is required for child browser QA');
  }

  const loginUrl = new URL('/api/dev/qa-child-login', resolveQaLoginBaseUrl());
  const loginResponse = await page.request.post(loginUrl.toString(), {
    data: { token: qaToken }
  });

  expect(loginResponse.status()).toBe(200);
  const loginBody = await loginResponse.text();
  expect(loginBody).toContain('"status":"ok"');
  expect(loginBody).toContain('"child_name":"QA Seed Child"');

  await applySessionCookies(page, loginResponse);
  await routeBackendApis(page);

  const payload = JSON.parse(loginBody) as QaChildLoginResponse;
  return {
    childId: payload.child_id,
    childName: payload.child_name,
    childRoute: payload.child_route,
    familyId: payload.family_id,
    reused: payload.reused,
    parentEmail: payload.parent_email
  };
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
      const isInteractive = tagName === 'button' || tagName === 'a' || element.getAttribute('role') === 'button';
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

export async function assertReadableElement(locator: Locator, options: ReadableElementOptions) {
  await assertElementReadable(locator, options);
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
