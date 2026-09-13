import json

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


KEY = 'private-test-key-do-not-echo'


def draft(**changes):
    return dict(provider='openai_compatible', api_url='http://127.0.0.1:9999/v1',
                model='test-model', temperature=0.2, max_output_tokens=1400,
                http_timeout_seconds=30, key_action='replace', api_key=KEY, **changes)


@pytest.fixture
def local_client(api_app, monkeypatch, tmp_path):
    monkeypatch.setenv('INVESTMENT_BOARD_AI_SETTINGS_FILE', str(tmp_path / 'ai.json'))
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///' + str(tmp_path / 'test.db'))
    with TestClient(api_app, base_url='http://localhost', client=('127.0.0.1', 50123)) as client:
        yield client


def save(client, payload):
    token = client.get('/api/ai/settings').json()['mutation_token']
    return client.put('/api/ai/settings', json=payload, headers={'X-AI-Settings-Token': token})


def test_settings_are_redacted_persistent_and_resettable(local_client):
    initial = local_client.get('/api/ai/settings')
    assert initial.status_code == 200
    assert initial.headers['cache-control'] == 'no-store'
    assert 'api_key' not in initial.json()
    response = save(local_client, draft())
    assert response.status_code == 200
    assert response.json()['source'] == 'web'
    assert response.json()['api_key_configured'] is True
    assert KEY not in response.text
    with TestClient(create_app(), base_url='http://localhost', client=('127.0.0.1', 99)) as restarted:
        view = restarted.get('/api/ai/settings').json()
        assert view['model'] == 'test-model'
        assert view['mutation_token'] != response.json()['mutation_token']
    response = local_client.delete('/api/ai/settings', headers={'X-AI-Settings-Token': initial.json()['mutation_token']})
    assert response.status_code == 200
    assert response.json()['source'] in {'environment', 'default'}


@pytest.mark.parametrize('field,value', [
    ('temperature', 'NaN'), ('temperature', -0.01), ('temperature', 2.01),
    ('max_output_tokens', 0), ('max_output_tokens', 131073), ('max_output_tokens', 1.5),
    ('http_timeout_seconds', 0), ('http_timeout_seconds', 601), ('model', '  '),
    ('provider', KEY), ('api_url', 'http://example.com'),
    ('api_url', f'https://{KEY}@example.com'), ('api_url', f'https://example.com/?key={KEY}'),
    ('api_url', f'https://example.com/#{KEY}'), ('api_key', ''), ('key_action', KEY),
])
def test_validation_never_echoes_rejected_values(local_client, field, value):
    payload = draft()
    payload[field] = value
    response = save(local_client, payload)
    assert response.status_code == 422
    assert KEY not in response.text
    assert response.headers['cache-control'] == 'no-store'


@pytest.mark.parametrize('payload', [None, [], 'private-test-key-do-not-echo', {'api_key': KEY}])
def test_invalid_body_is_controlled(local_client, payload):
    token = local_client.get('/api/ai/settings').json()['mutation_token']
    response = local_client.put('/api/ai/settings', content=json.dumps(payload), headers={'X-AI-Settings-Token': token})
    assert response.status_code == 422
    assert KEY not in response.text


def test_malformed_json_never_echoes_key(local_client):
    token = local_client.get('/api/ai/settings').json()['mutation_token']
    response = local_client.put('/api/ai/settings', content='{"api_key":"' + KEY, headers={'X-AI-Settings-Token': token})
    assert response.status_code == 422
    assert KEY not in response.text


@pytest.mark.parametrize('headers', [
    {'Host': 'evil.example'}, {'Host': 'localhost.evil.example'},
    {'Origin': 'https://evil.example'}, {'Origin': 'null'},
    {'Origin': 'http://127.0.0.1:7777'}, {'Sec-Fetch-Site': 'cross-site'},
    {'Host': 'evil.example', 'X-Forwarded-Host': 'localhost'},
])
def test_settings_reject_untrusted_origin_or_host(local_client, headers):
    response = local_client.get('/api/ai/settings', headers=headers)
    assert response.status_code == 403
    assert response.headers['cache-control'] == 'no-store'


def test_settings_reject_actual_remote_client(api_app):
    with TestClient(api_app, base_url='http://localhost', client=('192.0.2.1', 50123)) as client:
        response = client.get('/api/ai/settings', headers={'X-Forwarded-For': '127.0.0.1'})
    assert response.status_code == 403


@pytest.mark.parametrize('method,path', [('put', '/api/ai/settings'), ('delete', '/api/ai/settings'), ('post', '/api/ai/settings/test')])
def test_mutations_require_app_token(local_client, method, path):
    response = getattr(local_client, method)(path, headers={'X-AI-Settings-Token': 'wrong'})
    assert response.status_code == 403
    assert response.headers['cache-control'] == 'no-store'


