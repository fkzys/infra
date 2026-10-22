import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.wlb import (
    DEFAULT_WLB_IMAGE,
    normalize_wlb,
    prepare_wlb,
    resolve_wlb,
    validate_wlb,
)

INSTANCE = 'proxy-eu'
INSTANCES_KEY = 'instances'
COOKIE_KEYS = ('cookies_yandex', 'cookies_vk')


def _valid_wlb():
    return {
        'VK_TOKEN': 'vk1.a.TOKEN',
        'VK_GROUP_ID': '123456789',
        'cookies_yandex': '[{"name": "sessionid", "value": "abc"}]',
        'cookies_vk': '[{"name": "remixsid", "value": "def"}]',
    }


def _shared_wlb(**overrides):
    wlb = {
        'vk_token': 'vk1.a.TOKEN',
        'vk_group_id': '123456789',
        'cookies_yandex': '[{"name": "sessionid", "value": "abc"}]',
        'cookies_vk': '[{"name": "remixsid", "value": "def"}]',
    }
    wlb.update(overrides)
    return wlb


def _secrets(instance_wlb=True, shared=None):
    secrets = {INSTANCES_KEY: {INSTANCE: {'wlb': instance_wlb}}}
    if shared is not None:
        secrets['wlb'] = shared
    return secrets


class TestResolveWlb:
    def test_absent_wlb_is_disabled(self):
        secrets = {INSTANCES_KEY: {INSTANCE: {}}}
        assert resolve_wlb(secrets, INSTANCE, INSTANCES_KEY) is None

    def test_false_wlb_is_disabled(self):
        assert resolve_wlb(_secrets(False), INSTANCE, INSTANCES_KEY) is None

    def test_true_uses_shared_block(self):
        assert resolve_wlb(_secrets(True, _shared_wlb()), INSTANCE, INSTANCES_KEY) == _shared_wlb()

    def test_true_without_shared_block_raises(self):
        with pytest.raises(ValueError, match='no wlb: config block'):
            resolve_wlb(_secrets(True), INSTANCE, INSTANCES_KEY)

    def test_dict_overrides_shared_block(self):
        resolved = resolve_wlb(
            _secrets({'resources': 'custom'}, _shared_wlb()),
            INSTANCE,
            INSTANCES_KEY,
        )
        assert resolved['resources'] == 'custom'
        assert resolved['vk_token'] == 'vk1.a.TOKEN'

    def test_dict_without_shared_block(self):
        own = _shared_wlb()
        assert resolve_wlb(_secrets(own), INSTANCE, INSTANCES_KEY) == own

    def test_empty_dict_uses_shared_block(self):
        assert resolve_wlb(_secrets({}, _shared_wlb()), INSTANCE, INSTANCES_KEY) == _shared_wlb()

    @pytest.mark.parametrize('value', ['enabled', 1, []])
    def test_invalid_type_raises(self, value):
        with pytest.raises(ValueError, match='expected true/false or a dict'):
            resolve_wlb(_secrets(value, _shared_wlb()), INSTANCE, INSTANCES_KEY)


class TestNormalizeWlb:
    def test_env_keys_and_direct_are_normalized(self):
        raw = {
            'vk_token': 'token',
            'vk_group_id': 'group',
            'vk_user_ids': 'users',
            'resources': 'default',
            'direct': True,
            'image': 'image',
            'cookies_yandex': '[]',
            'cookies_vk': '[]',
        }
        assert normalize_wlb(raw) == {
            'VK_TOKEN': 'token',
            'VK_GROUP_ID': 'group',
            'VK_USER_IDS': 'users',
            'RESOURCES': 'default',
            'direct': True,
            'image': 'image',
            'cookies_yandex': '[]',
            'cookies_vk': '[]',
        }

    def test_uppercase_keys_stay_uppercase(self):
        assert normalize_wlb({'VK_TOKEN': 'token'}) == {'VK_TOKEN': 'token'}

    @pytest.mark.parametrize('value', [None, 'enabled', []])
    def test_non_dict_returns_none(self, value):
        assert normalize_wlb(value) is None


