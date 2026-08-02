import { expect, test, type Page } from "@playwright/test";
import { collectInternalLinks, createBrowserIssueTracker } from "./qa-support";

type PageCase = {
  path: string;
  heading: string;
  headingLevel?: "h1" | "h2";
  expectedText?: string;
  safeClickTarget?: string;
};

const PUBLIC_CASES: PageCase[] = [
  {
    path: "/",
    heading: "One clear place for the work that keeps a school moving.",
    headingLevel: "h1",
    expectedText: "Parents use Family Hero Hub",
    safeClickTarget: "/login",
  },
  {
    path: "/features",
    heading: "The connected school workflows that matter now.",
    expectedText: "Behaviour and positive recognition",
    safeClickTarget: "/pilot",
  },
  {
    path: "/how-it-works",
    heading: "A clear path from school setup to family understanding.",
    expectedText: "Family Hero Hub displays enabled school information",
    safeClickTarget: "/features",
  },
  {
    path: "/schools",
    heading:
      "A school platform people can understand before they have to master it.",
    expectedText: "For school leaders",
    safeClickTarget: "/pilot",
  },
  {
    path: "/family-connection",
    heading:
      "School information reaches parents without giving parents staff-system access.",
    expectedText: "There is no CHH parent app",
    safeClickTarget: "/guides/families",
  },
  {
    path: "/pilot",
    heading: "Start with the school problem you want to solve.",
    expectedText: "No published pricing yet",
    safeClickTarget: "/features",
  },
  {
    path: "/login",
    heading: "Welcome to Class Hero Hub",
    headingLevel: "h1",
    expectedText: "Continue with Google",
    safeClickTarget: "/",
  },
  {
    path: "/privacy",
    heading: "Privacy Policy",
    headingLevel: "h1",
    expectedText: "Legal review required",
    safeClickTarget: "/terms",
  },
  {
    path: "/terms",
    heading: "Terms of Service",
    headingLevel: "h1",
    expectedText: "Authorised users and roles",
    safeClickTarget: "/privacy",
  },
  {
    path: "/data-requests",
    heading: "Start with the organisation that controls the record.",
    expectedText: "Identity checks may be required",
    safeClickTarget: "/privacy",
  },
  {
    path: "/contact",
    heading: "Talk to the Class Hero Hub team.",
    headingLevel: "h1",
    expectedText: "support@classherohub.com",
    safeClickTarget: "/faq",
  },
  {
    path: "/faq",
    heading: "Frequently asked questions",
    headingLevel: "h1",
    expectedText: "Do parents log in to Class Hero Hub?",
    safeClickTarget: "/contact",
  },
  {
    path: "/safety-privacy",
    heading:
      "Clear authority for school data. Deliberate boundaries for protected work.",
    headingLevel: "h1",
    expectedText: "Safeguarding is a separate mode",
    safeClickTarget: "/contact",
  },
  {
    path: "/guides/administrator",
    heading: "Build a reliable school foundation before the busy work begins.",
    expectedText: "Create the academic structure",
    safeClickTarget: "/guides/teacher",
  },
  {
    path: "/guides/teacher",
    heading: "Work from the class context, with the next action close at hand.",
    expectedText: "Remember the parent boundary",
    safeClickTarget: "/safety-privacy",
  },
  {
    path: "/guides/families",
    heading: "Parents use Family Hero Hub for linked school information.",
    expectedText: "No Class Hero Hub parent app",
    safeClickTarget: "/family-connection",
  },
];

const SAFE_PUBLIC_PATHS = new Set([
  "/",
  "/features",
  "/how-it-works",
  "/schools",
  "/family-connection",
  "/pilot",
  "/login",
  "/privacy",
  "/terms",
  "/data-requests",
  "/contact",
  "/faq",
  "/safety-privacy",
  "/guides/administrator",
  "/guides/teacher",
  "/guides/families",
]);

