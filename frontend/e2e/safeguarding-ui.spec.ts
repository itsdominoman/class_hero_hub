import { expect, test, type Page, type Route } from "@playwright/test";

const membership = {
  membership_id: 51,
  school_id: 7,
  school_name: "Al Noor School",
  role: "school_admin",
};

const conversationId = "00000000-0000-4000-8000-000000000301";
const reviewSessionId = "00000000-0000-4000-8000-000000000302";
const messageId = "00000000-0000-4000-8000-000000000303";

const allPermissions = [
  "messaging.safeguarding_review",
  "messaging.moderate",
  "messaging.export_evidence",
  "messaging.export_internal_notes",
  "messaging.manage_safeguarding_permissions",
];

const context = {
  school: { id: 7, name: "Al Noor School", timezone: "Asia/Muscat" },
  reviewer: {
    user_id: 5,
    membership_id: 51,
    name: "Admin One",
    role: "school_admin",
  },
  permissions: allPermissions,
  review_ttl_minutes: 30,
  audit_notice: true,
  filters: {
    branches: [
      { id: 11, name: "Al Khoud", name_ar: "الخوض" },
      { id: 12, name: "Boushar", name_ar: "بوشر" },
    ],
    grade_levels: [{ id: 21, name: "Grade 4", name_ar: "الصف الرابع" }],
    class_sections: [
      {
        id: 31,
        name: "Class 4A",
        name_ar: "الصف الرابع أ",
        branch_id: 11,
        grade_level_id: 21,
      },
    ],
  },
};

const searchItem = {
  conversation_id: conversationId,
  reference: "MSG-00000000",
  kind: "student_staff",
  status: "active",
  participant_state: "read_only",
  restricted: true,
  flag_count: 1,
  student: {
    id: 91,
    display_name: "Mariam Al Harthy",
    name_ar: "مريم الحارثية",
  },
  school_context: {
    class_section: { id: 31, name: "Class 4A", name_ar: "الصف الرابع أ" },
    grade_level: { id: 21, name: "Grade 4", name_ar: "الصف الرابع" },
    branch: { id: 11, name: "Al Khoud", name_ar: "الخوض" },
  },
  participants: [
    {
      display_name: "Ms Aisha Al Balushi with a safely wrapping long name",
      kind: "staff",
      role: "teacher",
      side: "staff",
    },
    {
      display_name: "Fatma Al Harthy",
      kind: "fhh_parent",
      role: null,
      side: "guardian",
    },
  ],
  branch_id: 11,
  branch: { id: 11, name: "Al Khoud", name_ar: "الخوض" },
  last_activity_at: "2026-07-21T08:30:00Z",
};

const reviewDetail = {
  mode: "safeguarding_review",
  review: {
    id: reviewSessionId,
    reason_category: "reported_concern",
    justification: "Reported concern requires an authorised review",
    started_at: "2026-07-21T08:30:00Z",
    expires_at: "2099-07-21T09:00:00Z",
    audited: true,
  },
  reviewer: context.reviewer,
  school: context.school,
  permissions: allPermissions,
  conversation: {
    id: conversationId,
    reference: "MSG-00000000",
    kind: "student_staff",
    status: "active",
    restriction_type: "family_replies",
    reopening_requires_approval: true,
    created_at: "2026-07-21T08:00:00Z",
    last_message_sequence: 1,
    student: searchItem.student,
    school_context: searchItem.school_context,
    branch: searchItem.branch,
    participants: [
      {
        reference: "participant-1",
        display_name: "Ms Aisha Al Balushi",
        kind: "staff",
        role: "teacher",
        side: "staff",
        joined_at: "2026-07-21T08:00:00Z",
        left_at: null,
        receipt_cursor: { delivered_sequence: 1, read_sequence: 1 },
      },
      {
        reference: "participant-2",
        display_name: "Fatma Al Harthy",
        kind: "fhh_parent",
        role: null,
        side: "guardian",
        joined_at: "2026-07-21T08:00:00Z",
        left_at: null,
        receipt_cursor: { delivered_sequence: 1, read_sequence: 1 },
      },
    ],
  },
  messages: [
    {
      id: messageId,
      sequence: 1,
      sender_display_name: "Fatma Al Harthy",
      sender_kind: "fhh_parent",
      sender_role: null,
      sender_side: "guardian",
      message_type: "standard",
      body: "Please review this school communication.",
      state: "active",
      urgent: false,
      created_at: "2026-07-21T08:15:00Z",
      photos: [],
      voice_note: null,
      flags: [
        {
          id: "flag-1",
          category: "follow_up",
          severity: "high",
          status: "open",
        },
      ],
    },
  ],
  next_after_sequence: null,
  receipt_evidence: [],
  conversation_flags: [],
  internal_notes: [],
  moderation_history: [],
  audit_history: [
    {
      event_id: "audit-1",
      action: "safeguarding.review_started",
      occurred_at: "2026-07-21T08:30:00Z",
    },
  ],
  exports: [],
  capabilities: { can_moderate: true, can_export: true, has_composer: false },
};

