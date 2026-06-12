# PLAN — Premium polish pass (branch `claude`)

## Architecture summary (as understood)

- **Frontend**: SvelteKit (Svelte 5 runes) + Tailwind 3, static adapter, in
  `frontend/`. All API calls go through `frontend/src/lib/api.ts` to the
  FastAPI backend under `/api`. No SSR data loading — every page fetches
  client-side in `onMount`.
- **Backend**: FastAPI + PostgreSQL (`backend/`, alembic migrations).
  Out of scope for this branch — no API changes.
- **Routes**:
  - `/` marketing homepage, `/login`, `/request-access`, plus static info
    pages (faq, terms, privacy, guides, safety-privacy, contact).
  - `/parent` — main parent dashboard: children grid, a single "picker"
    modal per child with tabs (points / requests / school / calendar /
    savings / points-log), plus settings-menu modals (rewards, family,
    presets, week start, device links).
  - `/child/[id]` — child dashboard (works in child-device session mode or
    parent-preview mode), warm cream palette, dragon pet progression
    (`frontend/static/pets/dragon-1/*.png`: egg → hatchling → young →
    hero → legendary).
  - `/allowance`, `/calendar`, `/redemptions` — parent tools.
- **i18n**: `frontend/src/lib/i18n/messages.ts` exports `en` and `ar`
  objects (same nested key structure); `svelte-i18n` with RTL handled by
  `localeDirection()` + `dir` attribute on `<html>`.
