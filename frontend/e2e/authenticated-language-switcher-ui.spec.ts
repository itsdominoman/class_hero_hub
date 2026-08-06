import { expect, test, type Page, type Route } from "@playwright/test";

const LANGUAGE_KEY = "familyHeroHub.language";
const CONTEXT_PATH = "/faq?tab=years&membership=102&context=school-7";

async function json(route: Route, body: unknown, status = 200) {
  await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
}

async function emulateAndroidShell(page: Page) {
  await page.addInitScript(() => {
    Object.assign(window, { androidBridge: {} });
    Object.assign(globalThis, {
      Capacitor: {
        isNativePlatform: () => true,
        getPlatform: () => "android",
        PluginHeaders: [
          {
            name: "SecureStorage",
            methods: [
              { name: "get", rtype: "promise" },
              { name: "set", rtype: "promise" },
              { name: "remove", rtype: "promise" },
            ],
          },
          {
            name: "App",
            methods: [
              { name: "addListener", rtype: "callback" },
              { name: "removeListener", rtype: "callback" },
              { name: "exitApp", rtype: "promise" },
            ],
          },
        ],
        nativePromise: async (plugin: string, method: string, options: { key?: string } = {}) => {
          if (plugin === "SecureStorage" && method === "get") {
            return { value: options.key === "chh_access_token" ? "language-switcher-token" : null };
          }
          return {};
        },
        nativeCallback: () => "language-switcher-listener",
      },
    });
  });
}

async function mockAuthenticatedShell(page: Page, initialLocale?: "en" | "ar") {
  if (initialLocale) {
    await page.addInitScript(
      ({ key, value }) => {
        if (!localStorage.getItem(key)) localStorage.setItem(key, value);
      },
      { key: LANGUAGE_KEY, value: initialLocale },
    );
  }

  const membership = {
    membership_id: 102,
    school_id: 7,
    school_name: "Language Test School",
    role: "school_admin",
    capabilities: [],
  };
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("/api/me") || path.endsWith("/api/me/v2")) {
      await json(route, {
        user: { id: 5, name: "Language Test User" },
        is_platform_admin: false,
        can_manage_school_entitlements: false,
        memberships: [membership],
      });
      return;
    }
    if (path.endsWith("/safeguarding/availability")) {
      await json(route, { available: false });
      return;
    }
    if (path.endsWith("/school/surveys/availability")) {
      await json(route, { available: true });
      return;
    }
    if (path.endsWith("/messaging/unread-count")) {
      await json(route, { total: 0, conversations: 0 });
      return;
    }
    await json(route, {});
  });
}

async function expectStoredLanguage(page: Page, expected: "en" | "ar") {
  await expect.poll(() => page.evaluate((key) => localStorage.getItem(key), LANGUAGE_KEY)).toBe(expected);
}

for (const width of [1280, 1440]) {
  test(`desktop authenticated switcher preserves route and persists both directions at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await mockAuthenticatedShell(page, "en");
    await page.goto(CONTEXT_PATH);

    await expect(page.locator('a[href="/school"]').filter({ hasText: "Dashboard" }).first()).toBeVisible({ timeout: 15_000 });
    const selector = page.locator(".app-header nav").getByTestId("language-selector");
    await expect(selector).toBeVisible({ timeout: 15_000 });
    await expect(selector.getByTestId("language-globe")).toBeVisible();
    const englishControl = selector;
    await expect(englishControl).toHaveAccessibleName("التبديل إلى العربية");
    await expect(englishControl).toContainText("العربية");
    await englishControl.focus();
    await expect(englishControl).toBeFocused();

    const initialUrl = page.url();
    await englishControl.click();
    await expect(page).toHaveURL(initialUrl);
    await expect(page.locator("html")).toHaveAttribute("lang", "ar");
    await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
    await expect(selector).toHaveAccessibleName("Switch to English");
    await expect(selector).toContainText("English");
    await expectStoredLanguage(page, "ar");

    await page.reload();
    await expect(page).toHaveURL(initialUrl);
    await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
    const arabicControl = page.locator(".app-header nav").getByTestId("language-selector");
    await expect(arabicControl).toHaveAccessibleName("Switch to English");
    await arabicControl.click();
    await expect(page).toHaveURL(initialUrl);
    await expect(page.locator("html")).toHaveAttribute("lang", "en");
    await expect(page.locator("html")).toHaveAttribute("dir", "ltr");
    await expectStoredLanguage(page, "en");

    await page.reload();
    await expect(page).toHaveURL(initialUrl);
    await expect(page.locator("html")).toHaveAttribute("dir", "ltr");
    await expect(page.locator(".app-header nav").getByTestId("language-selector")).toHaveAccessibleName("التبديل إلى العربية");
    expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(1);
  });
}

for (const width of [390, 768, 1024]) {
  test(`drawer switcher preserves native route, direction and Back order at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await emulateAndroidShell(page);
    await mockAuthenticatedShell(page, "en");
    await page.goto(CONTEXT_PATH);

    await page.getByRole("button", { name: "Open menu" }).click();
    let drawer = page.getByRole("dialog", { name: "Menu" });
    const selector = drawer.getByTestId("language-selector");
    await expect(selector.getByTestId("language-globe")).toBeVisible();
    const initialUrl = page.url();
    await expect(selector).toHaveAccessibleName("التبديل إلى العربية");
    await selector.click();

    drawer = page.getByRole("dialog", { name: "القائمة" });
    await expect(drawer).toBeVisible();
    await expect(page).toHaveURL(initialUrl);
    await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
    await expect(drawer.getByTestId("language-selector")).toHaveAccessibleName("Switch to English");
    await expectStoredLanguage(page, "ar");
    const drawerBox = await drawer.boundingBox();
    expect(drawerBox?.x ?? 1).toBeLessThanOrEqual(1);

    await page.evaluate(() => window.dispatchEvent(new Event("chh:native-back", { cancelable: true })));
    await expect(drawer).not.toBeVisible();
    await expect(page).toHaveURL(initialUrl);

    await page.reload();
    await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
    await page.getByRole("button", { name: "فتح القائمة" }).click();
    await expect(page.getByRole("dialog", { name: "القائمة" }).getByTestId("language-selector")).toHaveAccessibleName("Switch to English");
    expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(1);
  });
}

