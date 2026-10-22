#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.deploy import ServiceDeployer

BASE = Path(__file__).parent
REMOTE_BASE = '/opt/podman/element-call'


def build_context(secrets, instance_name=None):
    livekit = secrets.get('livekit', {})
    missing = [
        key
        for key in ('rtc_domain', 'key', 'secret', 'as_token', 'hs_token')
        if not livekit.get(key)
    ]
    if missing:
        sys.exit(
            'element-call secrets are missing '
            + ', '.join(f'livekit.{key}' for key in missing)
        )
    return secrets


deployer = ServiceDeployer({
    'templates_dir': BASE / 'templates',
    'secrets_file': BASE / 'secrets' / 'secrets.enc.yaml',
    'files': [
        ('livekit.yaml.j2',                 f'{REMOTE_BASE}/config/livekit.yaml'),
        ('lk-jwt-registration.yaml.j2',     f'{REMOTE_BASE}/config/lk-jwt-registration.yaml', {'mode': '600'}),
        ('element-call.pod.j2',             '/etc/containers/systemd/element-call.pod'),
        ('livekit.container.j2',            '/etc/containers/systemd/livekit.container'),
        ('lk-jwt.container.j2',             '/etc/containers/systemd/lk-jwt.container'),
    ],
    'context_builder': build_context,
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
