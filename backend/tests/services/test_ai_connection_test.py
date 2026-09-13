import json

import httpx
import pytest

from app.core.settings import Settings
from app.services.investment_advice_types import InvestmentAdviceProviderError


@pytest.mark.parametrize('provider', ['openai', 'anthropic'])
def test_connection_sends_only_fixed_prompt_and_closes_transport(provider):
    from app.services.ai_connection_test import test_ai_connection
    seen = []
    class Transport(httpx.MockTransport):
        closed = False
        def close(self):
            self.closed = True
    def handler(request):
        seen.append(request)
        payload = json.loads(request.content)
        assert payload == {'model': 'fixture-model', 'max_tokens': 16, 'temperature': 0.2,
                           'messages': [{'role': 'user', 'content': 'Reply with OK.'}]}
        if provider == 'openai':
            assert request.headers['authorization'] == 'Bearer local-test-key'
            assert request.url.path == '/custom/v1/chat/completions'
            return httpx.Response(200, json={'choices': [{'message': {'content': 'OK'}}]})
        assert request.headers['x-api-key'] == 'local-test-key'
        assert request.url.path == '/custom/v1/messages'
        return httpx.Response(200, json={'content': [{'type': 'text', 'text': 'OK'}]})
    transport = Transport(handler)
    result = test_ai_connection(Settings(ai_provider=provider, ai_api_url='https://mock.example/custom/v1', ai_model='fixture-model', ai_api_key='local-test-key'), transport=transport)
    assert result['ok'] is True
    assert result['elapsed_ms'] >= 0
    assert len(seen) == 1
    assert transport.closed


@pytest.mark.parametrize('provider', ['openai', 'anthropic'])
@pytest.mark.parametrize('status', [401, 403, 404, 429, 503, 302])
def test_connection_errors_are_sanitized_and_redirects_not_followed(provider, status):
    from app.services.ai_connection_test import test_ai_connection
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(status, headers={'location': 'https://other.example'}, json={'error': {'message': 'secret-test-key'}})
    with pytest.raises(InvestmentAdviceProviderError) as exc:
        test_ai_connection(Settings(ai_provider=provider, ai_api_key='secret-test-key'), transport=httpx.MockTransport(handler))
    assert str(status) in str(exc.value)
    assert 'secret-test-key' not in str(exc.value)
    assert len(calls) == 1


@pytest.mark.parametrize('provider', ['openai', 'anthropic'])
@pytest.mark.parametrize('body', ['not-json secret-test-key', 'null', '[]', '{}', '{"content":[],"choices":[]}'])
def test_connection_malformed_responses_are_controlled(provider, body):
    from app.services.ai_connection_test import test_ai_connection
    with pytest.raises(InvestmentAdviceProviderError) as exc:
        test_ai_connection(Settings(ai_provider=provider, ai_api_key='secret-test-key'), transport=httpx.MockTransport(lambda request: httpx.Response(200, text=body)))
    assert 'secret-test-key' not in str(exc.value)


@pytest.mark.parametrize('provider', ['openai', 'anthropic'])
def test_connection_timeout_is_controlled(provider):
    from app.services.ai_connection_test import test_ai_connection
    def handler(request):
        raise httpx.ReadTimeout('secret-test-key', request=request)
    with pytest.raises(InvestmentAdviceProviderError, match='timed out'):
        test_ai_connection(Settings(ai_provider=provider, ai_api_key='secret-test-key'), transport=httpx.MockTransport(handler))
