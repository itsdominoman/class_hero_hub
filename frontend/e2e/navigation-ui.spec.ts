import { expect, test, type Page, type Route } from "@playwright/test";

type RoleCase = {
  name: string;
  platformAdmin: boolean;
  roles: Array<"guardian" | "school_admin" | "teacher">;
  expectedLabels: string[];
};

const roleCases: RoleCase[] = [
  {
    name: "platform admin",
    platformAdmin: true,
    roles: [],
    expectedLabels: ["Platform admin"],
  },
  {
    name: "school admin",
    platformAdmin: false,
    roles: ["school_admin"],
    expectedLabels: [
      "School setup",
      "Messages",
      "Surveys",
      "Reports",
      "System & compliance",
      "Safeguarding",
    ],
  },
  {
    name: "teacher",
    platformAdmin: false,
    roles: ["teacher"],
    expectedLabels: ["Teach", "Messages", "Safeguarding"],
  },
  {
    name: "mixed role",
    platformAdmin: true,
    roles: ["guardian", "school_admin", "teacher"],
    expectedLabels: [
      "Platform admin",
      "School setup",
      "Teach",
      "Messages",
      "Surveys",
      "Reports",
      "System & compliance",
      "Safeguarding",
    ],
  },
];

const mixedRoleHrefs = [
  "/platform",
  "/school",
  "/teach",
  "/messages",
  "/school/surveys?membership=102",
  "/school/reports",
  "/school/administration",
  "/school/safeguarding?membership=102",
];

async function json(route: Route, body: unknown) {
  await route.fulfill({
    contentType: "application/json",
    body: JSON.stringify(body),
  });
}

async function mockSession(
  page: Page,
  roleCase: RoleCase,
  locale = "en",
  safeguardingAvailableMembershipIds?: number[],
) {
  await page.addInitScript((language) => {
    localStorage.setItem("familyHeroHub.language", language);
  }, locale);

  const memberships = roleCase.roles.map((role, index) => ({
    membership_id: 101 + index,
    school_id: 7,
    school_name: "Navigation Test School",
    role,
  }));
  const safeguardingMembershipIds = new Set(
    safeguardingAvailableMembershipIds ??
      memberships
        .filter((row) => row.role === "school_admin" || row.role === "teacher")
        .map((row) => row.membership_id),
  );

  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("/api/me") || path.endsWith("/api/me/v2")) {
      await json(route, {
        id: 5,
        name: "Navigation Test User",
        is_platform_admin: roleCase.platformAdmin,
        memberships,
      });
      return;
    }
    if (path.endsWith("/safeguarding/availability")) {
      await json(route, {
        available: safeguardingMembershipIds.has(
          Number(route.request().headers()["x-membership-id"]),
        ),
      });
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

async function openVisibleNavigation(page: Page, width: number) {
  const header = page.locator(".app-header");
  if (width < 1280) {
    const menuButton = header.locator(
      'button[aria-controls="mobile-navigation"]',
    );
    await expect(menuButton).toBeVisible({ timeout: 15_000 });
    await menuButton.click();
    return page.locator("#mobile-navigation nav");
  }
  await expect(header.getByRole("button", { name: "Open menu" })).toBeHidden();
  return header.locator("nav");
}

for (const roleCase of roleCases) {
  test(`${roleCase.name} sees only its ordered navigation destinations`, async ({
    page,
  }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await mockSession(page, roleCase);
    await page.goto("/login");

    const navigation = await openVisibleNavigation(page, 390);
    for (const label of roleCase.expectedLabels) {
      await expect(
        navigation.getByRole("link", { name: label, exact: true }),
      ).toBeVisible();
    }
    await expect(navigation.locator("a")).toHaveCount(
      roleCase.expectedLabels.length,
    );
  });
}

for (const width of [390, 1280]) {
  test(`teacher without actionable safeguarding access has no destination at ${width}px`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 900 });
    await mockSession(page, roleCases[2], "en", []);
    await page.goto("/login");

    const navigation = await openVisibleNavigation(page, width);
    await expect(
      navigation.locator('a[href^="/school/safeguarding"]'),
    ).toHaveCount(0);
  });
}

test("mixed-role navigation selects an actionable safeguarding membership", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await mockSession(page, roleCases[3], "en", [103]);
  await page.goto("/login");

  const navigation = await openVisibleNavigation(page, 390);
  await expect(
    navigation.getByRole("link", { name: "Safeguarding", exact: true }),
  ).toHaveAttribute("href", "/school/safeguarding?membership=103");
});

test("mixed-role staff cannot open the legacy CHH family dashboard", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await mockSession(page, roleCases[3], "en", [103]);

  await page.goto("/parent");

  await expect(page).toHaveURL(/\/family-connection$/);
  await expect(page.getByRole("heading", { name: "School updates for families." })).toBeVisible();
  await expect(page.getByRole("link", { name: "Family", exact: true })).toHaveCount(0);
});

for (const width of [390, 768, 1024, 1280, 1440]) {
  for (const locale of ["en", "ar"]) {
    test(`mixed-role ${locale} navigation is ordered and contained at ${width}px`, async ({
      page,
    }) => {
      await page.setViewportSize({ width, height: 900 });
      await mockSession(page, roleCases[3], locale);
      await page.goto("/login");

      const navigation = await openVisibleNavigation(page, width);
      await expect(navigation.locator("a")).toHaveCount(mixedRoleHrefs.length);
      expect(
        await navigation
          .locator("a")
          .evaluateAll((links) =>
            links.map((link) => link.getAttribute("href")),
          ),
      ).toEqual(mixedRoleHrefs);
      await expect(page.locator("html")).toHaveAttribute(
        "dir",
        locale === "ar" ? "rtl" : "ltr",
      );

      const overflow = await page.evaluate(
        () =>
          document.documentElement.scrollWidth -
          document.documentElement.clientWidth,
      );
      expect(overflow).toBeLessThanOrEqual(1);

      if (width >= 1280) {
        const brand = page.locator(".brand-title");
        const brandBox = await brand.boundingBox();
        const navigationBox = await navigation.boundingBox();
        expect(brandBox).not.toBeNull();
        expect(navigationBox).not.toBeNull();
        if (locale === "ar") {
          expect(
            (navigationBox?.x || 0) + (navigationBox?.width || 0),
          ).toBeLessThanOrEqual(brandBox?.x || 0);
        } else {
          expect(
            (brandBox?.x || 0) + (brandBox?.width || 0),
          ).toBeLessThanOrEqual(navigationBox?.x || 0);
        }
      }
    });
  }
}
