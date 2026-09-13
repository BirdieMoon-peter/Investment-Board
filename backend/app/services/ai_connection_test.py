"""Fixed-message protocol check; never loads investment context or repositories."""
from time import perf_counter

import httpx

from app.core.settings import Settings
from app.services.investment_advice_types import InvestmentAdviceProviderError
from app.services.providers.anthropic_investment_advice import (
    ANTHROPIC_VERSION,
    _extract_anthropic_text,
    _extract_openai_text,
    _provider_error_message,
    _response_payload,
    canonical_provider_destination,
)


def test_ai_connection(settings: Settings, *, transport: httpx.BaseTransport | None = None) -> dict:
    if not settings.ai_api_key:
        raise InvestmentAdviceProviderError('AI provider API key is not configured')
    try:
        protocol, endpoint = canonical_provider_destination(settings.ai_provider, settings.ai_api_url)
    except (ValueError, httpx.InvalidURL):
        raise InvestmentAdviceProviderError('AI provider configuration is invalid') from None
    headers = {'content-type': 'application/json'}
    if protocol == 'anthropic':
        headers.update({'x-api-key': settings.ai_api_key, 'anthropic-version': ANTHROPIC_VERSION})
    else:
        headers['authorization'] = f'Bearer {settings.ai_api_key}'
    started = perf_counter()
    try:
        with httpx.Client(timeout=settings.ai_http_timeout_seconds, transport=transport, follow_redirects=False) as client:
            response = client.post(endpoint, headers=headers, json={
                'model': settings.ai_model,
                'max_tokens': min(16, settings.ai_max_output_tokens),
                'temperature': settings.ai_temperature,
                'messages': [{'role': 'user', 'content': 'Reply with OK.'}],
            })
            response.raise_for_status()
            payload = _response_payload(response)
            (_extract_anthropic_text if protocol == 'anthropic' else _extract_openai_text)(payload)
    except httpx.HTTPError as exc:
        raise InvestmentAdviceProviderError(_provider_error_message(exc)) from None
    return {'ok': True, 'elapsed_ms': round((perf_counter() - started) * 1000, 2)}
