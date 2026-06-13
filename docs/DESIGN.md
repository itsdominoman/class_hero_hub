# Family Hero Hub — Design System

This documents the conventions established on the `claude` polish branch.
Keep new UI consistent with these rules.

## Type scale

| Weight | Use for |
| --- | --- |
| `font-black` | Page H1s and the single primary number on a screen (e.g. the child's "Available to spend" figure, parent summary-strip counts) — nothing else |
| `font-bold` | Section headings (h2–h4), key inline values |
| `font-semibold` | Labels, tabs, badges, buttons, secondary metadata |
| `font-medium` / regular | Body copy |

Uppercase micro-labels ("eyebrows") use the `.eyebrow` class from
`app.css` (`text-[11px] font-semibold uppercase tracking-wider
text-slate-400`). **At most 2–3 per page.** Do not reintroduce arbitrary
letter-spacing utilities like `tracking-[0.22em]`; the widest sanctioned
tracking is `tracking-wider`. Badges/pills may be uppercase
`font-semibold tracking-wide`, but prefer normal case where possible.

## Color tokens (tailwind.config.js)

### Core palette (cool — parent-facing screens)

- `hero` (#7c3aed, light #a78bfa, dark #5b21b6) — brand violet, primary actions
- `savings` (#10b981, dark #047857) — positive/award/green money
- `reward` (#f59e0b, dark #92400e) — rewards/amber
- `penalty` (#f43f5e, dark #be123c) — deductions/destructive

These are the single source of truth. **Never** redeclare `.bg-hero`,
`.text-savings`, etc. in component `<style>` blocks — that was the old
pattern and it caused three different greens to ship at once.

### Child palette (warm — child dashboard only)

The child dashboard intentionally uses a warm cream palette against the
parent screens' cool slate/white, so children feel the space is "theirs"
and parents get a calmer, more businesslike tool. Tokens (all under
`child-`):

- `child-bg` #fffaf4 (page), `child-card` #fffefb (item cards),
  `child-border` #f0e4d7, `child-accent` #ff8d59 (progress gradient end)
- `child-savings-bg/-border/-text` (#fff8e9 / #f4e3b2 / #b98612)
- `child-spend-bg/-border` (#f0fbf7 / #cdeee2)
- `child-hold-bg/-border` (#fff1f1 / #f0c6c6)

Do not use `child-*` tokens on parent-facing screens or vice versa.

## Cards (app.css)

- `.card` — default: white, `rounded-2xl`, `shadow-sm`, slate-200 border.
- `.card-lg` — feature cards: `rounded-[2rem]`, soft large shadow,
  slate-100 border. Used for dashboard section cards and modals-like
  panels.
- `.card-flat` — bordered, no shadow (e.g. dashed empty-state shells).

Buttons: `.btn-hero` / `.btn-secondary` from `app.css`; minimum tap
target 44px is enforced globally for buttons and these classes.

## Visual picker (behaviour presets & rewards)

The "Select Visual (Optional)" picker in the behaviour-preset editor and the
reward editor is **emoji-based**, sourced from one shared `DEFAULT_EMOJIS` array
in `parent/+page.svelte` — the single source of truth for both editors. Emoji are
deliberate over an icon library: they are font-rendered (no assets, no bundle
cost), need **no per-icon i18n** (the picker is visual-only), and render correctly
in both LTR and RTL. The array is **ordered by loose category** (hygiene, chores,
food, school, sport, screen & entertainment, outdoors & nature, pets, music &
creativity, sleep, social/family, treats & rewards, transport, health, plus a few
behaviour-feedback markers like 👍/🚫/😡) so the `flex-wrap` grid reads in groups;
**extend a category in place** rather than appending randomly. The grid keeps its
shape (40px tappable tiles, a leading "clear/none" `X` tile, `border-hero` on the
selected tile); growing the set just wraps more rows. Both editors live inside the
scrollable `#modal-scroll-area` (not the C6 fixed-height *tabbed* picker modal), so
a taller grid simply scrolls — it does not affect C6's constant-height rule.

## Empty / loading states

Use the dragon pet artwork (`/pets/dragon-1/*.png`) instead of bare
spinners or text on both dashboards: egg for loading/no-data, hatchling
for "no rewards yet", young dragon for "nothing waiting". Mark these
images `alt=""` + `aria-hidden="true"` — they are decorative.

## Internationalisation

- English and Arabic live side by side in
  `frontend/src/lib/i18n/messages.ts` and must keep **full key parity**.
- `npm run check:i18n` (in `frontend/`) fails if the key trees diverge.
  Run it whenever you add, rename, or remove a message key.
- Arabic should read as natural, family-friendly Arabic — match meaning
  and tone, not English structure. Keep product terms (Family Hero Hub)
  and established terminology (نقاط، مكافآت، لوحة الوالدين) consistent.
- RTL: layout direction flips via `dir` on `<html>`. When a directional
  icon implies "back/forward", add `rtl:` rotation variants (see the
  child dashboard back link). Prefer `gap-*` over `ml-*`/`mr-*` spacing.

## Motion & feedback (branch `claude-2`)

- **Parent point confirmation** (`point-float` in `parent/+page.svelte`):
  a small `+N`/`−N` chip floats ~44px up from the tapped preset/button
  and fades over ~1.1s, colored `savings`/`penalty`, paired with the
  existing award/penalty sounds. Decorative (`aria-hidden`); keep it
  subtle — parents tap several presets in a row, so no blocking or
  full-screen effects here.
- **Child celebration** (`celebration-*`/`confetti-*` in
  `child/[id]/+page.svelte`): a one-time overlay when the child opens
  the dashboard and has newly earned points since their last visit
  (cursor in `localStorage`, child sessions only). Bouncing dragon
  stage image, eased count-up of the summed new points, light CSS
  confetti, explicit dismiss button. Never triggered by point
  removals; never triggered while a parent previews.
- **Child reward news** (`rewardOutcomes` in `child/[id]/+page.svelte`,
  C9): a one-time overlay when the child returns and a reward request
  they made has since been approved or rejected. Same per-child
  `localStorage` cursor idea as the celebration (keyed on the newest
  `reviewed_at` seen), child sessions only. Approvals use a positive
  green panel with the reward name/icon; rejections stay deliberately
  gentle — slate panel, the parent's note if given, reassurance that the
  points returned, and **no confetti or celebration animation**. It is
  guarded with `!celebration` so it never stacks on the points
  celebration; the points celebration shows first, this follows.
- Keep these interactions distinct: the parent point-float is synchronous
  "that worked" feedback; the child celebration is asynchronous "look
  what you earned" delight; the child reward-news overlay is asynchronous
  "here's what your grown-up decided" — celebratory for yes, gentle for
  no.
- The points modal stays open after awards/removals; the exit is the
  existing X. The picker's Add/Remove grids lead with a dashed +/− tile
  that opens preset creation pre-signed (first so it needs no
  scrolling); the preset editor opens scrolled to the top with the
  title field focused, and an empty title is rejected inline (no
  backend round-trip, no generic error banner).
- Modals that switch tabs/views internally must keep a constant height
  (see the child picker: fixed sheet height, tabs scroll internally) —
  don't let the sheet grow/shrink as content changes.
- **Confirm-with-reason sheet** (A6 "Correct this entry"): for a
  consequential action that needs a quick confirmation plus an *optional*
  short note, use a compact secondary sheet stacked above the current
  modal (`z-[110]`, same bottom-sheet-on-mobile / centered-card-on-desktop
  chrome and dimmed backdrop as the primary modal). Pattern: a title, one
  plain-language explainer line (what the action actually does — here,
  "This adds a balancing entry while keeping the original history."), a
  read-only echo of the affected item, a single optional reason input, an
  inline error slot, and a Cancel / confirm button pair. Reserve this for
  destructive-feeling-but-reversible actions where a free-text reason adds
  value; simple yes/no confirmations still use the native `confirm()`.
- **Correction rows in the points log:** a correction is shown, never
  hidden — the original entry keeps its place with a muted "Corrected"
  badge (and its action removed), and the balancing entry renders
  immediately beneath it as a dashed `hero`-accent row labelled
  "Correction". Entries are grouped by their source link, not by date
  order, so the pair always reads together. Per-entry corrective actions
  are parent-only and never shown on child screens.
- **Child packing checklist** (`schoolItemRow` snippet in
  `child/[id]/+page.svelte`, B2): "Pack for tomorrow" items are tappable
  checkboxes — a circular toggle that is filled with the section accent
  (`amber` for tomorrow, `sky` for today) + a check when packed, and a thin
  outline when not. Packed labels get a muted strike-through. Updates are
  **optimistic**: the toggle flips immediately and reverts with an inline
  per-item error if the request fails (failures are never silent). Once the
  list's date has begun (server `locked=true`, the local-family midnight
  boundary) the checkboxes render as read-only `<span>`s showing the final
  state — same look, no interaction — and parent-preview mode is always
  read-only. The repeated row markup is factored into a single Svelte
  `{#snippet}` rendered in every school-bag branch; prefer a snippet over
  copy-pasting when the same item row appears in multiple template
  branches.
- **Distinguish expected rejections from unexpected failures:** when an
  action maps known backend error codes to specific messages (e.g. the
  correction flow's `correction_*` codes), the catch-all must read as a
  *generic* "Something went wrong. Please try again." — never reuse an
  action-specific rejection message for an unknown code, so an
  infrastructure problem (a 404 from a stale deploy, a 500, a CSRF/network
  failure) stays visually distinct from a legitimate "you can't do that"
  rejection.
- **Time-windowed visibility (decide on the backend; keep the rule pure)**
  (D3, School Bag summary): when a surface is only relevant during part of
  the day in the **family's local timezone** (e.g. "Pack for tomorrow" is a
  6pm→midnight evening nudge, "Needed today" a midnight-onward morning
  check), compute *which sections/data to return* on the **backend** so the
  client never receives — and can't accidentally render — content outside
  its window. Express the boundaries as **named hour constants** (here
  `PACK_TOMORROW_VISIBLE_FROM_HOUR = 18`, `NEEDED_TODAY_VISIBLE_FROM_HOUR = 0`
  in `school_items_service`) rather than magic numbers, so they're trivial to
  retune. Keep the window decision itself a **pure function of (local time,
  state counts)** — no DB, no request object — so the same rule can back a UI
  endpoint *and* a future scheduler (push notifications) without re-derivation;
  the HTTP handler only gathers data and calls into it. Pair the time window
  with a **resolution drop-out**: an item/child leaves its section once
  resolved (everything packed), so the section empties naturally instead of
  persisting a stale "all done" badge for the rest of the window — and let the
  dashboard tile **hide** when nothing is currently in-window rather than
  showing a lingering zero (this is separate from, and stacks with, hiding a
  whole opt-in feature that was never configured).
- **Dashboard summary tiles (count → tap → per-child modal)** (school bag,
  Today calendar): the parent dashboard's summary strip favours *actionable*
  tiles over inert numbers — each tile shows a single count and opens a modal
  with a per-child breakdown and any inline actions. New tiles should follow
  this shape rather than adding a static stat. Back each with a **single
  aggregate endpoint** (`/school-items/summary`, `/calendar/summary`) that
  returns the count, the per-child sections, and a `configured` flag, so the
  dashboard makes one call and the **hide-until-configured** rule (don't show an
  opt-in module a family has never used; once used, show it even at zero) is a
  server-decided boolean, not a frontend guess. A **look-ahead section** inside such
  a modal (the Today modal's "Coming up tomorrow", F1) should preview **item identity,
  not just counts** — list the actual event titles so the parent learns something
  without opening the full view; a bare "1 event · 2 tasks" is noise. Show only what's
  *actionable as a preview*: future tasks are dropped (they resurface in their own day's
  primary section when current), children with nothing fall out, and an all-empty
  look-ahead collapses to a single muted "nothing tomorrow" line. Close such a modal
  with a footer **link to the full surface** (`/calendar`, `/redemptions`) using the
  shared full-width bordered footer-link style, so the summary stays a summary.
- **"Do it yourself" vs "approve a claim" are distinct actions** (E2 vs C10):
  when both a subordinate (child) and an authority (parent) can advance the same
  record, keep the two actions visually and behaviourally separate. A parent
  marking a task complete *themselves* is **immediately final** (no second
  approval — the parent is the approver) and runs the same rewards side-effects
  as an approved claim; approving a *child's* claim stays its own review
  affordance. Don't offer both on the same item at once: an item already claimed
  by the child (pending) shows a read-only "awaiting your review" state in the
  do-it-yourself surface and routes the actual approve/reject to the review
  card — avoiding a duplicate action (and the backend's "already completed"
  conflict). The item can still appear as outstanding in both places while
  unresolved, since from each viewpoint it genuinely is.
- **One surface should answer "is this done?" regardless of who claimed it** (G1):
  once a primary surface exists (the Today modal), make it resolve *both* completion
  paths in place rather than bouncing the parent elsewhere for one of them. A task
  with no claim yet shows the parent's own "do it myself" action (immediately final);
  a task the child has **claimed (pending)** shows a distinct read-but-actionable
  state — a "[someone] says done" pill plus a one-tap **Confirm** (approve) **and
  Reject** — posting to the same review endpoints the per-child card already uses.
  Offer Reject on the primary surface too: if a parent can only confirm there but
  must leave to decline, the surface isn't really the single answer. (This *supersedes*
  the earlier read-only "awaiting your review" pill, which routed approve/reject away.)
  Keep the older per-record review affordance as a **secondary path** rather than
  deleting it the moment a unified surface ships — some users are habituated to it,
  and per-record review is a legitimate alternative workflow; flag it for a later pass
  once the unified surface proves fully redundant. The **badge/outstanding count is
  unaffected**: a pending claim still counts as outstanding until *approved* (the
  parent hasn't agreed yet), so unifying *where* it's resolved doesn't change *what*
  counts.
