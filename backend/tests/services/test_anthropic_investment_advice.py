from datetime import datetime
from decimal import Decimal

import httpx
import pytest

from app.core.settings import Settings
from app.schemas.investment_advice import InvestmentAdviceContext
from app.services.investment_advice_types import InvestmentAdviceProviderError
from app.services.providers.anthropic_investment_advice import (
    AnthropicInvestmentAdviceProvider,
    OpenAICompatibleInvestmentAdviceProvider,
    build_investment_advice_provider,
)



def test_anthropic_investment_advice_provider_parses_json_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/v1/messages")
        assert request.headers["x-api-key"] == "test-key"
        payload = {
            "content": [
                {
                    "type": "text",
                    "text": '{"recommendation":"hold","confidence":"medium","summary":"Stable but not compelling.","thesis_points":["profitability remains resilient"],"risk_points":["macro slowdown can weaken credit demand"],"position_notes":["current position size is manageable"],"recent_catalysts":["annual report release"],"full_analysis":"Detailed analysis.","warnings":["news flow is limited"],"disclaimer":"Model-generated content, not financial advice."}',
                }
            ]
        }
        return httpx.Response(200, json=payload)

    provider = AnthropicInvestmentAdviceProvider(
        settings=Settings(
            database_url="sqlite://",
            ai_api_key="test-key",
        ),
        transport=httpx.MockTransport(handler),
    )

    advice = provider.generate(
        InvestmentAdviceContext(
            target_type="stock",
            target_id=7,
            security={
                "security_id": 7,
                "market": "SZ",
                "code": "000001",
                "name": "Ping An Bank",
                "industry": "Banking",
                "status": "active",
            },
            holding=None,
            latest_price=Decimal("10.3000"),
            latest_change_percent=Decimal("3.0000"),
            latest_snapshot_time=datetime(2026, 3, 10, 15, 0, 0),
            price_history_closes=["2026-03-10: close 10.7000"],
            announcement_titles=["2025 annual results released"],
            news_titles=["Broker raises target price"],
            financial_metric_points=["2025Q4: revenue=1000000000.0000"],
            company_profile_summary="main_business=商业银行业务",
        )
    )

    assert advice.recommendation == "hold"
    assert advice.confidence == "medium"
    assert advice.summary == "Stable but not compelling."
    assert advice.thesis_points == ["profitability remains resilient"]
    assert advice.risk_points == ["macro slowdown can weaken credit demand"]
    assert advice.position_notes == ["current position size is manageable"]
    assert advice.recent_catalysts == ["annual report release"]
    assert advice.full_analysis == "Detailed analysis."
    assert advice.warnings == ["news flow is limited"]
    assert advice.disclaimer == "Model-generated content, not financial advice."



