# Service Ports

## 1. Purpose
Quick reference for active services and ports.

## 2. Scope
Network mapping of all VPS hosts.

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

## Active Ports
- **US Production**: 
  - Public: HTTP(80), HTTPS(443)
  - Mesh-only: WireGuard(51820)
  - Internal-only: PostgreSQL (Not exposed publicly)
- **Europe Dev/Hermes**: 
  - Public: HTTP(80), HTTPS(443)
  - Mesh-only: WireGuard(51820), Hermes Dashboard(9119)
  - Internal-only: PostgreSQL (Not exposed publicly)
- **UK Hub**: 
  - Public/Mesh: WireGuard(51820), wg-easy(51821)

## Warnings
- **EXPLICIT WARNING**: Do NOT expose backup stores (`/opt/apps/backups`) publicly via Caddy or any web server.
- **EXPLICIT WARNING**: Do NOT expose PostgreSQL (`5432`) publicly.

## 18. Last verified date
2026-05-19

## 19. Restore rehearsal status
N/A
