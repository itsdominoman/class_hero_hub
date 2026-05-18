# QA Login Design

Last reviewed: 2026-05-18

This repo uses a dev-only parent QA login helper so browser tests can reach authenticated parent pages without depending on real OAuth in automation.

## Parent QA login

- Endpoint: `POST /api/dev/qa-login`
- Purpose: issue a safe dev-only parent session for browser QA
- Required input: `QA_LOGIN_TOKEN`
- Expected identity in the current QA environment: `qa-parent@dev.familyherohub.com`

## What the helper is for

- Loading `/parent`
- Loading `/allowance`
- Reading `/calendar`
- Reading `/redemptions`
- Exercising other parent-authenticated read-only pages

## What it is not for

- Production authentication
- Public domains
- Mutation-heavy stateful flows unless explicitly gated
- Child-only session impersonation

## Safety rules

- Keep the token out of logs
- Keep the endpoint blocked in production
- Keep QA login separate from normal user auth
- Do not invent a child-session workaround when no approved child fixture exists

## Current child-session status

- There is no dedicated child QA login fixture in this checkout
- Visual QA currently uses the safe parent-preview child dashboard route for layout coverage
- A future child-only QA helper should be dev-only and read-only unless a separate stateful plan explicitly approves more
