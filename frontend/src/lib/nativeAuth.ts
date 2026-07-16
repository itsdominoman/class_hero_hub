import { Capacitor, registerPlugin } from '@capacitor/core';

const CHH_NATIVE_API_BASE = 'https://class.familyherohub.com/api';
const ACCESS_TOKEN_KEY = 'chh_access_token';

interface GoogleAuthPlugin {
  getGoogleIdToken(options: { filterByAuthorizedAccounts: boolean }): Promise<{ idToken: string }>;
}

interface SecureStoragePlugin {
  get(options: { key: string }): Promise<{ value: string | null }>;
  set(options: { key: string; value: string }): Promise<void>;
  remove(options: { key: string }): Promise<void>;
}

type NativeGoogleErrorCode =
  | 'credential_cancelled'
  | 'no_credential'
  | 'provider_configuration'
  | 'google_id_token_parsing'
  | 'credential_unknown';

class NativeGoogleSignInError extends Error {
  readonly source: 'credential_manager' | 'network' | 'backend';
  readonly code?: NativeGoogleErrorCode;
  readonly status?: number;

  constructor(
    message: string,
    details: {
      source: 'credential_manager' | 'network' | 'backend';
      code?: NativeGoogleErrorCode;
      status?: number;
    }
  ) {
    super(message);
    this.source = details.source;
    this.code = details.code;
    this.status = details.status;
  }
}

const GoogleAuth = registerPlugin<GoogleAuthPlugin>('GoogleAuth');
const SecureStorage = registerPlugin<SecureStoragePlugin>('SecureStorage');

let accessToken: string | null = null;

export function isNativePlatform(): boolean {
  return Capacitor.isNativePlatform();
}

export function nativeApiUrl(path: string): string {
  const normalized = path === '/api' ? '' : path.replace(/^\/api(?=\/|$)/, '');
  return `${CHH_NATIVE_API_BASE}${normalized.startsWith('/') ? normalized : `/${normalized}`}`;
}

export async function getNativeAccessToken(): Promise<string | null> {
  if (!isNativePlatform()) return null;
  if (accessToken) return accessToken;
  const { value } = await SecureStorage.get({ key: ACCESS_TOKEN_KEY });
  accessToken = value;
  return value;
}

export async function clearNativeAccessToken(): Promise<void> {
  accessToken = null;
  if (isNativePlatform()) await SecureStorage.remove({ key: ACCESS_TOKEN_KEY });
}

export async function signInWithNativeGoogle(): Promise<boolean> {
  if (!isNativePlatform()) return false;

  let idToken: string | null = null;
  try {
    idToken = (await GoogleAuth.getGoogleIdToken({ filterByAuthorizedAccounts: true })).idToken;
  } catch {
    // First-time users need the interactive Google account picker.
  }
  if (!idToken) {
    try {
      idToken = (await GoogleAuth.getGoogleIdToken({ filterByAuthorizedAccounts: false })).idToken;
    } catch (error) {
      const code = (error as { code?: NativeGoogleErrorCode }).code ?? 'credential_unknown';
      console.error('[CHH] Credential Manager sign-in failed:', code);
      throw new NativeGoogleSignInError('Credential Manager could not return a Google ID token', {
        source: 'credential_manager',
        code
      });
    }
  }

  let response: Response;
  try {
    response = await fetch(nativeApiUrl('/auth/google/native'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id_token: idToken }),
      credentials: 'omit'
    });
  } catch {
    console.error('[CHH] Native Google sign-in network request failed');
    throw new NativeGoogleSignInError('Could not contact the native login endpoint', { source: 'network' });
  }
  if (!response.ok) {
    console.error('[CHH] Native Google sign-in backend rejected request:', response.status);
    throw new NativeGoogleSignInError('Native Google sign-in failed', {
      source: 'backend',
      status: response.status
    });
  }

  const payload = await response.json();
  if (!payload?.access_token) throw new Error('Native Google sign-in returned no session token');
  const token = payload.access_token as string;
  accessToken = token;
  await SecureStorage.set({ key: ACCESS_TOKEN_KEY, value: token });
  return true;
}
