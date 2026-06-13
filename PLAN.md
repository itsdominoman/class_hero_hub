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

## Standing conventions (apply every session)

- **Docs-sync rule:** whenever a code change affects something documented,
  update ALL relevant docs in the same commit or a closely-following doc
  commit — not just this PLAN.md changelog, but also `docs/DESIGN.md`,
  `docs/LOCALISATION_NOTES.md`, `docs/ROADMAP.md`, `docs/PROJECT_STATUS.md`,
  `docs/QA_COVERAGE_MATRIX.md`, the README, or any other file under
  `/opt/apps/family-hero-hub/docs/` whose content the change makes outdated
  or incomplete. If unsure whether a doc is affected, open it and check.
  (Mirrored in `docs/AGENT_WORKFLOW.md` Operating Rules.)
- **Backend deploys need a container rebuild:** the backend image bakes the
  code at build time (`build: ./backend`, only `./data` mounted), so after
  any backend change run `docker compose build backend && docker compose up
  -d backend` before dev testing — a frontend-only rebuild leaves the API on
  stale code (root cause of the A6 "every correction 404s" incident).
- **Test both layers:** service-layer tests alone don't prove an endpoint
  exists and is wired; add HTTP route-layer tests for new/changed endpoints.

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
- A6: was deferred here (needed a backend reverse endpoint) — **now
  implemented** as the "Correct this entry" linked-reversal flow; see the
  A6 entry in CHANGELOG (claude-3).

### i18n
- New keys, both locales: `parent.pointsActions.newPreset`,
  `parent.addChildHint` (claude), `child.avatarAlt`,
  `child.celebration{Title,Body,Total,Dismiss}`, `common.showOlder`.

### Docs
- docs/DESIGN.md gained a "Motion & feedback" section covering the two
  animations and the stay-open modal rule.

---

# PLAN — Quick fixes (branch `claude-3`, off `claude-2`)

- **C3**: move the dashed "create preset" +/− tile to the FRONT of the
  Add and Remove grids in the picker's Points tab, so it's visible
  without scrolling past existing presets.
- **C4**: the preset-creation modal must open scrolled to the top with
  the Preset Title input focused (it currently opens with whatever
  scroll position/focus falls out of rendering; `startEditing` already
  scrolls to top but plain opening does not, and nothing receives
  focus).
- **C5**: review-only — A6 and B1/B2 proposals re-presented for
  discussion (see sections above); explicitly NOT implemented here,
  awaiting go-ahead.
- C1/C2 were referenced in the brief but never defined in any prompt
  available to this branch; skipped and flagged.

## CHANGELOG (claude-3)

- Pricing-copy fix (`958d5ac`→`88a6aac`): `gettingStartedAnswer7` (en + ar)
  now states the concrete "$4-5/month per family" figure, consistent with
  `betaTrustLine`, replacing the vaguer "affordable subscription" /
  "اشتراك ميسور التكلفة" phrasing. Both languages updated; i18n parity
  confirmed at 1102/1102.
- C3 (`e380c55`): the dashed create-preset tile is now the FIRST tile
  in both the Add and Remove grids.
- C4 (`218333c`): opening the preset editor (settings entry or +/−
  tile) focuses the Preset Title input with `preventScroll` and resets
  the modal scroll area to the top, so it no longer opens mid-form.
- C5: review-only — A6 and B1/B2 proposals summarized and presented
  for discussion; no implementation in this branch.
- C1/C2: referenced in the brief but never defined in any prompt this
  branch received; skipped and flagged for the requester.
- docs/DESIGN.md motion section updated (tile position, editor focus).
- C1 (defined in follow-up, `72ee866`): submitting a behaviour preset
  with an empty title no longer reaches the backend ("Action failed").
  Client-side check in `handleModalSubmit` shows an inline error under
  the Preset Title field (`parent.presets.titleRequired`, en/ar), adds
  an error border + `aria-invalid`/`aria-describedby`, and refocuses
  the field. Error clears on input/open/edit-toggle. Covers both the
  +/− quick tiles and Settings > Manage Behaviours (shared form).
  C2 remains undefined.
- C6 (`a3283e3`): the per-child picker modal holds a constant height
  across its tabs (full sheet on mobile, `min(50rem, 92dvh)` on
  desktop) with internal scrolling, instead of resizing per tab.
  Swept other modals (calendar, child dashboard, admin) — single-view
  forms, no tab size-jumping, unchanged.
