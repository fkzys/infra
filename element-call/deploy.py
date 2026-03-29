#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.deploy import ServiceDeployer

BASE = Path(__file__).parent
REMOTE_BASE = '/opt/podman/element-call'

deployer = ServiceDeployer({
    'templates_dir': BASE / 'templates',
    'secrets_file': BASE / 'secrets' / 'secrets.enc.yaml',
    'files': [
        ('livekit.yaml.j2',          f'{REMOTE_BASE}/config/livekit.yaml'),
        ('element-call.pod.j2',      '/etc/containers/systemd/element-call.pod'),
        ('livekit.container.j2',     '/etc/containers/systemd/livekit.container'),
        ('lk-jwt.container.j2',     '/etc/containers/systemd/lk-jwt.container'),
    ],
    'setup_dirs': [
        f'{REMOTE_BASE}/config',
    ],
    'restart_cmd': (
        'systemctl daemon-reload && '
        'systemctl restart element-call-pod'
    ),
})

if __name__ == '__main__':
    deployer.run_cli()
