# infra

[![CI](https://github.com/fkzys/infra/actions/workflows/ci.yml/badge.svg)](https://github.com/fkzys/infra/actions/workflows/ci.yml)
![License](https://img.shields.io/github/license/fkzys/infra)
[![Spec](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/fkzys/specs/refs/heads/main/version.json&maxAge=300)](https://github.com/fkzys/specs)

Infrastructure-as-code for a personal server stack and home network. Podman Quadlet configs, OpenWrt router configs, service configs and secrets — all templated, versioned and deployed over SSH or distributed via Cloudflare Workers KV.

## Docs

- **[usage](docs/usage.md)**
    - [Adding a new service](docs/usage.md#adding-a-new-service)
    - [File permissions](docs/usage.md#file-permissions)
    - [Restart command](docs/usage.md#restart-command)
    - [Dynamic file paths](docs/usage.md#dynamic-file-paths)
    - [Multi-instance services with `instances_key`](docs/usage.md#multi-instance-services-with-instances_key)
    - [CLI](docs/usage.md#cli)

- **[structure](docs/structure.md)**
    - [Secrets structure](docs/structure.md#secrets-structure)
    - [What gets deployed where](docs/structure.md#what-gets-deployed-where)
    - [Remote server layout](docs/structure.md#remote-server-layout)
    - [Router layout](docs/structure.md#router-layout)

- **[notes](docs/notes.md)**
    - [Single-instance vs multi-instance](docs/notes.md#single-instance-vs-multi-instance)
    - [Containerized vs native](docs/notes.md#containerized-vs-native)
    - [Traefik middleware notes](docs/notes.md#traefik-middleware-notes)
    - [Pod vs shared network](docs/notes.md#pod-vs-shared-network)
    - [Sing-box](docs/notes.md#sing-box)

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

## Secrets

All secrets are SOPS-encrypted.

SSH connection info (shared by all services) is stored at:
```bash
sops secrets/hosts.enc.yaml
```

And service secrets are stored at:
```bash
.../secrets/secrets.enc.yaml
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

Fork-Parity-1.0.1
