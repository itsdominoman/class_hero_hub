# Smoke Testing

Last reviewed: 2026-06-04

The Europe dev smoke script is still the read-only baseline for fast checks. It should stay safe to run repeatedly without mutating app data.

## Current smoke scope

- Backend health
- Public frontend pages
- Header authentication state (anonymous)
- Unauthenticated API access behavior
- Public dev URL reachability checks for information only

## Parent session notes

- Parent sessions last 30 days by default.
- The backend uses `ACCESS_TOKEN_EXPIRE_MINUTES` for parent JWT expiry and parent `access_token` cookie max-age.
- The CSRF cookie lifetime is aligned with the parent session lifetime.
- Logout still clears both `access_token` and `csrf_token`.
- Smoke remains read-only and does not attempt to wait out or mutate long-lived sessions.

## Family settings notes

- Parents can set the family-level week start day from the parent Family Settings modal.
- Default is Sunday.
- Available values are Sunday, Monday, Tuesday, Wednesday, Thursday, Friday, and Saturday.
- The setting affects weekly allowance periods, calendar week calculations, and weekly Points Log filtering where implemented.
- Smoke remains read-only and does not PATCH `/api/family/settings`; use backend tests or an approved stateful QA plan for mutation coverage.

## Allowance currency notes

- Allowance setup uses a searchable ISO-style currency selector.
- Search should match currency code, name, and symbol for examples such as USD, OMR, ZAR, AED, INR, AUD, CAD, BRL, and JPY.
- Allowance and savings value displays should include the currency code with a symbol where possible.
- The app does not perform exchange-rate conversion or live-rate lookup.
- Smoke remains read-only and does not save allowance currency changes; use backend tests or an approved authenticated QA run for mutation coverage.

## Parents & Caregivers notes

- Settings -> Parents & Caregivers lets parents view accepted grownups and pending invites.
- The derived family owner can remove another grownup; removal is a soft revoke of that `ParentUser`, not deletion of children or family data.
- Pending invites can be cancelled, and cancelled invite links no longer verify.
- Smoke remains read-only and does not remove grownups or cancel invites; use backend tests or an approved stateful QA plan for mutation coverage.

## Commands

```bash
bash scripts/smoke/europe-dev-smoke.sh
bash scripts/qa/europe-dev-qa.sh smoke
```

## Browser QA commands

```bash
cd frontend
npm run test:e2e:public
npm run test:e2e:auth
npm run test:e2e:child
npm run test:e2e:visual
```

Route inventory:

```bash
node scripts/qa/list-sveltekit-routes.mjs
```

The full read-only daily harness remains:

```bash
bash scripts/qa/europe-dev-qa.sh daily
```

That wrapper loads `/home/administrator/.hermes/fhh-qa.env` automatically and runs:
- Backend health and tests
- Public frontend pages and internal link integrity
- Authenticated header checks (anonymous, parent, admin states)
- Seeded child visual QA through the real dashboard route
- DOM-level layout consistency checks for common regressions

## Screenshot artifacts

- Visual QA screenshots are written to timestamped directories: `tmp/qa-runs/YYYYMMDD-HHMMSS-<mode>/`
- The directory is ignored by git
- Screenshots are artifact-only; do not commit generated files unless a future baseline policy says otherwise
- Real seeded child visual QA uses `QA_CHILD_LOGIN_TOKEN` plus the dev-only child login helper when available
- The read-only smoke mode itself does not run the child visual suite; that lives in the daily/full visual QA path

## Safety assumptions

- Smoke checks must remain read-only
- Do not add form submits, approvals, deletions, or login mutations to smoke
- Keep production out of scope
- Keep dev-only QA login blocked from production/public domains

## Known limitations

- Smoke does not prove the child dashboard session flow by itself
- Smoke does not exercise linked-device unlink because unlink is an intentional mutation; use backend tests or a stateful QA plan for that flow.
- Smoke does not change the family week start setting because that is an intentional mutation.
- Smoke does not remove grownups or cancel family invites because those are intentional mutations.
- Smoke does not replace the real seeded child visual QA run
- Smoke does not replace mobile visual QA
- Tokenized routes such as child-link and family-invite are discovered, but not deeply exercised by smoke