test("native language preference survives cold pages and a later authenticated session", async ({ page, context }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await emulateAndroidShell(page);
  await mockAuthenticatedShell(page, "en");
  await page.goto(CONTEXT_PATH);
  await page.getByRole("button", { name: "Open menu" }).click();
  await page.getByRole("dialog", { name: "Menu" }).getByRole("button", { name: "التبديل إلى العربية" }).click();
  const preservedUrl = page.url();
  await page.close();

  const restarted = await context.newPage();
  await restarted.setViewportSize({ width: 390, height: 844 });
  await emulateAndroidShell(restarted);
  await mockAuthenticatedShell(restarted);
  await restarted.goto(preservedUrl);
  await expect(restarted.locator("html")).toHaveAttribute("dir", "rtl");
  await restarted.getByRole("button", { name: "فتح القائمة" }).click();
  await restarted.getByRole("dialog", { name: "القائمة" }).getByRole("button", { name: "Switch to English" }).click();
  await expect(restarted.locator("html")).toHaveAttribute("dir", "ltr");
  await expectStoredLanguage(restarted, "en");
  await restarted.close();

  const laterSession = await context.newPage();
  await laterSession.setViewportSize({ width: 390, height: 844 });
  await emulateAndroidShell(laterSession);
  await mockAuthenticatedShell(laterSession);
  await laterSession.goto(preservedUrl);
  await expect(laterSession).toHaveURL(preservedUrl);
  await expect(laterSession.locator("html")).toHaveAttribute("lang", "en");
  await expect(laterSession.locator("html")).toHaveAttribute("dir", "ltr");
  await laterSession.getByRole("button", { name: "Open menu" }).click();
  await expect(laterSession.getByRole("dialog", { name: "Menu" }).getByRole("button", { name: "التبديل إلى العربية" })).toContainText("العربية");
});

test("public login language behaviour remains available and route-neutral", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.addInitScript((key) => {
    if (!localStorage.getItem(key)) localStorage.setItem(key, "en");
  }, LANGUAGE_KEY);
  let meRequests = 0;
  await page.route("**/api/**", (route) => {
    if (new URL(route.request().url()).pathname.endsWith("/me")) meRequests += 1;
    return json(route, { detail: "Unauthenticated" }, 401);
  });
  await page.goto("/login?return=%2Fschool%3Ftab%3Dyears");

  const initialUrl = page.url();
  const selector = page.locator('[data-testid="language-selector"]:visible');
  await expect(selector).toHaveCount(1);
  await expect.poll(() => meRequests).toBeGreaterThanOrEqual(2);
  await expect(selector.getByTestId("language-globe")).toBeVisible();
  const control = selector;
  await expect(control).toHaveAccessibleName("التبديل إلى العربية");
  await expect(control).toContainText("العربية");
  await control.click();
  await expect(page).toHaveURL(initialUrl);
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  await expectStoredLanguage(page, "ar");
});
