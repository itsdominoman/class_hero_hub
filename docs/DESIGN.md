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
- Keep these two interactions distinct: the parent one is synchronous
  "that worked" feedback; the child one is asynchronous "look what you
  earned" delight.
- The points modal stays open after awards/removals; the exit is the
  existing X. The picker's Add/Remove grids lead with a dashed +/− tile
  that opens preset creation pre-signed (first so it needs no
  scrolling); the preset editor opens scrolled to the top with the
  title field focused, and an empty title is rejected inline (no
  backend round-trip, no generic error banner).
- Modals that switch tabs/views internally must keep a constant height
  (see the child picker: fixed sheet height, tabs scroll internally) —
  don't let the sheet grow/shrink as content changes.
