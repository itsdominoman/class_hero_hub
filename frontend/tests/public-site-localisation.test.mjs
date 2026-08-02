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

test("public-site copy keeps the CHH and FHH parent boundary explicit", () => {
  const englishText = strings(getPublicSiteCopy("en")).join(" ");
  const arabicText = strings(getPublicSiteCopy("ar")).join(" ");

  assert.match(
    englishText,
    /Parents and guardians do not sign in to CHH|Parents and guardians do not sign in to Class Hero Hub|Parents do not enter the staff system/,
  );
  assert.match(
    englishText,
    /Family clients never call CHH directly|Parents never call CHH directly|family clients do not call CHH directly/i,
  );
  assert.match(arabicText, /لا يسجل أولياء الأمور|لا يدخل أولياء الأمور/);
  assert.match(arabicText, /لا تتصل تطبيقات الأسرة بـ CHH مباشرة/);
});
