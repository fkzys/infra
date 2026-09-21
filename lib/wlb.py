"""
Shared whitelist-bypass (wlb) bot contract for sing-box instance deployers.
The resolved block is normalized (env-var keys uppercased) and validated before
anything is rendered.
"""

import json

DEFAULT_WLB_IMAGE = 'ghcr.io/kulikov0/whitelist-bypass-bot:latest'

# Keys in the wlb secrets block mapping 1:1 to bot env vars — normalized to canonical VK_TOKEN/VK_GROUP_ID/etc.
_WLB_ENV_KEYS = {'vk_token', 'vk_group_id', 'vk_user_ids', 'resources'}


def resolve_wlb(secrets, instance_name, instances_key):
    """Raw resolved wlb dict (un-normalized, no default image) or None when disabled."""
    wlb = secrets[instances_key][instance_name].get('wlb')
    if wlb is None or wlb is False:
        return None
    shared = secrets.get('wlb')
    if wlb is True:
        if not isinstance(shared, dict):
            raise ValueError(
                f"instance '{instance_name}' has wlb: true enabled, but no wlb: config block "
                f"at the top level of the secrets file"
            )
        return dict(shared)
    if isinstance(wlb, dict):
        return {**(shared or {}), **wlb}
    raise ValueError(
        f"instance '{instance_name}' has wlb: {wlb!r} — expected true/false or a dict of overrides"
    )


def normalize_wlb(wlb):
    """Canonical-case env-var keys (vk_token → VK_TOKEN); `direct` stays lowercase."""
    if not isinstance(wlb, dict):
        return None
    normalized = {}
    for k, v in wlb.items():
        if k.lower() in _WLB_ENV_KEYS:
            normalized[k.upper()] = v
        elif k.lower() == 'direct':
            normalized['direct'] = v
        else:
            normalized[k] = v
    return normalized


def validate_wlb(wlb, instance_name):
    for key in ('VK_TOKEN', 'VK_GROUP_ID'):
        if not wlb.get(key):
            raise ValueError(
                f"instance '{instance_name}' has wlb enabled, but the resolved config "
                f"is missing '{key}'"
            )
    raw_cookies = wlb.get('cookies_yandex')
    if not raw_cookies:
        raise ValueError(
            f"instance '{instance_name}' has wlb enabled, but the resolved config "
            f"is missing 'cookies_yandex'"
        )
    try:
        cookies = json.loads(raw_cookies)
    except (TypeError, ValueError) as e:
        raise ValueError(
            f"instance '{instance_name}' has invalid cookies_yandex JSON: {e}"
        ) from e
    if not isinstance(cookies, list) or not cookies:
        raise ValueError(
            f"instance '{instance_name}' has invalid cookies_yandex — expected a "
            f"non-empty JSON array, got {type(cookies).__name__}"
        )
    for c in cookies:
        if not isinstance(c, dict) or not c.get('name') or c.get('value') is None:
            raise ValueError(
                f"instance '{instance_name}' has invalid cookies_yandex — every entry "
                f"must be an object with 'name' and 'value'"
            )
    direct = wlb.get('direct')
    if direct is not None and not isinstance(direct, bool):
        raise ValueError(
            f"instance '{instance_name}' has invalid wlb.direct: {direct!r} — expected true/false"
        )


def prepare_wlb(secrets, instance_name, instances_key):
    """Resolved + default-image + normalized + validated wlb dict, or None when disabled."""
    wlb = resolve_wlb(secrets, instance_name, instances_key)
    if wlb is None:
        return None
    wlb.setdefault('image', DEFAULT_WLB_IMAGE)
    wlb = normalize_wlb(wlb)
    validate_wlb(wlb, instance_name)
    return wlb
