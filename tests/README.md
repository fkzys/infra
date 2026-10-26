# Tests

Tests cover shared library code in `lib/` only. Service deploy modules, templates and systemd units are verified manually on production.

## Overview

| File | What it tests |
|------|---------------|
| `test_lib.py` | Jinja2 environment, SOPS decryption, SSH/rsync, Cloudflare KV client, `ServiceDeployer` |
| `test_wlb.py` | `lib/wlb.py`: resolving, normalizing, validating and preparing the whitelist-bypass bot config |

## Running

```bash
pip install jinja2 pyyaml requests pytest
pytest tests/ -v
```

## `test_lib.py`

No network access, no SSH, no real secrets. Subprocess calls and HTTP requests are mocked.

- **Jinja**: variable interpolation, whitespace control, trailing newline, missing template, loops, nested dicts.
- **SOPS**: successful YAML parsing, nested structures, decryption failure, missing `sops` binary.
- **Remote**: SSH commands, default port, read/write helpers, rsync change detection.
- **Cloudflare**: uploader creation, upload, delete, list/pagination, delete by prefix.
- **Deploy helpers**: target resolution, owner/mode formatting.
- **ServiceDeployer**: config parsing, multi-instance context, rendering, deployment, restart behavior, callable files/setup dirs/restart command, owner/mode on files and setup dirs.

## `test_wlb.py`

Tests `lib/wlb.py` as a pure library. No deploy modules, templates or production access.

- `wlb: false` or absent → disabled.
- `wlb: true` → uses the shared `wlb:` block; missing shared block raises.
- `wlb: {dict}` → merges over the shared block; instance values win; works without a shared block.
- Env keys are normalized to uppercase; `direct` stays lowercase; cookie keys and `image` pass through.
- `VK_TOKEN` and `VK_GROUP_ID` are required.
- `cookies_yandex` and `cookies_vk` are required non-empty JSON arrays of objects with `name` and `value`.
- `direct` must be a boolean.
- Missing `image` falls back to `DEFAULT_WLB_IMAGE`.

## CI

CI runs `pytest tests/ -v` when `lib/`, `tests/*.py`, or `.github/workflows/ci.yml` change.