type MockOptions = { permissions?: string[] };

async function mockSafeguarding(page: Page, options: MockOptions = {}) {
  const requests: Array<{ path: string; method: string; body?: unknown }> = [];
  const permissionSet = options.permissions ?? allPermissions;
  const grants = new Set<string>(["messaging.safeguarding_review"]);

  await page.route("**/api/me", async (route) => {
    await route.fulfill({
      json: {
        id: 5,
        name: "Admin One",
        is_platform_admin: false,
        memberships: [membership],
      },
    });
  });
  await page.route("**/api/messaging/**", async (route) => {
    await route.fulfill({
      status: 404,
      json: { detail: "Messaging unavailable in focused mock" },
    });
  });
  await page.route("**/api/safeguarding/**", async (route: Route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;
    const method = request.method();
    const body = request.postDataJSON?.() ?? undefined;
    requests.push({ path, method, body });
    expect(request.headers()["x-school-id"]).toBe("7");
    expect(request.headers()["x-membership-id"]).toBe("51");

    if (path.endsWith("/availability")) {
      await route.fulfill({ json: { available: true } });
      return;
    }
    if (path.endsWith("/context")) {
      await route.fulfill({ json: { ...context, permissions: permissionSet } });
      return;
    }
    if (path.endsWith("/conversations")) {
      await route.fulfill({ json: { items: [searchItem] } });
      return;
    }
    if (path.endsWith("/permissions") && method === "GET") {
      await route.fulfill({
        json: {
          available_permissions: allPermissions,
          memberships: [
            {
              membership_id: 61,
              name: "Teacher One",
              role: "teacher",
              active: true,
              branch: { id: 11, name: "Al Khoud", name_ar: "الخوض" },
              permissions: [...grants].map((permission, index) => ({
                id: `00000000-0000-4000-8000-0000000004${index}`,
                permission,
                granted_at: "2026-07-20T09:00:00Z",
              })),
            },
          ],
        },
      });
      return;
    }
    if (path.endsWith("/permissions") && method === "POST") {
      grants.add(String((body as { permission: string }).permission));
      await route.fulfill({
        json: {
          id: "grant-new",
          permission: (body as { permission: string }).permission,
        },
      });
      return;
    }
    if (path.includes("/permissions/") && path.endsWith("/revoke")) {
      await route.fulfill({ json: { revoked: true } });
      return;
    }
    if (path.endsWith("/reviews") && method === "POST") {
      await route.fulfill({
        json: {
          review_session_id: reviewSessionId,
          conversation_id: conversationId,
          expires_at: "2099-07-21T09:00:00Z",
        },
      });
      return;
    }
    if (path.endsWith(`/reviews/${reviewSessionId}`) && method === "GET") {
      await route.fulfill({ json: reviewDetail });
      return;
    }
    if (path.endsWith(`/reviews/${reviewSessionId}/end`)) {
      await route.fulfill({ json: { ended: true } });
      return;
    }
    await route.fulfill({ json: { ok: true } });
  });

  return requests;
}