- **Design state today**: `font-black` and 10px letter-spaced uppercase
  eyebrows everywhere; child page hardcodes ~20 hex colors in arbitrary
  Tailwind values; `.card`, `.btn-hero` etc. defined in `app.css` but then
  **overridden** by per-page `:global(.card)` style blocks in parent and
  child pages (radius 2rem vs 1rem, different shadows) and by per-page
  re-declarations of `.text-hero`/`.bg-savings`-style utility classes with
  *different* hex values than tailwind.config.js (#10B981 vs #16a34a…).

## Planned changes

### Phase 2 — design tokens + typography
- tailwind.config.js: align hero/savings/reward/penalty hexes with the
  values actually used in pages (#7c3aed, #10b981, #f59e0b, #f43f5e) and
  add semantic child-palette tokens:
  `child.bg #fffaf4`, `child.card #fffefb`, `child.border #f0e4d7`,
  `child.savings.bg #fff8e9`, `child.savings.border #f4e3b2`,
  `child.savings.text #b98612`, `child.spend.bg #f0fbf7`,
  `child.spend.border #cdeee2`, `child.hold.bg #fff1f1`,
  `child.hold.border #f0c6c6`, `child.accent #ff8d59`,
  `savings.deep #008c81` (hover shade used on bank buttons).
- app.css: single source of truth for `card`, `card-lg` (2rem radius,
  bigger shadow), `card-flat` (no shadow, dashed-friendly), plus an
  `eyebrow` helper class for the few uppercase micro-labels we keep.
  Delete the per-page `:global(.card)` overrides and duplicated color
  utility declarations in parent/child `<style>` blocks.
- Typography pass on the four main pages: `font-black` only for page H1 +
  hero numbers; section headings → `font-bold`; labels/badges/buttons →
  `font-semibold`; demote tracked-uppercase eyebrows to ≤3 per page
  (rest become plain `text-xs font-semibold text-slate-500`).

### Phase 3 — login page
- Inline Google "G" SVG instead of hotlinked favicon.
- Remove blur blobs; add the dragon hero artwork as a friendly visual.

### Phase 4 — child dashboard
- Make **Available to spend** the single dominant number in the header
  card (it currently shows `spending_balance` under an "Available points"
  label while "available to spend" sits in a small tile — confusing).
- Demote saved / locked / on-hold to one compact secondary row.
- Empty states and the loading state use the dragon egg/pet artwork.

### Phase 5 — parent dashboard
- Summary strip above the children grid from already-fetched data:
  total available points across children, pending requests count
  (links to /redemptions), today's pending tasks signal (school-prep
  items already loaded). No new endpoints.
- Empty state (no children yet) uses the dragon egg artwork.

### Phase 6 — homepage
- Collapse the 6 near-identical stat tiles (3 in the hero card + the
  3-tile strip below) into a single set of 3 distinct tiles.

### Phase 7 — workflow friction fixes (audited, each listed before fixing)
1. **Add child** uses `window.prompt()` — jarring and unstylable; replace
   with the existing modal pattern (small inline form modal). Still one
   POST to `/children/` — no API change.
2. **Child dashboard back-navigation**: "Back to parent dashboard" pill is
   uppercase micro-text; make it a clear, normal-case link.
3. **Reject redemption** uses `window.prompt()` for the note — keep
   (single text input, low harm) but confirm copy is clear; out of budget
   to rebuild. *Left alone deliberately.*
4. **Reward request flow (child)**: disabled Request buttons get an
   aria-label explaining why ("Need N more points" already shown — keep).
5. **Settings menu (`<details>`)** stays open after navigation clicks;
   close it on selection.

### Phase 8 — i18n
- `frontend/scripts/check-i18n-parity.mjs`: recursively compares en/ar key
  sets, exits non-zero on divergence; wired as `npm run check:i18n`.
- New keys added for: parent summary strip, add-child modal, empty states,
  consolidated homepage tiles. Arabic written as natural, warm phrasing
  (not literal English), consistent with existing Arabic terminology
  (نقاط, مكافآت, لوحة الوالدين, حصالة...).
- RTL check on every touched screen (logical properties; no new
  left/right-specific utilities without rtl: variants; arrows already
  rotate via existing patterns).

### Phase 9 — docs
- `docs/DESIGN.md` (type scale, tokens, card classes, palette rationale).
- README pointer to DESIGN.md + i18n parity check.
- This file doubles as the changelog (below).

## Deliberately NOT doing
- No backend/API changes, no new dependencies, no new features.
- No redesign of the `/calendar` and `/allowance` pages beyond shared
  class/typography cleanup — they are functional and large; deep rework
  is out of scope.
- Keeping the `window.prompt` rejection-note flow (small, works, and a
  modal rebuild risks regressions in the approval path).

## CHANGELOG

### Design system (`be7c3d5`, `bf25f59`, `a7433ea`)
- `tailwind.config.js`: added `child-*` semantic tokens for the warm
  child palette; aligned `hero/savings/reward/penalty` (+`dark` shades)
  with the values pages actually rendered via per-page overrides.
- `app.css`: new `card-lg`, `card-flat`, `eyebrow` classes; brand CSS
  vars updated to match.
- Deleted the duplicated `:global(.card)`, `.btn-*`, and color-utility
  declarations from parent/child page `<style>` blocks (they shipped
  three different greens and two card radii).
- Typography sweep across home, login, parent, child, calendar,
  allowance, redemptions, request-access: `font-black` now only on page
  H1s and primary numbers; section headings `font-bold`; labels, tabs,
  badges, buttons `font-semibold`; all `tracking-[0.12–0.3em]` arbitrary
  letter-spacing collapsed to `tracking-wide`; 9px text bumped to 10px.
- All hardcoded child-dashboard hex values replaced with tokens.

### Login (`d72631f`)
- Inline Google "G" SVG replaces the hotlinked google.com favicon.
- Blur-blob decorations removed; hero-dragon artwork added as a mascot
  beneath the card (decorative, `aria-hidden`).

### Child dashboard (`86473f7`, `18d9828`)
- "Available to spend" is now the single dominant number (5xl–6xl, in a
  highlighted mint panel); previously the big number was
  `spending_balance` labelled "Available points" while the actual
  spendable figure sat in a small tile.
- Saved / locked / on-hold demoted to one compact 3-tile secondary row
  (all values + allowance equivalents preserved).
- Loading state and empty states (no rewards / no activity / nothing
  waiting) use the dragon artwork instead of spinner/plain text.
- Redundant uppercase section eyebrows removed (kept ≤3 per page).

### Parent dashboard (`4a32ed4`)
- New at-a-glance summary strip above the children grid: total
  available points, pending reward requests (card links to
  /redemptions), school items needed today. Uses only already-fetched
  client-side data; no new endpoints.
- Loading spinner and the no-children empty state use dragon egg art.

### Homepage (`f9822bb`)
- Removed the hero card's Rewards/Access/Devices mini-tile grid, which
  duplicated the Trust/Routines/Momentum strip directly below; three
  distinct tiles remain. (Keys retained in messages.ts.)

### Workflows (`18d9828`)
- Add child: `window.prompt()` replaced with the standard modal
  (labelled input, Enter-to-submit, inline validation + error display).
- Parent settings dropdown closes after choosing an item.
- Child dashboard "back to parent" link: normal case, ≥44px tall, arrow
  direction flips correctly in RTL (`rtl:rotate-0`).
- Left alone deliberately: the reject-redemption note still uses
  `window.prompt` (single optional field; a modal rebuild risks the
  approval path), and `/calendar` + `/allowance` got only the shared
  typography/token sweep, not a structural redesign.

### i18n (`884d105`)
- `frontend/scripts/check-i18n-parity.mjs` + `npm run check:i18n` —
  fails when en/ar key trees diverge.
- Fixed a real pre-existing divergence it caught:
  `faq.gettingStartedQuestion7/Answer7` existed only in Arabic, so the
  English FAQ rendered raw key ids. English strings added.
- New keys (both locales, Arabic phrased naturally): `parent.summary.*`,
  `parent.addChildHint`.

### Docs (`8e4edc5`)
- `docs/DESIGN.md` (type scale, tokens, card classes, child-vs-parent
  palette rationale, empty-state artwork, i18n/RTL rules).
- README section linking design system + parity check.
- `docs/LOCALISATION_NOTES.md` documents the parity check.

## Needs human judgement
- Arabic phrasing of the new strings (`parent.summary.*`,
  `parent.addChildHint`, `faq.gettingStartedAnswer7`) deserves the same
  native-speaker review already flagged in LOCALISATION_NOTES.md.
- The English `gettingStartedAnswer7` mentions "an affordable
  subscription" (mirroring the Arabic) while `home.faqAnswer7` quotes
  "$4–$5 per month" — confirm which pricing wording should be canonical.
- Savings green standardised on #10b981 (the in-app value); marketing
  pages previously rendered the darker #16a34a from the old config.

---

# PLAN — Interaction polish pass (branch `claude-2`, off `claude`)

Baseline: the `claude` design-system branch (tokens, type scale,
card classes, i18n parity check). All new work extends it.

## Scope A plan

- **A1 — keep points modal open**: `applyPreset()` and
  `submitCustomPoints()` currently call `closeModal()` after a
  successful award/penalty. Stop closing; refresh the open modal's
  child reference after `loadDashboard()` (same pattern as
  `saveChildEdit`) so the header points pill updates live.
- **A2 — "+N" confirmation float**: capture the tapped element's
  viewport position, render a small fixed-position `+N`/`−N` chip that
  floats up ~40px and fades over ~1.1s (CSS animation, removed from a
  list on `animationend`/timeout). Green for award, red for removal.
  Decorative: `aria-hidden`, paired with the existing sounds.
- **A3 — "+"/"−" tiles**: append one dashed tile to the Add grid and
  one to the Remove grid in the picker's Points tab; both open the
  existing `presets` modal with `modalForm.points` pre-set to +1 / −1.
  Settings → Behaviour presets unchanged.
- **A4 — child summary tile alignment**: secondary-row tiles become
  `flex flex-col` with the value block pinned via `mt-auto`, so values
  and currency lines align even when one label wraps to two lines.
- **A5 — avatar in child header**: drop the "Avatar: N" badge; render
  the child's actual avatar image (via `$lib/avatars`) as a small
  circle overlapping the dragon-stage tile next to the name.
- **A7 — points-log "show older"**: backend returns the full period
  window (up to a month) but both UIs slice to 8 rows. Add a "show
  older" control revealing more of the already-fetched window
  (parent picker points-log tab + child Recent Activity). History
  beyond one month needs backend work — see "Needs Scope B".
- **A8 — child celebration on new points**: child-session only
  (parent preview never marks entries seen). Track the newest ledger
  `created_at` the child has seen in `localStorage`
  (`familyHeroHub.lastSeenLedger.<childId>`). On dashboard load (and
  `visibilitychange` back to visible → light refetch), collect entries
  newer than the stored cursor: if earned entries (`award`,
  positive `adjustment`, `savings_bonus`) net positive, show a one-time
  overlay — dragon artwork, count-up of the summed new points, small
  CSS confetti — then store the new cursor. If only negative/neutral
  entries, just store the cursor and let the totals update silently.
  First-ever visit stores the cursor without celebrating.

## Needs Scope B (discovered gaps — not implemented)

- **A6 — delete a points-log entry**: there is no backend endpoint to
  delete or reverse a ledger transaction (`backend/app/routes/ledger.py`
  only creates entries; nothing exposes DELETE, and balances are
  derived from the full ledger). A correct implementation needs e.g.
  `DELETE /children/{id}/ledger/{tx_id}` that either hard-deletes the
  row (simple, loses audit trail) or writes a linked reversing entry
  (`source_transaction_id` already exists on the model and would suit
  this), plus rules for entries with downstream effects (savings
  deposits with bonus rows, redemption holds, pet lifetime points from
  awards). Skipped rather than approximating client-side.
- **A7 beyond one month**: `get_ledger_transactions` filters by a
  day/week/month window with no offset/limit. Older history needs a
  paged endpoint (e.g. `?before=<cursor>&limit=50`). The UI's "Year"
  tab already silently maps to "month" — worth fixing alongside.

## Scope B — Proposals for Discussion (DO NOT IMPLEMENT)

### B1 — Meaningful "School items needed today"
Tapping the parent summary tile should show which items, for which
children, are still unpacked. Depends on B2's per-item packed state.
Backend: B2's data plus either a parent query endpoint
(`GET /school-items/packing-status?date=`) returning items with
`packed_at` per child, or extending the existing
`/school-items/today` response with the packed flag. Open questions:
does "still unpacked" mean today's items (morning view) or last
night's pack-for-tomorrow list (accountability view)? Probably both,
labelled differently.

### B2 — Child ticks off "Pack for tomorrow" items
Needs a per-item, per-date "packed" state, resettable daily:
- New table `school_item_checks(id, school_item_id, child_id,
  check_date, packed_at)` — one row per item per date keeps history
  for B1 without a scheduled reset job (the "reset" is implicit:
  no row for today's date = unpacked).
- Endpoints: child-scope `POST /child/school-items/{id}/pack` and
  `DELETE .../pack` (untick), date defaulting to the offset the list
  was shown for; parent-scope read access (feeds B1).
- Open questions: can a child untick after midnight (probably no —
  lock once the target day starts); should packing award points
  (ties into rewardable tasks — suggest no for v1); offline taps on
  the child device (retry queue or accept loss).

### B3 — Child-initiated avatar changes
Two options, no recommendation:
1. **Child picks freely** (no backend change): expose the existing
   avatar set in the child session; reuse `PATCH /children/{id}`…
   except that endpoint is parent-authenticated, so it *does* need a
   child-scope variant (`PATCH /child/me/avatar`) — small but real
   backend change. Trade-offs: maximal child agency, zero parent
   friction; risk is churn/novelty-clicking and parents losing the
   "reward" lever of avatar changes.
2. **Request + parent approval**: child taps a new avatar → creates a
   pending request the parent approves (new table or reuse of the
   redemption-request pattern with a special type). Trade-offs: keeps
   parents in control and makes avatar changes feel earned; costs a
   new approval flow, more backend surface, and slower gratification
   for something cosmetically harmless.

### B4 — Child-facing longer history + visual summary
With existing data only:
- History: same gap as A7 — child ledger endpoint is window-bound to
  a month; a child-scope paged endpoint would be needed for "show me
  everything". Within a month, the UI can already show all rows.
- Visual summary: the parent picker's "good %" donut derives entirely
  from ledger rows already sent to the child
  (`/child/ledger?period=month`), so a child-friendly version (e.g.
  "8 of 10 green days this month" or a weekly bar of net points)
  needs **no new aggregation** for one month. A "good days" ratio per
  calendar day = group fetched rows client-side by date. Anything
  spanning multiple months (streaks, all-time bests) would need a new
  aggregation endpoint (`GET /child/ledger/daily-summary?months=6`)
  to avoid shipping the entire ledger.

## CHANGELOG (claude-2)

### Parent points flow
- A1: awarding/removing points keeps the picker modal open on the
  Points tab; the header points pill refreshes in place
  (`refreshActiveModalChild`). Exit remains the X button.
- A2: `point-float` confirmation chip (+N/−N) floats up from the
  tapped control and fades (~1.1s), paired with the existing sounds.
- A3: dashed +/− tiles at the end of the Add/Remove grids open the
  existing preset-creation modal with points pre-set to +1/−1;
  Settings > Behaviour presets unchanged.

### Child dashboard
- A4: saved/locked/on-hold summary tiles are flex columns with values
  pinned to the bottom edge so numbers and currency lines align.
- A5: "Avatar: N" badge removed; the child's avatar image renders as a
  badge on the dragon tile (RTL-safe `-end-2`).
- A8: one-time celebration overlay for newly earned points since the
  child's last visit (localStorage cursor, child sessions only;
  negative-only changes update totals silently). Dragon bounce,
  count-up, CSS confetti, dismiss button.

### Points logs
- A7: "Show older (N more)" reveals the rest of the already-fetched
  period window in both the parent picker log and the child activity
  list (was hard-truncated at 8 rows). Counter resets on period/modal
  change.
- A6: **not implemented** — requires a backend delete/reverse endpoint
  (see "Needs Scope B" above).

### i18n
- New keys, both locales: `parent.pointsActions.newPreset`,
  `parent.addChildHint` (claude), `child.avatarAlt`,
  `child.celebration{Title,Body,Total,Dismiss}`, `common.showOlder`.

### Docs
- docs/DESIGN.md gained a "Motion & feedback" section covering the two
  animations and the stay-open modal rule.
