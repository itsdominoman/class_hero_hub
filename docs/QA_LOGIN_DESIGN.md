# QA Login Design

Last reviewed: 2026-05-18

This repo uses dev-only QA login helpers so browser tests can reach authenticated parent and child pages without depending on real OAuth in automation.
The standard Europe/dev QA runner sources `/home/administrator/.hermes/fhh-qa.env` automatically, so Zeus/daily QA does not need ad hoc token exports for the normal flow.

## Parent QA login

- Endpoint: `POST /api/dev/qa-login`
- Purpose: issue a safe dev-only parent session for browser QA
- Required input: `QA_LOGIN_TOKEN`
- Expected identity in the current QA environment: `qa-parent@dev.familyherohub.com`

## Child QA login

- Endpoint: `POST /api/dev/qa-child-login`
- Purpose: issue a safe dev-only seeded child session for browser QA
- Required input: `QA_CHILD_LOGIN_TOKEN`
- Fallback token in local dev: `QA_LOGIN_TOKEN` if child-specific token is not set
- Seeded identity in the current QA environment: `QA Seed Child`
- Seeded family owner: `qa-child-parent@dev.familyherohub.com`

## What the helper is for

- Loading `/parent`
- Loading `/allowance`
- Reading `/calendar`
- Reading `/redemptions`
- Exercising other parent-authenticated read-only pages

## Testing HttpOnly Cookies

The `access_token` issued by the backend is `HttpOnly`. The Playwright test harness in `e2e/qa-support.ts` correctly extracts and applies this attribute to the browser context. This ensures that `document.cookie` in tests accurately reflects production (i.e., the token is invisible to frontend JS), forcing the app to rely on `/api/me` for authentication status.

## What it is not for

- Production authentication
- Public domains
- Mutation-heavy stateful flows unless explicitly gated
- Child-only session impersonation

## Safety rules

- Keep the token out of logs
- Keep the endpoint blocked in production
- Keep QA login separate from normal user auth
- Keep child QA login restricted to the deterministic QA seed
- Do not accept arbitrary child IDs or arbitrary family/session impersonation

## Current child-session status

- The visual QA flow now uses a real seeded child session for the child dashboard route
- The child seed is deterministic and idempotent for the QA family
- Current visual QA uses a real seeded child session. Parent-preview is no longer the primary visual QA path and should only be treated as an emergency fallback if the seeded child fixture is unavailable.
- The child visual run covers the real child route at `320`, `360`, `375`, `390`, `430`, and `768` widths, plus a parent desktop alignment check at `1024`
- Zeus/daily QA does not need a separate child token export when `QA_CHILD_LOGIN_TOKEN` is unset because the helper falls back to `QA_LOGIN_TOKEN`
- The helper should remain dev-only and read-only unless a separate stateful plan explicitly approves more
