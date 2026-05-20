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
- **US Production**: 80/443 Caddy, 22 SSH, 25/465/587/110/143/993/995/4190 Mailcow, 8000 Family Hero Hub API, 5173 Family Hero Hub frontend preview, 7654 Redis proxy, 8443 Mailcow UI proxy, 13306 MySQL proxy, 2019 Caddy admin, 20241 `cloudflared` local tunnel port, 51820 mesh WireGuard, 51821 wg-easy admin.
- **Europe Dev/Hermes**: 80/443 Caddy, 22 SSH, 3000 Hermes workspace UI, 4173 static preview, 4174 Vite preview, 4180 Vite dev, 8000 Family Hero Hub API, 5173 Family Hero Hub frontend, 8642 Hermes gateway, 9119 Hermes dashboard, 8765 competitor-review viewer, 8766 docs viewer, 8767 QA reports viewer, 51820 mesh WireGuard, 51821 wg-easy admin. `8768` is currently not listening.
- **UK Hub**: 22 SSH, 51820 mesh WireGuard, 51821 wg-easy admin. UK is restricted to backup/DR/VPN/Google Drive sync roles.

## Warnings
- **EXPLICIT WARNING**: Do NOT expose backup stores (`/opt/apps/backups`) publicly via Caddy or any web server.
- **EXPLICIT WARNING**: Do NOT expose PostgreSQL (`5432`) publicly.

## 18. Last verified date
2026-05-19

## 19. Restore rehearsal status
N/A

## 20. Restore port validation

On every restored server, validate listening ports before exposing traffic:

```bash
sudo ss -ltnup
sudo docker ps --format 'table {{.Names}}\t{{.Ports}}'
sudo ufw status verbose
```

Hard checks:

- PostgreSQL must not listen publicly.
- `/opt/apps/backups` must not be served publicly.
- wg-easy admin `51821` must not be public unless Dom explicitly approves a temporary allowlisted restore window.
- Europe private dashboards and viewers must remain mesh/private.
- UK must remain backup/DR/VPN only; no n8n/OpenClaw active restore path.

## 21. Final verification status

Verified on 2026-05-20:

- US, Europe, and UK backup runs completed successfully and produced the verified restore-readiness archive set.
- The verified sys-config archives contain the firewall, Docker, WireGuard, SSH trust, and systemd/timer report files required for restore.
- UK `gdrive-crypt` listing confirms the uploaded archive names are visible through the crypt remote as expected.