def test_anthropic_compatible_provider_uses_configured_url_and_dashscope_key() -> None:
    configured_settings = Settings(
        database_url="sqlite://",
        ai_provider="dashscope_anthropic",
        ai_api_key="dashscope-test-key",
        ai_api_url="https://coding.dashscope.aliyuncs.com/apps/anthropic",
        ai_model="kimi-k2.5",
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == httpx.URL("https://coding.dashscope.aliyuncs.com/apps/anthropic/v1/messages")
        assert request.headers["x-api-key"] == "dashscope-test-key"
        payload = request.read().decode("utf-8")
        assert '"model":"kimi-k2.5"' in payload
        return httpx.Response(
            200,
            json={
                "content": [
                    {
                        "type": "text",
                        "text": '{"recommendation":"watch","confidence":"low","summary":"Wait for better confirmation.","thesis_points":["context remains mixed"],"risk_points":["signal quality is low"],"position_notes":["position sizing should remain conservative"],"recent_catalysts":["policy headlines"],"full_analysis":"Long-form explanation.","warnings":[],"disclaimer":"Model-generated content, not financial advice."}',
                    }
                ]
            },
        )

    provider = build_investment_advice_provider(
        settings=configured_settings,
        transport=httpx.MockTransport(handler),
    )

    advice = provider.generate(
        InvestmentAdviceContext(
            target_type="stock",
            target_id=7,
            security={
                "security_id": 7,
                "market": "SZ",
                "code": "000001",
                "name": "Ping An Bank",
                "industry": "Banking",
                "status": "active",
            },
            holding=None,
            latest_price=Decimal("10.3000"),
            latest_change_percent=Decimal("3.0000"),
            latest_snapshot_time=datetime(2026, 3, 10, 15, 0, 0),
            price_history_closes=["2026-03-10: close 10.7000"],
            announcement_titles=["2025 annual results released"],
            news_titles=["Broker raises target price"],
            financial_metric_points=["2025Q4: revenue=1000000000.0000"],
            company_profile_summary="main_business=商业银行业务",
        )
    )

    assert advice.recommendation == "watch"
    assert advice.confidence == "low"



def test_build_investment_advice_provider_rejects_unknown_provider() -> None:
    with pytest.raises(InvestmentAdviceProviderError, match="Unsupported AI provider"):
        build_investment_advice_provider(
            settings=Settings(
                database_url="sqlite://",
                ai_provider="unknown_provider",
                ai_api_key="test-key",
            )
        )



def test_openai_compatible_investment_advice_provider_parses_json_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/v1/chat/completions")
        assert request.headers["authorization"] == "Bearer test-key"
        payload = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": '{"recommendation":"hold","confidence":"medium","summary":"Stable but not compelling.","thesis_points":["profitability remains resilient"],"risk_points":["macro slowdown can weaken credit demand"],"position_notes":["current position size is manageable"],"recent_catalysts":["annual report release"],"full_analysis":"Detailed analysis.","warnings":["news flow is limited"],"disclaimer":"Model-generated content, not financial advice."}',
                    }
                }
            ]
        }
        return httpx.Response(200, json=payload)

    provider = OpenAICompatibleInvestmentAdviceProvider(
        settings=Settings(
            database_url="sqlite://",
            ai_provider="openai_compatible",
            ai_api_key="test-key",
            ai_api_url="http://127.0.0.1:8317",
            ai_model="gpt-5.4",
        ),
        transport=httpx.MockTransport(handler),
    )

    advice = provider.generate(
        InvestmentAdviceContext(
            target_type="stock",
            target_id=7,
            security={
                "security_id": 7,
                "market": "SZ",
                "code": "000001",
                "name": "Ping An Bank",
                "industry": "Banking",
                "status": "active",
            },
            holding=None,
            latest_price=Decimal("10.3000"),
            latest_change_percent=Decimal("3.0000"),
            latest_snapshot_time=datetime(2026, 3, 10, 15, 0, 0),
            price_history_closes=["2026-03-10: close 10.7000"],
            announcement_titles=["2025 annual results released"],
            news_titles=["Broker raises target price"],
            financial_metric_points=["2025Q4: revenue=1000000000.0000"],
            company_profile_summary="main_business=商业银行业务",
        )
    )

    assert advice.recommendation == "hold"
    assert advice.confidence == "medium"
    assert advice.summary == "Stable but not compelling."



def test_anthropic_investment_advice_provider_extracts_json_from_wrapped_text() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "content": [
                    {
                        "type": "text",
                        "text": 'Here is the result:\n```json\n{"recommendation":"hold","confidence":"medium","summary":"Wrapped response.","thesis_points":["profitability remains resilient"],"risk_points":["macro slowdown can weaken credit demand"],"position_notes":["current position size is manageable"],"recent_catalysts":["annual report release"],"full_analysis":"Detailed analysis.","warnings":[],"disclaimer":"Model-generated content, not financial advice."}\n```',
                    }
                ]
            },
        )

    provider = AnthropicInvestmentAdviceProvider(
        settings=Settings(database_url="sqlite://", ai_api_key="test-key"),
        transport=httpx.MockTransport(handler),
    )

    advice = provider.generate(
        InvestmentAdviceContext(
            target_type="stock",
            target_id=7,
            security={
                "security_id": 7,
                "market": "SZ",
                "code": "000001",
                "name": "Ping An Bank",
                "industry": "Banking",
                "status": "active",
            },
            holding=None,
            latest_price=Decimal("10.3000"),
            latest_change_percent=Decimal("3.0000"),
            latest_snapshot_time=datetime(2026, 3, 10, 15, 0, 0),
            price_history_closes=["2026-03-10: close 10.7000"],
            announcement_titles=["2025 annual results released"],
            news_titles=["Broker raises target price"],
            financial_metric_points=["2025Q4: revenue=1000000000.0000"],
            company_profile_summary="main_business=商业银行业务",
        )
    )

    assert advice.summary == "Wrapped response."