async function assertPublicPage(page: Page, testCase: PageCase) {
  const tracker = createBrowserIssueTracker(page);
  tracker.ignoreConsoleErrorSnippet(
    "the server responded with a status of 401",
  );

  await page.route("**/api/me", async (route) => {
    await route.fulfill({
      status: 401,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Not authenticated" }),
    });
  });
  await page.route("**/api/auth/refresh", async (route) => {
    await route.fulfill({
      status: 401,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Not authenticated" }),
    });
  });

  await page.goto(testCase.path, { waitUntil: "networkidle" });
  await page.waitForTimeout(250);

  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  await expect(page.locator("html")).toHaveAttribute("dir", "ltr");
  expect(await page.locator("body").innerText()).not.toContain("TODO");
  const overflow = await page.evaluate(
    () =>
      document.documentElement.scrollWidth -
      document.documentElement.clientWidth,
  );
  expect(overflow, `${testCase.path} horizontal overflow`).toBeLessThanOrEqual(
    1,
  );

  const links = await collectInternalLinks(page);
  expect(
    links.length,
    `${testCase.path} internal link inventory`,
  ).toBeGreaterThan(0);

  const safeLinks = links.filter((link) =>
    SAFE_PUBLIC_PATHS.has(new URL(link.href, page.url()).pathname),
  );
  expect(
    safeLinks.length,
    `${testCase.path} safe public links`,
  ).toBeGreaterThan(0);
  for (const link of safeLinks) {
    const resolved = new URL(link.href, page.url());
    const response = await page.request.get(resolved.toString());
    expect(
      response.ok(),
      `${testCase.path} internal link ${resolved.pathname}`,
    ).toBeTruthy();
  }

  const heading = page.locator(testCase.headingLevel ?? "h1", {
    hasText: testCase.heading,
  });
  await expect(heading).toBeVisible();

  if (testCase.expectedText) {
    await expect(
      page.getByText(testCase.expectedText, { exact: false }).first(),
    ).toBeVisible();
  }

  if (testCase.safeClickTarget) {
    const safeLink = page
      .locator(`a[href="${testCase.safeClickTarget}"]`)
      .first();
    await expect(
      safeLink,
      `${testCase.path} safe link ${testCase.safeClickTarget}`,
    ).toBeVisible();
    await safeLink.click();
    await expect(page).toHaveURL(
      new RegExp(
        `${testCase.safeClickTarget.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}$`,
      ),
    );
  }

  expect(tracker.issues.pageErrors, `${testCase.path} page errors`).toEqual([]);
  expect(
    tracker.issues.consoleErrors,
    `${testCase.path} console errors`,
  ).toEqual([]);
}

test.describe("Europe dev public pages", () => {
  for (const testCase of PUBLIC_CASES) {
    test(`${testCase.path} renders without browser errors`, async ({
      page,
    }) => {
      await assertPublicPage(page, testCase);
    });
  }

  test("public website switches to Arabic RTL without changing the route", async ({
    page,
  }) => {
    await page.route("**/api/me", (route) =>
      route.fulfill({ status: 401, json: { detail: "Not authenticated" } }),
    );
    await page.route("**/api/auth/refresh", (route) =>
      route.fulfill({ status: 401, json: { detail: "Not authenticated" } }),
    );
    await page.goto("/", { waitUntil: "networkidle" });
    await page.getByRole("combobox", { name: "Language" }).selectOption("ar");

    await expect(page).toHaveURL(/\/$/);
    await expect(page.locator("html")).toHaveAttribute("lang", "ar");
    await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
    await expect(
      page.getByRole("heading", {
        level: 1,
        name: "مكان واحد واضح للعمل الذي يحافظ على سير المدرسة.",
      }),
    ).toBeVisible();
    await expect(
      page.getByText(
        "كلاس هيرو هب لموظفي المدرسة والأدوار المدرسية المصرح لها.",
        { exact: false },
      ),
    ).toBeVisible();
    const overflow = await page.evaluate(
      () =>
        document.documentElement.scrollWidth -
        document.documentElement.clientWidth,
    );
    expect(overflow).toBeLessThanOrEqual(1);
  });

  test("native root bypasses the public website and opens staff login when signed out", async ({
    page,
  }) => {
    await page.addInitScript(() =>
      Object.assign(window, { androidBridge: {} }),
    );
    await page.route("**/api/me", (route) =>
      route.fulfill({ status: 401, json: { detail: "Not authenticated" } }),
    );
    await page.route("**/api/auth/refresh", (route) =>
      route.fulfill({ status: 401, json: { detail: "Not authenticated" } }),
    );
    await page.goto("/");

    await expect(page).toHaveURL(/\/login$/);
    await expect(
      page.getByRole("heading", {
        level: 1,
        name: "Welcome to Class Hero Hub",
      }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", {
        level: 1,
        name: "One clear place for the work that keeps a school moving.",
      }),
    ).toHaveCount(0);
  });
});
