# Smoke Testing

Last reviewed: 2026-05-18

The Europe dev smoke script is still the read-only baseline for fast checks. It should stay safe to run repeatedly without mutating app data.

## Current smoke scope

- Backend health
- Public frontend pages
- Header authentication state (anonymous)
- Unauthenticated API access behavior
- Public dev URL reachability checks for information only

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
- Smoke does not replace the real seeded child visual QA run
- Smoke does not replace mobile visual QA
- Tokenized routes such as child-link and family-invite are discovered, but not deeply exercised by smoke
