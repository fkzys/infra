# infra

## Secrets structure

### hosts.enc.yaml

Central SSH config referenced by all services:

```yaml
server1:
  address: server1.example.com
  ssh_port: 2222
  ssh_user: user_A
server2:
  address: server2.example.com
  ssh_port: 2222
  ssh_user: user_A
```

### certs secrets

```yaml
domain: example.com
acme_email: you@example.com
acme_eab_kid: "..."
acme_eab_hmac: "..."
cf_api_token: "..."

targets:
  - host: server1
    post_deploy: "touch /opt/podman/traefik/settings/dynamic/dynamic_tls.yml"
  - host: server2
    post_deploy: "touch /opt/podman/traefik/settings/dynamic/dynamic_tls.yml"
```

### Single-instance secrets

```yaml
host: server1

synapse:
  server_name: matrix.example.com
  matrix_rtc_domain: rtc.example.com
  postgres_password: "..."
```

### Multi-instance secrets

```yaml
common:
  cert_domain: example.com
  cloudflare_ips:
    - ...

instances:
  server1:
    host: server1
    domain: metrics1.example.com
  server2:
    host: server2
    domain: metrics2.example.com
```

### system secrets

```yaml
common:
  ssh_port: 2222
  ssh_allowed_users:
    - user_A
    - user_B
  ssh_otp_users:
    - user_A
  journal_max_use: 200M
  network_stack: dual

instances:
  instance1:
    host: server1
    network_stack: dual
  instance2:
    host: server2
    network_stack: dual
```

### firewall secrets

```yaml
common:
  ssh_port: 2222
  wg_port: 51453
  i2pd_port: 12345
  trusted_ips:
    - 10.0.0.0/8
    - ...

instances:
  instance1:
    host: server1
    filter_zone: true
    ssh_on_public: true
    wireguard: true
    wg_endpoint: true
    web: true
    turn: true
    livekit: true
    i2pd: true
  instance2:
    host: server2
    filter_zone: true
    ssh_on_public: true
    wireguard: true
    wg_endpoint: true
    web: true
    turn: true
    livekit: true
    i2pd: true
```

### backup secrets

```yaml
host: server1

backup:
  hostname: vps1
  kopia_password: "..."
  schedule: "*-*-* 04:00:00"
  repositories:
    - name: s3-backup
      bucket: my-bucket
      prefix: vps1
      endpoint: s3.example.com
      region: us-east-1
      access_key: "..."
      secret_key: "..."
```

### mirotalk secrets

```yaml
host: server1

mirotalk:
  domain: meet.example.com
  announced_ip: "203.0.113.20"
  host_users: "..."
  api_key_secret: "..."
  jwt_secret: "..."
```

### element-call secrets

```yaml
host: server1

synapse:
  server_name: matrix.example.com

livekit:
  rtc_domain: rtc.example.com
  key: "..."
  secret: "..."
```

### wireguard secrets

```yaml
common:
  listen_port: 51453

instances:
  server1:
    host: server1
    address: "...::1/128"
    private_key: "..."
    peers:
      - name: Vps2
        public_key: "..."
        allowed_ips: ["...::2/128", "...::5/128", "...::6/128"]
        endpoint: "1.2.3.4:51453"
        keepalive: 20
      - name: Phone
        public_key: "..."
        allowed_ips: ["...::3/128"]
      - name: Pc
        public_key: "..."
        allowed_ips: ["...::4/128"]
  server2:
    host: server2
    address: "...::2/128"
    private_key: "..."
    peers:
      - name: Vps1
        public_key: "..."
        allowed_ips: ["...::1/128", "...::3/128", "...::4/128"]
        endpoint: "4.5.6.7:51453"
        keepalive: 20
      - name: Phone
        public_key: "..."
        allowed_ips: ["...::6/128"]
      - name: Pc
        public_key: "..."
        allowed_ips: ["...::5/128"]
```

### router secrets

```yaml
cloudflare:
  account_id: "..."
  api_token: "..."
  kv_namespace_id: "..."
  worker_domain: "..."

shared:
  timezone: "UTC-2"
  zonename: "Afrika/Juba"
  wifi:
    country: "PA"
    main:
      ssid: "main"
      key: "..."
      mobility_domain: "4f11"
    guest:
      ssid: "guest"
      key: "..."
  sing_box:
    binary: "/root/sing-box"
    config_dir: "/etc/sing-box"
    files:
      - main.json
      - sing-box_prx.json

routers:
  router-1:
    hostname: "OpenWrt"
    token: "..."
    sing_box_token: "..."
    network:
      wan_mac: "..."
      lan_ipaddr: "192.168.x.1"
      ...
    nftables:
      local_v6: [...]
    dhcp:
      router_ipv4: "..."
      router_ula: "..."
      static_hosts: [...]
    radios: [...]
    leds: [...]
```

### sing-box secrets

sing-box uses two instance groups in one secrets file — proxy nodes and relay nodes:

```yaml
common:
  basename: my-container          # container/pod name, systemd unit name
  volume_path: /opt/podman/my-container
  image: ghcr.io/sagernet/sing-box:latest

instances:                        # proxy nodes (deployed via deploy.py)
  instance1:
    host: server1
    reality:
      server_name: "proxy-sni.com"
    wlb: true                     # whitelist-bypass bot on this proxy (optional, see below)
  instance2:
    host: server2
    reality:
      server_name: "proxy-sni.com"
    image: ghcr.io/sagernet/sing-box:latest-beta    # per-instance override

relay_instances:                  # relay nodes (deployed via deploy-relay.py)
  relay-eu:
    host: server3
    address: "..."
    reality:
      server_name: "relay-sni.com"
    image: ghcr.io/sagernet/sing-box:latest-testing    # per-instance override
    password: "..."               # relay→proxy authentication
    short_id: "..."
    wlb: true                     # whitelist-bypass bot on this relay (optional, see below)

wlb:                              # shared whitelist-bypass config (top level)
  image: ghcr.io/kulikov0/whitelist-bypass-bot:latest
  vk_token: "..."
  vk_group_id: "..."
  vk_user_ids: "12345,67890"      # optional — space-separated VK IDs allowed to use the bot
  resources: default              # optional, defaults to "default"
  cookies_yandex: |
    [
      {"name": "Session_id", "value": "..."},
      {"name": "ys", "value": "..."}
    ]

users:                            # same credentials for both relay and proxy inbounds
  - name: alice
    uuid: "..."
    password: "..."
    short_id: "..."
    token: "..."
```

## What gets deployed where

Quadlet units go to `/etc/containers/systemd/` on remote.

Service configs go to `/opt/podman/<service>/` and are mounted into containers via Quadlet `Volume=`.

Secrets (signing keys, API tokens) are written via SSH with `chmod 600`.

Certificates go to `/etc/ssl/certs/` and `/etc/ssl/private/` — mounted read-only into containers that need them, read directly by native services.

Native service configs:
- system → `/etc/ssh/sshd_config`, `/etc/sysctl.d/`, `/etc/systemd/network/`, `/etc/systemd/journald.conf`, systemd timers
- firewall → `/etc/firewalld/zones/`
- backup → `/root/scripts/backup.sh`, systemd service + timer
- wireguard → `/etc/wireguard/wg0.conf`
- i2p → `/etc/i2pd/i2pd.conf`

Router configs (via KV):
- nftables → `/etc/nftables/nft-ipv6`
- network, wireless, firewall, dhcp, system → `/etc/config/`
- sing-box init → `/etc/init.d/sing-box_my`
- ip rules → `/etc/rc.local`

## Remote server layout

```text
/etc/ssh/
└── sshd_config

/etc/sysctl.d/
├── 10-default.conf
└── 11-overcommit_memory.conf

/etc/systemd/
├── network/10-default.network
├── journald.conf
└── system/
    ├── 10-paccache_user.timer
    ├── 10-paccache_user.service
    ├── 10-btrfs_scrub.timer
    ├── 10-btrfs_scrub.service
    ├── 10-sysctl_user.timer
    ├── 10-sysctl_user.service
    ├── backup.service
    ├── backup.timer
    ├── nextcloud-cron_podman.service
    └── nextcloud-cron_podman.timer

/etc/firewalld/zones/
├── public.xml
├── filter-closed.xml
├── wireguard.xml
└── trusted.xml

/etc/ssl/
├── certs/example.com.crt
└── private/example.com.key

/etc/wireguard/
└── wg0.conf

/etc/i2pd/
└── i2pd.conf

/root/scripts/
└── backup.sh

/opt/podman/
├── traefik/
│   ├── settings/traefik.yml
│   ├── settings/dynamic/dynamic1.yml
│   ├── settings/dynamic/dynamic_tls.yml
│   └── logs/
├── synapse/
│   ├── data/homeserver.yaml
│   ├── data/*.signing.key
│   ├── data/*.log.config
│   ├── data/media_store/
│   └── db/
├── nextcloud/
│   ├── nextcloud/config/config.php
│   ├── nginx.conf
│   ├── db/
│   └── log/
├── element_synapse_admin/
│   ├── element_config.json
│   └── synapse_config.json
├── element-call/
│   └── config/livekit.yaml
├── metrics/
│   └── prometheus/prometheus.yml
├── mirotalk/
│   └── mirotalk.env
└── sing-box/
    └── sing-box_settings/
        ├── main.json
        ├── inbounds.json
        ├── ruleset.json
        └── warp.json
```

## Router layout

```text
/etc/config/
├── network
├── wireless
├── firewall
├── dhcp
└── system

/etc/nftables/
└── nft-ipv6

/etc/init.d/
└── sing-box_my

/etc/rc.local

/etc/sing-box/
├── main.json
└── sing-box_prx.json

/root/
├── sing-box
└── update.sh
```

## License

Fork-Parity-1.0.0