- **C2 (now defined): the points-log "Year" tab showed month data.**
  Investigated: the backend `get_ledger`/`get_ledger_summary` routes
  only accept `period ∈ {day, week, month}` and `get_period_bounds`
  has no `year` case, so a genuine year/all-time view is **backend-only**
  work (see Scope C below). The frontend silently mapped `year → month`
  (`ledgerApiPeriod`) and showed an apologetic `yearlyNote` caption — a
  tab labelled "Year" that actually rendered the current calendar month.
  Decision (judgement call): rather than ship a tab that lies, relabel
  the third tab to **Month**, which is honest for the data already
  returned and needs no backend change. Renamed the period token
  `'year' → 'month'` throughout `parent/+page.svelte`, removed the
  `ledgerApiPeriod` mapping hack (now identity) and the `yearlyNote`
  caption + key (en/ar), giving a coherent Day / Week / Month
  progression. The real year/all-time view is deferred to Scope C and
  flagged in the C5 review summary.

- **C8: Reward Requests ordering — pending first, newest on top.**
  The full `/redemptions` page rendered the raw API order, and the
  backend `order_by` is subtly wrong: `RedemptionRequest.status ==
  pending` is a boolean, and Postgres sorts `false` before `true`, so
  pending requests actually came **last**. Fixed client-side (no API
  change, matching the branch convention and keeping the order
  deterministic regardless of backend): new `$lib/redemptions.ts`
  `sortRedemptions()` puts pending first (newest `created_at` on top),
  then resolved by `reviewed_at` desc (fallback `created_at`). Applied
  to the `/redemptions` page (`sortedRedemptions` derived) and to the
  parent dashboard's `pendingRedemptions` derived (which feeds the
  summary tile count and the pending-only picker/child request lists),
  so both views are guaranteed newest-first. The backend boolean-order
  quirk is left in place (the frontend now sorts authoritatively); a
  future backend tidy could use `(status == pending).desc()`.
- **C10: surfaced the child task-done → parent approval flow.**
  Investigated first: the flow is **fully backend-supported and was
  simply not surfaced**. A child marking a My-Day task done POSTs
  `/child/calendar/{entry_id}/complete`, which creates a
  `CalendarCompletion` with `status="pending"`; parents already have
  `POST /calendar/completions/{id}/approve` and `/reject`
  (`backend/app/routes/calendar.py`) — approve awards the task's points
  (with the existing weekly-streak bonus logic) and writes the ledger
  entry, reject just marks it rejected. The parent calendar GET already
  returns each occurrence's `completion` (id + status + points_awarded).
  No backend change needed. Built the missing UI: a "Tasks to review"
  card at the top of the child picker's **Calendar** tab listing pending
  task completions (newest occurrence first) with Approve/Reject buttons,
  mirroring the C8 reward-request pattern. `processCompletion` posts the
  decision then refreshes the dashboard totals + the child's calendar and
  re-syncs the open modal, so the points pill and the pending list update
  in place. New keys `parent.childCalendar.reviewHeading` / `reviewError`
  (en/ar); status/points labels reuse existing `calendar.pendingApproval`
  and `common.*`. Known limitation (documented, not a workaround): the
  picker's calendar query is a today→+14d window, so a completion for a
  task dated before today won't appear here; the full `/calendar` page is
  the catch-all. Widening that window or adding a dedicated
  pending-completions feed is a possible follow-up.
- **C9: child notification for reward-request approvals/rejections.**
  Extended the A8 "returns and sees what happened" pattern (per-child
  `localStorage` cursor, child sessions only) to reward requests. New
  cursor `familyHeroHub.lastSeenRedemptions.<childId>` stores the newest
  `reviewed_at` the child has seen among resolved requests;
  `maybeNotifyRewardOutcomes()` (called right after
  `maybeCelebrateNewPoints` in the child branch of `loadData`, so it also
  runs on the visibility-return refresh) collects requests resolved since
  the cursor and shows a "Reward news" overlay. Approved items read as a
  happy moment (green panel, `BadgeCheck` + `Gift`, reward name);
  rejected items stay gentle (slate panel, reward name, the parent's note
  if one was given, reassurance that the points came back) with **no
  celebration animation/confetti**. First-ever visit records the cursor
  silently; parent preview never notifies. The overlay is guarded with
  `!celebration` so it sequences *after* the points celebration rather
  than stacking. New keys under `child.rewardNews.*` (en + natural ar).
