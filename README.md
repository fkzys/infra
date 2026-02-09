

```markdown
# infra

Infrastructure-as-code for personal server stack. Podman Quadlet configs, service configs and secrets — all templated, versioned, and deployed over SSH.

## Stack

| Service | What |
|---|---|
| **traefik** | Reverse proxy, TLS termination (Google ACME + Cloudflare DNS) |
| **synapse** | Matrix homeserver + PostgreSQL |
| **nextcloud** | Nextcloud + MariaDB + Valkey + Nginx |
| **element** | Element Web + Synapse Admin |
| **metrics** | Prometheus + Node Exporter + Grafana |
| **sing-box** | Proxy server (templates only, generator lives in a separate repo) |

## Structure

```
infra/
├── secrets/
│   └── hosts.enc.yaml          # SSH connection info for all servers
├── lib/
│   ├── sops.py                 # SOPS decryption
│   ├── remote.py               # SSH/rsync helpers
│   ├── jinja.py                # Jinja2 environment
│   └── deploy.py               # Core deploy logic (render/diff/deploy)
├── traefik/
│   ├── deploy.py               # Service-specific config
│   ├── templates/              # Jinja2 templates
│   │   ├── traefik.yml.j2
│   │   ├── dynamic1.yml.j2
│   │   └── traefik.container.j2
│   └── secrets/
│       └── secrets.enc.yaml
├── synapse/
│   ├── deploy.py
│   ├── templates/
│   │   ├── synapse.pod.j2
│   │   ├── 1-postgresql.container.j2
│   │   ├── 2-synapse.container.j2
│   │   ├── homeserver.yaml.j2
│   │   └── log.config.j2
│   └── secrets/
│       └── secrets.enc.yaml
├── nextcloud/
│   ├── deploy.py
│   ├── templates/
│   │   ├── nextcloud.pod.j2
│   │   ├── 1-mariadb.container.j2
│   │   ├── 2-valkey.container.j2
│   │   ├── 3-nextcloud-app.container.j2
│   │   ├── 4-nginx.container.j2
│   │   ├── nginx.conf.j2
│   │   └── config.php.j2
│   └── secrets/
│       └── secrets.enc.yaml
├── element/
│   ├── deploy.py
│   ├── templates/
│   │   ├── element-web.container.j2
│   │   ├── synapse-admin.container.j2
│   │   ├── element_config.json.j2
│   │   └── synapse_config.json.j2
│   └── secrets/
│       └── secrets.enc.yaml
├── metrics/
│   ├── deploy.py
│   ├── templates/
│   │   ├── metrics.pod.j2
│   │   ├── 1-prometheus.container.j2
│   │   ├── 2-node-exporter.container.j2
│   │   ├── 3-grafana.container.j2
│   │   └── prometheus.yml.j2
│   └── secrets/
│       └── secrets.enc.yaml
└── sing-box/
    ├── templates/              # Consumed by external generator
    └── secrets/
        └── secrets.enc.yaml
```

## How it works

Each service has:
- **`templates/`** — Jinja2 templates for Quadlet units (`.container`, `.pod`) and service configs
- **`secrets/`** — SOPS-encrypted YAML with passwords, domains, keys
- **`deploy.py`** — thin config that plugs into `lib/deploy.py`

`lib/deploy.py` handles all the logic:
1. Decrypts secrets with SOPS
2. Resolves SSH target from `secrets/hosts.enc.yaml`
3. Renders Jinja2 templates
4. Syncs files to remote via rsync (checksum-based, idempotent)
5. Restarts systemd units only if something changed

### Single-instance vs multi-instance

Services deployed to one server (synapse, nextcloud, element) use `host: server1` in their secrets.

Services deployed to multiple servers (traefik, metrics) use `instances:` with a `host:` reference per instance, and support `--all` flag.

## Prerequisites

- Python 3.10+
- `pip install jinja2 pyyaml`
- [SOPS](https://github.com/getsops/sops) configured with your age key
- SSH access to target hosts
- rsync

## Secrets

All secrets are SOPS-encrypted. To edit:

```bash
# SSH connection info (shared by all services)
sops secrets/hosts.enc.yaml

# Service secrets
sops traefik/secrets/secrets.enc.yaml
sops synapse/secrets/secrets.enc.yaml
sops nextcloud/secrets/secrets.enc.yaml
sops element/secrets/secrets.enc.yaml
sops metrics/secrets/secrets.enc.yaml
```

### `hosts.enc.yaml`

Central SSH config, referenced by all services:

```yaml
server1:
  address: server1.example.ru
  ssh_port: 2222
  ssh_user: root
