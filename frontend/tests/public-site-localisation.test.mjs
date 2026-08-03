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
