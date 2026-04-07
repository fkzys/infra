#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.deploy import ServiceDeployer

BASE = Path(__file__).parent
REMOTE_BASE = '/opt/podman/sing-box'


def build_context(secrets, instance_name):
    relay = secrets['relay_instances'][instance_name]
    # Relay inbounds accept regular users (users→relay auth)
    inbound_users = secrets.get('users', [])

    return {
        **secrets,
        'reality': relay['reality'],
        'current_instance': {
            **relay,
        },
        'inbound_users': inbound_users,
        'instances': secrets['instances'],  # proxy nodes for relay outbounds
        'instance_name': instance_name,
    }


def restart_cmd(secrets, instance_name):
    image = secrets['relay_instances'][instance_name]['image']
    return (
        f'podman pull {image}'
        f' && systemctl daemon-reload'
        f' && systemctl reset-failed sing-box sing-box-pod 2>/dev/null;'
        f' systemctl restart sing-box'
    )


deployer = ServiceDeployer({
    'templates_dir': BASE / 'templates',
    'secrets_file': BASE / 'secrets' / 'secrets.enc.yaml',
    'multi_instance': True,
    'instances_key': 'relay_instances',
    'context_builder': build_context,
    'files': [
        ('relay_main.json.j2',     f'{REMOTE_BASE}/sing-box_settings/main.json'),
        ('server_inbounds.json.j2', f'{REMOTE_BASE}/sing-box_settings/inbounds.json'),
        ('server_ruleset.json.j2',  f'{REMOTE_BASE}/sing-box_settings/ruleset.json'),
        ('server_container.j2',     '/etc/containers/systemd/sing-box.container'),
        ('server_pod.j2',           '/etc/containers/systemd/sing-box.pod'),
    ],
    'setup_dirs': [f'{REMOTE_BASE}/sing-box_settings', f'{REMOTE_BASE}/sing-box_settings/cache'],
    'restart_cmd': restart_cmd,
})

if __name__ == '__main__':
    deployer.run_cli()
