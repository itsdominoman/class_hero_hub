# QA Coverage Matrix

Last reviewed: 2026-06-04

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
| `/child/[id]` | child | `frontend/e2e/authenticated-child-pages.spec.ts`, visual layout | child auth fixture + visual | yes | yes | yes | yes | yes | medium | visual |
| `/child-link/[token]` | unknown | route discovery only | manual / token-specific visual | maybe | yes | yes | yes | yes | low | manual-only |
| `/family-invite/[token]` | unknown | route discovery only | manual / token-specific visual | maybe | yes | yes | yes | yes | low | manual-only |
| `/admin/registration-requests` | admin | smoke only via status check | authenticated admin + manual review | yes | yes | yes | yes | yes | high | manual-only |
| `/admin/users` | admin | smoke only via status check | authenticated admin + manual review | yes | yes | yes | yes | yes | high | manual-only |

## Global UI Components

| component | auth type | current test coverage | recommended test coverage | screenshot needed |
| --- | --- | --- | --- | --- |
| Header (Parent) | mixed | `e2e/authenticated-qa-login.spec.ts` | anonymous vs parent vs admin | yes |
| Header (Child) | child | `e2e/visual-layout.spec.ts` | child dashboard specific | yes |

## Visual Regression Surface

- **Custom Request Form:** Verified 1-point conversion text, total value readability, and field alignment (mobile/desktop).
- **Parent Child Cards:** Verified "Dashboard" and "Points" button labels fit without bleeding, and buttons align across cards at desktop widths.
- **Reward Cards:** Verified value sits below title and is not clipped by card boundaries.

## Notes

- **Authentication Source of Truth:** Authenticated header state is sourced exclusively from `/api/me`.
- **Admin Security:** The Admin navigation link is strictly gated by the `is_admin` property of the `currentParent` object.
- **Header QA Coverage:** `frontend/e2e/authenticated-qa-login.spec.ts` now explicitly verifies the header state:
  - Anonymous users see the "Login" link only.
  - Logged-in parents see "Parent Dashboard" and "Logout" (Login is hidden).
  - Logged-in admins see "Parent Dashboard", "Admin", and "Logout".
  - The "Admin" link is verified to be hidden for non-admin users.
- **Layout Consistency:** QA coverage now includes reward card value visibility, custom request form alignment, and parent child-card button alignment.
- **Parent Modal Coverage:** The parent dashboard child modal is expected to show `Points` first, with persistent `Child Dashboard` and `Edit Child` actions plus `Requests`, `School Bag`, `Calendar`, `Savings`, and `Points Log` sections. The repeated summary block is no longer part of the modal body.
- **Child Device Management Coverage:** `backend/tests/test_child_device_management.py` covers parent listing of linked child devices, family scoping, single-device unlink, revoked-session rejection, preserving other linked devices, unauthenticated blocking, and response safety so hashes/raw tokens are not exposed.
- **Avatar Contract:** QA checks should assume numeric avatar keys `1` through `24` resolve to `/avatars/{key}.png`, with initials fallback when an avatar asset is missing.
- **Points Log Coverage:** Behaviour percentage checks should exclude savings, banking, redemptions, holds, and other system financial entries; the ring chart should show the good percentage only.
- `frontend/e2e/public-pages.spec.ts` now covers `/faq` and checks safe internal links.
- `frontend/e2e/visual-layout.spec.ts` saves screenshots under `tmp/qa-runs/YYYYMMDD-HHMMSS-visual-layout/`.
- The child dashboard is now exercised through a deterministic seeded child session in visual QA.
- The child visual checks cover reward cards, the custom request form, pending requests, tasks, events, savings snapshot values, the banking popup, the savings bonus preview, the grouped unlock schedule, and points history.
- The parent visual check includes a desktop/laptop alignment assertion at `1024px` for child-card buttons, while mobile widths keep the safer stacked layout checks.
- `frontend/e2e/authenticated-child-pages.spec.ts` covers the seeded child route directly.
- Visual checks are intentionally focused on obvious layout explosions: horizontal overflow, narrow/over-tall text blocks, crushed headings, and buttons that stop fitting their containers.
- Mutation-heavy surfaces remain out of the default read-only harness unless a future stateful fixture is explicitly approved.