- **A6 (implemented): "Correct this entry" for points-log entries.**
  Parents can now correct a fat-fingered award/penalty/adjustment via a
  **linked reversing row**, not a delete — the original stays for history.
  - *Model:* added `TransactionType.reversal`. Because `string_enum` uses
    `native_enum=False` (values are stored as VARCHAR, not a DB enum
    type), **no migration is needed** for the new value; the reversing
    row reuses the existing `source_transaction_id` self-FK
    (`2f3c4d5e6a7b`) to point at the entry it cancels. Judgement call per
    the PLAN discussion: a dedicated `reversal` type (over reusing
    `adjustment`) keeps display, eligibility and summary logic
    unambiguous.
  - *Endpoint:* `POST /children/{id}/ledger/{tx_id}/reverse` (parent-auth,
    optional `reason`). Logic lives in `points_service.correct_transaction`
    (unit-tested). Eligibility: type ∈ {award, penalty, adjustment},
    **spending jar only** (savings spawns maturity/bonus rows), not itself
    derived/a correction (`source_transaction_id is None`), nothing
    already references it (`_source_processed` — catches double-correction
    and matured deposits), and within a **7-day** window of `created_at`.
    Ineligible cases raise `CorrectionError` with a stable code
    (`correction_ineligible_type` / `_window_expired` /
    `_already_processed`) → HTTP 400; the frontend maps codes to localized
    messages (both languages).
  - *Monotonic pet progress:* the reverse path **deliberately does not
    touch `pet.lifetime_points`**. Lifetime points were already an
    award-only high-water-mark (penalties/adjustments never decremented
    them, and stage is derived from that field, never recomputed from the
    ledger sum), so a correction that reduces spendable points can never
    regress a dragon stage. Covered by
    `test_correct_transaction_does_not_regress_pet_progress`.
  - *Ledger/summary:* `get_ledger_summary` now folds `reversal` into the
    gained/lost/net tallies (like `adjustment`, by sign) so period totals
    stay honest. The correction row carries the parent's reason as its
    description.
  - *UI:* points-log entries (parent child-modal only — children never see
    it) show a "Correct this entry" pencil action when eligible; it opens
    a small confirm sheet with the explainer "This adds a balancing entry
    while keeping the original history." + an optional reason field. The
    correction renders as a dashed accent row **directly beneath its
    original** (front-end groups by `source_transaction_id`, independent of
    the date sort), and the original gains a "Corrected" badge with its
    action removed. New keys under `parent.pointsLog.correct*` (en +
    natural ar, parity confirmed). New confirm-sheet pattern documented in
    DESIGN.md.
  - *Dev-deploy bug (fixed, `09b7924`):* corrections failed on dev for
    **every** attempt with the generic "Unable to add correction" toast.
    Root cause was **not** the A6 code — the backend image (`build:
    ./backend`, code baked at build, only `./data` mounted) had not been
    rebuilt after the A6 commits, so the running container lacked the
    `/reverse` route. Every POST got a 404 `"Not Found"`, which the
    frontend's code-based mapper doesn't recognise → generic fallback. The
    138 unit tests passed because the A6 tests called
    `points_service.correct_transaction` **directly** and never exercised
    the API route/contract. Fix: redeploy (`docker compose build backend`)
    **and** add HTTP-level regression tests
    (`tests/test_ledger_correction_http.py`) that go through the real route
    so a missing/mis-wired endpoint can't pass again. Verified end-to-end
    against the live Postgres: the new `reversal` VARCHAR value stores fine,
    success nets to zero, and each rejection returns its specific code.
- **B2 (implemented): child-facing school-bag packing checklist.**
  Children can tick "Pack for tomorrow" items off; the gap was that the
  school-bag view was read-only with no per-item packed state.
  - *Model + migration `3a7e1c9d4b52`:* `school_item_checks(id,
    school_item_id, child_id, check_date, packed_at)`, unique on
    (`school_item_id`, `check_date`) + a (`child_id`, `check_date`) index.
    One row per item per date; **absence of a row = not packed** — the
    implicit daily reset, no cron, and dated rows give B1/history for free.
  - *Midnight lock (timezone):* `school_items_service.is_date_locked` =
    `check_date <= family_today`, where `family_today` comes from the
    existing `calendar_service.get_family_today(family.timezone)`. So a date
    is editable only while still in the future locally; `offset=1`
    (tomorrow) is editable, `offset=0` (today) is locked the moment the day
    begins. No reset job, no stored "lock time" — the boundary is derived.
  - *Endpoints:* child-scope `POST` / `DELETE
    /api/child/school-items/{id}/pack` (child-session auth + CSRF like other
    child unsafe routes), idempotent, typed `SchoolCheckError` →
    `409 checklist_locked` / `400 weekday_mismatch` / `404 item_not_found`.
    Both `/today` endpoints (child + parent) now return `packed` / `locked`
    / `check_date` (backward-compatible extra fields; parent dashboard
    ignores them, and they pre-stage B1). **No points awarded** for packing.
  - *Frontend:* "Pack for tomorrow" rows are tappable checkboxes with an
    **optimistic** toggle that reverts + shows a per-item inline error on
    failure (never silent); "Needed today" renders read-only with the final
    state. Markup factored into one `schoolItemRow` snippet. New `child.*`
    strings (en + natural ar, parity verified). No offline/retry queue (v1).
  - *Tests both layers (A6 lesson):* service-layer lock/idempotency/reject
    + HTTP route tests in `tests/test_school_items.py`.
  - *Deploy:* backend image rebuilt (`docker compose build backend && up
    -d backend`) so the migration runs and the new routes are live —
    per the standing rule, not a frontend-only rebuild.
  - *Docs synced:* DESIGN.md (packing checklist + snippet pattern, and the
    expected-rejection-vs-unexpected-failure rule), LOCALISATION_NOTES.md
    (glossary rows + review date), ROADMAP.md, PROJECT_STATUS.md,
    QA_COVERAGE_MATRIX.md. **B1 not built** (parent "N of M packed" tile is
    the next session).
