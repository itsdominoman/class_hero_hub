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
    heading: "Give staff one clear place to keep school life moving.",
    headingLevel: "h1",
    expectedText: "Demonstration school and staff data only.",
    safeClickTarget: "/login",
  },
  {
    path: "/features",
    heading: "The tools schools need, without the usual maze.",
    expectedText: "Everyday teaching workflows",
    safeClickTarget: "/pilot",
  },
  {
    path: "/how-it-works",
    heading: "A simpler route from school setup to everyday use.",
    expectedText: "Carry useful information home",
    safeClickTarget: "/features",
  },
  {
    path: "/schools",
    heading: "Built around the people who keep a school running.",
    expectedText: "For school leaders",
    safeClickTarget: "/pilot",
  },
  {
    path: "/family-connection",
    heading: "School updates meet families where family life already happens.",
    expectedText: "Parents see school information in Family Hero Hub",
    safeClickTarget: "/guides/families",
  },
  {
    path: "/pilot",
    heading: "Let’s start with a conversation about your school.",
    expectedText: "Send pilot enquiry",
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
    expectedText: "Necessary service providers",
    safeClickTarget: "/terms",
  },
  {
    path: "/terms",
    heading: "Terms of Service",
    headingLevel: "h1",
    expectedText: "Authorised accounts",
    safeClickTarget: "/privacy",
  },
  {
    path: "/data-requests",
    heading: "Start with the team that knows the record.",
    expectedText: "Keep the first message simple",
    safeClickTarget: "/privacy",
  },
  {
    path: "/contact",
    heading: "How can we help?",
    headingLevel: "h1",
    expectedText: "support@classherohub.com",
    safeClickTarget: "/faq",
  },
  {
    path: "/faq",
    heading: "The practical questions schools ask first.",
    headingLevel: "h1",
    expectedText: "Do parents sign in to Class Hero Hub?",
    safeClickTarget: "/contact",
  },
  {
    path: "/safety-privacy",
    heading: "Practical safeguards for everyday school work.",
    headingLevel: "h1",
    expectedText: "Safeguarding review is separate",
    safeClickTarget: "/contact",
  },
  {
    path: "/guides/administrator",
    heading: "Build a school workspace people can rely on.",
    expectedText: "Start with the academic structure",
    safeClickTarget: "/guides/teacher",
  },
  {
    path: "/guides/teacher",
    heading: "Start with your classes. Keep the next action close.",
    expectedText: "Share useful updates",
    safeClickTarget: "/safety-privacy",
  },
  {
    path: "/guides/families",
    heading: "Parents see school information in Family Hero Hub.",
    expectedText: "Use the right place for help",
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
        name: "مكان واحد واضح يساعد الموظفين على إبقاء المدرسة في حركة.",
      }),
    ).toBeVisible();
    await expect(
      page.getByText(
        "لقادة المدارس والمسؤولين والمعلمين · العربية والإنجليزية",
        {
          exact: true,
        },
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
        name: "Give staff one clear place to keep school life moving.",
      }),
    ).toHaveCount(0);
  });

  test("pilot enquiry shows success only after the server accepts the message", async ({
    page,
  }) => {
    await page.route("**/api/me", (route) =>
      route.fulfill({ status: 401, json: { detail: "Not authenticated" } }),
    );
    await page.route("**/api/auth/refresh", (route) =>
      route.fulfill({ status: 401, json: { detail: "Not authenticated" } }),
    );
    await page.route("**/api/public/pilot-enquiries", (route) =>
      route.fulfill({ status: 200, json: { status: "sent" } }),
    );
    await page.goto("/pilot", { waitUntil: "networkidle" });

    await page.getByLabel("Your name").fill("Amina Patel");
    await page.getByLabel("School", { exact: true }).fill("Riverside School");
    await page.getByLabel("Your role").fill("Deputy principal");
    await page.getByLabel("Country or region").fill("Oman");
    await page.getByLabel("Work email").fill("amina@example.com");
    await page
      .getByLabel("What would you like to improve?")
      .fill("We would like to make family communication easier for teachers.");
    await page.getByRole("button", { name: "Send pilot enquiry" }).click();

    await expect(
      page.getByRole("heading", {
        name: "Thank you — your enquiry has been sent.",
      }),
    ).toBeVisible();
  });

  test("pilot enquiry reports delivery failure without showing success", async ({
    page,
  }) => {
    await page.route("**/api/me", (route) =>
      route.fulfill({ status: 401, json: { detail: "Not authenticated" } }),
    );
    await page.route("**/api/auth/refresh", (route) =>
      route.fulfill({ status: 401, json: { detail: "Not authenticated" } }),
    );
    await page.route("**/api/public/pilot-enquiries", (route) =>
      route.fulfill({ status: 503, json: { detail: "Unavailable" } }),
    );
    await page.goto("/pilot", { waitUntil: "networkidle" });

    await page.getByLabel("Your name").fill("Amina Patel");
    await page.getByLabel("School", { exact: true }).fill("Riverside School");
    await page.getByLabel("Your role").fill("Deputy principal");
    await page.getByLabel("Country or region").fill("Oman");
    await page.getByLabel("Work email").fill("amina@example.com");
    await page
      .getByLabel("What would you like to improve?")
      .fill("We would like to make family communication easier for teachers.");
    await page.getByRole("button", { name: "Send pilot enquiry" }).click();

    await expect(
      page.getByText(
        "Email delivery is temporarily unavailable. Please use the direct email option below.",
      ),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", {
        name: "Thank you — your enquiry has been sent.",
      }),
    ).toHaveCount(0);
  });
});
