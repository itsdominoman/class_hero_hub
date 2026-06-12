# Family Hero Hub Wording / Terminology Decision

## 1. Current status

- This wording and terminology direction has now been implemented in the product where relevant.
- The child savings flow now uses a visible `Bank points` action, a popup savings modal, `savings bonus`, and `next unlock` wording.
- The remaining notes here are the approved terminology baseline for future copy work.

## 2. Approved terminology direction

- Use **points** as the everyday term.
- Keep **Hero Points** as the branded/fun term only.
- Remove public **HP** unless there is a very strong compact UI reason and it is explained.
- Remove **House Points** from public wording.
- Use **Available points**, **Saved points**, and **Points on hold**.
- When allowance is enabled, show the money equivalent beside points and keep points first.
- When allowance is enabled, current points gain allowance value; do not split old and new points for the available balance.
- Replace **Positive / Negative / Other** with **Add points / Remove points / Custom**.
- Replace **Open child** with **View child dashboard**.
- Replace **Points** button with **Add / remove points**.
- Use **Bank points** on the child savings card for the savings flow.
- Use **Savings bonus** for the extra points earned when saved points unlock.
- Use **Next unlock** and **Unlock schedule** for child savings timing.
- Replace **Reward Approvals** with **Reward requests / Review reward requests**.
- Keep **dragon** as the main child-progress identity.

## 3. Dom’s refinements

- Do not use plain **Family points** unless the meaning is obvious.
- Prefer **Total available points** or **Family points total** depending on what the value actually represents.
- Avoid **Saved but locked** unless absolutely necessary.
- Prefer:
  - **Locked saved points** if genuinely locked
  - **Points on hold** if reserved during a reward request
  - **Saved points** or **Saved for later** for child-friendly savings language, depending on context
- Do not use **owed**, **withdraw**, **cash out**, **payment**, or **salary payment** in child-facing allowance copy.
- Do not imply Family Hero Hub directly pays money.
- Treat allowance start timestamps as history/context, not as a cutoff for available allowance value.
- Use sentence case for user-facing headings and CTAs where possible.

## 4. Approved homepage direction

- **Headline:** Less nagging. Clearer routines. Rewards kids can actually earn.
- **Subheadline:** Family Hero Hub helps parents track points, approve rewards, and keep routines clear — while kids build progress on their own dragon dashboard.
- **Primary CTA:** Join the Free Beta
- **Secondary CTA:** See how it works

## 5. Approved login direction

- **Parent sign-in**
- **Continue with Google**
- **Don’t have beta access yet? Join the Free Beta**
- Trust copy must explain that Family Hero Hub never asks for or stores Google passwords.

## 6. Approved request-access direction

- Make clear that the public CTA now says **Join the Free Beta**.
- Explain that beta access is free and no payment details are required.
- Explain that the team plans an affordable parent subscription after public launch.
- Explain that family data will not be sold and ads will not be shown to children.
- Explain that beta families will receive notice before any pricing changes.
- Keep the approval flow before account creation.
- After approval, parents sign in with Google.
- Children do not need Google accounts.

## 7. Files expected for later implementation review

- `frontend/src/routes/+page.svelte`
- `frontend/src/routes/login/+page.svelte`
- `frontend/src/routes/request-access/+page.svelte`
- `frontend/src/routes/parent/+page.svelte`
- `frontend/src/routes/child/[id]/+page.svelte`
- `frontend/src/routes/faq/+page.svelte`
- `frontend/src/routes/family-invite/[token]/+page.svelte` if needed
- `frontend/src/routes/child-link/[token]/+page.svelte` if needed
- `frontend/src/routes/privacy/+page.svelte` if needed
- `frontend/src/routes/terms/+page.svelte` if needed
- `frontend/src/routes/contact/+page.svelte` if needed
- `docs/manuals/glossary.md`
- `docs/manuals/parent-user-manual.md`
- `docs/manuals/child-user-manual.md`
- `docs/manuals/quick-start-for-parents.md`
- `docs/manuals/quick-start-for-children.md`
- `docs/manuals/faq.md`
- `docs/manuals/troubleshooting.md`

## 8. Later implementation rules

- Do not change product logic.
- Do not change routes.
- Do not change backend behavior.
- Do not change deployment config.
- Copy changes must keep frontend and docs/manuals consistent.
- Run frontend build after implementation.
- Report changed files, build/test results, git diff summary, and confirm no deploy occurred.
- Public beta messaging now uses **Join the Free Beta** and clarifies free beta access, no payment details required, future parent subscription intent, no ads to children, and no selling family data.
