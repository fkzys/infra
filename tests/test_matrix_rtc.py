"""MatrixRTC / LiveKit Application Service template tests.

Pure rendering and deploy-context validation. No secrets or remote access.
"""

import importlib.util
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.jinja import create_jinja_env

REPO = Path(__file__).resolve().parent.parent
SERVER_NAME = "matrix.example.com"
RTC_DOMAIN = "rtc.example.com"
AS_TOKEN = "as-token-for-tests"
HS_TOKEN = "hs-token-for-tests"

ELEMENT_CALL_CONTEXT = {
    "host": "server1",
    "synapse": {"server_name": SERVER_NAME},
    "livekit": {
        "rtc_domain": RTC_DOMAIN,
        "key": "test-key",
        "secret": "test-secret",
        "as_token": AS_TOKEN,
        "hs_token": HS_TOKEN,
    },
}

SYNAPSE_CONTEXT = {
    "host": "server1",
    "synapse": {
        "server_name": SERVER_NAME,
        "matrix_rtc_domain": RTC_DOMAIN,
        "postgres_password": "test-password",
        "registration_shared_secret": "test-registration-secret",
        "signing_key": "test-signing-key",
    },
    "livekit": {"as_token": AS_TOKEN, "hs_token": HS_TOKEN},
}


def _load_deploy(service):
    path = REPO / service / "deploy.py"
    spec = importlib.util.spec_from_file_location(f"{service}_deploy", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _render(service, template, context):
    env = create_jinja_env(REPO / service / "templates")
    return env.get_template(template).render(**context)


def _registration(service, context):
    return yaml.safe_load(
        _render(service, "lk-jwt-registration.yaml.j2", context)
    )


class TestRegistrationTemplates:
    @pytest.mark.parametrize(
        ("service", "context", "proxy_domain"),
        [
            ("element-call", ELEMENT_CALL_CONTEXT, RTC_DOMAIN),
            ("synapse", SYNAPSE_CONTEXT, RTC_DOMAIN),
        ],
    )
    def test_registration_fields(self, service, context, proxy_domain):
        reg = _registration(service, context)

        assert reg["id"] == "lk-jwt-service"
        assert reg["as_token"] == AS_TOKEN
        assert reg["hs_token"] == HS_TOKEN
        assert reg["sender_localpart"] == "_lk_jwt_service"
        assert reg["url"] is None
        assert reg["namespaces"]["users"] == [
            {"exclusive": False, "regex": ".*"}
        ]
        assert reg["io.element.msc4502.scopes"] == [
            "urn:matrix:client:io.element.msc4502:rooms:is_joined"
        ]
        assert reg["io.element.msc4512.proxy_prefix"] == "rtc/livekit"
        assert (
            reg["io.element.msc4512.proxy_url"]
            == f"https://{proxy_domain}/livekit/jwt"
        )

    def test_element_call_uses_livekit_domain(self):
        reg = _registration("element-call", ELEMENT_CALL_CONTEXT)
        assert RTC_DOMAIN in reg["io.element.msc4512.proxy_url"]

    def test_synapse_uses_matrix_rtc_domain(self):
        reg = _registration("synapse", SYNAPSE_CONTEXT)
        assert RTC_DOMAIN in reg["io.element.msc4512.proxy_url"]


class TestLkJwtContainer:
    def test_bind_has_colon(self):
        out = _render(
            "element-call", "lk-jwt.container.j2", ELEMENT_CALL_CONTEXT
        )
        assert "Environment=LIVEKIT_JWT_BIND=:8080" in out
        assert "Environment=LIVEKIT_JWT_BIND=8080\n" not in out

    def test_as_registration_and_hs_server_name(self):
        out = _render(
            "element-call", "lk-jwt.container.j2", ELEMENT_CALL_CONTEXT
        )
        assert (
            "Environment=LIVEKIT_AS_REGISTRATION_FILE="
            "/etc/lk-jwt-registration.yaml" in out
        )
        assert f"Environment=LIVEKIT_HS_SERVER_NAME={SERVER_NAME}" in out
        assert (
            "Volume=/opt/podman/element-call/config/"
            "lk-jwt-registration.yaml:/etc/lk-jwt-registration.yaml:ro,Z"
        ) in out

    def test_livekit_credentials_and_shared_pod_are_kept(self):
        out = _render(
            "element-call", "lk-jwt.container.j2", ELEMENT_CALL_CONTEXT
        )
        assert "Environment=LIVEKIT_KEY=test-key" in out
        assert "Environment=LIVEKIT_SECRET=test-secret" in out
        assert f"Environment=LIVEKIT_FULL_ACCESS_HOMESERVERS={SERVER_NAME}" in out
        assert "Pod=element-call.pod" in out


class TestLivekitConfig:
    def test_webhook_points_at_lk_jwt_on_localhost(self):
        out = _render("element-call", "livekit.yaml.j2", ELEMENT_CALL_CONTEXT)
        cfg = yaml.safe_load(out)

        assert cfg["webhook"]["api_key"] == "test-key"
        assert cfg["webhook"]["urls"] == [
            "http://localhost:8080/sfu_webhook"
        ]

    def test_key_and_room_settings_are_kept(self):
        out = _render("element-call", "livekit.yaml.j2", ELEMENT_CALL_CONTEXT)
        cfg = yaml.safe_load(out)

        assert cfg["keys"] == {"test-key": "test-secret"}
        assert cfg["room"]["auto_create"] is False
        assert cfg["rtc"]["tcp_port"] == 7881
        assert cfg["rtc"]["port_range_start"] == 50100
        assert cfg["rtc"]["port_range_end"] == 50200


class TestHomeserver:
    def test_app_service_registration_is_loaded(self):
        cfg = yaml.safe_load(
            _render("synapse", "homeserver.yaml.j2", SYNAPSE_CONTEXT)
        )
        assert cfg["app_service_config_files"] == [
            "/data/lk-jwt-registration.yaml"
        ]

    def test_rtc_foci_fallback_is_restored(self):
        cfg = yaml.safe_load(
            _render("synapse", "homeserver.yaml.j2", SYNAPSE_CONTEXT)
        )
        assert cfg["extra_well_known_client_content"] == {
            "org.matrix.msc4143.rtc_foci": [
                {
                    "type": "livekit",
                    "livekit_service_url": (
                        f"https://{RTC_DOMAIN}/livekit/jwt"
                    ),
                }
            ]
        }

    def test_matrix_rtc_and_experimental_flags_are_kept(self):
        cfg = yaml.safe_load(
            _render("synapse", "homeserver.yaml.j2", SYNAPSE_CONTEXT)
        )
        assert cfg["matrix_rtc"]["transports"] == [
            {
                "type": "livekit",
                "url": f"wss://{RTC_DOMAIN}/livekit/sfu",
                "livekit_service_url": f"https://{RTC_DOMAIN}/livekit/jwt",
            }
        ]
        assert cfg["experimental_features"] == {
            "msc4222_enabled": True,
            "msc4143_enabled": True,
            "msc4502_enabled": True,
            "msc4512_enabled": True,
        }

    def test_experimental_features_is_not_duplicated(self):
        out = _render("synapse", "homeserver.yaml.j2", SYNAPSE_CONTEXT)
        assert out.count("experimental_features:") == 1


class TestDeployContext:
    @pytest.mark.parametrize(
        ("service", "expected_opts"),
        [
            ("element-call", {"mode": "600"}),
            ("synapse", {"owner": "991:991", "mode": "600"}),
        ],
    )
    def test_registration_file_permissions(self, service, expected_opts):
        mod = _load_deploy(service)
        files = mod.deployer.files
        matches = [
            entry
            for entry in files
            if entry[0] == "lk-jwt-registration.yaml.j2"
        ]

        assert len(matches) == 1
        assert matches[0][2] == expected_opts

    @pytest.mark.parametrize("service", ["element-call", "synapse"])
    def test_valid_context_is_returned_unchanged(self, service):
        mod = _load_deploy(service)
        secrets = (
            ELEMENT_CALL_CONTEXT
            if service == "element-call"
            else SYNAPSE_CONTEXT
        )
        assert mod.build_context(secrets) is secrets

    @pytest.mark.parametrize(
        ("service", "secrets", "missing_key"),
        [
            ("element-call", ELEMENT_CALL_CONTEXT, "as_token"),
            ("element-call", ELEMENT_CALL_CONTEXT, "hs_token"),
            ("synapse", SYNAPSE_CONTEXT, "as_token"),
            ("synapse", SYNAPSE_CONTEXT, "hs_token"),
        ],
    )
    def test_missing_as_token_exits(self, service, secrets, missing_key):
        mod = _load_deploy(service)
        broken = {
            **secrets,
            "livekit": {
                key: value
                for key, value in secrets["livekit"].items()
                if key != missing_key
            },
        }

        with pytest.raises(SystemExit, match=rf"livekit\.{missing_key}"):
            mod.build_context(broken)