async function expectNoHorizontalOverflow(page: Page) {
  const dimensions = await page.evaluate(() => ({
    viewport: document.documentElement.clientWidth,
    document: document.documentElement.scrollWidth,
    body: document.body.scrollWidth,
  }));
  expect(dimensions.document).toBeLessThanOrEqual(dimensions.viewport);
  expect(dimensions.body).toBeLessThanOrEqual(dimensions.viewport);
}

test("landing page separates message reviews from permission management", async ({
  page,
}) => {
  await mockSafeguarding(page);
  await page.goto("/school/safeguarding?membership=51");
  await expect(
    page.getByRole("heading", { name: "Safeguarding" }),
  ).toBeVisible();
  await expect(page.getByTestId("message-reviews-action")).toBeVisible();
  await expect(page.getByTestId("permission-management-action")).toBeVisible();
  await expect(page.getByText("Full safeguarding access")).toBeVisible();
  await expect(page.getByTestId("safeguarding-search-form")).toHaveCount(0);
  await expect(page.getByTestId("permission-checklist-form")).toHaveCount(0);
});

test("mobile search is labelled, friendly, focused, and has correct Back behavior", async ({
  page,
}) => {
  const requests = await mockSafeguarding(page);
  await page.setViewportSize({ width: 320, height: 760 });
  await page.goto("/school/safeguarding/message-reviews?membership=51");
  await expect(
    page.getByRole("heading", { name: "Message reviews" }),
  ).toBeVisible();
  await expect(page.getByLabel("Student")).toBeVisible();
  await expect(page.getByLabel("Participant", { exact: true })).toBeVisible();
  await expect(page.getByLabel("Conversation status")).toBeVisible();

  const searchForm = page.getByTestId("safeguarding-search-form");
  const actionFollowsFilters = await searchForm.evaluate((form) => {
    const action = form.querySelector(
      '[data-testid="safeguarding-search-action"]',
    );
    const status = form.querySelector("select");
    return Boolean(
      action &&
      status &&
      status.compareDocumentPosition(action) & Node.DOCUMENT_POSITION_FOLLOWING,
    );
  });
  expect(actionFollowsFilters).toBe(true);

  await page.getByTestId("advanced-filters-toggle").click();
  await expect(page.getByTestId("advanced-filters")).toBeVisible();
  const optionLabels = await page.locator("select option").allTextContents();
  expect(optionLabels.every((label) => label.trim().length > 0)).toBe(true);
  await expect(
    page.getByTestId("branch-filter").getByRole("option", { name: "Al Khoud" }),
  ).toHaveText("Al Khoud");
  await expect(
    page.getByTestId("branch-filter").getByRole("option", { name: "11" }),
  ).toHaveCount(0);

  const card = page.getByTestId("conversation-card");
  await expect(card).toBeVisible();
  await expect(card).toContainText("Teacher");
  await expect(card).toContainText("Parent or guardian");
  await expect(card).not.toContainText("fhh_parent");
  await expect(card).not.toContainText("school_admin");
  const cardBounds = await card.evaluate((element) => {
    const rect = element.getBoundingClientRect();
    return {
      left: rect.left,
      right: rect.right,
      width: rect.width,
      inner: element.clientWidth,
      scroll: element.scrollWidth,
    };
  });
  expect(cardBounds.left).toBeGreaterThanOrEqual(0);
  expect(cardBounds.right).toBeLessThanOrEqual(320);
  expect(cardBounds.scroll).toBeLessThanOrEqual(cardBounds.inner);
  await expectNoHorizontalOverflow(page);

  await page.getByRole("button", { name: "Review" }).click();
  await expect(page.getByTestId("start-review-dialog")).toBeVisible();
  await expect(card.getByRole("button", { name: "Selected" })).toBeVisible();
  await page.evaluate(() =>
    window.dispatchEvent(
      new CustomEvent("chh:native-back", { cancelable: true }),
    ),
  );
  await expect(page.getByTestId("start-review-dialog")).toHaveCount(0);

  await page.getByRole("button", { name: "Review" }).click();
  await page.getByLabel("Justification").fill("blah");
  await page.getByRole("button", { name: "Start review" }).click();
  await expect(
    page.getByText(
      "Enter a meaningful justification using at least 15 characters and 8 letters or numbers.",
    ),
  ).toBeVisible();
  await page
    .getByLabel("Justification")
    .fill("Reported concern for authorised review");
  await page.getByRole("button", { name: "Start review" }).click();
  await expect(
    page.getByText(
      "You must acknowledge audited access before starting the review.",
    ),
  ).toBeVisible();
  await page
    .getByLabel(
      "I understand that this time-limited access is audited and must be used only for the stated purpose.",
    )
    .check();
  await page.getByRole("button", { name: "Start review" }).click();
  await expect(page).toHaveURL(
    new RegExp(`/school/safeguarding/message-reviews/${reviewSessionId}`),
  );
  expect(
    requests.some(
      (request) =>
        request.path.endsWith("/reviews") && request.method === "POST",
    ),
  ).toBe(true);
  expect(
    requests.some((request) =>
      /acknowledgements|notification|push/.test(request.path),
    ),
  ).toBe(false);
});

