# Class Hero Hub — Product Strategy Notes (post-S4 unconstrained review)

**Date:** 2026-07-07
**Author:** Claude (Fable 5) — opinion/strategy report requested by Dom after the post-S4 checkpoint audit. Deliberately unconstrained by the existing blueprint and codebase. No code was changed.
**Companions:** `docs/CLASS_HERO_HUB_MASTER_BLUEPRINT.md` (execution plan), `docs/audits/2026-07-07-post-s4-fable-checkpoint-audit.md` (technical audit).

**Authority note (2026-07-16):** this remains useful product-strategy history. Its messaging,
notification-channel, safeguarding, and pilot recommendations have now been reconciled against the
live CHH and FHH repositories in
[`docs/planning/2026-07-messaging-v1-architecture-plan.md`](../planning/2026-07-messaging-v1-architecture-plan.md).
That plan is authoritative for Messaging v1 architecture and implementation; this document does
not mean messaging or the proposed notification channels are implemented.

---

## 1. Executive summary

**The codebase is now ahead of the product thinking.** The schema, tenancy, and lifecycle work are better than most funded SaaS at this stage. The things most likely to kill this app are not in the repo: notification delivery, teacher habit formation, the pilot design, and the questions a school principal will ask in the sales meeting. That is where the next thinking cycles should go, in parallel with Codex grinding S5–S8.

The failure modes left are **distribution and habit** — code reviews won't catch them. The scarcest resource (Dom's attention) should go to the pilot school relationship; Codex plus checkpoint audits can carry the build.

## 2. Questions Dom has not asked yet

The prompts worth issuing next, roughly in value order:

1. **"Design the pilot as an experiment, not a deployment."** Define what must be true in week 4 for the pilot to be a success (see §13–§14) *before* the pilot starts, or success will be declared because the software worked while the school quietly returns to WhatsApp.
2. **"What's our notification delivery story, concretely, on a GCC parent's phone?"** The single biggest product gap in the blueprint (see §7).
3. **"Who is the buyer, and what do they ask in the meeting?"** Buyer = principal/owner; user = teacher; beneficiary = parent — three different products. The principal will ask: *Where is our data hosted? Can we see teacher–parent messages? What happens when we leave? Can it have our logo?* Draft those four answers now; they are architectural-adjacent and cheap to lock early.
4. **"Walk a real school through the model on paper."** Flagged in blueprint §36.6 and again in the checkpoint audit; still not done. One hour with the pilot school's real timetable and staff list validates or breaks the subject-group/assignment model better than any audit.
5. **"What's the offboarding/export story?"** Schools will ask; regulators eventually will (see §16).
6. **"Audit Codex's diffs as a routine, not an event."** Per-slice, not per-crisis — the S4 lifecycle mess happened because three slices went unreviewed.

## 3. Strategic positioning

Class Hero Hub's pitch is **"the school gets back control of the channel"**: no parent-to-parent noise, no teachers' personal numbers exposed, records kept, safeguarding-visible, bilingual, school-governed. That pitch is genuinely strong *for the principal* — the buyer. It only works if the parent experience is at least as immediate as WhatsApp (§7) and the teacher experience is at least as fast (§8).

Stay a **communication product**. Never become an SIS or LMS: no report cards, no homework submission, no timetabling engine. Integrate with those worlds later; don't build them.

## 4. WhatsApp as the real competitor

**Treat WhatsApp as the competitor, not ClassDojo.** In the GCC, every class already has a free, zero-training, 100%-delivery communication channel: the class WhatsApp group. The product must beat it on control, record-keeping, safeguarding, and bilinguality — and must not lose to it on immediacy or speed. Every product decision should be tested against "would this make a teacher or parent fall back to the WhatsApp group?"

## 5. School-governed / top-down adoption doctrine

**Sell top-down only.** No freemium teacher signups, no "one class free" bottom-up motion. School-governed is the differentiator and the safeguarding story; teacher-initiated adoption would undermine both. The blueprint already leans this way — make it explicit doctrine.

