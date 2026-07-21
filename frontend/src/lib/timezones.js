import { rawTimeZones } from "@vvo/tzdb";

const optionCache = new Map();

function normaliseSearch(value) {
  return String(value ?? "")
    .normalize("NFKD")
    .replace(/[\u0300-\u036f\u064b-\u065f\u0670]/g, "")
    .replace(/[_/,-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .toLocaleLowerCase();
}

function localeLanguage(locale) {
  return String(locale || "en")
    .toLocaleLowerCase()
    .startsWith("ar")
    ? "ar"
    : "en";
}

function cityFromIdentifier(identifier) {
  return identifier.split("/").at(-1).replaceAll("_", " ");
}

function countryDisplayName(countryCode, fallback, language) {
  try {
    return (
      new Intl.DisplayNames([language], { type: "region" }).of(countryCode) ||
      fallback
    );
  } catch {
    return fallback;
  }
}

function genericTimeName(identifier, language) {
  try {
    const formatter = new Intl.DateTimeFormat(language, {
      timeZone: identifier,
      timeZoneName: "longGeneric",
    });
    return (
      formatter
        .formatToParts(new Date())
        .find((part) => part.type === "timeZoneName")?.value || ""
    );
  } catch {
    return "";
  }
}

export function currentUtcOffset(identifier, now = new Date()) {
  try {
    const formatter = new Intl.DateTimeFormat("en-US", {
      timeZone: identifier,
      timeZoneName: "longOffset",
    });
    const offset =
      formatter.formatToParts(now).find((part) => part.type === "timeZoneName")
        ?.value || "GMT";
    return offset === "GMT" ? "UTC+00:00" : offset.replace("GMT", "UTC");
  } catch {
    return "";
  }
}

export function getTimeZoneOptions(locale = "en", now = new Date()) {
  const language = localeLanguage(locale);
  const cacheKey = `${language}:${now.toISOString().slice(0, 13)}`;
  if (optionCache.has(cacheKey)) return optionCache.get(cacheKey);

  const options = rawTimeZones
    .filter((zone) => {
      try {
        new Intl.DateTimeFormat("en", { timeZone: zone.name }).format(now);
        return true;
      } catch {
        return false;
      }
    })
    .map((zone) => {
      const city = cityFromIdentifier(zone.name);
      const country = countryDisplayName(
        zone.countryCode,
        zone.countryName,
        language,
      );
      const primaryLabel = `${city}, ${country}`;
      const regionName = genericTimeName(zone.name, language);
      const offset = currentUtcOffset(zone.name, now);
      const searchText = normaliseSearch(
        [
          primaryLabel,
          city,
          country,
          zone.countryName,
          zone.countryCode,
          zone.continentName,
          zone.alternativeName,
          regionName,
          zone.name,
          ...zone.mainCities,
        ].join(" "),
      );

      return {
        value: zone.name,
        primaryLabel,
        country,
        city,
        regionName,
        offset,
        searchText,
      };
    })
    .sort((left, right) =>
      left.primaryLabel.localeCompare(right.primaryLabel, language),
    );

  optionCache.set(cacheKey, options);
  return options;
}

export function filterTimeZoneOptions(options, query) {
  const search = normaliseSearch(query);
  if (!search) return options;
  const terms = search.split(" ");
  return options
    .filter((option) =>
      terms.every((term) => option.searchText.includes(term)),
    )
    .sort((left, right) => {
      const score = (option) => {
        const label = normaliseSearch(option.primaryLabel);
        const labelWords = new Set(label.split(" "));
        const words = new Set(option.searchText.split(" "));
        if (terms.every((term) => labelWords.has(term))) return 0;
        if (label.startsWith(search)) return 1;
        if (terms.every((term) => words.has(term))) return 2;
        if (label.includes(search)) return 3;
        return 4;
      };
      return score(left) - score(right);
    });
}

export function isSelectableTimeZone(
  value,
  options = getTimeZoneOptions("en"),
) {
  return options.some((option) => option.value === value);
}
