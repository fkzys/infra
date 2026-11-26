#!/usr/bin/env python3
"""Router config generator."""

import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.sops import decrypt_sops
from lib.jinja import create_jinja_env
from lib.cloudflare import create_uploader as create_cloudflare_uploader
from lib.gcore import create_uploader as create_gcore_uploader

BASE = Path(__file__).parent
TEMPLATES_DIR = BASE / 'templates'
SECRETS_FILE = BASE / 'secrets' / 'secrets.enc.yaml'
OUTPUT_DIR = BASE / '.output'

BACKENDS = {
    'gcore': create_gcore_uploader,
    'cloudflare': create_cloudflare_uploader,
}
DEFAULT_BACKEND = 'gcore'
BACKEND_LABELS = {'gcore': 'Gcore', 'cloudflare': 'Cloudflare'}

# (template, output_filename, kv_key)
KV_FILES = [
    ('nftables.j2',       'nftables.nft',  'nftables.nft'),
    ('network.j2',        'network',       'network'),
    ('wireless.j2',       'wireless',      'wireless'),
    ('firewall.j2',       'firewall',      'firewall'),
    ('dhcp.j2',           'dhcp',          'dhcp'),
    ('system.j2',         'system',        'system'),
    ('rc_local.j2',       'rc_local',      'rc_local'),
    ('sing_box_init.j2',  'sing_box_init', 'sing_box_init'),
]

# Generated locally only
LOCAL_FILES = [
    ('update_sh.j2', 'update.sh'),
]


def get_uploader(secrets, backend):
    uploader = BACKENDS[backend](secrets)
    if not uploader:
        print(f"⚠ {BACKEND_LABELS[backend]} not configured",
              file=sys.stderr)
    return uploader


def build_context(secrets, router_name, backend):
    if backend == 'gcore':
        url = (secrets.get('gcore') or {}).get('app_url', '').rstrip('/')
        secret_key = 'gcore.app_url'
    else:
        worker = (secrets.get('cloudflare') or {}).get(
            'worker_domain', '').rstrip('/')
        url = f"https://{worker}" if worker else ''
        secret_key = 'cloudflare.worker_domain'

    if not url:
        print(f"ERROR: router secrets need {secret_key} "
              f"for the {backend} backend", file=sys.stderr)
        sys.exit(1)

    return {
        'shared': secrets['shared'],
        'router': secrets['routers'][router_name],
        'config_url': url,
        'router_name': router_name,
    }


def cmd_list(secrets):
    for name in secrets.get('routers', {}):
        print(f"  {name}")


def cmd_render(secrets, env, router_name, backend):
    ctx = build_context(secrets, router_name, backend)
    for tpl_name, out_name, _ in KV_FILES:
        print(f"\033[1;33m═══ {out_name} ═══\033[0m")
        print(env.get_template(tpl_name).render(**ctx))
        print()
    for tpl_name, out_name in LOCAL_FILES:
        print(f"\033[1;33m═══ {out_name} ═══\033[0m")
        print(env.get_template(tpl_name).render(**ctx))
        print()


def cmd_generate(secrets, env, router_name, backend, upload=False):
    ctx = build_context(secrets, router_name, backend)
    router_dir = OUTPUT_DIR / router_name
    router_dir.mkdir(parents=True, exist_ok=True)

    uploader = None
    token = secrets['routers'][router_name].get('token', '')
    if upload:
        uploader = get_uploader(secrets, backend)

    for tpl_name, out_name, kv_key in KV_FILES:
        rendered = env.get_template(tpl_name).render(**ctx)
        (router_dir / out_name).write_text(rendered)
        print(f"✓ {out_name}")

        if uploader and token:
            url = uploader.upload(f"{token}/{kv_key}", rendered)
            print(f"  ↳ {url}")

    for tpl_name, out_name in LOCAL_FILES:
        rendered = env.get_template(tpl_name).render(**ctx)
        (router_dir / out_name).write_text(rendered)
        print(f"✓ {out_name} (local only)")

    print(f"\n✓ Output: {router_dir}")


def main():
    parser = argparse.ArgumentParser(description='Router config generator')
    parser.add_argument('command', choices=['list', 'render', 'generate'],
                        nargs='?', default='generate')
    parser.add_argument('router', nargs='*')
    parser.add_argument('--upload', action='store_true')
    parser.add_argument('--all', action='store_true')
    parser.add_argument('--backend', choices=sorted(BACKENDS),
                        default=DEFAULT_BACKEND,
                        help=f'Config storage backend (default: {DEFAULT_BACKEND})')
    args = parser.parse_args()

    secrets = decrypt_sops(SECRETS_FILE)

    if args.command == 'list':
        cmd_list(secrets)
        return

    env = create_jinja_env(TEMPLATES_DIR)
    routers = secrets.get('routers', {})

    if args.all:
        names = list(routers.keys())
    elif args.router:
        unknown = [r for r in args.router if r not in routers]
        if unknown:
            print(f"Unknown: {', '.join(unknown)}. "
                  f"Available: {', '.join(routers.keys())}", file=sys.stderr)
            sys.exit(1)
        names = args.router
    else:
        parser.error("Specify router name(s) or --all")

    for name in names:
        print(f"\033[1;36m── {name} ──\033[0m")
        if args.command == 'render':
            cmd_render(secrets, env, name, args.backend)
        else:
            cmd_generate(secrets, env, name, args.backend, upload=args.upload)
        print()


if __name__ == '__main__':
    main()
