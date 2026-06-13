# QA Coverage Matrix

Last reviewed: 2026-06-04

2026-06-09 localisation update: English/Arabic fixed UI support now needs QA coverage in both `ltr` and `rtl` document directions. Compact public selectors live on `/`, `/login`, and `/request-access`; the logged-in selector lives in Parent Dashboard -> Settings. Browser language detection only applies when no `localStorage` language is saved.

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

- **Localisation / RTL:** Arabic mode should verify `html[lang="ar"][dir="rtl"]`, no horizontal overflow, readable labels, and contained modals at `320`, `375`, `390`, and `430` px. Parent-entered content must remain unchanged.
- **Custom Request Form:** Verified 1-point conversion text, total value readability, and field alignment (mobile/desktop).
- **Parent Child Cards:** Verified "Dashboard" and "Points" button labels fit without bleeding, and buttons align across cards at desktop widths.
- **Reward Cards:** Verified value sits below title and is not clipped by card boundaries.

## Notes

- **Authentication Source of Truth:** Authenticated header state is sourced exclusively from `/api/me`.
- **Parent Session Coverage:** `backend/tests/test_parent_auth_session.py` verifies configured parent JWT expiry, OAuth `access_token` cookie max-age, CSRF cookie max-age alignment, logout cookie clearing, valid `/api/me` cookie auth, expired JWT rejection, and `Authorization: Bearer` compatibility.
- **Parents & Caregivers Coverage:** `backend/tests/test_family_grownup_management.py` verifies grownup listing, owner-only removal, removed caregiver access rejection, cross-family blocking, self/last-grownup safeguards, unauthenticated blocking, pending invite cancellation, and cancelled invite rejection.
- **Family Settings Coverage:** `backend/tests/test_family_settings.py` verifies default named `week_start_day`, parent updates, invalid value rejection, unauthenticated blocking, current-family scoping, weekly Points Log filtering, and calendar/allowance week-boundary alignment.
- **Allowance Currency Coverage:** `backend/tests/test_allowance.py` verifies strict allowance currency validation and representative global currency codes. Authenticated frontend checks should confirm the searchable allowance currency selector remains usable on desktop and mobile.
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
- **School Bag Packing (B2) Coverage:** `backend/tests/test_school_items.py` covers, at both layers, the child packing checklist — service-layer midnight-lock boundary (`is_date_locked`), idempotent pack/unpack, and rejection of locked dates / weekday mismatch / missing item; HTTP route-layer tests prove the child-scope `POST`/`DELETE /api/child/school-items/{id}/pack` endpoints are wired with child-session auth, that `/today` carries `packed`/`locked`/`check_date`, that `offset=1` (tomorrow) is editable while `offset=0` (today) is locked (`409 checklist_locked`), and that an unknown item returns `404`. Packing awards no points. Frontend: the "Pack for tomorrow" checkboxes are an optimistic mutation surface (revert + inline error on failure) and stay outside the read-only visual harness.
- **School items missing tile (B1) Coverage:** B1 added **no backend surface** — it is a pure frontend read on the B2 `/school-items/today` packed state already covered above, so there are no new service/HTTP tests for it. The midnight-lock boundary it depends on is covered by the B2 `is_date_locked` service tests; B1's own correctness was confirmed by code review (two-timezone trace of the lock boundary recorded in PLAN.md, result PASS) plus `svelte-check`/build. Frontend (manual/visual): the summary tile is a button whose badge counts items still missing for *today*, opening a family-wide modal with per-child "Needed today" / "Pack for tomorrow" "N of M packed / Missing: …" rows and positive "All packed" / "Nothing for this day" states — read-only, outside the optimistic-mutation harness. **B1 follow-up:** the family-wide existence check that hides the tile until set up *does* have both-layer coverage in `test_school_items.py` — service `family_has_school_items` (False when none, True after one, False again after soft-delete, and family-scoped so it doesn't leak across families) and HTTP `GET /api/school-items/configured` returning `{configured: false}` then `{configured: true}` once an item exists.
