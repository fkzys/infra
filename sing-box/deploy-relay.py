#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.deploy import ServiceDeployer
from lib.wlb import DEFAULT_WLB_IMAGE, prepare_wlb, resolve_wlb

BASE = Path(__file__).parent

INSTANCES_KEY = 'relay_instances'


def build_context(secrets, instance_name):
    relay = secrets[INSTANCES_KEY][instance_name]

    basename = secrets['common']['basename']
    image = relay.get('image') or secrets['common']['image']
    volume_path = relay.get('volume_path') or secrets['common']['volume_path']

    inbound_users = secrets.get('users', [])

    return {
        **secrets,
        'basename': basename,
        'volume_path': volume_path,
        'reality': relay['reality'],
        'wlb': prepare_wlb(secrets, instance_name, INSTANCES_KEY),
        'current_instance': {
            **relay,
            'image': image,
        },
        'inbound_users': inbound_users,
        'instances': secrets['instances'],
        'instance_name': instance_name,
    }


def make_files(secrets, instance_name):
    relay = secrets[INSTANCES_KEY][instance_name]
    basename = secrets['common']['basename']
    volume_path = relay.get('volume_path') or secrets['common']['volume_path']
    settings_dir = f'{volume_path}/settings'
    files = [
        ('relay_main.json.j2',     f'{settings_dir}/main.json'),
        ('server_inbounds.json.j2', f'{settings_dir}/inbounds.json'),
        ('server_ruleset.json.j2',  f'{settings_dir}/ruleset.json'),
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
    relay = secrets[INSTANCES_KEY][instance_name]
    volume_path = relay.get('volume_path') or secrets['common']['volume_path']
    settings_dir = f'{volume_path}/settings'
    dirs = [f'{settings_dir}', f'{volume_path}/cache']
    if resolve_wlb(secrets, instance_name, INSTANCES_KEY):
        dirs += [f'{volume_path}/cookies', f'{volume_path}/wlb-sessions']
    return dirs


def restart_cmd(secrets, instance_name):
    relay = secrets[INSTANCES_KEY][instance_name]
    image = relay.get('image') or secrets['common']['image']
    basename = secrets['common']['basename']

    pulls = [f'podman pull {image}']
    units = f'{basename} {basename}-pod'
    restart_units = basename
    wlb = resolve_wlb(secrets, instance_name, INSTANCES_KEY)
    if wlb:
        pulls.append(f"podman pull {wlb.get('image') or DEFAULT_WLB_IMAGE}")
        units += f' {basename}-wlb'
        restart_units = f'{basename} {basename}-wlb'
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
    'instances_key': INSTANCES_KEY,
    'context_builder': build_context,
    'files': make_files,
    'setup_dirs': make_setup_dirs,
    'restart_cmd': restart_cmd,
})

if __name__ == '__main__':
    deployer.run_cli()