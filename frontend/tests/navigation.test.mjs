import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import { en, ar } from "../src/lib/i18n/messages.ts";
import {
  activeNavigationItem,
  GLOBAL_NAVIGATION_ORDER,
} from "../src/lib/navigation.ts";

const layoutSource = readFileSync(
  new URL("../src/routes/+layout.svelte", import.meta.url),
  "utf8",
);

test("global navigation has one role-neutral order for desktop and compact menus", () => {
  assert.deepEqual(GLOBAL_NAVIGATION_ORDER, [
    "family",
    "platform",
    "school",
    "teach",
    "messages",
    "surveys",
    "reports",
    "system",
    "safeguarding",
    "dashboard",
  ]);
  assert.equal(
    (layoutSource.match(/\{#each navigationItems/g) || []).length,
    2,
  );
  assert.match(layoutSource, /hidden xl:flex/);
  assert.match(layoutSource, /class="xl:hidden fixed inset-0/);
  assert.doesNotMatch(layoutSource, /hidden md:flex items-center gap-8/);
});

test("specific school areas win over the general school active state", () => {
  assert.equal(activeNavigationItem("/school"), "school");
  assert.equal(activeNavigationItem("/school/students/42"), "school");
  assert.equal(activeNavigationItem("/school/reports"), "reports");
  assert.equal(activeNavigationItem("/school/reports/behaviour"), "reports");
  assert.equal(activeNavigationItem("/school/surveys/9"), "surveys");
  assert.equal(
    activeNavigationItem("/school/safeguarding/message-reviews/12"),
    "safeguarding",
  );
  for (const path of [
    "/school/administration",
    "/school/recognition",
    "/school/governance",
    "/school/operations",
  ]) {
    assert.equal(activeNavigationItem(path), "system");
  }
  assert.equal(activeNavigationItem("/school/reporting"), "school");
});

test("English and Arabic navigation labels describe the destination", () => {
  assert.deepEqual(
    [en.nav.admin, en.nav.school, en.nav.reports, en.nav.administration],
    ["Platform admin", "School setup", "Reports", "System & compliance"],
  );
  assert.deepEqual(
    [ar.nav.admin, ar.nav.school, ar.nav.reports, ar.nav.administration],
    ["إدارة المنصة", "إعداد المدرسة", "التقارير", "النظام والامتثال"],
  );
});

test("known role workspaces receive a current-page target", () => {
  assert.equal(activeNavigationItem("/parent"), "family");
  assert.equal(activeNavigationItem("/platform/7"), "platform");
  assert.equal(activeNavigationItem("/teach/assignments/4"), "teach");
  assert.equal(activeNavigationItem("/messages"), "messages");
  assert.equal(activeNavigationItem("/"), null);
});
