import { expect, test } from "@playwright/test";
import { createBrowserIssueTracker } from "./qa-support";

const PUBLIC_ROUTES = [
  "/",
  "/features",
  "/how-it-works",
  "/schools",
  "/family-connection",
  "/faq",
  "/pilot",
  "/contact",
  "/guides/administrator",
  "/guides/teacher",
  "/guides/families",
  "/safety-privacy",
  "/privacy",
  "/terms",
  "/data-requests",
  "/login",
] as const;

const VIEWPORTS = [390, 768, 1024, 1280, 1440] as const;
const LANGUAGES = [
  {
    code: "en",
    direction: "ltr",
    navigationName: "Explore Class Hero Hub",
    openMenuName: "Open website menu",
  },
  {
    code: "ar",
    direction: "rtl",
    navigationName: "استكشف كلاس هيرو هب",
    openMenuName: "فتح قائمة الموقع",
  },
] as const;

for (const language of LANGUAGES) {
  for (const width of VIEWPORTS) {
    test(`all public routes render in ${language.code.toUpperCase()} at ${width}px`, async ({
      page,
    }) => {
      const tracker = createBrowserIssueTracker(page);
      tracker.ignoreConsoleErrorSnippet(
        "the server responded with a status of 401",
      );

      await page.setViewportSize({ width, height: 900 });
      await page.addInitScript((code) => {
        localStorage.setItem("familyHeroHub.language", code);
      }, language.code);
      await page.route("**/api/me", (route) =>
        route.fulfill({ status: 401, json: { detail: "Not authenticated" } }),
      );
      await page.route("**/api/auth/refresh", (route) =>
        route.fulfill({ status: 401, json: { detail: "Not authenticated" } }),
      );

      for (const path of PUBLIC_ROUTES) {
        await page.goto(path, { waitUntil: "networkidle" });

        await expect(page.locator("html")).toHaveAttribute(
          "lang",
          language.code,
        );
        await expect(page.locator("html")).toHaveAttribute(
          "dir",
          language.direction,
        );
        await expect(page.locator("main h1")).toBeVisible();

        const overflow = await page.evaluate(
          () =>
            document.documentElement.scrollWidth -
            document.documentElement.clientWidth,
        );
        expect(
          overflow,
          `${path} ${language.code} overflow at ${width}px`,
        ).toBeLessThanOrEqual(1);

        const desktopNavigationVisible = await page
          .getByRole("navigation", { name: language.navigationName })
          .isVisible();
        const compactMenuVisible = await page
          .getByRole("button", { name: language.openMenuName })
          .isVisible();
        expect(
          desktopNavigationVisible || compactMenuVisible,
          `${path} ${language.code} has an accessible navigation entry point at ${width}px`,
        ).toBeTruthy();

        const brokenImages = await page.evaluate(() =>
          Array.from(document.images)
            .filter((image) => image.complete && image.naturalWidth === 0)
            .map((image) => image.getAttribute("src") || ""),
        );
        expect(
          brokenImages,
          `${path} ${language.code} broken images at ${width}px`,
        ).toEqual([]);

        if (path === "/") {
          const productImages = page.locator('img[src^="/product/"]');
          await expect(productImages).toHaveCount(2);
          await productImages.evaluateAll((images) => {
            for (const image of images)
              image.scrollIntoView({ block: "center" });
          });
          await expect
            .poll(() =>
              productImages.evaluateAll((images) =>
                images.every(
                  (image) =>
                    image instanceof HTMLImageElement && image.naturalWidth > 0,
                ),
              ),
            )
            .toBe(true);
        }
      }

      expect(tracker.issues.pageErrors).toEqual([]);
      expect(tracker.issues.consoleErrors).toEqual([]);
    });
  }
}
