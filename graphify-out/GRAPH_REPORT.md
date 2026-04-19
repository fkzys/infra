# Graph Report - .  (2026-04-18)

## Corpus Check
- Corpus is ~9,992 words - fits in a single context window. You may not need a graph.

## Summary
- 198 nodes · 428 edges · 8 communities detected
- Extraction: 64% EXTRACTED · 36% INFERRED · 0% AMBIGUOUS · INFERRED: 156 edges (avg confidence: 0.75)
- Token cost: 3,200 input · 1,900 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Infrastructure Services|Infrastructure Services]]
- [[_COMMUNITY_Config Generation|Config Generation]]
- [[_COMMUNITY_Deployment & Remote Execution|Deployment & Remote Execution]]
- [[_COMMUNITY_Template Rendering|Template Rendering]]
- [[_COMMUNITY_Cloudflare KV Operations|Cloudflare KV Operations]]
- [[_COMMUNITY_Deployment Configuration|Deployment Configuration]]
- [[_COMMUNITY_Certificate Management|Certificate Management]]
- [[_COMMUNITY_Library Init|Library Init]]

## God Nodes (most connected - your core abstractions)
1. `CFKVUploader` - 33 edges
2. `ServiceDeployer Library` - 30 edges
3. `create_jinja_env()` - 26 edges
4. `ServiceDeployer` - 19 edges
5. `TestServiceDeployer` - 19 edges
6. `cmd_generate()` - 14 edges
7. `decrypt_sops()` - 13 edges
8. `create_uploader()` - 10 edges
9. `TestJinja` - 10 edges
10. `rsync_file()` - 8 edges

## Surprising Connections (you probably didn't know these)
- `Render template and validate JSON.` --uses--> `CFKVUploader`  [INFERRED]
  sing-box/generate.py → lib/cloudflare.py
- `Return users filtered by names and/or type.      Args:         secrets: decrypte` --uses--> `CFKVUploader`  [INFERRED]
  sing-box/generate.py → lib/cloudflare.py
- `Load previously saved urls.json, return empty structure if missing.` --uses--> `CFKVUploader`  [INFERRED]
  sing-box/generate.py → lib/cloudflare.py
- `Merge new URLs into existing urls.json and regenerate urls.md.` --uses--> `CFKVUploader`  [INFERRED]
  sing-box/generate.py → lib/cloudflare.py
- `Generate configs for client-type users.      Args:         users: pre-filtered l` --uses--> `CFKVUploader`  [INFERRED]
  sing-box/generate.py → lib/cloudflare.py

## Hyperedges (group relationships)
- **Pod-based Services** — synapse_service, elementcall_service, nextcloud_service [INFERRED]
- **Native System Services** — coturn_service, wireguard_service, system_service, firewall_service [INFERRED]
- **Deployment Models** — router_service, singbox_service [INFERRED]

## Communities

### Community 0 - "Infrastructure Services"
Cohesion: 0.05
Nodes (20): Backup Service - Kopia Snapshots, Certificates Service - TLS Certificates, Coturn Service - TURN STUN Relay, restart_cmd(), Element Service - Element Web, Element Call Service - LiveKit SFU, Firewall Service - Firewalld Zones, Jitsi Service - Video Conferencing (+12 more)

### Community 1 - "Config Generation"
Cohesion: 0.09
Nodes (31): build_context(), cmd_generate(), cmd_kv_purge(), cmd_kv_revoke(), cmd_list(), cmd_render(), cmd_revoke(), filter_users() (+23 more)

### Community 2 - "Deployment & Remote Execution"
Cohesion: 0.1
Nodes (29): write_signing_key(), rsync_file(), ssh_read_file(), ssh_run(), write_secret_remote(), Tests for lib/ — pure logic + mocked externals., test_deploy_applies_opts(), test_deploy_callable_files() (+21 more)

### Community 3 - "Template Rendering"
Cohesion: 0.17
Nodes (3): create_jinja_env(), TestJinja, TestServiceDeployer

### Community 4 - "Cloudflare KV Operations"
Cohesion: 0.14
Nodes (16): CFKVUploader, create_uploader(), cmd_kv_list(), cmd_list_kv(), cmd_purge_kv(), Handle 'kv-list' subcommand., test_create_uploader_missing_fields(), test_delete() (+8 more)

### Community 5 - "Deployment Configuration"
Cohesion: 0.2
Nodes (7): _apply_opts(), _fmt_opts(), load_hosts(), resolve_target(), ServiceDeployer, test_fmt_opts(), TestDeployHelpers

### Community 6 - "Certificate Management"
Cohesion: 0.23
Nodes (14): cert_paths(), distribute(), issue(), main(), Push certificate and key to target servers at /etc/ssl/., Print certificate status., Start a local DNS proxy with DoH upstream for lego., Return local lego output paths for a wildcard domain. (+6 more)

### Community 7 - "Library Init"
Cohesion: 1.0
Nodes (0): 

## Knowledge Gaps
- **16 isolated node(s):** `Start a local DNS proxy with DoH upstream for lego.`, `Return local lego output paths for a wildcard domain.`, `Read expiry date from a PEM certificate via openssl.`, `Obtain or renew the wildcard certificate using lego.`, `Push certificate and key to target servers at /etc/ssl/.` (+11 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Library Init`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ServiceDeployer Library` connect `Infrastructure Services` to `Deployment & Remote Execution`, `Certificate Management`?**
  _High betweenness centrality (0.333) - this node is a cross-community bridge._
- **Why does `decrypt_sops()` connect `Config Generation` to `Cloudflare KV Operations`, `Deployment Configuration`, `Certificate Management`?**
  _High betweenness centrality (0.175) - this node is a cross-community bridge._
- **Why does `main()` connect `Certificate Management` to `Config Generation`, `Deployment Configuration`?**
  _High betweenness centrality (0.155) - this node is a cross-community bridge._
- **Are the 25 inferred relationships involving `CFKVUploader` (e.g. with `Render template and validate JSON.` and `Return users filtered by names and/or type.      Args:         secrets: decrypte`) actually correct?**
  _`CFKVUploader` has 25 INFERRED edges - model-reasoned connections that need verification._
- **Are the 25 inferred relationships involving `create_jinja_env()` (e.g. with `get_jinja_env()` and `._get_env()`) actually correct?**
  _`create_jinja_env()` has 25 INFERRED edges - model-reasoned connections that need verification._
- **Are the 8 inferred relationships involving `ServiceDeployer` (e.g. with `TestJinja` and `TestSops`) actually correct?**
  _`ServiceDeployer` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `TestServiceDeployer` (e.g. with `CFKVUploader` and `ServiceDeployer`) actually correct?**
  _`TestServiceDeployer` has 2 INFERRED edges - model-reasoned connections that need verification._