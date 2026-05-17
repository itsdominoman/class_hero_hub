# Agent Workflow: Family Hero Hub

## 8-Agent Structure
The project uses a specialized agent structure to manage different aspects of the product lifecycle.

| Agent | Role | Profile Path |
| :--- | :--- | :--- |
| **Zeus** | Chief of Staff / Orchestrator | *Root* |
| **Athena** | Product Manager | `/home/administrator/.hermes/profiles/athena` |
| **Hercules** | Full-Stack Developer | `/home/administrator/.hermes/profiles/hercules` |
| **Hermes** | DevOps / Release | `/home/administrator/.hermes/profiles/hermes` |
| **Apollo** | Marketing Strategy | `/home/administrator/.hermes/profiles/apollo` |
| **Aphrodite** | UX / Family Experience | `/home/administrator/.hermes/profiles/aphrodite` |
| **Ares** | QA / Testing | `/home/administrator/.hermes/profiles/ares` |
| **Calliope** | Content Creation | `/home/administrator/.hermes/profiles/calliope` |

## Operating Rules
- **Mandatory Docs Check:** Before taking action on Family Hero Hub, read the project docs in `/opt/apps/family-hero-hub/docs/`. At minimum check `PROJECT_STATUS.md`, `ROADMAP.md`, and `AGENT_WORKFLOW.md`. For product, market, UX, or feature planning, also check `MARKET_RESEARCH_SUMMARY.md` and relevant PRDs such as `MISSIONS_PRD.md`. Do not rely on memory alone. Inspect docs first, then act.
- Europe dev/Hermes daily QA must keep the read-only `/qa-daily` harness intact. It runs backend pytest, frontend build, Playwright read-only E2E, and smoke checks from `/opt/apps/family-hero-hub/scripts/qa/europe-dev-qa.sh` and loads `/home/administrator/.hermes/fhh-qa.env`.
- Token-based QA login is `POST /api/dev/qa-login`; it must require `QA_LOGIN_TOKEN`, must not log the token, and must stay blocked in production and on production/public domains.
- Stateful QA remains separate and backup-gated. Do not restore or use it until the backup gate is explicitly satisfied.
- Do not remove the Europe dev QA files from main or Europe dev unless an equivalent documented runner replaces them.
- If an agent claims the repo or docs are missing, verify `/opt/apps/family-hero-hub`, `/opt/apps/family-hero-hub/docs`, and `family-hero-hub/` when working inside a profile workspace before concluding the files are unavailable.
- If an agent appears stuck in stale context, start a fresh session rather than guessing from memory.
- **Zeus** is the default profile and orchestrates the team.
- **Hercules** uses the Gemini CLI (`/usr/bin/gemini`) version `0.41.2` for coding tasks.
- Codex CLI is available at `/usr/bin/codex` version `0.128.0` and may be used situationally for deeper refactors or high-confidence work.
- **Athena** defines the product direction and PRDs.
- **Hermes** manages deployments and infrastructure. Hermes now runs on the Europe/France VPS (`vmi3285205`, `213.199.61.244`) with `hermes-gateway.service` and `hermes-dashboard.service` active and the private dashboard at `http://10.250.50.1:9119`.
- Hermes lives at `/opt/apps/hermes-agent` with home `/home/administrator/.hermes`.
- Hermes currently has sudo disabled. Keep any future privilege changes narrow and explicit.
- Do not expose Hermes publicly; use the private WireGuard mesh only.
- Verify Hermes host identity from `hostname`, IP, and logs when needed rather than relying on model memory.
- Current host identity: hostname `vmi3285205`, public IP `213.199.61.244`, private mesh IP `10.250.50.1`.
- Internal review tooling is local/private only: the competitor review viewer lives under `/opt/apps/family-hero-hub/tmp/competitor-review/viewer/` and serves private URL `http://10.250.50.1:8765`; the docs viewer/editor lives under `/opt/apps/family-hero-hub/tmp/docs-viewer/` and serves private URL `http://10.250.50.1:8766`.
- **Ares** ensures quality through automated and manual testing.
- `HERMES_RULES.md` at `/opt/apps/family-hero-hub/HERMES_RULES.md` is a local-only rules file and is intentionally excluded from GitHub.
- `tmp/` is ignored and may contain local agent logs or drafts.

## Model Policy
- Use smaller or cheaper models for review, summarization, and orchestration when they are sufficient; reserve heavier models for major architecture, difficult debugging, or higher-risk implementation decisions.
- **Hercules** (Developer) uses Gemini CLI 0.41.2 directly.
- **Zeus** may use gpt-5.4-mini for orchestration and delegated review work when it is the right fit.
- OpenAI fallback (gpt-4o-mini) remains an explicit-approval option for limited cases.

## Workflow Patterns
- **Research -> Strategy -> Execution**
- Inspect first, edit second.
- Show diffs before deploy.
- Deploy only after approval.
- Commit only after successful deployment and visual QA.
