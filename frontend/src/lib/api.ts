import { normalizeErrorMessage } from '$lib/errors';

const API_BASE = '/api';

function getCookie(name: string): string | null {
  if (typeof document === 'undefined') return null;

  const match = document.cookie
    .split('; ')
    .find((row) => row.startsWith(`${name}=`));

  if (!match) return null;

  return decodeURIComponent(match.substring(name.length + 1));
}

function isUnsafeMethod(method: string): boolean {
  return ['POST', 'PUT', 'PATCH', 'DELETE'].includes(method.toUpperCase());
}

function buildApiUrl(path: string): string {
  if (path.startsWith('http://') || path.startsWith('https://')) {
    return path;
  }

  if (path.startsWith('/api/')) {
    return path;
  }

  if (path === '/api') {
    return path;
  }

  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${API_BASE}${normalizedPath}`;
}

async function throwForErrorResponse(res: Response): Promise<never> {
  const contentType = res.headers.get('content-type') || '';

  if (contentType.includes('application/json')) {
    const error = await res.json().catch(() => ({ detail: 'Request failed' }));
    const requestError = new Error(normalizeErrorMessage(error, 'Request failed')) as Error & { status?: number };
    requestError.status = res.status;
    throw requestError;
  }

  const text = await res.text().catch(() => '');
  const requestError = new Error(normalizeErrorMessage(text, `Request failed with status ${res.status}`)) as Error & { status?: number };
  requestError.status = res.status;
  throw requestError;
}

async function request(path: string, options: RequestInit = {}) {
  const url = buildApiUrl(path);
  const method = (options.method || 'GET').toUpperCase();

  const headers = new Headers(options.headers || {});

  if (options.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  if (isUnsafeMethod(method)) {
    const csrfToken = getCookie('csrf_token');
    if (csrfToken) {
      headers.set('X-CSRF-Token', csrfToken);
    }
  }

  const res = await fetch(url, {
    ...options,
    method,
    headers,
    credentials: 'include'
  });

  if (!res.ok) {
    await throwForErrorResponse(res);
  }

  if (res.status === 204) {
    return null;
  }

  const contentType = res.headers.get('content-type') || '';
  if (!contentType.includes('application/json')) {
    const text = await res.text().catch(() => '');
    throw new Error(`Expected JSON response but received ${contentType || 'unknown content type'}: ${text.slice(0, 120)}`);
  }

  return res.json();
}

// Multipart upload (CSV import, etc.): the browser must set its own
// multipart Content-Type boundary, so this bypasses request()'s JSON body
// handling but still attaches the CSRF header and cookies the same way.
async function upload(path: string, formData: FormData, options: RequestInit = {}) {
  const url = buildApiUrl(path);
  const headers = new Headers(options.headers || {});
  const csrfToken = getCookie('csrf_token');
  if (csrfToken) {
    headers.set('X-CSRF-Token', csrfToken);
  }

  const res = await fetch(url, { ...options, method: 'POST', headers, body: formData, credentials: 'include' });
  if (!res.ok) {
    await throwForErrorResponse(res);
  }
  return res.json();
}

// File download (CSV template, etc.): the response is not JSON, so this
// bypasses request()'s JSON-only response handling and returns a Blob.
async function download(path: string, options: RequestInit = {}): Promise<Blob> {
  const url = buildApiUrl(path);
  const res = await fetch(url, { ...options, method: 'GET', credentials: 'include' });
  if (!res.ok) {
    await throwForErrorResponse(res);
  }
  return res.blob();
}

export const api = {
  get: (path: string, options: RequestInit = {}) => request(path, options),
  post: (path: string, body: any = {}, options: RequestInit = {}) => request(path, { ...options, method: 'POST', body: JSON.stringify(body) }),
  put: (path: string, body: any = {}, options: RequestInit = {}) => request(path, { ...options, method: 'PUT', body: JSON.stringify(body) }),
  patch: (path: string, body: any = {}, options: RequestInit = {}) => request(path, { ...options, method: 'PATCH', body: JSON.stringify(body) }),
  delete: (path: string, options: RequestInit = {}) => request(path, { ...options, method: 'DELETE' }),
  upload: (path: string, formData: FormData, options: RequestInit = {}) => upload(path, formData, options),
  download: (path: string, options: RequestInit = {}) => download(path, options)
};
