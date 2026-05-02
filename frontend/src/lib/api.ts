// Use relative path for same-origin API calls. 
// This ensures the browser uses the same protocol (https) as the page.
const BASE_URL = '/api';

async function request(path: string, options: RequestInit = {}) {
    // Ensure path starts with /
    const normalizedPath = path.startsWith('/') ? path : `/${path}`;
    
    // In production, we want to avoid absolute URLs that might use http://
    // Using a relative URL is the safest way to ensure same-origin and same-protocol.
    const url = `${BASE_URL}${normalizedPath}`;

    const res = await fetch(url, {
        ...options,
        credentials: 'include',
        headers: {
            'Content-Type': 'application/json',
            ...options.headers,
        },
    });

    if (!res.ok) {
        let errorDetail = 'Unknown error';
        try {
            const error = await res.json();
            errorDetail = error.detail || error.message || JSON.stringify(error);
        } catch (e) {
            errorDetail = res.statusText;
        }
        throw new Error(errorDetail);
    }

    if (res.status === 204) return null;
    return res.json();
}

export const api = {
    get: (path: string) => request(path),
    post: (path: string, body: any) => request(path, { method: 'POST', body: JSON.stringify(body) }),
    patch: (path: string, body: any) => request(path, { method: 'PATCH', body: JSON.stringify(body) }),
    delete: (path: string) => request(path, { method: 'DELETE' }),
};
