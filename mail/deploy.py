#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.deploy import ServiceDeployer
from lib.remote import ssh_run

BASE = Path(__file__).parent


def after_hook(secrets, target, port):
    sel = secrets['common']['dkim_selector']
    ssh_run(target, (
        'postmap /etc/postfix/vmailbox '
        '&& newaliases'
    ), port)


deployer = ServiceDeployer({
    'templates_dir': BASE / 'templates',
    'secrets_file': BASE / 'secrets' / 'secrets.enc.yaml',
    'multi_instance': True,
    'files': [
        ('main.cf.j2', '/etc/postfix/main.cf'),
        ('master.cf.j2', '/etc/postfix/master.cf'),
        ('vmailbox.j2', '/etc/postfix/vmailbox'),
        ('keytable.j2', '/etc/postfix/dkim/keytable'),
        ('signingtable.j2', '/etc/postfix/dkim/signingtable'),
        ('dkim_key.j2',
         lambda s: f'/etc/postfix/dkim/{s["common"]["dkim_selector"]}.private',
         {'owner': 'opendkim:opendkim', 'mode': '600'}),
        ('opendkim.conf.j2', '/etc/opendkim/opendkim.conf'),
        ('dovecot.conf.j2', '/etc/dovecot/dovecot.conf'),
        ('virtual_users.j2', '/etc/dovecot/virtual-users', '600'),
    ],
    'setup_dirs': [
        '/etc/postfix/dkim',
        '/etc/opendkim',
        '/etc/dovecot',
    ],
    'secrets_hooks': [after_hook],
    'restart_cmd': 'systemctl restart postfix dovecot opendkim',
})

if __name__ == '__main__':
    deployer.run_cli()
