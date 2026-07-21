import assert from "node:assert/strict";
import test from "node:test";
import {
  filterTimeZoneOptions,
  getTimeZoneOptions,
  isSelectableTimeZone,
} from "../src/lib/timezones.js";

const englishOptions = getTimeZoneOptions(
  "en",
  new Date("2026-07-21T12:00:00Z"),
);

function valuesFor(query, options = englishOptions) {
  return filterTimeZoneOptions(options, query).map((option) => option.value);
}

test("loads the saved Muscat timezone with a friendly Oman label", () => {
  const muscat = englishOptions.find(
    (option) => option.value === "Asia/Muscat",
  );
  assert.ok(muscat);
  assert.equal(muscat.primaryLabel, "Muscat, Oman");
  assert.match(muscat.offset, /^UTC[+-]\d{2}:\d{2}$/);
});

test("searches by city, country, common region, and IANA identifier", () => {
  assert.ok(valuesFor("Muscat").includes("Asia/Muscat"));
  assert.ok(valuesFor("Oman").includes("Asia/Muscat"));
  assert.equal(valuesFor("Oman")[0], "Asia/Muscat");
  assert.ok(valuesFor("Johannesburg").includes("Africa/Johannesburg"));
  assert.ok(valuesFor("New York").includes("America/New_York"));
  assert.ok(valuesFor("Eastern Time").includes("America/New_York"));
  assert.ok(valuesFor("America/New_York").includes("America/New_York"));
});

test("rejects arbitrary values and exposes only Intl-supported IANA timezones", () => {
  assert.equal(
    isSelectableTimeZone("Around/About-Tea_Time", englishOptions),
    false,
  );
  assert.ok(englishOptions.length > 250);
  for (const option of englishOptions) {
    assert.doesNotThrow(
      () => new Intl.DateTimeFormat("en", { timeZone: option.value }),
    );
  }
});

test("Arabic options preserve IANA values and support Arabic country search", () => {
  const arabicOptions = getTimeZoneOptions(
    "ar",
    new Date("2026-07-21T12:00:00Z"),
  );
  const muscat = arabicOptions.find((option) => option.value === "Asia/Muscat");
  assert.ok(
    muscat?.primaryLabel.includes("عُمان") ||
      muscat?.primaryLabel.includes("عمان"),
  );
  assert.ok(valuesFor("عمان", arabicOptions).includes("Asia/Muscat"));
  assert.ok(valuesFor("Muscat", arabicOptions).includes("Asia/Muscat"));
});
