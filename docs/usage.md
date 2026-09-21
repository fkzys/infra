# infra

## Adding a new service

1. Create `<service>/templates/`, `<service>/secrets/`, `<service>/deploy.py`
2. Write Jinja2 templates (replace hardcoded secrets with variables)
3. Create SOPS-encrypted secrets
4. Write `deploy.py`:

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
        ('secret.conf.j2', '/etc/myservice/secret.conf', {'owner': 'root:root', 'mode': '600'}),
    ],
    'setup_dirs': ['/opt/podman/myservice'],
    # string — same command for every instance:
    'restart_cmd': 'systemctl daemon-reload && systemctl restart myservice',
    # or callable(secrets, instance_name) — dynamic command per instance:
    # 'restart_cmd': lambda secrets, instance_name: f"podman pull {secrets['instances'][instance_name]['image']} && systemctl restart myservice",
})

if __name__ == '__main__':
    deployer.run_cli()
```

5. Test: `render` then `diff` then `deploy`

## File permissions

Files in the `files` list support an optional third element — a dict with `owner` and/or `mode`:

```python
'files': [
    ('config.yml.j2', '/opt/podman/myservice/config.yml'),                           # no perms
    ('wg0.conf.j2', '/etc/wireguard/wg0.conf', {'owner': 'root:root', 'mode': '600'}),   # both
    ('config.php.j2', '/opt/podman/nextcloud/config.php', {'owner': '33:33'}),            # owner only
    ('backup.sh.j2', '/root/scripts/backup.sh', {'owner': 'root:root', 'mode': '700'}),  # script
]
```

Applied after rsync via `chown`/`chmod` over SSH. Shown in `render` and `diff` output.

## Restart command

`restart_cmd` controls what runs after files change. It can be a **string** or a **callable**:

```python
# Static — same command for all instances
'restart_cmd': 'systemctl daemon-reload && systemctl restart myservice',

# Dynamic — receives (secrets, instance_name), returns command string
'restart_cmd': lambda secrets, instance_name: (
    f"podman pull {secrets['instances'][instance_name]['image']}"
    f" && systemctl daemon-reload"
    f" && systemctl restart myservice"
),
```

Useful when the restart command depends on per-instance secrets (e.g. pulling a specific container image before restarting).

## Dynamic file paths

`files` and `setup_dirs` can be **callables** that receive `(secrets, instance_name)` and return a list:

```python
# Dynamic paths per instance
'files': lambda secrets, instance_name: [
    ('container.j2', f'/etc/containers/systemd/{secrets["common"]["basename"]}.container'),
    ('config.yml.j2', f'/opt/podman/{secrets["common"]["basename"]}/config.yml'),
],
'setup_dirs': lambda secrets, instance_name: [
    f'/opt/podman/{secrets["common"]["basename"]}',
],
```

Useful when paths depend on secrets (e.g., container name from `common.basename`). Static lists still work as before — callable is checked first.

## Multi-instance services with `instances_key`

The `ServiceDeployer` supports deploying multiple instances of the same service from a single secrets file. By default, it looks for an `instances:` key in the secrets, but this can be overridden via `instances_key`:

```python
# Default — reads secrets['instances']
deployer = ServiceDeployer({
    'multi_instance': True,
})

# Custom key — reads secrets['relay_instances']
deployer = ServiceDeployer({
    'multi_instance': True,
    'instances_key': 'relay_instances',
})
```

The CLI (`list`, `render`, `diff`, `deploy --all`) uses this key to enumerate available instances. This allows a single secrets file to manage different logical groups (e.g., proxy nodes and relay nodes) with separate deploy scripts.

## CLI

### Single-instance (synapse, nextcloud, element, element-call, mirotalk, backup)

```bash
cd synapse/
python deploy.py render
python deploy.py diff
python deploy.py deploy
python deploy.py deploy --no-restart
```

### Multi-instance (traefik, metrics, wireguard, sing-box, system, firewall, i2p)

```bash
cd firewall/
python deploy.py list
python deploy.py render instance1
python deploy.py diff instance1
python deploy.py deploy instance1
python deploy.py deploy instance1 instance2   # multiple instances
python deploy.py diff --all
python deploy.py deploy --all
python deploy.py deploy --all --no-restart
```

### sing-box client/router configs

`sing-box/generate.py` generates client and router configs locally and optionally uploads them to Cloudflare Workers KV for remote distribution via URL. Uses subcommands:

```bash
cd sing-box/

# Generate configs locally
python generate.py generate                        # all clients + routers
python generate.py generate --target clients       # only clients
python generate.py generate --target router        # only routers
python generate.py generate --user alice bob       # only specific users

# Generate + upload to Cloudflare KV
python generate.py generate --upload
python generate.py generate --upload --user alice   # upload only alice

# Token management
python generate.py gen-token                        # generate 1 token
python generate.py gen-token -n 5                   # generate 5 tokens
python generate.py gen-token --user bob alice       # tokens formatted for secrets.yaml

# KV management
python generate.py kv-list                          # list all keys in KV
python generate.py kv-list --prefix phone           # filter by prefix
python generate.py kv-revoke phone-m                # delete phone-m configs from KV
python generate.py kv-purge                         # delete everything from KV
```

When uploading with `--user`, the generated `urls.json` is merged with existing data instead of overwriting — so single-user uploads don't erase other users' URLs.

Add new user:

1. `python generate.py gen-token --user new-phone`
2. `sops secrets/secrets.enc.yaml` — add user block with token
3. `python generate.py generate --upload`
4. Send URL from `output/urls.md`

### Router configs

`router/generate.py` generates OpenWrt configs (nftables, network, wireless, firewall, dhcp, system, init scripts) and uploads to KV. Routers pull configs via `update.sh`.

```bash
cd router/

python generate.py list                        # list routers
python generate.py render router-1             # print rendered configs
python generate.py generate router-1           # generate to output/
python generate.py generate --upload router-1  # generate + upload to KV
python generate.py generate --upload --all     # all routers
```

On the router:

```bash
sh /root/update.sh                             # pull configs from KV
reboot                                         # apply
```

### Certificates

Wildcard certificate is managed centrally by `certs/deploy.py`:

1. Obtains `*.example.com` from Google ACME via Cloudflare DNS challenge using [lego](https://github.com/go-acme/lego)
2. Uses a local DoH proxy ([dnsproxy](https://github.com/AdguardTeam/dnsproxy)) to bypass DNS caching during propagation checks
3. Stores certificate locally in `.certstore/`
4. Distributes cert and key to `/etc/ssl/certs/` and `/etc/ssl/private/` on target servers via rsync
5. Triggers Traefik config reload via `touch` on dynamic config (no restart needed)

```bash
cd certs/
python deploy.py status                # check certificate expiry
python deploy.py issue                 # obtain/renew certificate
python deploy.py issue --force         # force re-issue regardless of expiry
python deploy.py distribute            # push to all target servers
python deploy.py distribute server1    # push to specific server
python deploy.py renew                 # issue if <30 days + distribute
```

Traefik reads certificates from `/etc/ssl/` via file provider with `watch: true` — updating the cert files and touching the dynamic config is enough, no container restart required.

The same wildcard certificate is used by other native services — they read directly from `/etc/ssl/` on the host.

Auto-renewal via cron:

```
0 3 * * * cd /path/to/infra/certs && python deploy.py renew >> /var/log/cert-renew.log 2>&1
```

## License

Fork-Parity-1.0.0
