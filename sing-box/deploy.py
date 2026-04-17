#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.deploy import ServiceDeployer

BASE = Path(__file__).parent


def build_context(secrets, instance_name):
    instance = secrets['instances'][instance_name]
    warp_instance = secrets.get('warp', {}).get(instance_name, {})

    basename = secrets['common']['basename']
    image = instance.get('image') or secrets['common']['image']

    if secrets.get('relay_instances'):
        inbound_users = [{'name': name, **data} for name, data in secrets['relay_instances'].items()]
    else:
        inbound_users = secrets.get('users', [])

    return {
        **secrets,
        'basename': basename,
        'reality': instance['reality'],
        'current_instance': {
            **instance,
            'image': image,
            'warp_private_key': warp_instance.get('private_key', ''),
            'warp_ipv4': warp_instance.get('ipv4', ''),
            'warp_ipv6': warp_instance.get('ipv6', ''),
        },
        'inbound_users': inbound_users,
        'instance_name': instance_name,
    }


def make_files(secrets, instance_name):
    instance = secrets['instances'][instance_name]
    basename = secrets['common']['basename']
    volume_path = instance.get('volume_path') or secrets['common']['volume_path']
    settings_dir = f'{volume_path}/settings'
    return [
        ('server_main.json.j2',     f'{settings_dir}/main.json'),
        ('server_inbounds.json.j2', f'{settings_dir}/inbounds.json'),
        ('server_ruleset.json.j2',  f'{settings_dir}/ruleset.json'),
        ('server_warp.json.j2',     f'{settings_dir}/warp.json'),
        ('server_container.j2',     f'/etc/containers/systemd/{basename}.container'),
        ('server_pod.j2',           f'/etc/containers/systemd/{basename}.pod'),
    ]


def make_setup_dirs(secrets, instance_name):
    volume_path = secrets['instances'][instance_name].get('volume_path') or secrets['common']['volume_path']
    settings_dir = f'{volume_path}/settings'
    return [f'{settings_dir}', f'{volume_path}/cache']


def restart_cmd(secrets, instance_name):
    instance = secrets['instances'][instance_name]
    image = instance.get('image') or secrets['common']['image']
    basename = secrets['common']['basename']
    volume_path = instance.get('volume_path') or secrets['common']['volume_path']
    return (
        f'podman pull {image}'
        f' && systemctl daemon-reload'
        f' && systemctl reset-failed {basename}-pod {basename} 2>/dev/null;'
        f' systemctl restart {basename}-pod'
    )


deployer = ServiceDeployer({
    'templates_dir': BASE / 'templates',
    'secrets_file': BASE / 'secrets' / 'secrets.enc.yaml',
    'multi_instance': True,
    'context_builder': build_context,
    'files': make_files,
    'setup_dirs': make_setup_dirs,
    'restart_cmd': restart_cmd,
})

if __name__ == '__main__':
    deployer.run_cli()
