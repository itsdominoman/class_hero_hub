# CHH reporting scope and gaps

## Pre-CEO export and messaging-share extension (2026-08-06)

- The filtered School Behaviour Overview now has audited English/Arabic PDF and
  UTF-8 CSV exports. Both reuse the existing school/department permission scope,
  preserve the active date and dimension filters, exclude private behaviour notes,
  and cap the export at 25,000 events. The human-readable PDF includes up to 200
  matching event rows alongside the complete summary; CSV contains the complete
  bounded event set and neutralises spreadsheet-formula cells.
- Authorised management can stage a filtered report PDF and confirmed recognition
  certificate, enter the existing School Messages workflow, choose recipients under
  normal messaging scope, add text, and send the immutable protected document.
- Direct and staged generation are audit-logged. Staged documents expire after 24
  hours if unused; attached documents inherit messaging retention and participant
  access. No public links or second messaging system were added.
- Server-generated certificates use the configured school name and approved accent
  colour in English or Arabic. The existing browser print/PDF certificate continues
  to include the configured HTTPS school logo. Remote logo retrieval was deliberately
  not added to backend PDF generation because doing so without a managed upload would
  introduce an SSRF boundary; a managed school-logo asset can be considered from
  pilot feedback.

## Answer-first position

CHH already has a reusable, school-scoped behaviour reporting foundation. The pre-demo objective is to make it reliable and available to the correct management roles, add useful exports, and keep language neutral and supportive. This project will not turn CHH into generic BI, an MIS, HR/appraisal, finance, attendance or academic-performance system.

## Existing reports

The `/school/reports` UI and `/api/school/reports/behaviour/*` endpoints currently provide:

- date, branch, grade, class, subject, subject group, duty, category, staff, student and category-type filters;
- totals, positive/needs-work split, positive ratio, active students, active staff and signed point totals;
- daily trends;
- class, grade, subject, duty and category breakdowns;
- repeated needs-work, positive recognition, improving and worsening student support lists;
- staff usage/adoption volume with a warning that activity is not performance;
- a bounded one/two-dimensional matrix explorer;
- safe, paginated event drill-down without private family data or behaviour notes.

All baseline endpoints enforce same-school `school_admin` membership, validate referenced dimensions against that school and exclude reversed events.

## Immediate gaps to implement

1. Authorise principal/deputy school-wide reporting and HOD department-scoped reporting without granting setup administration.
2. Add a clean school-level management overview/landing treatment.
3. Add filter-preserving CSV for structured analysis and PDF for human-readable sharing.
4. Audit-log sensitive export generation.
5. Add neutral consistency indicators primarily against each staff member's own baseline, including sample size and the exact wording: `This pattern may warrant a supportive review.`
6. Add recognition distribution/repetition and communication activity summaries only where supported by CHH-owned data and lawful filters.
7. Support secure sharing of an authorised generated artefact through existing School Messages.

## Interpretation safeguards

- Do not publish staff rankings or describe usage volume as teaching quality.
- Do not diagnose personal causes or infer health, menstruation, family problems, mental health, burnout or misconduct.
- Compare a staff member primarily with their own history; cohort comparisons are context only.
- Show sample size and suppress/qualify small samples.
- Indicators require human interpretation and cannot trigger appraisal or discipline automatically.
- Negative behaviour remains private; recognition views remain positive-only.

## Sensible pilot follow-ups

Broadly useful requests discovered during the pilot may become standard CHH features for future schools after product review. Plausible follow-ups include term presets, scheduled management packs, configurable minimum sample sizes, recognition fairness dimensions approved by school policy, and additional CHH-owned engagement summaries.

## Explicitly out of scope

- generic report builders or arbitrary SQL/pivots;
- attendance, grades, examinations, payroll, finance or HR appraisal;
- predictive diagnosis, automated staff discipline or student risk labels;
- public negative rankings, shame boards or “worst” lists;
- FHH private household, allowance, reward or device data in CHH reports;
- demographic analysis without a lawful, explicitly approved school policy and trustworthy data.