## 6. Safeguarding as a headline feature

Teacher↔parent 1:1 messaging is the highest-liability surface in the product. Recommendation: school admins **can review any thread**, this is **disclosed in the UI to both sides** ("messages are visible to school administration"), and that disclosure is a *selling point*, not a weakness. It is exactly why a school would push teachers off WhatsApp. Decide before S15 because it shapes the messaging UI copy and the pitch.

## 7. Notification delivery strategy

**Pull notification delivery forward — it is existential, and the blueprint defers it too casually.** The current plan is in-app + email until "native apps (deferred)". Honest funnel: GCC parents do not live in email, and a mobile web app they visit voluntarily is a dead letterbox. If parents miss the first two notices, the school reverts to WhatsApp and the pilot dies *while all the software works perfectly*.

- Make the parent app a proper installable **PWA with web push** (Android web push is excellent; iOS supports it since 16.4 but only for home-screen-installed PWAs — design the "add to home screen" moment into guardian onboarding as a first-class step, right after the QR link succeeds; see §9).
- Seriously evaluate the **WhatsApp Business API as a notification channel** — not for content, just "New notice from {School} → open app" nudges. It sounds like heresy ("replacing WhatsApp with… WhatsApp?") but it is market-correct: meet parents where they are, own the content and record inside the app. Even if rejected, reject it deliberately.
- **Measure delivery:** "% of guardians who saw the post within 24h" should be a dashboard number from day one of the pilot.

## 8. Teacher 60-second workflow principle

The product lives or dies on whether posting a photo + caption is faster than WhatsApp (~10 seconds). Budget the teacher flows in **taps and seconds**, test them on a mid-range Android phone on school Wi-Fi, and treat any regression as a P1.

- `/teach` should be designed **phone-first**, not tablet-first as the blueprint says — GCC teachers will use their phones.
- Plan the sad path: 30 kids, photos, one spotty connection — upload retry/queue UX matters more than any feature on the S11–S13 list.

## 9. Parent/guardian onboarding and PWA install strategy

The QR-letter funnel is the growth mechanic; its conversion rate should be measured per class (letters printed → scanned → linked). Extend the funnel one step further: after the guardian link succeeds, the very next screen should drive **PWA installation** ("add to home screen") so the push channel exists from day one. On iOS this is the only route to web push, so it must be designed as a first-class onboarding step with bilingual visual instructions, not an afterthought banner.

## 10. School branding recommendation

Add **school branding (logo + accent colour)** on the parent app, invite letters, and emails earlier than the blueprint's post-MVP deferral — around S10–S11 (parent-facing launch). It is cheap and disproportionately persuasive to the buyer: the principal is buying *their school's app*.

## 11. Behaviour points vs pilot priority

**Do not let behaviour points (S14) delay the pilot.** Posts + photos + diary + working notifications is a sellable, retainable product; points are a habit-hook that can land mid-pilot as a "look, it got better" moment. Keep S14 in the plan, but if calendar pressure appears, the pilot starts without it.

## 12. Messaging risk and admin visibility

Messaging (S15) is kept, but it is the **last** thing to ship before the pilot, not the first — it is the highest-moderation surface, and the notice/diary loop is the actual WhatsApp displacement. Ship it with the admin-visibility + disclosure model from §6 baked in from the first release; retrofitting visibility policy onto an in-use messaging product is far harder than launching with it.

## 13. Pilot-as-experiment design

Treat the pilot as an experiment with a hypothesis, instrumentation, and a kill/iterate criterion — not as a deployment. Decide in advance: what behaviour proves product-market fit at one school, what data is collected, who reviews it weekly, and what happens (fix vs feature vs abandon-surface) when a metric misses. The instrumented funnel: teachers posting → guardians linked → guardians seeing posts within 24h → guardians returning weekly.

## 14. Week-4 pilot success metrics

Proposed definition of success — *teachers still posting without being chased*:

