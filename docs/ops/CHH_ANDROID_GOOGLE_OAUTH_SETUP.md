# CHH Android and Google OAuth setup

Status date: 2026-07-28. This document records the current debug configuration; it
does not configure Google Cloud or release signing.

## Revocable staff sessions (AUTH-001)

Google OAuth, native Google sign-in, magic links and the dev-only QA login all issue
the same server-backed session. Access JWTs last 15 minutes. Each browser or Android
installation has a separate rotating refresh session with a 30-day idle limit and a
180-day absolute limit. The database stores only an HMAC hash of the refresh
credential plus safe device/browser metadata; raw access and refresh credentials
must not be logged.

Browser access and refresh credentials are `Secure`, `HttpOnly`, `SameSite=Lax`
cookies. The refresh cookie is restricted to `/api/auth`; the readable CSRF cookie
continues to protect cookie-authenticated unsafe requests. Android stores both
credentials in the existing Keystore-backed encrypted storage and sends them only in
request bodies or `Authorization` headers over HTTPS.

Refresh rotates the credential. Reuse after the ten-second concurrent-request grace
revokes that device/browser session chain. Normal logout revokes only the current
session; `POST /api/auth/logout-all` revokes every session for the user. Inactive
users cannot use access or refresh credentials. Invitation codes, guardian links,
school memberships and Google identity matching are unchanged.

During rollout only, `LEGACY_ACCESS_TOKEN_ACCEPT_UNTIL` may be set to an explicit
short UTC deadline. A current browser or updated APK silently exchanges an existing
legacy access token for a refresh session before that deadline. After it, a user on
an old client signs in once; they do not need a new invitation or family/school link.

## Google Cloud project and clients

Using the same Google Cloud project as Family Hero Hub (FHH) is acceptable. CHH must,
however, have its **own Android OAuth client**. Do not reuse FHH's Android OAuth client.

Configure the CHH Android OAuth client with:

| Setting | Current value |
| --- | --- |
| Package name | `com.classherohub.app` |
| Debug SHA-1 | `FD:41:EB:F1:CB:01:8A:BB:31:49:AB:80:D4:81:8B:B8:E5:C4:C6:A3` |
| Debug SHA-256 | `E9:50:6D:FC:7F:53:38:8B:B6:CC:5C:8F:EF:DD:16:80:4F:74:07:45:16:7B:60:2E:FB:72:5E:17:30:33:06:0B` |

These fingerprints are from the current local Android debug keystore
(`/home/administrator/.android/debug.keystore`) and therefore apply only while that
debug signing identity remains the one used to build CHH. Add separately verified
production signing fingerprints before any release distribution.

## Client ID rules

- `GOOGLE_CLIENT_ID` must remain the **Web OAuth client ID**. Gradle exposes it to the
  native Google Credential Manager request as the server client ID.
- The Android client ID identifies the Android package/certificate in Google Cloud; it
  is **not** used as the backend ID-token audience in this implementation.
- The backend native endpoint is `POST /api/auth/google/native`. It verifies the
  returned Google ID token against `GOOGLE_CLIENT_ID` and requires
  `google-auth[requests]` in backend dependencies.
- Do not put a client secret, token, keystore password, or full OAuth credential JSON
  in this repository or this document.

## Browser OAuth remains independent

Browser OAuth still uses the browser redirect/session flow and its CSRF/state
validation. It is not replaced by native bearer authentication. Do not disable OAuth
state validation to accommodate Android; diagnose redirect/client configuration instead.

## Native flow summary

1. Android Credential Manager returns an ID token for the configured Web client ID.
2. The Capacitor shell posts it to `/api/auth/google/native`.
3. CHH stores the returned short-lived access and rotating refresh credentials using
   encrypted native storage. Native API requests send the access token as a bearer;
   renewal is silent while the account remains authorised. Browser requests use the
   equivalent secure cookie session.

## Operator verification before distribution

- Confirm the CHH Android OAuth client exists in the intended Google Cloud project.
- Confirm its package name and both current debug fingerprints exactly match this file.
- Confirm the OAuth consent screen/test-user policy permits the intended test accounts.
- Confirm `GOOGLE_CLIENT_ID` is the intended Web client ID in both backend runtime and
  Android build environment.
- Obtain and register release signing SHA-1/SHA-256 only when release signing is
  explicitly approved.
