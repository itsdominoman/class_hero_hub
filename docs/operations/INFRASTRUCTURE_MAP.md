# Infrastructure Map

## 1. Purpose
Overview of server roles and connectivity.

## 2. Scope
Entire infrastructure topology.

## 3. When to use this restore path
N/A

## 4. What this restores
N/A

## 5. What this does NOT restore
N/A

## 6. Required access
N/A

## 7. Required offline secrets/keys
N/A

## 8. Required backup source options
N/A

## 9. Required approval gates before destructive actions
N/A

## 10. Exact backup source paths
N/A

## 11. Exact restore target paths
N/A

## 12. Exact commands
N/A

## 13. Expected outputs
N/A

## 14. Validation checks
N/A

## 15. Failure handling
N/A

## 16. Rollback notes
N/A

## 17. What not to do
N/A

## Server Roles
- **US Server (10.250.50.2)**: 
  - Role: Production Family Hero Hub, PostgreSQL (pgBackRest), Caddy, Mailcow, and a legacy `cloudflared` tunnel service.
  - Public Domain: `familyherohub.com`
  - Rules: Should push backups to UK. Should NOT SSH into Europe or UK for anything else.
- **Europe Server (10.250.50.1)**: 
  - Role: Dev/test Family Hero Hub, Hermes agent, Hermes workspace, and private internal tools/viewers.
  - Public Domain: `dev.familyherohub.com`
  - Rules: Should pull from US. Should push to US and UK. Orchestration hub.
- **UK Server (10.250.50.3)**: 
  - Role: Backup hub, Google Drive rclone sync, and WireGuard/VPN node.
  - Public Domain: None (infrastructure node).
  - Rules: Should NOT SSH into US or Europe. Read-only receiver of backups.

## Backup Flow
1. US -> UK (Push)
2. Europe -> US (Pull)
3. Europe -> US (Push)
4. Europe -> UK (Push)
5. UK -> Google Drive (Push via rclone sync)

## SSH Trust Directions
- US -> UK
- Europe -> UK
- Europe -> US

## 18. Last verified date
2026-05-19

## 19. Restore rehearsal status
N/A
