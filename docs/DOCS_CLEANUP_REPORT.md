# Docs Cleanup Report

Date: 2026-07-09

Scope: `docs/` markdown files plus top-level markdown files. Application code, database files, migrations, frontend logic, and backend logic were not changed.

## Classification Summary

### 1. Class Hero Hub current docs

Keep as current Class Hero Hub documentation.

| File | Recommended action | Notes |
| --- | --- | --- |
| `README.md` | Rewrite as current Class Hero Hub repo README | Existing file was Family Hero Hub product README; preserve old version in archive first. |
| `docs/BACKEND_PERFORMANCE.md` | Keep | Current school/admin/teacher/student performance reference. |
| `docs/CLASS_HERO_HUB_MASTER_BLUEPRINT.md` | Keep | Current master implementation blueprint; inherited Family Hero Hub content is intentional context. |
| `docs/DEMO_DATA.md` | Keep | Current generated school demo-data note. |
| `docs/audits/2026-07-07-post-s4-fable-checkpoint-audit.md` | Keep | Current audit trail; do not remove. |
| `docs/audits/2026-07-07-post-s5-teachers-assignments-audit.md` | Keep | Current audit trail; do not remove. |
| `docs/audits/CLAUDE_CLASS_HERO_HUB_AUDIT.md` | Keep | Current audit trail; Family references are part of migration analysis. |
| `docs/audits/CODEX_CLASS_HERO_HUB_AUDIT.md` | Keep | Current audit trail; Family references are part of migration analysis. |
| `docs/implementation/CLASS_HERO_HUB_IMPLEMENTATION_LOG.md` | Keep | Current Class Hero Hub implementation log. |
| `docs/product/CLASS_HERO_HUB_PRODUCT_STRATEGY_NOTES.md` | Keep | Current Class Hero Hub product notes. |
| `docs/DOCS_CLEANUP_REPORT.md` | Keep | This cleanup audit report. |

### 2. Inherited Family Hero Hub architecture/reference docs

Move to `docs/archive/family-hero-hub/` and add a short historical-context note at the top.

| File | Recommended action | Notes |
| --- | --- | --- |
| `PLAN.md` | Archive under `top-level/` | Old Family Hero Hub UI polish/design plan. |
| `SECURITY_CHECKLIST.md` | Archive under `top-level/` | Old bootstrap/admin checklist using Family-era terminology. |
| `docs/AGENT_WORKFLOW.md` | Archive | Old Family Hero Hub agent workflow and paths. |
| `docs/APK_FUTURE.md` | Archive | Old Family Hero Hub Capacitor wrapper notes. |
| `docs/CLOUDFLARE_TUNNEL.md` | Archive | Old deployment reference for Family Hero Hub. |
| `docs/CURRENT_DEPLOYMENT.md` | Archive | Family Hero Hub infrastructure/deployment snapshot. |
| `docs/DESIGN.md` | Archive | Old Family Hero Hub design system; useful only as visual history. |
| `docs/GOOGLE_OAUTH.md` | Archive | Old Family Hero Hub OAuth setup and domains. |
| `docs/LOCALISATION_NOTES.md` | Archive | Old family/parent/child localisation glossary. |
| `docs/MISSIONS_PRD.md` | Archive | Old parent-to-child mission concept. |
| `docs/PROJECT_STATUS.md` | Archive | Detailed Family Hero Hub status/history. |
| `docs/QA_COVERAGE_MATRIX.md` | Archive | Old family-app QA matrix. |
| `docs/QA_LOGIN_DESIGN.md` | Archive | Old QA login design for Family Hero Hub flows. |
| `docs/ROADMAP.md` | Archive | Old Family Hero Hub roadmap. |
| `docs/SMOKE_TESTING.md` | Archive | Old family-app smoke-test guide. |
| `docs/UPGRADE_TRACKER.md` | Archive | Old Family Hero Hub upgrade log. |
| `docs/WORDING_TERMINOLOGY_DECISION_20260514.md` | Archive | Old family-app wording decision. |
| `docs/operations/*.md` | Archive under `operations/` | Operational/infrastructure history. Preserve as audit trail; several files contain Family Hero Hub domains, backup names, and host paths. |

### 3. Irrelevant Family Hero Hub product/market docs

Propose deletion after review. Do not delete in this pass.

| File | Recommended action | Notes |
| --- | --- | --- |
| `docs/MARKET_RESEARCH_SUMMARY.md` | Proposed deletion | Family chore/allowance market research, not Class Hero Hub school product research. |
| `docs/manuals/child-user-manual.md` | Proposed deletion | Family child-user manual. |
| `docs/manuals/faq.md` | Proposed deletion | Family Hero Hub FAQ. |
| `docs/manuals/glossary.md` | Proposed deletion | Family product glossary. |
| `docs/manuals/parent-user-manual.md` | Proposed deletion | Family parent-user manual. |
| `docs/manuals/quick-start-for-children.md` | Proposed deletion | Family child quick-start. |
| `docs/manuals/quick-start-for-parents.md` | Proposed deletion | Family parent quick-start. |
| `docs/manuals/troubleshooting.md` | Proposed deletion | Family product troubleshooting. |

### 4. Mixed docs

Split or rewrite into Class Hero Hub version.

| File | Recommended action | Notes |
| --- | --- | --- |
| `README.md` | Split/rewrite | Archive the old Family Hero Hub README and replace with a concise current Class Hero Hub README that points to blueprint, implementation log, audits, demo data, and performance docs. |

## Actions Performed

This section is updated as the cleanup is applied.

- Archived inherited Family Hero Hub reference docs under `docs/archive/family-hero-hub/`.
- Added historical-context notes to archived markdown files.
- Rewrote top-level `README.md` as a Class Hero Hub repo README.
- Left proposed-deletion product/manual files in place for review.
- Preserved all audit trail docs.

## 2026-07-16 messaging documentation authority update

- Added `docs/planning/2026-07-messaging-v1-architecture-plan.md` as the primary
  authoritative CHH/FHH Messaging v1 architecture and implementation plan.
- Marked the master blueprint's original S15 messaging model partially superseded rather
  than deleting it.
- Linked the current plan from the README, product strategy, implementation/integration
  audit, and implementation log.
- The FHH companion source is unambiguously identified as
  `/opt/apps/family-hero-hub/docs/planning/2026-07-fhh-school-messaging-integration-plan.md`.
- Messaging remains planned; no documentation updated in this pass claims that messaging,
  notification workers, native deep links, or new schema have been implemented.
