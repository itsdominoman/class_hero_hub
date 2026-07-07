type ErrorLike = {
  message?: unknown;
  detail?: unknown;
  error?: unknown;
  statusText?: unknown;
};

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

function cleanMessage(value: string): string {
  const trimmed = value.trim();
  if (!trimmed || trimmed === '[object Object]') return '';
  if (/Traceback \(most recent call last\):/i.test(trimmed)) return '';
  return trimmed;
}

function fieldLabelFromLoc(loc: unknown): string {
  if (!Array.isArray(loc)) return '';
  const field = String(loc[loc.length - 1] || '').replace(/_/g, ' ');
  return field ? `${field.charAt(0).toUpperCase()}${field.slice(1)}` : '';
}

function normalizePart(value: unknown): string[] {
  if (value == null) return [];
  if (typeof value === 'string') {
    const cleaned = cleanMessage(value);
    return cleaned ? [cleaned] : [];
  }
  if (typeof value === 'number' || typeof value === 'boolean') return [String(value)];
  if (Array.isArray(value)) return value.flatMap((item) => normalizePart(item));
  if (isPlainObject(value)) {
    if (typeof value.msg === 'string') {
      const label = fieldLabelFromLoc(value.loc);
      const message = cleanMessage(value.msg);
      if (!message) return [];
      return [label ? `${label}: ${message}` : message];
    }
    for (const key of ['detail', 'message', 'error']) {
      if (key in value) {
        const nested = normalizePart(value[key]);
        if (nested.length) return nested;
      }
    }
    return Object.values(value).flatMap((item) => normalizePart(item));
  }
  return [];
}

export function normalizeErrorMessage(error: unknown, fallback = 'Something went wrong.'): string {
  const messages = normalizePart(error);
  if (messages.length) return [...new Set(messages)].join('\n');

  if (isPlainObject(error)) {
    const errorLike = error as ErrorLike;
    for (const value of [errorLike.detail, errorLike.message, errorLike.error, errorLike.statusText]) {
      const nested = normalizePart(value);
      if (nested.length) return [...new Set(nested)].join('\n');
    }
  }

  return fallback;
}
