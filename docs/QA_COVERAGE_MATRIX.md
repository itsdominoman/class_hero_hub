# QA Coverage Matrix

Last reviewed: 2026-05-18

This matrix is meant to keep the Europe dev QA surface practical: read-only by default, screenshot-backed where layout matters, and explicit about where we still do not have a safe fixture.

| route | auth type | current test coverage | recommended test coverage | desktop coverage needed | mobile coverage needed | screenshot needed | links checked | buttons/forms checked | data mutation risk | recommended test type |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `/` | public | `frontend/e2e/public-pages.spec.ts`, smoke | public + visual | yes | yes | yes | yes | yes | none | smoke |
| `/login` | public | `frontend/e2e/public-pages.spec.ts`, smoke | public + visual | yes | yes | yes | yes | yes | none | smoke |
| `/privacy` | public | `frontend/e2e/public-pages.spec.ts`, smoke | public + visual | yes | yes | yes | yes | no | none | smoke |
| `/terms` | public | `frontend/e2e/public-pages.spec.ts`, smoke | public + visual | yes | yes | yes | yes | no | none | smoke |
| `/contact` | public | `frontend/e2e/public-pages.spec.ts`, smoke | public + visual | yes | yes | yes | yes | no | none | smoke |
| `/request-access` | public | `frontend/e2e/public-pages.spec.ts`, smoke | public + visual | yes | yes | yes | yes | yes | low | smoke |
| `/faq` | public | `frontend/e2e/public-pages.spec.ts`, visual | public + visual | yes | yes | yes | yes | no | none | smoke |
| `/calendar` | parent | smoke, visual layout (parent auth) | authenticated + visual | yes | yes | yes | yes | yes | medium | authenticated |
| `/parent` | parent | `frontend/e2e/authenticated-qa-login.spec.ts`, visual layout | authenticated + visual | yes | yes | yes | yes | yes | low | authenticated |
| `/allowance` | parent | `frontend/e2e/authenticated-qa-login.spec.ts`, visual layout | authenticated + visual | yes | yes | yes | yes | yes | medium | authenticated |
| `/redemptions` | parent | visual layout | authenticated + visual | yes | yes | yes | yes | yes | medium | authenticated |
| `/child/[id]` | child | visual layout via parent-preview fallback; no child-only fixture yet | child auth fixture + visual | yes | yes | yes | yes | yes | medium | visual |
| `/child-link/[token]` | unknown | route discovery only | manual / token-specific visual | maybe | yes | yes | yes | yes | low | manual-only |
| `/family-invite/[token]` | unknown | route discovery only | manual / token-specific visual | maybe | yes | yes | yes | yes | low | manual-only |
| `/admin/registration-requests` | admin | smoke only via status check | authenticated admin + manual review | yes | yes | yes | yes | yes | high | manual-only |
| `/admin/users` | admin | smoke only via status check | authenticated admin + manual review | yes | yes | yes | yes | yes | high | manual-only |

## Notes

- `frontend/e2e/public-pages.spec.ts` now covers `/faq` and checks safe internal links.
- `frontend/e2e/visual-layout.spec.ts` saves screenshots under `frontend/test-results/visual-layout/`.
- The child dashboard is currently exercised through a safe parent-preview route in visual QA because there is no dedicated child QA login fixture yet.
- Visual checks are intentionally focused on obvious layout explosions: horizontal overflow, narrow/over-tall text blocks, crushed headings, and buttons that stop fitting their containers.
- Mutation-heavy surfaces remain out of the default read-only harness unless a future stateful fixture is explicitly approved.
