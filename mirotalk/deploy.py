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
        ('mirotalk.env.j2',       '/opt/podman/mirotalk/mirotalk.env'),
        ('mirotalk.network.j2',    '/etc/containers/systemd/mirotalk.network'),
        ('mirotalk.container.j2',  '/etc/containers/systemd/mirotalk.container'),
    ],
    'setup_dirs': [
        '/opt/podman/mirotalk',
    ],
    'restart_cmd': (
        'systemctl daemon-reload && '
        'systemctl restart mirotalk'
    ),
})

if __name__ == '__main__':
    deployer.run_cli()
