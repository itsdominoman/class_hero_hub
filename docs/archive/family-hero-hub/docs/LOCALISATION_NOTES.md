> Historical note: This document was inherited from Family Hero Hub and is preserved as historical context for the Class Hero Hub fork. It may describe old domains, paths, product assumptions, or infrastructure that are not current.

# Localisation Notes

Last reviewed: 2026-06-13

Family Hero Hub supports English and Arabic UI labels for fixed app interface text. Parent-entered content is not translated: child names, reward names, custom point reasons, task titles, calendar event titles, school bag items, and family-entered descriptions remain exactly as entered.

Arabic uses neutral Modern Standard Arabic with short, family-friendly labels where possible. Oman/GCC family usage is the first audience, with wider Arabic readability as a second goal.

| English term | Arabic term used | Reason / note | Needs native review? |
| --- | --- | --- | --- |
| Family Hero Hub | Family Hero Hub | Brand name remains English to avoid an awkward literal product name. | No |
| Parent Dashboard | لوحة الوالدين | Clear app Arabic; shorter than a literal “control panel” phrase. | Yes |
| Child Dashboard | لوحة الطفل | Short and understandable for parents and children. | Yes |
| Points | النقاط | Standard app/game term, clear for children. | No |
| Rewards | المكافآت | Natural family-app term for earned rewards. | No |
| Reward Requests | طلبات المكافآت | Clearer than a literal redemption phrase. | Yes |
| Redeem | طلب / صرف حسب السياق | “Redeem” is not always natural in Arabic family usage; request/spend wording is used where clearer. | Yes |
| Allowance | المصروف | Natural GCC/wider Arabic family term for child allowance or pocket money; shorter than literal alternatives. | Yes |
| Savings | الادخار / النقاط المدخرة | “Savings” is rendered as saving/saved points to avoid implying real banking. | Yes |
| School Bag | الحقيبة المدرسية | Common and clear. | No |
| Pack for tomorrow | جهز للغد | Child action label; "جهز" (prepare/pack) is natural and short for the pack-tomorrow checklist (B2). | Yes |
| Packed / Not packed yet | تم التجهيز / لم يُجهز بعد | Checkbox state labels on the child packing checklist. | Yes |
| Tap to tick off what you have packed | اضغط لتعليم ما جهزته | Hint above the checkable list; "تعليم" = mark/tick. | Yes |
| This list is locked for today | قائمة اليوم مقفلة | Shown when a child tries to change a list whose day has already begun. | Yes |
| School items missing — tap to see | أغراض مدرسية ناقصة — اضغط للعرض | Parent summary tile (B1); signals the tile is tappable, not just a count. | Yes |
| School bag — all packed | حقيبة المدرسة — كل شيء جاهز | Positive empty state of the same tile when nothing is missing. | Yes |
| Needed today / Pack for tomorrow | مطلوب اليوم / جهّز للغد | Section headers in the parent B1 school-summary modal. | Yes |
| {packed} of {total} packed | تم تجهيز {packed} من {total} | Per-child progress line in the B1 modal. | Yes |
| Missing: | ناقص: | Prefix before the comma-joined list of unpacked items (ar uses "، " separator). | Yes |
| All packed / Nothing for this day | كل شيء جاهز / لا شيء لهذا اليوم | Per-child positive/neutral states in the B1 modal. | Yes |
| Mark packed | تحديد كمجهّز | Parent action button on a still-missing "Needed today" item (D2) — confirms the child packed it this morning after the checklist locked. | Yes |
| Packed | تم التجهيز | Read-only state badge on an already-packed "Needed today" item (D2). | Yes |
| Pack the school bag for tomorrow | جهّز الحقيبة المدرسية للغد | Evening tile label (D3) when the tile is in pack-tomorrow mode (6pm→midnight). | Yes |
| Nothing to pack right now | لا شيء للتجهيز الآن | Empty state in the time-windowed school-summary modal (D3) when no section is currently in-window/unresolved. | Yes |
| On the calendar today | على جدول اليوم | Parent dashboard "Today" tile label (E1) when something is on; replaced the old "Points available" tile. | Yes |
| Coming up tomorrow | قادم غدًا | De-emphasized look-ahead heading in the Today modal (E1). | Yes |
| {events} events · {tasks} tasks | {events} فعاليات · {tasks} مهام | Per-child counts line in the Today modal (E1); interpolated numbers. | Yes |
| Mark complete | تحديد كمكتمل | Parent action button on a task in the Today modal (E2) — parent records it done themselves; immediately final. Distinct from "Approve" (reviewing a child's claim). | Yes |
| Says done | يقول إنه أنجزها | Pill on a child-claimed (pending) task in the Today modal (G1) — the child says they finished it, awaiting the parent's decision. Paired with Confirm/Reject. | Yes |
| Confirm | تأكيد | One-tap action on a child-claimed task in the Today modal (G1) — approves the child's claim (same effect as the per-child review card's Approve). Reuses the shared "Reject" alongside it. | Yes |
| Nothing on the calendar tomorrow | لا شيء على الجدول غدًا | Empty state for the "Coming up tomorrow" look-ahead (F1) when no child has an event tomorrow. | Yes |
| Open full calendar | فتح التقويم الكامل | Footer link in the Today modal (F2) to the full `/calendar` page. | Yes |
| This entry can't be corrected automatically because some of these points have already been spent. Add a manual adjustment instead. | لا يمكن تصحيح هذا السجل تلقائيًا لأن بعض هذه النقاط صُرفت بالفعل. أضف تعديلاً يدويًا بدلاً من ذلك. | Parent correction-sheet error for `correction_insufficient_available_balance`; keep it practical and action-oriented. | Yes |
| Requests | الطلبات | Short UI label. | No |
| Approve | قبول | Button action for approving a request; use “موافقة” only when approval is a noun/status. | Yes |
| Reject | رفض | Short and standard. | No |
| Tasks | المهام | Standard neutral app Arabic. | No |
| Calendar | التقويم | Standard app term. | No |
| Grownup | ولي أمر / مقدم رعاية | Prefer the family-role wording in visible UI; avoid “شخص بالغ” unless the exact context needs it. | Yes |
| Caregiver | مقدم رعاية | Clear formal-neutral term; may need GCC parent review for warmth. | Yes |
| Points Log | سجل النقاط | Clear and compact. | No |
| Positive | إيجابي | Use as a type/category label, not as an action verb. | Yes |
| Negative | سلبي | Use as a type/category label, not as an action verb. | Yes |
| Add | إضافة | Use for the UI action when adding points or another item. | No |
| Remove | إزالة | Use for the UI action when removing points or another item. | No |
| Positive behaviour | سلوك إيجابي | Child-facing behaviour label. Keep it gentle and non-shaming. | Yes |
| Negative behaviour | سلوك سلبي | Child-facing behaviour label. Keep it gentle and non-shaming. | Yes |
| Custom reason | سبب مخصص / السبب | Uses simple “reason” wording in compact forms. | Yes |
| Preset (saved point action) | قالب | Standardised term for a reusable saved point action/template. Always use قالب for the saved item — do **not** mix in إجراء (“action”) or use سلوك for the preset itself. | Yes |
| Behaviour (the thing a preset rewards) | سلوك | Use سلوك only for the behaviour concept itself (e.g. “Edit Behaviour” تعديل السلوك, positive/negative behaviour labels), not for the saved preset. “Behaviour presets” = قوالب السلوك keeps the two words distinct. | Yes |