def test_supported_origins_and_explicit_alternate_port(local_client, monkeypatch):
    for origin in ['http://localhost', 'http://localhost:5173', 'http://127.0.0.1:5173']:
        assert local_client.get('/api/ai/settings', headers={'Origin': origin}).status_code == 200
    monkeypatch.setenv('INVESTMENT_BOARD_AI_SETTINGS_ORIGINS', 'http://127.0.0.1:5189, https://evil.example')
    assert local_client.get('/api/ai/settings', headers={'Origin': 'http://127.0.0.1:5189'}).status_code == 200
    assert local_client.get('/api/ai/settings', headers={'Origin': 'https://evil.example'}).status_code == 403


def test_corruption_recoverable_without_breaking_browsing(local_client, tmp_path):
    (tmp_path / 'ai.json').write_text('{secret:' + KEY)
    view = local_client.get('/api/ai/settings')
    assert view.status_code == 200
    assert view.json()['configuration_error']
    assert KEY not in view.text
    assert local_client.get('/api/holdings').status_code == 200
    response = local_client.post('/api/ai/stocks/1/advice?use_cache=false')
    assert response.status_code == 503
    assert KEY not in response.text
    assert local_client.get('/api/ai/history').status_code == 200
    assert save(local_client, draft()).status_code == 200
    (tmp_path / 'ai.json').write_text('{bad')
    token = local_client.get('/api/ai/settings').json()['mutation_token']
    assert local_client.delete('/api/ai/settings', headers={'X-AI-Settings-Token': token}).status_code == 200


def test_test_route_uses_draft_without_saving(local_client, monkeypatch, tmp_path):
    from app.api import ai_settings
    seen = []
    def test_connection(settings):
        seen.append(settings)
        return {'ok': True, 'elapsed_ms': 5.0}
    monkeypatch.setattr(ai_settings, 'test_ai_connection', test_connection)
    token = local_client.get('/api/ai/settings').json()['mutation_token']
    response = local_client.post('/api/ai/settings/test', json=draft(), headers={'X-AI-Settings-Token': token})
    assert response.json() == {'ok': True, 'elapsed_ms': 5.0}
    assert seen[0].ai_api_key == KEY
    assert not (tmp_path / 'ai.json').exists()


def test_non_ascii_token_is_denied_without_an_internal_error(local_client):
    response = local_client.delete('/api/ai/settings', headers={'X-AI-Settings-Token': b'\xff'})
    assert response.status_code == 403
    assert response.headers['cache-control'] == 'no-store'


def test_invalid_header_key_is_rejected_before_persistence(local_client):
    for key in ['line\nbreak', '密钥', '\x00private-test-key-do-not-echo']:
        payload = draft()
        payload['api_key'] = key
        response = save(local_client, payload)
        assert response.status_code == 422
        assert key not in response.text


def test_invalid_draft_test_body_is_sanitized(local_client):
    token = local_client.get('/api/ai/settings').json()['mutation_token']
    response = local_client.post('/api/ai/settings/test', json={'api_key': KEY}, headers={'X-AI-Settings-Token': token})
    assert response.status_code == 422
    assert KEY not in response.text
    assert response.headers['cache-control'] == 'no-store'


def test_api_write_failure_returns_controlled_503(local_client, monkeypatch):
    from app.core import ai_settings_store
    assert save(local_client, draft()).status_code == 200
    def fail(*args):
        raise OSError(KEY)
    monkeypatch.setattr(ai_settings_store.os, 'replace', fail)
    response = save(local_client, {**draft(), 'model': 'replacement'})
    assert response.status_code == 503
    assert KEY not in response.text
    assert response.headers['cache-control'] == 'no-store'
    assert local_client.get('/api/ai/settings').json()['model'] == 'test-model'


def test_each_advice_dependency_keeps_one_effective_snapshot(local_client, session, monkeypatch):
    from app.api import investment_advice
    from app.core.ai_settings_store import AISettingsStore
    from starlette.requests import Request
    assert save(local_client, draft()).status_code == 200
    monkeypatch.setattr(investment_advice, 'InvestmentAdviceService', lambda **kwargs: kwargs)
    monkeypatch.setattr(investment_advice, 'build_investment_advice_provider', lambda **kwargs: kwargs['settings'])
    reads = []
    original_read = AISettingsStore._read
    def recording_read(self):
        reads.append(1)
        return original_read(self)
    monkeypatch.setattr(AISettingsStore, '_read', recording_read)
    req = Request({'type': 'http', 'method': 'POST', 'path': '/api/ai/stocks/1/advice', 'headers': []})
    first = investment_advice.get_investment_advice_service(req, session)
    assert len(reads) == 1
    assert first['settings'] is first['provider']
    assert first['settings'].ai_model == 'test-model'
    assert save(local_client, {**draft(), 'model': 'new-model'}).status_code == 200
    reads.clear()
    second = investment_advice.get_investment_advice_service(req, session)
    assert len(reads) == 1
    assert second['settings'].ai_model == 'new-model'
    assert first['settings'].ai_model == 'test-model'