- **A6 follow-up (`this session`): unexpected-error message split.** The
  "Correct this entry" flow now shows a distinct "Something went wrong.
  Please try again." (`correctErrorUnexpected`, en+ar) for any
  non-`correction_*` error (a deploy-gap 404, 500, CSRF, network), separate
  from the specific correction rejections — so an infra problem is visually
  distinguishable from a legitimate "can't correct this" rejection.

## Scope C — Future

- **Pending task-approvals are window-bound (C10 follow-up).** The parent
  child-modal **Calendar** tab's "Tasks to review" card is fed by the
  picker's `/calendar` query, which is a **today → +14d** window. A child
  task-done completion whose `occurrence_date` is **before today** (an
  overdue task the child only just marked done) therefore **never appears**
  in that card — the full `/calendar` page is the only catch-all today.
  Proposed fix (not implemented here): a dedicated
  `GET /calendar/completions?status=pending` endpoint, **decoupled from any
  date window**, returning all pending completions for the family's
  children (newest first), so the Calendar tab can surface **every** pending
  approval regardless of age. Decoupling from the date window is the whole
  point — do not re-introduce a forward-looking bound. Pairs naturally with
  the same paged-ledger backend pass noted for the C2-followup.

## Scope C — Proposals for Discussion (DO NOT IMPLEMENT)

### C2-followup — Genuine "Year" / all-time points history
The points-log periods are bounded windows (current day / current week
/ current calendar **month**) with no offset or limit, computed in
`points_service.get_period_bounds`. A real "Year" view (or "all time")
needs backend work:
- extend the `Literal["day","week","month"]` on `GET /children/{id}/ledger`
  and `/ledger/summary` to include `year` (and/or a paged
  `?before=<cursor>&limit=50` endpoint for true all-time scrolling),
- add a `year` branch to `get_period_bounds` (Jan 1 → Jan 1 next year),
- decide whether the child-facing ledger endpoint mirrors it (ties into
  the A7 "beyond one month" gap and B4 child-history proposal).
This shares the same root cause as the deferred **A7 beyond-one-month**
note: the ledger is window-bound with no pagination. Worth doing the
paged endpoint once and letting both the parent "Year" tab and the
child longer-history view consume it.

---

# C5 — Review summary (REVIEW-ONLY, awaiting go-ahead)

Nothing in this section is implemented. It re-presents the two proposals
the brief asked to surface for a human decision, with the specific
angles requested, so a yes/no (and which-variant) can be given before
any code is written. Related deferred items already written up above:
A6 / A7 (Scope B, claude-2) and the C2-followup (Scope C).

## A6 — Reverse / undo a points-log entry

**Why it keeps coming back:** parents fat-finger an award or a penalty
and there is currently no way to take it back — balances are derived
from the full ledger and `ledger.py` only ever *creates* rows. This is
the single most-requested correction affordance.

**Backend shape (decision needed):** the cleanest audit-preserving
option is a **linked reversing entry**, not a hard delete. The model
already has `LedgerTransaction.source_transaction_id`
(self-FK, `models.py:292`) made for exactly this — a reversal row points
at the row it cancels, the original stays for history, and balances
stay a pure sum. Either add a `reversal` value to `TransactionType`
(`models.py:7`) or reuse `adjustment` with the source FK set. A new
endpoint, e.g. `POST /children/{id}/ledger/{tx_id}/reverse`.

**Three decisions to make:**