Known follow-up: Arabic wording should receive native-speaker review before production launch, especially allowance, caregiver, redeem/request, and child-facing encouragement copy. Terms that still need context review include Positive/Negative labels and any place where approval is used as a noun/status instead of a button action.

## Arabic implementation status — 2026-06-11

The Arabic localisation pass on `develop` has now covered the main non-admin app flows. Production/main was not touched during this work.

Completed non-admin areas include:

- public family invite flow
- public child link flow
- parent dashboard and parent child modals
- parent rewards, reward request, family/caregiver, child link, savings/bank, points action, calendar-week, and behaviour preset modal text
- child dashboard static UI and key fallback/error states
- redemptions page
- allowance page
- calendar page labels, date/time formatting, duration units, and error fallbacks

Admin pages are intentionally English-only and are excluded from Arabic localisation scope.

### Fixed during the June 2026 Arabic pass

The implementation included both static UI localisation and dynamic error fallback cleanup.

Static UI fixes included:

- hardcoded prompts and confirmations
- modal labels, placeholders, headings, helper text, and buttons
- generated date connectors such as `to`
- generated point/unit labels such as `pts`, `point`, `points`, `h`, and `m`
- school bag fallback labels
- default generated transaction/reward descriptions
- selected accessibility labels and alt text

Dynamic error fallback fixes included replacing raw backend/API messages with translated app fallbacks. Non-admin pages should not directly render backend text such as:

- `Not authenticated`
- `Request failed with status 502`
- raw `e.message` / `Error.message` values

`Error.message` may still be inspected internally for known public-link mapping, but it should not be displayed directly to the user.

### Final tracked commit range

Key Arabic localisation commits pushed to `origin/develop` during this phase:

- `31a1ca1 Localise family invite page`
- `422936a Localise allowance page leftovers`
- `11d5d0e Localise parent page leftover strings`
- `c7d283b Localise child and link error fallbacks`
- `d8ad8eb Polish final Arabic locale leaks`
- `2d00110 Localise calendar error fallbacks`
- `00a0654 Localise remaining raw error fallbacks`

### Current non-blocking follow-up

The generic framework 404 page may still show raw `404 Not Found` on mistyped or invalid URLs. This is not part of the normal Arabic app flow, but can be improved later with a branded localised not-found page.

Arabic wording still needs native-speaker review before production launch, especially:

- allowance/pocket money wording
- caregiver/grownup role wording
- redeem/request/spend wording
- child-facing encouragement and negative-behaviour wording
- approval/status wording where context changes the best Arabic term

## Preset terminology standardisation (C7, 2026-06-13)

The Arabic preset/behaviour strings used three synonyms for the same
saved point-action: قالب (template/preset), سلوك (behaviour), and إجراء
(action). قالب was already the dominant term (~11 strings: titles,
existing list, edit/delete/create/apply, errors, behaviourPresets).
Standardised on:

- **قالب = preset** (the saved item) everywhere.
- **سلوك = behaviour** only where the English source says “behaviour”
  (Manage Behaviours, Edit Behaviour, “title for this behaviour”, the
  New behaviour quick tile) and for the positive/negative behaviour
  labels. “Behaviour presets” stays قوالب السلوك.
- The stray **إجراء (action)** term was removed from the preset modal:
  `presets.subtitle` and `presets.update` now use قالب
  (إعداد قوالب قابلة لإعادة الاستخدام / تحديث هذا القالب). إجراء is still
  used elsewhere only for genuine “point actions” menus (إجراءات النقاط),
  a different concept.

## i18n key-parity check (added 2026-06-12)

English and Arabic in `frontend/src/lib/i18n/messages.ts` must always
contain exactly the same keys. A guard script now enforces this:

```
cd frontend
npm run check:i18n
```

It exits non-zero and lists missing keys per locale. Run it whenever
message keys are added, renamed, or removed. On its first run it caught
`faq.gettingStartedQuestion7/Answer7` existing only in Arabic (the
English FAQ rendered the raw key ids); the English strings were added.