@pytest.mark.parametrize('operation', ['initial', 'reset', 'corrupt'])
def test_legacy_secret_url_is_sanitized_in_every_recovery_view(local_client, monkeypatch, tmp_path, operation):
    raw_url = 'https://fixture-user:fixture-password@safe.example/custom/v1?api_key=fixture-query-secret#fixture-fragment-secret'
    monkeypatch.setenv('AI_API_URL', raw_url)
    monkeypatch.setenv('AI_API_KEY', 'fixture-separate-key')
    if operation == 'reset':
        assert save(local_client, draft()).status_code == 200
        token = local_client.get('/api/ai/settings').json()['mutation_token']
        response = local_client.delete('/api/ai/settings', headers={'X-AI-Settings-Token': token})
    else:
        if operation == 'corrupt':
            (tmp_path / 'ai.json').write_text('{bad')
        response = local_client.get('/api/ai/settings')
    assert response.status_code == 200
    body = response.json()
    assert body['api_url'] == 'https://safe.example/custom/v1'
    assert body['configuration_error']
    assert body['api_key_configured'] is (operation != 'corrupt')
    for secret in ['fixture-user', 'fixture-password', 'fixture-query-secret', 'fixture-fragment-secret', 'fixture-separate-key']:
        assert secret not in response.text
    if operation == 'corrupt':
        assert 'Saved AI configuration cannot be read' in body['configuration_error']
    # Only the redacted display changes; the environment reader remains untouched.
    from app.core.settings import Settings
    assert Settings().ai_api_url == raw_url
    assert Settings().ai_api_key == 'fixture-separate-key'


@pytest.mark.parametrize('raw_url', [
    'https://[fixture-secret', 'https://safe.example:fixture-secret/v1',
    'fixture-secret', 'https://fixture-secret\\@safe.example/v1',
    'https://safe.example/\nfixture-secret',
])
def test_malformed_legacy_url_is_blanked_without_echo(local_client, monkeypatch, raw_url):
    monkeypatch.setenv('AI_API_URL', raw_url)
    response = local_client.get('/api/ai/settings')
    assert response.status_code == 200
    assert response.json()['api_url'] == ''
    assert response.json()['configuration_error']
    assert 'fixture-secret' not in response.text
    assert response.headers['cache-control'] == 'no-store'


@pytest.mark.parametrize('legacy_key', ['', '   '])
def test_copied_environment_template_allows_keep_of_absent_key(local_client, monkeypatch, tmp_path, legacy_key):
    from pathlib import Path
    template = Path(__file__).resolve().parents[2] / '.env.example'
    local_env = tmp_path / 'copied.env'
    local_env.write_text(template.read_text())
    monkeypatch.setenv('INVESTMENT_BOARD_ENV_FILE', str(local_env))
    if legacy_key:
        monkeypatch.setenv('AI_API_KEY', legacy_key)
    else:
        monkeypatch.delenv('AI_API_KEY', raising=False)
    initial = local_client.get('/api/ai/settings').json()
    if not legacy_key:
        assert initial['api_key_configured'] is False
    payload = {name: initial[name] for name in ['provider', 'api_url', 'model', 'temperature', 'max_output_tokens', 'http_timeout_seconds']}
    payload.update(model='changed-template-model', key_action='keep')
    response = save(local_client, payload)
    assert response.status_code == 200
    assert response.json()['api_key_configured'] is False
    assert response.json()['model'] == 'changed-template-model'
    assert json.loads((tmp_path / 'ai.json').read_text())['api_key'] is None
    from app.core.settings import Settings
    assert Settings().ai_api_key == legacy_key


@pytest.mark.parametrize('legacy_key', ['fixture\nsecret', 'fixture密钥'])
def test_invalid_legacy_kept_key_requires_controlled_replace_or_clear(local_client, monkeypatch, legacy_key):
    monkeypatch.setenv('AI_PROVIDER', 'openai_compatible')
    monkeypatch.setenv('AI_API_URL', 'http://127.0.0.1:9999/v1')
    monkeypatch.setenv('AI_API_KEY', legacy_key)
    payload = {**draft(), 'key_action': 'keep', 'api_key': None}
    response = save(local_client, payload)
    assert response.status_code == 409
    assert 'replace or clear' in response.json()['detail']
    assert legacy_key not in response.text
    assert response.headers['cache-control'] == 'no-store'
    assert save(local_client, {**payload, 'key_action': 'clear'}).status_code == 200
