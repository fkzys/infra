#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.deploy import ServiceDeployer

BASE = Path(__file__).parent
REMOTE_BASE = '/opt/podman/opencloud'
RADICALE_BASE = '/opt/podman/radicale'

deployer = ServiceDeployer({
    'templates_dir': BASE / 'templates',
    'secrets_file': BASE / 'secrets' / 'secrets.enc.yaml',
    'files': [
        ('opencloud.pod.j2', '/etc/containers/systemd/opencloud.pod'),
        ('opencloud.container.j2', '/etc/containers/systemd/opencloud.container'),
        ('radicale.container.j2', '/etc/containers/systemd/radicale.container'),
        ('radicale.config.j2', f'{RADICALE_BASE}/config/config', {'owner': '1000:1000', 'mode': '640'}),
        ('opencloud.proxy.yaml.j2', f'{REMOTE_BASE}/config/proxy.yaml', {'owner': '1000:1000', 'mode': '640'}),
    ],
    'setup_dirs': [
        (f'{REMOTE_BASE}', {'owner': '1000:1000'}),
        (f'{REMOTE_BASE}/config', {'owner': '1000:1000'}),
        (f'{REMOTE_BASE}/data', {'owner': '1000:1000'}),
        (f'{RADICALE_BASE}', {'owner': '1000:1000'}),
        (f'{RADICALE_BASE}/config', {'owner': '1000:1000'}),
        (f'{RADICALE_BASE}/data', {'owner': '1000:1000'}),
    ],
    'restart_cmd': 'systemctl daemon-reload && systemctl restart opencloud radicale',
})

if __name__ == '__main__':
    deployer.run_cli()
