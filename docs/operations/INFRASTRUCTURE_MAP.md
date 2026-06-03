# Infrastructure Map

## 1. Purpose
Canonical current network, trust, and recovery map for Family Hero Hub infrastructure.

## 2. Scope
Live WireGuard mesh, routed wg-easy client subnets, SSH trust, restore node, and the helper services that keep routed VPN paths persistent across reboot.

## 3. Current Trusted Topology

| Host | Role | Hostname | Mesh IP | Public IP | Routed / client subnet | Notes |
|---|---|---|---|---|---|---|
| Europe hub | Central WireGuard site-to-site hub / route reflector | `fhh-europe` | `10.250.50.1` | `213.199.61.244` | `10.60.0.0/24` via Europe wg-easy | Europe is the hub for the site mesh and the Europe wg-easy client range. |
| US spoke | Production site-mesh node | `fhh-us` | `10.250.50.2` | `204.12.209.190` | `10.8.0.0/24` | US wg-easy clients are routed through the US node. |
| UK spoke | Backup / DR / VPN node | `fhh-uk` | `10.250.50.3` | `87.106.54.49` | `10.70.0.0/24` | UK wg-easy clients are routed through the UK node. |
| Singapore spoke | Site-mesh node | `fhh-singapore` | `10.250.50.4` | `194.233.71.132` | `10.10.0.0/24` | Singapore wg-easy clients are routed through the Singapore node. |
| Restore node | DR receiving node / break-glass restore / recovery node | `vmi3310324` / `fhh-restore` | `10.250.50.5` | `95.111.243.235` | none | Receives the UK backup replica, can reach Europe/US/UK/Singapore by public IP without relying on the Europe mesh, and uses `wg-quick@wg-site`. |
| Home brain | Routed home peer behind Europe wg-easy | `fhh-home-brain` | routed via Europe | - | `10.11.0.0/24` behind `10.60.0.7` | User: `aibotadmin`. Not a direct `10.250.50.0/24` site-to-site peer. |

Restore peer public key currently used in the Europe WireGuard config:

```text
JywJlzQptH5HtqN+Z361o3FqUZ18Rpv+BlaSEr8v5B0=
```

## 4. Trusted Ranges

| Range | Use |
|---|---|
| `10.250.50.0/24` | Site-to-site mesh |
| `10.60.0.0/24` | Europe wg-easy clients and the home peer path |
| `10.8.0.0/24` | US wg-easy clients |
| `10.70.0.0/24` | UK wg-easy clients |
| `10.10.0.0/24` | Singapore wg-easy clients |
| `10.11.0.0/24` | Home VPN clients routed behind home brain |
| `95.111.243.235/32` | Restore node public endpoint |

`10.80.0.0/24` is not active. Treat it as historical or future-only unless live config is later updated to prove otherwise.

## 5. Routing Design Completed

Europe now carries the trusted mesh routes for:

- `10.8.0.0/24` via the US spoke.
- `10.70.0.0/24` via the UK spoke.
- `10.10.0.0/24` via the Singapore spoke.
- `10.250.50.5/32` for the restore server.
- `10.11.0.0/24` routed behind home through the Europe wg-easy/home peer path.

Europe host routing for `10.11.0.0/24` uses source `10.250.50.1` so return routing works correctly.

US, UK, and Singapore were updated so their Europe peer `AllowedIPs` include the remote trusted ranges that are meant to be reachable across the mesh.

## 6. Persistence Services

These services keep the routed wg-easy subnet integration in place after reboot:

- US: `/usr/local/sbin/fhh-us-wg-easy-mesh-route.sh` and `/etc/systemd/system/fhh-us-wg-easy-mesh-route.service` route `10.8.0.0/24` via the wg-easy Docker bridge and add the required FORWARD rules.
- UK: `/usr/local/sbin/fhh-uk-wg-easy-mesh-route.sh` and `/etc/systemd/system/fhh-uk-wg-easy-mesh-route.service` route `10.70.0.0/24` via the wg-easy Docker bridge and add the required FORWARD rules.
- Singapore: `/usr/local/sbin/fhh-singapore-wg-easy-mesh-route.sh` and `/etc/systemd/system/fhh-singapore-wg-easy-mesh-route.service` route `10.10.0.0/24` via the wg-easy Docker bridge and add the required FORWARD rules.
- Europe/home: `/usr/local/sbin/fhh-europe-home-vpn-route.sh` and `/etc/systemd/system/fhh-europe-home-vpn-route.service` route `10.11.0.0/24` through the Europe wg-easy container/home peer path.
- UK DR sync: `/usr/local/sbin/fhh-uk-to-restore-sync.sh`, `/etc/systemd/system/fhh-uk-to-restore-sync.service`, and `/etc/systemd/system/fhh-uk-to-restore-sync.timer` mirror the filtered UK backup set to the restore inbox at `/srv/fhh-restore-inbox/uk/backups` on a daily 06:00 UTC schedule.
- UK and Europe backup retention: `/usr/local/sbin/fhh-uk-backup-retention.sh`, `/etc/systemd/system/fhh-uk-backup-retention.timer`, `/usr/local/sbin/fhh-europe-backup-retention.sh`, and `/etc/systemd/system/fhh-europe-backup-retention.timer` cap Hermes app backups to the latest 2 and Hermes home backups to the latest 3.

After reboot, check each persistence service on its matching host:

| Host | Service |
|---|---|
| `fhh-us` | `fhh-us-wg-easy-mesh-route.service` |
| `fhh-uk` | `fhh-uk-wg-easy-mesh-route.service` |
| `fhh-singapore` | `fhh-singapore-wg-easy-mesh-route.service` |
| `fhh-europe` | `fhh-europe-home-vpn-route.service` |

Example:

```bash
systemctl is-enabled <service>
systemctl is-active <service>
```

## 7. SSH Trust

Completed key-only SSH relationships:

| Source | Destination | Result |
|---|---|---|
| Restore node | `administrator@10.250.50.1` (`fhh-europe`) | Success |
| Restore node | `administrator@10.250.50.2` (`fhh-us`) | Success |
| Restore node | `administrator@10.250.50.3` (`fhh-uk`) | Success |
| Restore node | `administrator@10.250.50.4` (`fhh-singapore`) | Success |
| Restore node | `aibotadmin@10.60.0.7` (`fhh-home-brain`) | Success |
| Europe / US / UK / Singapore / Home brain | `administrator@10.250.50.5` (`vmi3310324` / `fhh-restore`) | Success |

SSH hardening now in force:

- Password authentication is disabled.
- SSH is key-only.
- Public SSH is allowlisted only from trusted public IPs and VPN ranges.
- Restore, Europe, US, UK, and Singapore may be reached by public break-glass SSH from trusted source IPs; SSH is not open to the world.

Restore-side mesh key files:

- `~/.ssh/id_ed25519_fhh_mesh`
- `~/.ssh/id_ed25519_fhh_mesh.pub`

Known hosts were populated for the mesh IPs so host key verification does not fail during restore or recovery work.

## 8. Deprecated / Historical Notes

- `10.50.0.0/24` was abandoned because it conflicted with office/local routing.
- `10.80.0.0/24` is not an active trusted range.
- Home is routed through Europe wg-easy as `10.60.0.7` with `10.11.0.0/24` behind it; it is not a normal `10.250.50.x` site-to-site peer.
- `10.250.50.10` remains a future office-spoke candidate, not an active node.

## 9. Verification

Last verified on `2026-06-03`:

- Restore node rebooted and `wg-quick@wg-site` returned active.
- `10.250.50.5` came back after reboot.
- Restore could ping Europe after reboot.
- Restore could SSH to Europe after reboot using the mesh SSH key.
- Restore could ping `10.250.50.1`, `10.250.50.2`, `10.250.50.3`, `10.250.50.4`, and `10.60.0.7`.
- Restore could SSH out to Europe, US, UK, Singapore, and home brain.
- Europe, US, UK, Singapore, and home brain could SSH into the restore node.
- UK restore inbox verified at `/srv/fhh-restore-inbox/uk/backups` and measured at about `3.6G` after cleanup.
- UK to restore sync uses `rsync` over SSH to `ukbackup@95.111.243.235` with `--delete` and `--delete-excluded`.

## 10. Pending / Next Pass

- Home UFW still needs a careful separate pass.
- Direct Dom to Restore emergency VPN is still optional/future.
- Home to Restore direct DR tunnel is still optional/future.