- ≥70% of classes with ≥3 posts/week in week 4;
- ≥60% of guardians linked by end of week 4;
- (delivery) a majority of guardians seeing a post within 24h of publication;
- teacher posting time ≤60 seconds for the common case (photo + caption).

Adjust the numbers with the pilot school, but fix *some* numbers before go-live.

## 15. Data/privacy one-pager recommendation

Write the **data one-pager now** — not a GDPR essay; one page: where the server is, who can access what, retention, export, deletion. Omani PDPL (Royal Decree 6/2022) and Saudi/UAE equivalents mean private schools are starting to ask. One decision has architectural weight: **where is the VPS?** If it is in Europe while selling "school-controlled data" to Gulf schools, know the answer before someone asks.

## 16. Export/offboarding recommendation

A per-school export (CSV/JSON dump of their data) is a small feature that closes deals and de-risks trust. It is on the deferral list — write the *answer* now (what a school gets, in what format, how fast) even if the button ships later. "What happens when we leave?" is a sales-meeting question, not a hardening-slice question.

## 17. Demo school recommendation

Seed a fictional bilingual school (classes, teachers, students, posts, photos, points) via the existing dev seeding pattern, right after S6. It is simultaneously: the sales demo, the screenshot factory, the QA fixture, and the Playwright target. A demo school is a product asset, not test data.

## 18. Pricing / open commercial questions

- Decide pricing **roughly** now — per-student-per-year is the sector norm; in GCC private schools the school pays and may pass it through fees. Not to charge the pilot, but because "what does it cost?" is asked in every first meeting, and the answer shapes whether to build for 200-student nurseries or 2,000-student academies.
- Accept that **this is a services business wearing a SaaS costume for the first five schools**: onboarding = cleaning their Excel exports, training teachers at a staff meeting, answering "I can't log in" at 7:10am. Budget Dom-hours for it; it is also where the roadmap gets learned. The S7 CSV importer's error UX is really *support tooling* — invest accordingly.
- Fee/payment reminders stay firmly out of scope, but the buyer will ask — keep a roadmap answer ready.

## 19. Recommended next-week priorities

In order, and mostly not code:

1. Finish S5–S6 with Codex (the machine is running well).
2. Walk the pilot school's real structure through the data model on paper.
3. Write the data one-pager and the four principal answers (§2.3).
4. Prototype the guardian PWA-install + push moment before S9 lands.
5. Define the week-4 pilot metrics with the pilot school.

## 20. Product safety rule: silent import / no accidental outbound communication

**Rule (binding for all bulk import and seeding work, S7/S8 and any later bulk tooling):** real school data may be imported for demo/pilot preparation, but **bulk import must never send invites, magic links, notifications, emails, or WhatsApp messages by default.**

- Imports create **draft/unsent** invite records (e.g. `send_status='draft'`), never dispatched ones. The same applies to any notification fan-out an import could trigger.
- Contacting teachers or guardians requires an **explicit, separate go-live/release action** by a school admin (or platform admin), clearly labelled with who will be contacted and how many messages will go out ("Release 214 guardian invites for Grade 1–3?").
- This protects the pilot workflow (load a school's real data, review it, fix it, *then* launch), prevents the reputation-killing failure mode of a test import emailing 500 real parents, and makes re-imports safe by default.
- Codex prompts for S7/S8 must state this rule explicitly; tests must assert that an import run produces zero outbound sends.

## 21. Decisions needed from Dom

1. **Notification channel strategy:** PWA web push commitment; WhatsApp Business API nudges — evaluate or explicitly reject.
2. **Messaging admin-visibility policy** (recommend: admins can review, disclosed to both sides) — needed before S15.
3. **Hosting/data-residency answer** for the one-pager — where is the VPS, and is that the long-term answer for Gulf schools?
4. **Pilot success metrics** — agree concrete week-4 numbers (see §14).
5. **Pricing posture** — rough per-student-per-year figure and who pays.
6. **Points-vs-pilot ordering** — confirm the pilot may start without S14 if calendar pressure appears.
7. **Branding slice timing** — approve pulling school logo/colour to ~S10–S11.
