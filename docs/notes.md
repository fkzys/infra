# infra

## Single-instance vs multi-instance

Services deployed to **one server** (synapse, nextcloud, element, element-call, mirotalk, backup) have `host: server1` in their secrets.

Services deployed to **multiple servers** (traefik, metrics, wireguard, sing-box, system, firewall, i2p) have `instances:` with a `host:` reference per instance and support `--all`.

**Router** uses a different model — multiple routers defined under `routers:` in secrets, configs delivered via KV instead of SSH.

## Containerized vs native

Most services run as **Podman containers** managed via Quadlet units.

**i2p**, **wireguard**, **system**, and **firewall** run as **native systemd services** — they need host networking, kernel-level interfaces (WireGuard), or direct system integration. Only config files are deployed, no Quadlet units.

**Router** configs are native OpenWrt UCI/nftables files — no containers involved.

## Traefik middleware notes

Two IP allowlist middlewares in `dynamic1.yml`:

**`blacklist`** — for services behind Cloudflare. Uses `ipStrategy.excludedIPs` to strip CF proxy IPs and check real client IP.

**`blacklist-direct`** — for services accessed directly (no CF). Same allowlist, no `ipStrategy`.

Controlled by `behind_cf` flag in service secrets.

## Pod vs shared network

Some services use a Quadlet **Pod** (shared network namespace, containers talk via `localhost`): synapse + postgresql, nextcloud + mariadb + valkey + nginx, element-call (livekit + lk-jwt).

## Sing-box

**Architecture:** Users connect to relay instances, relay proxies traffic to proxy nodes, proxy nodes route through WARP.

**whitelist-bypass bot:** `wlb` is an option for ANY instance — proxy nodes (`instances`, deploy.py) and relay nodes (`relay_instances`, deploy-relay.py) alike.
Adding `wlb: true` deploys the bot container in that instance's pod.
It polls VK for allowed-user requests and creates Yandex Telemost conferences via an HTTP API.
The bot's own HTTP calls to VK API/Telemost go out directly from its own IP; with upstream SOCKS enabled (default) the joiner's tunneled traffic is routed through the instance's sing-box SOCKS (`127.0.0.1:1080` in the pod), where the instance's route rules/filters apply.
It needs fresh Yandex cookies — paste the JSON into `wlb.cookies_yandex` verbatim; do not re-format it with shell tools like `xargs` (they strip the JSON quotes and the creator fails with "Cannot parse cookies"). Cookie file is written `999:999, 600` and mounted read-only; the bot session volume is mounted with `:U`.

`wlb` per instance can also be a **dict** — a merge on top of the shared `wlb:` block (instance keys win), e.g. to give one instance its own cookies or bot image:

```yaml
instances:
  instance1:
    wlb:
      cookies_yandex: '[...]'    # own session for this instance, everything else shared
```

`wlb.direct: true` (optional) disables `UPSTREAM_SOCKS` on the bot — the creator then opens the joiner's connections straight from its own IP, without going through the local sing-box tunnel.
Default (`false`/absent) keeps `UPSTREAM_SOCKS=127.0.0.1:1080`.

`wlb: true` without a top-level `wlb:` block is an error; a dict form works standalone. `wlb: false` (or absent) leaves the instance untouched.

Config validation at render time: the resolved wlb config must contain `vk_token`, `vk_group_id` and a `cookies_yandex` that is a non-empty JSON array of `{"name", "value"}` objects. `direct`, when present, must be a boolean. Missing `image` falls back to `ghcr.io/kulikov0/whitelist-bypass-bot:latest`.

Direct outbound rules: Client configs bypass the proxy for BitTorrent traffic (rejected) and route `qbittorrent`/`i2pd` processes and the `i2pd` user directly — these services need uncapped bandwidth or unfiltered connectivity.

Removing relay: If `relay_instances` is removed from secrets, clients connect directly to proxy nodes and proxy inbounds accept `users` credentials — no code changes needed.

## License

Fork-Parity-1.0.1