for (const width of [320, 360, 390, 430]) {
  test(`conversation results have no horizontal overflow at ${width}px`, async ({
    page,
  }) => {
    await mockSafeguarding(page);
    await page.setViewportSize({ width, height: 800 });
    await page.goto("/school/safeguarding/message-reviews?membership=51");
    await expect(page.getByTestId("conversation-card")).toBeVisible();
    await expectNoHorizontalOverflow(page);
  });
}

test("active review is mobile-safe, RTL-aware, and contains no composer", async ({
  page,
}) => {
  await page.addInitScript(() =>
    localStorage.setItem("familyHeroHub.language", "ar"),
  );
  await mockSafeguarding(page);
  await page.setViewportSize({ width: 390, height: 800 });
  await page.goto(
    `/school/safeguarding/message-reviews/${reviewSessionId}?membership=51`,
  );
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  await expect(
    page.getByTestId("safeguarding-review-mode-banner"),
  ).toBeVisible();
  await expect(page.getByTestId("safeguarding-review-workspace")).toBeVisible();
  await expect(
    page.locator('[data-testid*="composer"], [contenteditable="true"]'),
  ).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: /Send message|إرسال الرسالة/i }),
  ).toHaveCount(0);
  await expect(page.getByText("ولي أمر أو وصي").first()).toBeVisible();
  await expect(page.getByText("fhh_parent")).toHaveCount(0);
  await expect(page.getByText("school_admin")).toHaveCount(0);
  await expectNoHorizontalOverflow(page);
});

test("permission management uses one friendly checklist and warns before manager access", async ({
  page,
}) => {
  await mockSafeguarding(page);
  await page.setViewportSize({ width: 360, height: 800 });
  await page.goto("/school/safeguarding/permissions?membership=51");
  await page.getByTestId("staff-selector").selectOption("61");
  await expect(
    page.getByRole("heading", { name: "Teacher One" }),
  ).toBeVisible();
  await expect(
    page.getByLabel("Review safeguarding conversations"),
  ).toBeChecked();
  await page.getByLabel("Manage safeguarding access").check();
  await expect(page.getByTestId("manage-access-warning")).toBeVisible();
  await expect(
    page.getByText("messaging.manage_safeguarding_permissions"),
  ).toHaveCount(0);
  await page.getByRole("button", { name: "Save access" }).click();
  await expect(
    page.getByText(
      "Enter a meaningful reason using at least 8 letters or numbers.",
    ),
  ).toBeVisible();
  await page
    .getByLabel("Reason for access change")
    .fill("Assigned as deputy safeguarding lead");
  await page.getByRole("button", { name: "Save access" }).click();
  await expect(
    page.getByText("Safeguarding access was updated."),
  ).toBeVisible();
  await expectNoHorizontalOverflow(page);
});

test("permission route still fails closed without manage access", async ({
  page,
}) => {
  const requests = await mockSafeguarding(page, {
    permissions: ["messaging.safeguarding_review"],
  });
  await page.goto("/school/safeguarding/permissions?membership=51");
  await expect(
    page.getByText(
      "Only staff with Manage safeguarding access can open this page.",
    ),
  ).toBeVisible();
  expect(
    requests.some(
      (request) =>
        request.path.endsWith("/permissions") && request.method === "GET",
    ),
  ).toBe(false);
});
