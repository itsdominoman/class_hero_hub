import assert from "node:assert/strict";
import test from "node:test";

import { getPublicSiteCopy } from "../src/lib/publicSite.ts";

function shape(value) {
  if (Array.isArray(value)) return value.map(shape);
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value).map(([key, child]) => [key, shape(child)]),
    );
  }
  return typeof value;
}

function strings(value) {
  if (Array.isArray(value)) return value.flatMap(strings);
  if (value && typeof value === "object")
    return Object.values(value).flatMap(strings);
  return typeof value === "string" ? [value] : [];
}

test("public-site English and Arabic catalogues have the same complete shape", () => {
  const english = getPublicSiteCopy("en");
  const arabic = getPublicSiteCopy("ar");

  assert.deepEqual(shape(arabic), shape(english));
  assert.equal(
    strings(english).some((value) => /TODO|lorem ipsum/i.test(value)),
    false,
  );
  assert.equal(
    strings(arabic).some((value) => /TODO|lorem ipsum/i.test(value)),
    false,
  );
  assert.ok(strings(arabic).some((value) => /[\u0600-\u06ff]/.test(value)));
});

test("public-site copy explains the CHH and FHH relationship in plain language", () => {
  const englishText = strings(getPublicSiteCopy("en")).join(" ");
  const arabicText = strings(getPublicSiteCopy("ar")).join(" ");

  assert.match(
    englishText,
    /Parents do not sign in to Class Hero Hub|Parents and guardians see the school information shared with them through Family Hero Hub/,
  );
  assert.match(
    englishText,
    /School staff work in Class Hero Hub|Staff use Class Hero Hub for school work/,
  );
  assert.match(arabicText, /لا يسجل أولياء الأمور الدخول إلى كلاس هيرو هب/);
  assert.match(arabicText, /يستخدم الموظفون كلاس هيرو هب للعمل المدرسي/);
});

test("public-site copy positions CHH as an everyday workspace alongside existing systems", () => {
  const english = getPublicSiteCopy("en");
  const arabic = getPublicSiteCopy("ar");
  const englishText = strings(english).join(" ");
  const arabicText = strings(arabic).join(" ");

  assert.match(
    englishText,
    /A practical workspace for teachers, school communication and family updates that can complement the systems the school already uses\./,
  );
  assert.match(englishText, /works? alongside|complements? the school/);
  assert.match(arabicText, /تكمل الأنظمة التي تستخدمها المدرسة/);
  assert.equal(english.home.proofItems[0].src, "/product/teacher-workflow.png");
  assert.equal(arabic.home.proofItems[0].src, "/product/teacher-workflow.png");
});

test("public homepage uses the final direct bilingual hero and family wording", () => {
  const english = getPublicSiteCopy("en");
  const arabic = getPublicSiteCopy("ar");

  assert.equal(english.home.heading, "Help teachers. Keep families informed.");
  assert.equal(
    english.home.intro,
    "Class Hero Hub gives school teams one place for homework, behaviour, recognition, notices, chats, surveys and family updates—alongside the systems your school already uses.",
  );
  assert.equal(english.home.familyHeading, "School updates for families.");
  assert.match(arabic.home.heading, /المعلمين.*الأسر/);
  assert.equal(arabic.home.familyHeading, "تحديثات المدرسة للأسر.");
});

test("public legal pages show the current effective date in both languages", () => {
  const english = getPublicSiteCopy("en");
  const arabic = getPublicSiteCopy("ar");

  for (const page of [english.pages.privacy, english.pages.terms]) {
    assert.ok(page.highlights?.includes("Effective 3 August 2026"));
  }
  for (const page of [arabic.pages.privacy, arabic.pages.terms]) {
    assert.ok(page.highlights?.includes("سارية من 3 أغسطس 2026"));
  }
});

test("public-site copy contains no internal implementation or drafting language", () => {
  const englishText = strings(getPublicSiteCopy("en")).join(" ");

  assert.doesNotMatch(
    englishText,
    /\b(boundary|scoped|opaque|proxy|authority|protected|governance|merge|server-side)\b/i,
  );
  assert.doesNotMatch(
    englishText,
    /legal review required|Dom|no published pricing|commercial terms come later|no invented/i,
  );
});