1. **UI wording — "Undo" vs "Reverse" vs "Correct this".**
   - *Undo* — friendliest, implies "as if it never happened"; but the
     audit row makes it a reversal, not a true erase, so "Undo" slightly
     over-promises.
   - *Reverse* — accurate to the linked-entry model; reads slightly
     technical to non-finance parents.
   - *Correct this* — frames it as fixing a mistake (warm + honest);
     pairs well with the audit trail and avoids implying deletion.
   - Recommendation to confirm: **"Correct this"** as the action label,
     with a one-line explainer ("Adds a balancing entry — the history is
     kept"). Reject the temptation to literally hide the original.

2. **Time-limiting.** Should reversal be allowed only for a window
   (e.g. the entry is still the most recent, or < 24h old, or before the
   child has "seen" it via the A8 cursor)? Trade-off: a short window
   keeps the ledger trustworthy and avoids re-litigating old history,
   but a parent may only notice a mistake days later. Options:
   (a) no limit; (b) fixed window (24–48h); (c) "latest entry only";
   (d) allow any, but entries already consumed downstream (a savings
   deposit's bonus row, a redemption hold) are blocked. Recommendation
   to confirm: **(d) + a soft 7-day default**, configurable later.

3. **Dragon stage-up clawback.** This is the sharp edge.
   `update_pet_progress` (`points_service.py`) only ever *adds* to
   `pet.lifetime_points` on awards, and the dragon stage is derived from
   lifetime points via `PET_THRESHOLDS`. Reversing an **award** therefore
   raises the question: do we subtract those lifetime points?
   - *Clawback (subtract):* keeps lifetime points honest, but the dragon
     can visibly **regress a stage** (hero → young) — punishing and
     confusing for a child, especially if the correction is the parent's
     own mis-tap.
   - *Monotonic (don't subtract):* the dragon never goes backwards
     (kind, predictable), but lifetime-points no longer equal the summed
     ledger, so the two diverge.
   - Recommendation to confirm: **keep pet progress monotonic — never
     regress the dragon.** Treat lifetime pet points as a "best ever"
     measure decoupled from spendable balance. If a true clawback is
     wanted, gate it so it can *never* drop a stage mid-week, and never
     as a result of a parent-side correction.

**Scope guard:** redemption holds, savings deposits (which spawn a bonus
row) and calendar-task awards (which may carry streak bonuses) all have
downstream rows; v1 should **refuse** to reverse those and only allow
plain `award` / `penalty` / `adjustment` corrections, surfacing a clear
"can't auto-correct this kind of entry" message.

## B1 / B2 — School "pack for tomorrow" checklist

**The gap today:** the parent summary tile "School items needed today"
and the child school-bag view are **read-only** — there is no per-item
"packed" state, so nothing is actually checkable and the tile can't show
*what's still unpacked*.

**B2 — child ticks items off (the foundation):**
- New table **`school_item_checks(id, school_item_id, child_id,
  check_date, packed_at)`** — one row per item per date. No reset job
  needed: "no row for today = unpacked" is the implicit daily reset, and
  keeping dated rows gives B1/history for free.
- Child-scope endpoints `POST /child/school-items/{id}/pack` and
  `DELETE …/pack` (date defaults to the offset the list was shown for).
- Decisions: can a child untick after the target day starts (suggest
  **no — lock at midnight**); does packing award points (suggest
  **no for v1** — keep it a routine, not a points farm); offline taps on
  the child device (retry queue vs. accept loss — suggest accept loss
  for v1).

**B1 — make the parent "needed today" tile meaningful:**
- Tappable tile → list of still-unpacked items per child, fed by B2's
  state. Either a new `GET /school-items/packing-status?date=` or extend
  the existing `/school-items/today` response with a `packed` flag.
- Open question to settle: does "needed today" mean **this morning's**
  items (did they pack for today?) or **last night's pack-for-tomorrow**
  list (accountability)? Likely both, surfaced as two labelled views.

**Sequencing:** B2 is the prerequisite; B1 is a thin read on top. Both
are net-new backend surface (one table, a few endpoints) — genuinely
new feature work, not polish, hence review-only here.

## Recommendation to the requester

Both are worth doing; both need backend work this branch chain has
deliberately avoided. Suggested order if approved: **A6 first** (highest
demand, smallest surface, mostly a guarded reversing-entry endpoint +
one modal action) with the monotonic-dragon decision locked in, then
**B2 → B1** as a small self-contained feature. The C2-followup year/
all-time view can ride along with whichever backend pass happens first,
since it is the same "the ledger needs pagination" root cause.