class TestValidateWlb:
    def test_valid_config_passes(self):
        validate_wlb(_valid_wlb(), INSTANCE)

    @pytest.mark.parametrize('key', ['VK_TOKEN', 'VK_GROUP_ID'])
    def test_missing_env_key_raises(self, key):
        wlb = _valid_wlb()
        del wlb[key]
        with pytest.raises(ValueError, match=rf"missing '{key}'"):
            validate_wlb(wlb, INSTANCE)

    @pytest.mark.parametrize('key', COOKIE_KEYS)
    def test_missing_cookie_file_raises(self, key):
        wlb = _valid_wlb()
        del wlb[key]
        with pytest.raises(ValueError, match=rf"missing '{key}'"):
            validate_wlb(wlb, INSTANCE)

    @pytest.mark.parametrize('key', COOKIE_KEYS)
    def test_invalid_cookie_json_raises(self, key):
        wlb = _valid_wlb()
        wlb[key] = '{not json}'
        with pytest.raises(ValueError, match=rf"invalid {key} JSON"):
            validate_wlb(wlb, INSTANCE)

    @pytest.mark.parametrize('key', COOKIE_KEYS)
    @pytest.mark.parametrize('value', ['{"name": "sessionid"}', '[]', 'null'])
    def test_cookie_must_be_non_empty_array(self, key, value):
        wlb = _valid_wlb()
        wlb[key] = value
        with pytest.raises(ValueError, match=rf"invalid {key}"):
            validate_wlb(wlb, INSTANCE)

    @pytest.mark.parametrize('key', COOKIE_KEYS)
    @pytest.mark.parametrize(
        'entry',
        [
            '[{"name": "sessionid"}]',
            '[{"value": "abc"}]',
            '[{"name": "", "value": "abc"}]',
            '["sessionid"]',
        ],
    )
    def test_cookie_entry_must_have_name_and_value(self, key, entry):
        wlb = _valid_wlb()
        wlb[key] = entry
        with pytest.raises(ValueError, match=rf"invalid {key}"):
            validate_wlb(wlb, INSTANCE)

    @pytest.mark.parametrize('value', ['yes', 1, []])
    def test_direct_must_be_boolean(self, value):
        wlb = _valid_wlb()
        wlb['direct'] = value
        with pytest.raises(ValueError, match='invalid wlb.direct'):
            validate_wlb(wlb, INSTANCE)


class TestPrepareWlb:
    def test_disabled_returns_none(self):
        assert prepare_wlb(_secrets(False), INSTANCE, INSTANCES_KEY) is None
        assert prepare_wlb(_secrets(None), INSTANCE, INSTANCES_KEY) is None

    def test_default_image_is_added(self):
        result = prepare_wlb(_secrets(True, _shared_wlb()), INSTANCE, INSTANCES_KEY)
        assert result['image'] == DEFAULT_WLB_IMAGE

    def test_custom_image_is_kept(self):
        result = prepare_wlb(
            _secrets(True, _shared_wlb(image='ghcr.io/me/bot:1')),
            INSTANCE,
            INSTANCES_KEY,
        )
        assert result['image'] == 'ghcr.io/me/bot:1'

    def test_both_cookie_files_pass_through(self):
        result = prepare_wlb(_secrets(True, _shared_wlb()), INSTANCE, INSTANCES_KEY)
        assert result['cookies_yandex'] == '[{"name": "sessionid", "value": "abc"}]'
        assert result['cookies_vk'] == '[{"name": "remixsid", "value": "def"}]'

    def test_normalizes_before_validation(self):
        result = prepare_wlb(_secrets(True, _shared_wlb()), INSTANCE, INSTANCES_KEY)
        assert result['VK_TOKEN'] == 'vk1.a.TOKEN'
        assert result['VK_GROUP_ID'] == '123456789'
        assert 'vk_token' not in result

    def test_dict_only_is_normalized_and_validated(self):
        result = prepare_wlb(
            _secrets(_shared_wlb(direct=True)),
            INSTANCE,
            INSTANCES_KEY,
        )
        assert result['direct'] is True
        assert result['VK_TOKEN'] == 'vk1.a.TOKEN'

    def test_missing_cookies_vk_raises(self):
        shared = _shared_wlb()
        del shared['cookies_vk']
        with pytest.raises(ValueError, match="missing 'cookies_vk'"):
            prepare_wlb(_secrets(True, shared), INSTANCE, INSTANCES_KEY)
