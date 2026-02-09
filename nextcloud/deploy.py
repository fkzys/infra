#!/usr/bin/env python3
"""deploy.py - Nextcloud deployer"""

import subprocess
import sys
import tempfile
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.sops import decrypt_sops
from lib.remote import ssh_run, ssh_read_file, rsync_file
from lib.jinja import create_jinja_env

TEMPLATES_DIR = Path(__file__).parent / 'templates'
SECRETS_FILE = Path(__file__).parent / 'secrets' / 'secrets.enc.yaml'
REMOTE_BASE = '/opt/podman/nextcloud'

FILES = [
    ('nextcloud.pod.j2', '/etc/containers/systemd/nextcloud.pod'),
    ('1-mariadb.container.j2', '/etc/containers/systemd/1-mariadb.container'),
    ('2-valkey.container.j2', '/etc/containers/systemd/2-valkey.container'),
    ('3-nextcloud-app.container.j2', '/etc/containers/systemd/3-nextcloud-app.container'),
    ('4-nginx.container.j2', '/etc/containers/systemd/4-nginx.container'),
    ('nginx.conf.j2', f'{REMOTE_BASE}/nginx.conf'),
    ('config.php.j2', f'{REMOTE_BASE}/nextcloud/config/config.php'),
]

SETUP_DIRS = [
    f'{REMOTE_BASE}/db',
    f'{REMOTE_BASE}/nextcloud/config',
    f'{REMOTE_BASE}/log',
]


def get_target(secrets: dict) -> tuple[str, int]:
    ssh = secrets['ssh']
    return f"{ssh.get('user', 'root')}@{ssh['host']}", ssh.get('port', 22)


def cmd_render(secrets: dict, env) -> None:
    for tpl, remote_path in FILES:
        name = tpl.removesuffix('.j2')
        print(f"\033[1;33m═══ {name} → {remote_path} ═══\033[0m")
        print(env.get_template(tpl).render(**secrets))
        print()


def cmd_diff(secrets: dict, env) -> None:
    target, port = get_target(secrets)
    for tpl, remote_path in FILES:
        name = tpl.removesuffix('.j2')
        rendered = env.get_template(tpl).render(**secrets)
        remote_content = ssh_read_file(target, remote_path, port)
        if rendered == remote_content:
            print(f"\033[0;32m✓\033[0m {name}")
        else:
            print(f"\033[1;33m→\033[0m {name} differs")
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as lf, \
                 tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as rf:
                lf.write(rendered); lf.flush()
                rf.write(remote_content); rf.flush()
                subprocess.run(['diff', '--color', '-u', rf.name, lf.name])
            print()


def cmd_deploy(secrets: dict, env, no_restart: bool = False) -> None:
    target, port = get_target(secrets)
    print(f"\033[1;33m→\033[0m deploying nextcloud to {target}")

    ssh_run(target, f"mkdir -p {' '.join(SETUP_DIRS)}", port)

    changed = False
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        for tpl, remote_path in FILES:
            rendered = env.get_template(tpl).render(**secrets)
            local_file = tmpdir / tpl.removesuffix('.j2')
            local_file.write_text(rendered)
            if rsync_file(local_file, target, remote_path, port):
                print(f"  \033[1;33m→\033[0m {tpl.removesuffix('.j2')} updated")
                changed = True
            else:
                print(f"  \033[0;32m✓\033[0m {tpl.removesuffix('.j2')} unchanged")

    if not no_restart and changed:
        ssh_run(target, "systemctl daemon-reload && systemctl restart nextcloud-pod", port)
        print(f"  \033[0;32m✓\033[0m restarted")
    elif not changed:
        print(f"  \033[0;32m✓\033[0m no changes")

    print(f"\033[0;32m✓\033[0m done\n")


def main():
    parser = argparse.ArgumentParser(description='Nextcloud deployer')
    parser.add_argument('command', choices=['render', 'diff', 'deploy'])
    parser.add_argument('-s', '--secrets', default=str(SECRETS_FILE))
    parser.add_argument('--no-restart', action='store_true')
    args = parser.parse_args()

    secrets = decrypt_sops(Path(args.secrets))
    env = create_jinja_env(TEMPLATES_DIR)

    if args.command == 'render':
        cmd_render(secrets, env)
    elif args.command == 'diff':
        cmd_diff(secrets, env)
    elif args.command == 'deploy':
        cmd_deploy(secrets, env, no_restart=args.no_restart)


if __name__ == '__main__':
    main()
