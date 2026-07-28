# CHH Android and Google OAuth setup

Status date: 2026-07-29. This document records the current debug configuration; it
does not configure Google Cloud or release signing.

## Authentication is not admission

Google OAuth and magic links prove control of an identity; they do not grant CHH
access. A normal browser or Android session is issued only when the active user has
at least one of these current entitlements:

- an active, non-revoked platform-administrator record;
- an active administrator or teacher membership at a non-suspended school; or
- an active guardian link to an active student at a non-suspended school.

An explicit, valid staff invitation (`/invite/<token>`) or guardian join code
(`/join?c=<code>`) may authenticate a new identity into a short-lived,
invite-scoped pending session. That session can inspect and complete only the exact
hashed invitation context; ordinary authenticated routes remain unavailable. The
pending scope is cleared after the membership or guardian link commits. Bare OAuth
or magic-link authentication never creates a user or session and receives the
privacy-safe response `This account is not authorised for Class Hero Hub.` Magic
link requests remain enumeration-safe and do not create or send a token when there
is no entitlement or valid invitation.

Admission is checked again on access-token resolution and refresh. Removing,
revoking or suspending the last entitlement therefore blocks both existing access
and renewal. Google consent-screen/test-user permission is not CHH authorisation.

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
session; `POST /api/auth/logout-all` revokes every session for the user. Inactive or
no-longer-authorised users cannot use access or refresh credentials. Invitation
codes, guardian links, school memberships and Google identity matching remain
separate from session admission.

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
2. The Capacitor shell posts it and the pending deep-link return path to
   `/api/auth/google/native`; the backend applies the same admission rule used by
   browser OAuth and magic links.
3. CHH stores the returned short-lived access and rotating refresh credentials using
   encrypted native storage. Native API requests send the access token as a bearer;
   renewal is silent while the account remains authorised. Browser requests use the
   equivalent secure cookie session.

## Operator verification before distribution

- Confirm the CHH Android OAuth client exists in the intended Google Cloud project.
- Confirm its package name and both current debug fingerprints exactly match this file.
- Confirm the OAuth consent screen/test-user policy permits the intended test
  accounts, and separately confirm each account has a valid CHH entitlement or
  invitation.
- Confirm `GOOGLE_CLIENT_ID` is the intended Web client ID in both backend runtime and
  Android build environment.
- Obtain and register release signing SHA-1/SHA-256 only when release signing is
  explicitly approved.
