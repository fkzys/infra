"""Tests for sing-box/deploy-relay.py — pure logic + template rendering, no externals."""

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

REPO = Path(__file__).resolve().parent.parent


def _load_deploy_relay():
    path = REPO / "sing-box" / "deploy-relay.py"
    spec = importlib.util.spec_from_file_location("sing_box_deploy_relay", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _secrets(with_wlb=False, vk_user_ids=True):
    relay_instances = {
        "relay-eu": {
            "host": "server3",
            "password": "relaypw",
            "reality": {"server_name": "relay-sni.com"},
            "wlb": bool(with_wlb),
        },
    }
    secrets = {
        "common": {
            "basename": "singbox",
            "volume_path": "/opt/podman/singbox",
            "image": "ghcr.io/sagernet/sing-box:latest",
        },
        "instances": {
            "proxy1": {"host": "server1", "reality": {"server_name": "proxy-sni.com"}},
        },
        "relay_instances": relay_instances,
        "users": [{"name": "alice", "password": "pw1"}],
    }
    if with_wlb:
        wlb = {
            "image": "ghcr.io/kulikov0/whitelist-bypass-bot:latest",
            "vk_token": "vk1.a.TOKEN",
            "vk_group_id": "123456789",
            "resources": "default",
            "cookies_yandex": '[{"name": "sessionid", "value": "abc"}]',
        }
        if vk_user_ids:
            wlb["vk_user_ids"] = "12345,67890"
        secrets["wlb"] = wlb
    return secrets


def _render(secrets, instance_name, template):
    from lib.jinja import create_jinja_env
    mod = _load_deploy_relay()
    env = create_jinja_env(REPO / "sing-box" / "templates")
    return env.get_template(template).render(**mod.build_context(secrets, instance_name))


# ═══════════════════════════════════════════════════
# build_context
# ═══════════════════════════════════════════════════


class TestBuildContext:
    def test_flag_false_disables(self):
        mod = _load_deploy_relay()
        ctx = mod.build_context(_secrets(with_wlb=False), "relay-eu")
        assert ctx["wlb"] is None

    def test_flag_true_loads_top_level_config(self):
        mod = _load_deploy_relay()
        ctx = mod.build_context(_secrets(with_wlb=True), "relay-eu")
        assert ctx["wlb"]["VK_TOKEN"] == "vk1.a.TOKEN"
        assert ctx["wlb"]["VK_GROUP_ID"] == "123456789"
        assert ctx["wlb"]["VK_USER_IDS"] == "12345,67890"
        assert ctx["wlb"]["RESOURCES"] == "default"
        assert ctx["wlb"]["image"] == "ghcr.io/kulikov0/whitelist-bypass-bot:latest"
        assert ctx["wlb"]["cookies_yandex"] == '[{"name": "sessionid", "value": "abc"}]'

    def test_env_keys_normalized_to_canonical_case(self):
        mod = _load_deploy_relay()
        secrets = copy.deepcopy(_secrets(with_wlb=True))
        secrets["wlb"]["VK_TOKEN"] = secrets["wlb"].pop("vk_token")
        ctx = mod.build_context(secrets, "relay-eu")
        assert ctx["wlb"]["VK_TOKEN"] == "vk1.a.TOKEN"

    def test_flag_true_without_config_raises(self):
        mod = _load_deploy_relay()
        secrets = _secrets(with_wlb=True)
        del secrets["wlb"]
        with pytest.raises(ValueError, match="wlb enabled"):
            mod.build_context(secrets, "relay-eu")

    def test_volume_path_used_as_is(self):
        mod = _load_deploy_relay()
        ctx = mod.build_context(_secrets(), "relay-eu")
        assert ctx["volume_path"] == "/opt/podman/singbox"


# ═══════════════════════════════════════════════════
# make_files / make_setup_dirs
# ═══════════════════════════════════════════════════


class TestMakeFiles:
    def test_flag_false_only_base_files(self):
        mod = _load_deploy_relay()
        files = mod.make_files(_secrets(with_wlb=False), "relay-eu")
        assert [f[0] for f in files] == [
            "relay_main.json.j2",
            "server_inbounds.json.j2",
            "server_ruleset.json.j2",
            "server_container.j2",
            "server_pod.j2",
        ]

    def test_flag_true_adds_unit_and_cookies(self):
        mod = _load_deploy_relay()
        files = mod.make_files(_secrets(with_wlb=True), "relay-eu")
        templates = [f[0] for f in files]
        assert "wlb_bot.container.j2" in templates
        assert "/etc/containers/systemd/singbox-wlb.container" in [f[1] for f in files]

    def test_cookies_file_permissions(self):
        mod = _load_deploy_relay()
        files = mod.make_files(_secrets(with_wlb=True), "relay-eu")
        cookies = [f for f in files if f[0] == "wlb_cookies_yandex.json.j2"]
        assert len(cookies) == 1
        assert cookies[0][1] == "/opt/podman/singbox/cookies/cookies-yandex.json"
        assert cookies[0][2] == {"owner": "999:999", "mode": "600"}


class TestMakeSetupDirs:
    def test_flag_false(self):
        mod = _load_deploy_relay()
        assert mod.make_setup_dirs(_secrets(with_wlb=False), "relay-eu") == [
            "/opt/podman/singbox/settings",
            "/opt/podman/singbox/cache",
        ]

    def test_flag_true_adds_cookies_and_sessions(self):
        mod = _load_deploy_relay()
        assert mod.make_setup_dirs(_secrets(with_wlb=True), "relay-eu") == [
            "/opt/podman/singbox/settings",
            "/opt/podman/singbox/cache",
            "/opt/podman/singbox/cookies",
            "/opt/podman/singbox/wlb-sessions",
        ]


# ═══════════════════════════════════════════════════
# restart_cmd
# ═══════════════════════════════════════════════════


class TestRestartCmd:
    def test_flag_false_unchanged(self):
        mod = _load_deploy_relay()
        assert mod.restart_cmd(_secrets(with_wlb=False), "relay-eu") == (
            "podman pull ghcr.io/sagernet/sing-box:latest"
            " && systemctl daemon-reload"
            " && systemctl reset-failed singbox singbox-pod 2>/dev/null;"
            " systemctl restart singbox"
        )

    def test_flag_true_pulls_bot_and_restarts_both_units(self):
        mod = _load_deploy_relay()
        cmd = mod.restart_cmd(_secrets(with_wlb=True), "relay-eu")
        assert "podman pull ghcr.io/kulikov0/whitelist-bypass-bot:latest" in cmd
        assert "singbox singbox-pod singbox-wlb" in cmd
        assert cmd.endswith("systemctl restart singbox singbox-wlb")

    def test_flag_true_custom_bot_image(self):
        mod = _load_deploy_relay()
        secrets = _secrets(with_wlb=True)
        secrets["wlb"]["image"] = "ghcr.io/me/bot:1.2.3"
        assert "podman pull ghcr.io/me/bot:1.2.3" in mod.restart_cmd(secrets, "relay-eu")


# ═══════════════════════════════════════════════════
# template rendering (real templates, fake secrets)
# ═══════════════════════════════════════════════════


class TestInboundsRender:
    def test_flag_false_single_anytls_inbound(self):
        rendered = _render(_secrets(with_wlb=False), "relay-eu", "server_inbounds.json.j2")
        data = json.loads(rendered)
        assert [i["tag"] for i in data["inbounds"]] == ["anytls_in"]

    def test_flag_true_adds_socks_inbound(self):
        rendered = _render(_secrets(with_wlb=True), "relay-eu", "server_inbounds.json.j2")
        data = json.loads(rendered)
        socks = [i for i in data["inbounds"] if i.get("tag") == "wlb_socks_in"]
        assert len(socks) == 1
        assert socks[0]["type"] == "socks"
        assert socks[0]["listen"] == "127.0.0.1"
        assert socks[0]["listen_port"] == 1080
        assert "udp" not in socks[0]


class TestWlbUnitRender:
    def test_flag_true_sets_env_from_top_level_config(self):
        rendered = _render(_secrets(with_wlb=True), "relay-eu", "wlb_bot.container.j2")
        assert "Requires=singbox.pod" in rendered
        assert "Pod=singbox.pod" in rendered
        assert "Environment=VK_TOKEN=vk1.a.TOKEN" in rendered
        assert "Environment=VK_GROUP_ID=123456789" in rendered
        assert "Environment=TM_COOKIES=/data/cookies-yandex.json" in rendered
        assert "Environment=RESOURCES=default" in rendered
        assert "Environment=UPSTREAM_SOCKS=127.0.0.1:1080" in rendered
        assert "Environment=VK_USER_IDS=12345,67890" in rendered
        assert "/opt/podman/singbox/cookies/cookies-yandex.json:/data/cookies-yandex.json:ro" in rendered
        assert "/opt/podman/singbox/wlb-sessions:/data/sessions:U" in rendered
        assert "AutoUpdate=registry" in rendered
        assert "[Service]\nRestart=always" in rendered

    def test_image_default_when_absent(self):
        secrets = _secrets(with_wlb=True)
        del secrets["wlb"]["image"]
        rendered = _render(secrets, "relay-eu", "wlb_bot.container.j2")
        assert "Image=ghcr.io/kulikov0/whitelist-bypass-bot:latest" in rendered
        assert "podman pull ghcr.io/kulikov0/whitelist-bypass-bot:latest" in _load_deploy_relay().restart_cmd(secrets, "relay-eu")

    def test_unit_waits_for_singbox_container(self):
        rendered = _render(_secrets(with_wlb=True), "relay-eu", "wlb_bot.container.j2")
        assert "After=singbox.container" in rendered

    def test_vk_user_ids_omitted_when_absent(self):
        rendered = _render(_secrets(with_wlb=True, vk_user_ids=False), "relay-eu", "wlb_bot.container.j2")
        assert "VK_USER_IDS=" not in rendered

    def test_resources_default_when_absent(self):
        secrets = _secrets(with_wlb=True)
        del secrets["wlb"]["resources"]
        rendered = _render(secrets, "relay-eu", "wlb_bot.container.j2")
        assert "Environment=RESOURCES=default" in rendered


class TestCookiesRender:
    def test_outputs_cookie_json_verbatim(self):
        rendered = _render(_secrets(with_wlb=True), "relay-eu", "wlb_cookies_yandex.json.j2")
        assert rendered.strip() == '[{"name": "sessionid", "value": "abc"}]'