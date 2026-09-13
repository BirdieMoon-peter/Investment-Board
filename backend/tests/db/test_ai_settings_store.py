import json
import stat
from dataclasses import replace

import pytest

from app.core.settings import Settings


def fields(**changes):
    result = dict(provider='openai_compatible', api_url='https://test.example/v1', model='model-a',
                  temperature=0.3, max_output_tokens=1000, http_timeout_seconds=25,
                  key_action='replace', api_key='test-secret')
    result.update(changes)
    return result


@pytest.fixture
def store(monkeypatch, tmp_path):
    from app.core.ai_settings_store import AISettingsStore
    path = tmp_path / 'settings.json'
    monkeypatch.setenv('INVESTMENT_BOARD_AI_SETTINGS_FILE', str(path))
    return AISettingsStore(), path


def request(**changes):
    from app.schemas.ai_settings import AISettingsUpdate
    return AISettingsUpdate.model_validate(fields(**changes))


def test_atomic_private_persistence_and_snapshot(store):
    from app.core.ai_settings_store import AISettingsStore, load_effective_ai_settings
    value, path = store
    fallback = Settings(database_url='sqlite:///unchanged.db', ai_cache_limit=8, ai_api_key='env-secret')
    value.save(request(), fallback)
    first = load_effective_ai_settings(fallback)
    assert first.ai_model == 'model-a'
    assert first.database_url == fallback.database_url
    assert first.ai_cache_limit == 8
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    value.save(request(model='model-b', key_action='keep', api_key=None), fallback)
    second = AISettingsStore().effective(fallback)
    assert second.ai_model == 'model-b'
    assert second.ai_api_key == 'test-secret'
    assert first.ai_model == 'model-a'
    assert json.loads(path.read_text())['api_key'] == 'test-secret'
    value.reset()
    assert value.effective(fallback) == fallback


def test_key_replace_clear_and_alias_endpoint_equivalence(store):
    value, _ = store
    fallback = Settings()
    value.save(request(), fallback)
    value.save(request(provider='openai', api_url='https://test.example/v1/chat/completions/', key_action='keep', api_key=None), fallback)
    assert value.effective(fallback).ai_api_key == 'test-secret'
    value.save(request(api_key='new-secret'), fallback)
    assert value.effective(fallback).ai_api_key == 'new-secret'
    value.save(request(key_action='clear', api_key=None), fallback)
    assert value.effective(fallback).ai_api_key is None


@pytest.mark.parametrize('change', [{'provider': 'anthropic'}, {'api_url': 'https://other.example'}, {'api_url': 'https://test.example/other'}])
def test_keep_key_rejects_changed_destination(store, change):
    from app.core.ai_settings_store import AISettingsStoreError
    value, path = store
    fallback = Settings()
    value.save(request(), fallback)
    before = path.read_bytes()
    with pytest.raises(AISettingsStoreError, match='replace or clear'):
        value.save(request(key_action='keep', api_key=None, **change), fallback)
    assert path.read_bytes() == before
    value.save(request(key_action='clear', api_key=None, **change), fallback)
    assert value.effective(fallback).ai_api_key is None


def test_kept_environment_credential_obeys_destination_boundary(store):
    from app.core.ai_settings_store import AISettingsStoreError
    value, _ = store
    fallback = Settings(ai_provider='openai', ai_api_url='https://test.example', ai_api_key='env-key')
    value.save(request(key_action='keep', api_key=None), fallback)
    assert value.effective(fallback).ai_api_key == 'env-key'
    value.reset()
    with pytest.raises(AISettingsStoreError):
        value.save(request(api_url='https://other.example', key_action='keep', api_key=None), fallback)


def test_write_failure_preserves_prior_file_and_cleans_temporary_file(store, monkeypatch):
    from app.core import ai_settings_store
    value, path = store
    value.save(request(), Settings())
    before = path.read_bytes()
    def fail(*args):
        raise OSError('private-test-key-do-not-echo')
    monkeypatch.setattr(ai_settings_store.os, 'replace', fail)
    with pytest.raises(ai_settings_store.AISettingsStoreError) as exc:
        value.save(request(model='new-model'), Settings())
    assert 'private-test-key' not in str(exc.value)
    assert path.read_bytes() == before
    assert list(path.parent.iterdir()) == [path]


@pytest.mark.parametrize('raw', ['{secret', 'null', '[]', '{}', '{"provider":"openai","api_key":"private-key"}'])
def test_corrupt_store_blocks_effective_settings_but_allows_recovery(store, raw):
    from app.core.ai_settings_store import AISettingsStoreError
    value, path = store
    path.write_text(raw)
    with pytest.raises(AISettingsStoreError):
        value.effective(Settings())
    with pytest.raises(AISettingsStoreError):
        value.save(request(key_action='keep', api_key=None), Settings())
    value.save(request(), Settings())
    assert value.effective(Settings()).ai_model == 'model-a'
    path.write_text(raw)
    value.reset()
    assert not path.exists()


def test_default_user_file_is_not_read_in_pytest(monkeypatch, tmp_path):
    from app.core import ai_settings_store
    path = tmp_path / 'real-settings.json'
    path.write_text('{user-private-data')
    monkeypatch.delenv('INVESTMENT_BOARD_AI_SETTINGS_FILE', raising=False)
    monkeypatch.setattr(ai_settings_store, 'DEFAULT_AI_SETTINGS_PATH', path)
    fallback = Settings(ai_api_key='fallback-test-key')
    assert ai_settings_store.load_effective_ai_settings(fallback) == fallback
    assert path.read_text() == '{user-private-data'