@pytest.mark.parametrize("provider_class", [AnthropicInvestmentAdviceProvider, OpenAICompatibleInvestmentAdviceProvider])
@pytest.mark.parametrize("failure, expected", [
    (401, "AI provider authentication failed (401); check credentials or sign in again"),
    (403, "AI provider access denied (403); check account and model permissions"),
    (429, "AI provider rate limit reached (429); retry later or check quota"),
    (404, "AI provider model or endpoint was not found (404); check configuration"),
    ("auth_unavailable", "AI provider has no available authenticated account (503); sign in to the provider again"),
    (503, "AI provider is temporarily unavailable (503); retry later"),
    (500, "AI provider request failed (500)"),
    ("connect", "AI provider is unreachable; check that the service is running and the connection is available"),
    ("timeout", "AI provider request timed out; retry later"),
])
def test_provider_errors_are_actionable_and_do_not_leak_upstream_data(provider_class, failure, expected):
    def handler(request):
        if failure == "connect":
            raise httpx.ConnectError("secret upstream details test-key", request=request)
        if failure == "timeout":
            raise httpx.ReadTimeout("secret upstream details test-key", request=request)
        status = 503 if failure == "auth_unavailable" else failure
        return httpx.Response(status, json={"error": {"code": failure, "message": "secret upstream details test-key"}})

    provider = provider_class(
        settings=Settings(database_url="sqlite://", ai_api_key="test-key", ai_api_url="http://provider.invalid/private-test-key"),
        transport=httpx.MockTransport(handler),
    )
    context = InvestmentAdviceContext(
        target_type="stock", target_id=1,
        security={"security_id": 1, "market": "SZ", "code": "000001", "name": "Synthetic", "status": "active"},
        price_history_closes=[], announcement_titles=[], news_titles=[], financial_metric_points=[],
    )
    with pytest.raises(InvestmentAdviceProviderError) as captured:
        provider.generate(context)
    assert str(captured.value) == expected
    assert "test-key" not in str(captured.value)
    assert "upstream details" not in str(captured.value)


@pytest.mark.parametrize("provider_class", [AnthropicInvestmentAdviceProvider, OpenAICompatibleInvestmentAdviceProvider])
def test_proxy_auth_unavailable_message_marker_is_classified_without_leaking_envelope(provider_class):
    provider = provider_class(
        settings=Settings(database_url="sqlite://", ai_api_key="test-key"),
        transport=httpx.MockTransport(lambda request: httpx.Response(503, json={
            "error": {
                "message": "auth_unavailable: no auth available (providers=codex, model=gpt-5.5)",
                "type": "server_error", "code": "internal_server_error",
                "private_detail": "hidden-secret-test-key",
            },
        })),
    )
    context = InvestmentAdviceContext(
        target_type="stock", target_id=1,
        security={"security_id": 1, "market": "SZ", "code": "000001", "name": "Synthetic", "status": "active"},
        price_history_closes=[], announcement_titles=[], news_titles=[], financial_metric_points=[],
    )
    with pytest.raises(InvestmentAdviceProviderError) as captured:
        provider.generate(context)
    assert str(captured.value) == "AI provider has no available authenticated account (503); sign in to the provider again"
    assert "providers=codex" not in str(captured.value)
    assert "gpt-5.5" not in str(captured.value)
    assert "hidden-secret" not in str(captured.value)


@pytest.mark.parametrize('prefix', ['', '/custom', '/apps/anthropic'])
@pytest.mark.parametrize('base_suffix', ['', '/', '/v1', '/v1/'])
def test_protocol_url_base_forms(prefix, base_suffix):
    from app.services.providers.anthropic_investment_advice import _resolve_messages_url, _resolve_chat_completions_url
    base = 'https://test.example' + prefix
    assert _resolve_messages_url(base + base_suffix) == base + '/v1/messages'
    assert _resolve_chat_completions_url(base + base_suffix) == base + '/v1/chat/completions'
