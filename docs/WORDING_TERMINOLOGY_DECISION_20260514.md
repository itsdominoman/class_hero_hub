# Family Hero Hub Wording / Terminology Decision

## 1. Current status

- This is a pre-implementation wording and terminology cleanup project.
- The wording direction has been reviewed and approved in principle by Dom.
- No app copy changes have been implemented yet.

## 2. Approved terminology direction

- Use **points** as the everyday term.
- Keep **Hero Points** as the branded/fun term only.
- Remove public **HP** unless there is a very strong compact UI reason and it is explained.
- Remove **House Points** from public wording.
- Use **Available points**, **Saved points**, and **Points on hold**.
- Replace **Positive / Negative / Other** with **Add points / Remove points / Custom**.
- Replace **Open child** with **View child dashboard**.
- Replace **Points** button with **Add / remove points**.
- Replace **Reward Approvals** with **Reward requests / Review reward requests**.
- Keep **dragon** as the main child-progress identity.

## 3. Dom’s refinements

- Do not use plain **Family points** unless the meaning is obvious.
- Prefer **Total available points** or **Family points total** depending on what the value actually represents.
- Avoid **Saved but locked** unless absolutely necessary.
- Prefer:
  - **Locked saved points** if genuinely locked
  - **Points on hold** if reserved during a reward request
  - **Saved for later** for child-friendly savings language
- Use sentence case for user-facing headings and CTAs where possible.

## 4. Approved homepage direction

- **Headline:** Less nagging. Clearer routines. Rewards kids can actually earn.
- **Subheadline:** Family Hero Hub helps parents track points, approve rewards, and keep routines clear — while kids build progress on their own dragon dashboard.
- **Primary CTA:** Request access
- **Secondary CTA:** See how it works

## 5. Approved login direction

- **Parent sign-in**
- **Continue with Google**
- **Don’t have access yet? Request access**
- Trust copy must explain that Family Hero Hub never asks for or stores Google passwords.

## 6. Approved request-access direction

- Make clear that requesting access does not create an account immediately.
- Approval happens first.
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
