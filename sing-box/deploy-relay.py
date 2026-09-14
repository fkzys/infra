#!/usr/bin/env python3
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.deploy import ServiceDeployer

BASE = Path(__file__).parent

DEFAULT_WLB_IMAGE = 'ghcr.io/kulikov0/whitelist-bypass-bot:latest'

# Keys in the wlb secrets block mapping 1:1 to bot env vars — normalized to canonical
# VK_TOKEN/VK_GROUP_ID/etc. so the template never depends on case in secrets.
_WLB_ENV_KEYS = {'vk_token', 'vk_group_id', 'vk_user_ids', 'resources'}


def _resolve_wlb(secrets, instance_name):
    wlb = secrets['relay_instances'][instance_name].get('wlb')
    if wlb is None or wlb is False:
        return None
    shared = secrets.get('wlb')
    if wlb is True:
        if not isinstance(shared, dict):
            raise ValueError(
                f"relay instance '{instance_name}' has wlb: true enabled, but no wlb: config block "
                f"at the top level of the secrets file"
            )
        return dict(shared)
    if isinstance(wlb, dict):
        return {**(shared or {}), **wlb}
    raise ValueError(
        f"relay instance '{instance_name}' has wlb: {wlb!r} — expected true/false or a dict of overrides"
    )


def _normalize_wlb(wlb):
    if not isinstance(wlb, dict):
        return None
    return {k.upper() if k.lower() in _WLB_ENV_KEYS else k: v for k, v in wlb.items()}


def _validate_wlb(wlb, instance_name):
    for key in ('VK_TOKEN', 'VK_GROUP_ID'):
        if not wlb.get(key):
            raise ValueError(
                f"relay instance '{instance_name}' has wlb enabled, but the resolved config "
                f"is missing '{key}'"
            )
    raw_cookies = wlb.get('cookies_yandex')
    if not raw_cookies:
        raise ValueError(
            f"relay instance '{instance_name}' has wlb enabled, but the resolved config "
            f"is missing 'cookies_yandex'"
        )
    try:
        cookies = json.loads(raw_cookies)
    except (TypeError, ValueError) as e:
        raise ValueError(
            f"relay instance '{instance_name}' has invalid cookies_yandex JSON: {e}"
        ) from e
    if not isinstance(cookies, list) or not cookies:
        raise ValueError(
            f"relay instance '{instance_name}' has invalid cookies_yandex — expected a "
            f"non-empty JSON array, got {type(cookies).__name__}"
        )
    for c in cookies:
        if not isinstance(c, dict) or not c.get('name') or c.get('value') is None:
            raise ValueError(
                f"relay instance '{instance_name}' has invalid cookies_yandex — every entry "
                f"must be an object with 'name' and 'value'"
            )


def build_context(secrets, instance_name):
    relay = secrets['relay_instances'][instance_name]

    basename = secrets['common']['basename']
    image = relay.get('image') or secrets['common']['image']
    volume_path = relay.get('volume_path') or secrets['common']['volume_path']

    inbound_users = secrets.get('users', [])

    wlb = _resolve_wlb(secrets, instance_name)
    if wlb is not None:
        wlb.setdefault('image', DEFAULT_WLB_IMAGE)
        wlb = _normalize_wlb(wlb)
        _validate_wlb(wlb, instance_name)

    return {
        **secrets,
        'basename': basename,
        'volume_path': volume_path,
        'reality': relay['reality'],
        'wlb': wlb,
        'current_instance': {
            **relay,
            'image': image,
        },
        'inbound_users': inbound_users,
        'instances': secrets['instances'],
        'instance_name': instance_name,
    }


def make_files(secrets, instance_name):
    relay = secrets['relay_instances'][instance_name]
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
    if _resolve_wlb(secrets, instance_name):
        files += [
            ('wlb_bot.container.j2', f'/etc/containers/systemd/{basename}-wlb.container'),
            ('wlb_cookies_yandex.json.j2', f'{volume_path}/cookies/cookies-yandex.json',
             {'owner': '999:999', 'mode': '600'}),
        ]
    return files


def make_setup_dirs(secrets, instance_name):
    relay = secrets['relay_instances'][instance_name]
    volume_path = relay.get('volume_path') or secrets['common']['volume_path']
    settings_dir = f'{volume_path}/settings'
    dirs = [f'{settings_dir}', f'{volume_path}/cache']
    if _resolve_wlb(secrets, instance_name):
        dirs += [f'{volume_path}/cookies', f'{volume_path}/wlb-sessions']
    return dirs


def restart_cmd(secrets, instance_name):
    relay = secrets['relay_instances'][instance_name]
    image = relay.get('image') or secrets['common']['image']
    basename = secrets['common']['basename']

    pulls = [f'podman pull {image}']
    units = f'{basename} {basename}-pod'
    restart_units = basename
    wlb = _resolve_wlb(secrets, instance_name)
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
    'instances_key': 'relay_instances',
    'context_builder': build_context,
    'files': make_files,
    'setup_dirs': make_setup_dirs,
    'restart_cmd': restart_cmd,
})

if __name__ == '__main__':
    deployer.run_cli()
