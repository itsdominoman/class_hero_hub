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
- **Zeus** is the default profile and orchestrates the team.
- **Hercules** uses the Gemini CLI (`/usr/bin/gemini`) version `0.41.2` for coding tasks.
- Codex CLI is available at `/usr/bin/codex` version `0.128.0`.
- **Athena** defines the product direction and PRDs.
- **Hermes** manages deployments and infrastructure. Hermes now runs on the Europe/France VPS (`vmi3285205`, `213.199.61.244`) with `hermes-gateway.service` and `hermes-dashboard.service` active and the private dashboard at `http://10.250.50.1:9119`.
- Hermes lives at `/opt/apps/hermes-agent` with home `/home/administrator/.hermes`.
- Hermes currently has sudo disabled. Keep any future privilege changes narrow and explicit.
- Do not expose Hermes publicly; use the private WireGuard mesh only.
- Verify Hermes host identity from `hostname`, IP, and logs when needed rather than relying on model memory.
- **Ares** ensures quality through automated and manual testing.
- `HERMES_RULES.md` at `/opt/apps/family-hero-hub/HERMES_RULES.md` is a local-only rules file and is intentionally excluded from GitHub.
- `tmp/` is ignored and may contain local agent logs or drafts.

## Model Policy
- Use **Gemini 2.5 Flash Lite** for non-coding agents where possible to save tokens.
- **Hercules** (Developer) uses Gemini CLI 0.41.2 directly.
- **Zeus** should not default to gpt-5.4-mini.
- OpenAI fallback (gpt-4o-mini) only with explicit approval.

## Workflow Patterns
- **Research -> Strategy -> Execution**
- Inspect first, edit second.
- Show diffs before deploy.
- Deploy only after approval.
- Commit only after successful deployment and visual QA.