server2:
  address: server2.example.ru
  ssh_port: 2222
  ssh_user: root
```

### Service secrets

Single-instance services reference a host by name:

```yaml
host: server1

synapse:
  server_name: matrix.example.ru
  postgres_password: "..."
```

Multi-instance services define instances, each referencing a host:

```yaml
common:
  ech_domain: ech.example.ru

instances:
  server1:
    host: server1
    domain: metrics1.example.ru
  server2:
    host: server2
    domain: metrics2.example.ru
```

## Usage

### Single-instance services (synapse, nextcloud, element)

```bash
cd synapse/

# Preview rendered configs
python deploy.py render

# Compare with what's on the server
python deploy.py diff

# Deploy (restarts only if files changed)
python deploy.py deploy

# Deploy without restart
python deploy.py deploy --no-restart
```

### Multi-instance services (traefik, metrics)

```bash
cd traefik/

# List instances
python deploy.py list

# Target one instance
python deploy.py render instance1
python deploy.py diff instance1
python deploy.py deploy instance1

# Target all instances
python deploy.py diff --all
python deploy.py deploy --all
python deploy.py deploy --all --no-restart
```

## What gets deployed where

### Quadlet units → `/etc/containers/systemd/`

Podman Quadlet `.container` and `.pod` files. After rsync, `systemctl daemon-reload` picks them up.

### Service configs → `/opt/podman/<service>/`

Config files (homeserver.yaml, nginx.conf, prometheus.yml, etc.) mounted into containers via Quadlet `Volume=` directives.

### Secrets → `/opt/podman/<service>/` (mode 600)

Signing keys, API tokens — written via SSH, not rsync, with `chmod 600`.

## Remote server layout

```
/opt/podman/
├── traefik/
│   ├── settings/
│   │   ├── traefik.yml
│   │   └── dynamic/
│   │       └── dynamic1.yml
│   ├── google_acme/
│   ├── logs/
│   ├── cf_email
│   └── cf_token
├── synapse/
│   ├── data/
│   │   ├── homeserver.yaml
│   │   ├── *.signing.key
│   │   ├── *.log.config
│   │   └── media_store/
│   └── db/
├── nextcloud/
│   ├── nextcloud/
│   │   └── config/config.php
│   ├── nginx.conf
│   ├── db/
│   └── log/
├── element_synapse_admin/
│   ├── element_config.json
│   └── synapse_config.json
└── metrics/
    └── prometheus/
        └── prometheus.yml

/etc/containers/systemd/
├── traefik.container
├── synapse.pod
├── 1-postgresql.container
├── 2-synapse.container
├── nextcloud.pod
├── 1-mariadb.container
├── 2-valkey.container
├── 3-nextcloud-app.container
├── 4-nginx.container
├── element-web.container
├── synapse-admin.container
├── metrics.pod
├── 1-prometheus.container
├── 2-node-exporter.container
└── 3-grafana.container
```

## Adding a new service

1. Create `<service>/templates/`, `<service>/secrets/`, `<service>/deploy.py`
2. Write Jinja2 templates from existing configs (replace secrets with `{{ variables }}`)
3. Create SOPS-encrypted secrets file
4. Write `deploy.py` — define files list, setup dirs, restart command
5. Test: `render` → `diff` → `deploy`

Minimal `deploy.py`:

```python
#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.deploy import ServiceDeployer

BASE = Path(__file__).parent

deployer = ServiceDeployer({
    'templates_dir': BASE / 'templates',
    'secrets_file': BASE / 'secrets' / 'secrets.enc.yaml',
    'files': [
        ('myservice.container.j2', '/etc/containers/systemd/myservice.container'),
        ('config.yml.j2', '/opt/podman/myservice/config.yml'),
    ],
    'setup_dirs': ['/opt/podman/myservice'],
    'restart_cmd': 'systemctl daemon-reload && systemctl restart myservice',
})

if __name__ == '__main__':
    deployer.run_cli()
```

## Traefik middleware notes

Two IP allowlist middlewares exist in `dynamic1.yml`:

- **`blacklist`** — for services behind Cloudflare. Uses `ipStrategy.excludedIPs` to strip CF proxy IPs and check the real client IP.
- **`blacklist-direct`** — for services accessed directly (no CF). Same allowlist, no `ipStrategy`.

Services behind CF use `blacklist@file`, direct services use `blacklist-direct@file`. Controlled by `behind_cf` flag in metrics secrets.
```
