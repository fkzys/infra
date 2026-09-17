# infra

[![CI](https://github.com/fkzys/infra/actions/workflows/ci.yml/badge.svg)](https://github.com/fkzys/infra/actions/workflows/ci.yml)
![License](https://img.shields.io/github/license/fkzys/infra)
[![Spec](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/fkzys/specs/refs/heads/main/version.json&maxAge=300)](https://github.com/fkzys/specs)

Infrastructure-as-code for a personal server stack and home network. Podman Quadlet configs, OpenWrt router configs, service configs and secrets — all templated, versioned and deployed over SSH or distributed via Cloudflare Workers KV.

## Stack

| Service | What |
|---|---|
| `system` | Base OS hardening: sshd (TCP forwarding allowed), sysctl, systemd-networkd, maintenance timers (btrfs scrub, paccache, sysctl reapply) |
| `firewall` | Firewalld zones: public, wireguard, filter-closed, trusted — ports opened per-instance from secrets |
| `backup` | Kopia snapshots to S3 with btrfs atomic snapshots, systemd timer |
| `certs` | Centralized wildcard TLS certificates (Google ACME + Cloudflare DNS challenge via lego) |
| `traefik` | Reverse proxy, TLS termination |
| `synapse` | Matrix homeserver + PostgreSQL |
| `element` | Element Web + Synapse Admin |
| `element-call` | Element Call via LiveKit SFU + lk-jwt-service |
| `nextcloud` | Nextcloud + MariaDB + Valkey + Nginx + cron timer |
| `metrics` | Prometheus + Node Exporter + Grafana |
| `i2p` | I2P anonymous overlay network (i2pd daemon, native, no container) |
| `mirotalk` | MiroTalk SFU — WebRTC video conferencing (Podman container) |
| `wireguard` | WireGuard mesh + client tunnels (native, no container) |
| `sing-box` | Proxy server + client/router config generator with Cloudflare KV distribution |
| `router` | OpenWrt router configs: nftables tproxy, network, wireless, firewall, dhcp — distributed via KV |

## Structure

```text
infra/
...
├── certs/
│   ├── deploy.py
│   ├── secrets/
│   └── .certstore/              ← gitignored, lego state + certs
...
├── sing-box/
│   ├── deploy.py              ← server deploy (render/diff/deploy)
│   ├── generate.py            ← client/router config generator + KV
│   ├── templates/
│   ├── secrets/
│   └── .output/               ← gitignored
...
└── router/
    ├── generate.py            ← OpenWrt config generator + KV
    ├── templates/
    ├── secrets/
    └── .output/               ← gitignored
```

## How it works

Each service has:

- `templates/` — Jinja2 templates for Quadlet units, configs or scripts
- `secrets/` — SOPS-encrypted YAML with passwords, domains, keys
- `deploy.py` — thin config that plugs into `lib/deploy.py`

### Server deploy flow

1. Decrypts secrets with SOPS
2. Resolves SSH target from `secrets/hosts.enc.yaml`
3. Renders Jinja2 templates
4. Syncs files to remote via rsync (checksum-based, idempotent)
5. Applies file ownership/permissions if specified (`owner`, `mode` in file config)
6. Restarts systemd units only if something changed (restart command can be a static string or a callable for dynamic commands)

### Router/client config flow

`sing-box/generate.py` and `router/generate.py` use a different delivery model — configs are rendered locally, uploaded to Cloudflare Workers KV, and pulled by devices over HTTPS:

```
sops decrypt → jinja render → KV upload → device wget/curl
```

This avoids SSH to constrained devices (OpenWrt routers, phones) while keeping configs versioned and secrets encrypted at rest.

## What gets deployed where

Quadlet units go to `/etc/containers/systemd/` on remote.

Service configs go to `/opt/podman/<service>/` and are mounted into containers via Quadlet `Volume=`.

Secrets (signing keys, API tokens) are written via SSH with `chmod 600`.

Certificates go to `/etc/ssl/certs/` and `/etc/ssl/private/` — mounted read-only into containers that need them, read directly by native services.

Native service configs:
- system → `/etc/ssh/sshd_config`, `/etc/sysctl.d/`, `/etc/systemd/network/`, `/etc/systemd/journald.conf`, systemd timers
- firewall → `/etc/firewalld/zones/`
- backup → `/root/scripts/backup.sh`, systemd service + timer
- wireguard → `/etc/wireguard/wg0.conf`
- i2p → `/etc/i2pd/i2pd.conf`

Router configs (via KV):
- nftables → `/etc/nftables/nft-ipv6`
- network, wireless, firewall, dhcp, system → `/etc/config/`
- sing-box init → `/etc/init.d/sing-box_my`
- ip rules → `/etc/rc.local`

## Single-instance vs multi-instance

Services deployed to **one server** (synapse, nextcloud, element, element-call, mirotalk, backup) have `host: server1` in their secrets.

Services deployed to **multiple servers** (traefik, metrics, wireguard, sing-box, system, firewall, i2p) have `instances:` with a `host:` reference per instance and support `--all`.

**Router** uses a different model — multiple routers defined under `routers:` in secrets, configs delivered via KV instead of SSH.

## Containerized vs native

Most services run as **Podman containers** managed via Quadlet units.

**i2p**, **wireguard**, **system**, and **firewall** run as **native systemd services** — they need host networking, kernel-level interfaces (WireGuard), or direct system integration. Only config files are deployed, no Quadlet units.

**Router** configs are native OpenWrt UCI/nftables files — no containers involved.

## Traefik middleware notes

Two IP allowlist middlewares in `dynamic1.yml`:

**`blacklist`** — for services behind Cloudflare. Uses `ipStrategy.excludedIPs` to strip CF proxy IPs and check real client IP.

**`blacklist-direct`** — for services accessed directly (no CF). Same allowlist, no `ipStrategy`.

Controlled by `behind_cf` flag in service secrets.

## Pod vs shared network

Some services use a Quadlet **Pod** (shared network namespace, containers talk via `localhost`): synapse + postgresql, nextcloud + mariadb + valkey + nginx, element-call (livekit + lk-jwt).

## Secrets

All secrets are SOPS-encrypted.

SSH connection info (shared by all services) is stored at:
```bash
sops secrets/hosts.enc.yaml
```

And service secrets are stored at:
```bash
.../secrets/secrets/secrets.enc.yaml
```

## Prerequisites

- Python 3.10+
- `pip install jinja2 pyyaml requests`
- [SOPS](https://github.com/getsops/sops) configured with your age key
- SSH access to target hosts
- rsync
- [lego](https://github.com/go-acme/lego) (for `certs/`)
- [dnsproxy](https://github.com/AdguardTeam/dnsproxy) (for `certs/`)

## License

Fork-Parity-1.0.0
