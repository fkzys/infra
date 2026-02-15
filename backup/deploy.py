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
        ('backup.sh.j2', '/root/scripts/backup.sh', {'owner': 'root:root', 'mode': '700'}),
        ('backup.service.j2', '/etc/systemd/system/backup.service'),
        ('backup.timer.j2', '/etc/systemd/system/backup.timer'),
    ],
    'setup_dirs': ['/root/scripts'],
    'restart_cmd': 'systemctl daemon-reload && systemctl enable --now backup.timer',
})

if __name__ == '__main__':
    deployer.run_cli()
