import { expect, test, type Page, type Route } from "@playwright/test";

const membership = {
  membership_id: 51,
  school_id: 7,
  school_name: "Al Noor School",
  role: "school_admin",
};

async function mockSurveyWorkspace(page: Page) {
  await page.route("**/api/**", async (route: Route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("/api/me")) {
      await route.fulfill({
        json: {
          id: 5,
          name: "School Administrator",
          is_platform_admin: false,
          memberships: [membership],
        },
      });
      return;
    }
    if (path.endsWith("/school/surveys/availability")) {
      await route.fulfill({ json: { available: true } });
      return;
    }
    if (path.endsWith("/school/surveys/context")) {
      await route.fulfill({
        json: {
          school: { id: 7, name: "Al Noor School", timezone: "Asia/Muscat" },
          branches: [],
          grades: [],
          classes: [],
          linked_families: [],
        },
      });
      return;
    }
    if (path.endsWith("/school/surveys/permissions")) {
      await route.fulfill({ json: { can_manage: false, administrators: [] } });
      return;
    }
    if (path.endsWith("/school/surveys")) {
      await route.fulfill({ json: { items: [] } });
      return;
    }
    await route.fulfill({
      status: 404,
      json: { detail: "Not available in this test" },
    });
  });
}

for (const { width, height } of [
  { width: 390, height: 844 },
  { width: 768, height: 900 },
]) {
  for (const language of ["en", "ar"] as const) {
    test(`survey composer is a bounded ${language.toUpperCase()} dialog at ${width}px`, async ({
      page,
    }) => {
      await page.setViewportSize({ width, height });
      await page.addInitScript(
        (value) => localStorage.setItem("familyHeroHub.language", value),
        language,
      );
      await mockSurveyWorkspace(page);
      await page.goto("/school/surveys?membership=51");

      const createLabel = language === "ar" ? "إنشاء استبيان" : "Create survey";
      const closeLabel = language === "ar" ? "إغلاق" : "Close";
      const title = language === "ar" ? "تفاصيل الاستبيان" : "Survey details";
      const opener = page.getByRole("button", { name: createLabel });
      await opener.click();

      const dialog = page.getByRole("dialog", { name: title });
      const close = page.getByRole("button", { name: closeLabel, exact: true });
      await expect(dialog).toBeVisible();
      await expect(dialog).toHaveAttribute("aria-modal", "true");
      await expect(close).toBeVisible();
      await expect(close).toBeFocused();
      await expect(page.locator("body")).toHaveClass(/survey-composer-open/);
      await expect(page.locator("html")).toHaveAttribute(
        "dir",
        language === "ar" ? "rtl" : "ltr",
      );

      const geometry = await dialog.evaluate((element) => {
        const rect = element.getBoundingClientRect();
        const scrollable = Array.from(
          element.querySelectorAll<HTMLElement>("*"),
        ).filter((node) => {
          const overflow = getComputedStyle(node).overflowY;
          return (
            ["auto", "scroll"].includes(overflow) &&
            node.scrollHeight > node.clientHeight
          );
        });
        return {
          top: rect.top,
          right: rect.right,
          bottom: rect.bottom,
          left: rect.left,
          viewportWidth: window.innerWidth,
          viewportHeight: window.innerHeight,
          scrollableCount: scrollable.length,
          appMainOverflow: getComputedStyle(
            document.querySelector<HTMLElement>(".app-main")!,
          ).overflowY,
          horizontalOverflow:
            document.documentElement.scrollWidth -
            document.documentElement.clientWidth,
        };
      });
      expect(geometry.top).toBeGreaterThanOrEqual(11);
      expect(geometry.left).toBeGreaterThanOrEqual(11);
      expect(geometry.right).toBeLessThanOrEqual(geometry.viewportWidth - 11);
      expect(geometry.bottom).toBeLessThanOrEqual(geometry.viewportHeight - 11);
      expect(geometry.scrollableCount).toBe(1);
      expect(geometry.appMainOverflow).toBe("hidden");
      expect(geometry.horizontalOverflow).toBeLessThanOrEqual(0);

      await close.click();
      await expect(dialog).toHaveCount(0);
      await expect(opener).toBeFocused();
      await expect(page.locator("body")).not.toHaveClass(
        /survey-composer-open/,
      );
    });
  }
}

test("survey composer honours Escape and ordered keyboard/native Back handling", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.addInitScript(() =>
    localStorage.setItem("familyHeroHub.language", "en"),
  );
  await mockSurveyWorkspace(page);
  await page.goto("/school/surveys?membership=51");

  const opener = page.getByRole("button", { name: "Create survey" });
  await opener.click();
  await page.keyboard.press("Escape");
  await expect(
    page.getByRole("dialog", { name: "Survey details" }),
  ).toHaveCount(0);
  await expect(opener).toBeFocused();

  await opener.click();
  const titleInput = page.getByLabel("Title");
  await titleInput.focus();
  await page.evaluate(() =>
    document.documentElement.classList.add("native-keyboard-open"),
  );
  const keyboardBackHandled = await page.evaluate(
    () =>
      !window.dispatchEvent(
        new CustomEvent("chh:native-back", { cancelable: true }),
      ),
  );
  expect(keyboardBackHandled).toBe(true);
  await expect(
    page.getByRole("dialog", { name: "Survey details" }),
  ).toBeVisible();
  await expect(titleInput).not.toBeFocused();

  const dialogBackHandled = await page.evaluate(
    () =>
      !window.dispatchEvent(
        new CustomEvent("chh:native-back", { cancelable: true }),
      ),
  );
  expect(dialogBackHandled).toBe(true);
  await expect(
    page.getByRole("dialog", { name: "Survey details" }),
  ).toHaveCount(0);
  await expect(opener).toBeFocused();
});
