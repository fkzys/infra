#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.deploy import ServiceDeployer
from lib.wlb import DEFAULT_WLB_IMAGE, prepare_wlb, resolve_wlb

BASE = Path(__file__).parent

INSTANCES_KEY = 'instances'


def build_context(secrets, instance_name):
    instance = secrets['instances'][instance_name]
    warp_instance = secrets.get('warp', {}).get(instance_name, {})

    basename = secrets['common']['basename']
    image = instance.get('image') or secrets['common']['image']
    volume_path = instance.get('volume_path') or secrets['common']['volume_path']

    if secrets.get('relay_instances'):
        inbound_users = [{'name': name, **data} for name, data in secrets['relay_instances'].items()]
    else:
        inbound_users = secrets.get('users', [])

    return {
        **secrets,
        'basename': basename,
        'volume_path': volume_path,
        'reality': instance['reality'],
        'wlb': prepare_wlb(secrets, instance_name, INSTANCES_KEY),
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
    files = [
        ('server_main.json.j2',     f'{settings_dir}/main.json'),
        ('server_inbounds.json.j2', f'{settings_dir}/inbounds.json'),
        ('server_ruleset.json.j2',  f'{settings_dir}/ruleset.json'),
        ('server_warp.json.j2',     f'{settings_dir}/warp.json'),
        ('server_container.j2',     f'/etc/containers/systemd/{basename}.container'),
        ('server_pod.j2',           f'/etc/containers/systemd/{basename}.pod'),
    ]
    if resolve_wlb(secrets, instance_name, INSTANCES_KEY):
        files += [
            ('wlb_bot.container.j2', f'/etc/containers/systemd/{basename}-wlb.container'),
            ('wlb_cookies_yandex.json.j2', f'{volume_path}/cookies/cookies-yandex.json',
             {'owner': '999:999', 'mode': '600'}),
        ]
    return files


def make_setup_dirs(secrets, instance_name):
    volume_path = secrets['instances'][instance_name].get('volume_path') or secrets['common']['volume_path']
    settings_dir = f'{volume_path}/settings'
    dirs = [f'{settings_dir}', f'{volume_path}/cache']
    if resolve_wlb(secrets, instance_name, INSTANCES_KEY):
        dirs += [f'{volume_path}/cookies', f'{volume_path}/wlb-sessions']
    return dirs


def restart_cmd(secrets, instance_name):
    instance = secrets['instances'][instance_name]
    image = instance.get('image') or secrets['common']['image']
    basename = secrets['common']['basename']

    pulls = [f'podman pull {image}']
    units = f'{basename}-pod {basename}'
    restart_units = f'{basename}-pod'
    wlb = resolve_wlb(secrets, instance_name, INSTANCES_KEY)
    if wlb:
        pulls.append(f"podman pull {wlb.get('image') or DEFAULT_WLB_IMAGE}")
        units += f' {basename}-wlb'
        restart_units += f' {basename}-wlb'
    return (
        ' && '.join(pulls)
        + f' && systemctl daemon-reload'
        + f' && systemctl reset-failed {units} 2>/dev/null;'
        + f' systemctl restart {restart_units}'
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