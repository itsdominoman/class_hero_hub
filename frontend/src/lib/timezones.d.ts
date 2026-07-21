export type TimeZoneOption = {
  value: string;
  primaryLabel: string;
  country: string;
  city: string;
  regionName: string;
  offset: string;
  searchText: string;
};

export function currentUtcOffset(identifier: string, now?: Date): string;
export function getTimeZoneOptions(
  locale?: string,
  now?: Date,
): TimeZoneOption[];
export function filterTimeZoneOptions(
  options: TimeZoneOption[],
  query: string,
): TimeZoneOption[];
export function isSelectableTimeZone(
  value: string,
  options?: TimeZoneOption[],
): boolean;
