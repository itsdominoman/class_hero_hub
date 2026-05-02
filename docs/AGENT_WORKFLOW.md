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
- **Zeus** is the default profile and orchestrates the team.
- **Hercules** uses the Gemini CLI (`/usr/bin/gemini`) for coding tasks.
- **Athena** defines the product direction and PRDs.
- **Hermes** manages deployments and infrastructure.
- **Ares** ensures quality through automated and manual testing.

## Model Policy
- Use **Gemini 2.5 Flash Lite** for non-coding agents where possible to save tokens.
- **Hercules** (Developer) uses Gemini CLI 0.40.1 directly.
- **Zeus** should not default to gpt-5.4-mini.
- OpenAI fallback (gpt-4o-mini) only with explicit approval.

## Workflow Patterns
- **Research -> Strategy -> Execution**
- Inspect first, edit second.
- Show diffs before deploy.
- Deploy only after approval.
- Commit only after successful deployment and visual QA.
