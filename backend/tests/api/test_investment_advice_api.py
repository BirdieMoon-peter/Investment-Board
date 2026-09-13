from datetime import date, datetime
from decimal import Decimal

from app.api.investment_advice import get_investment_advice_service
from app.core.settings import Settings
from app.db.models import Announcement, CompanyProfile, FinancialMetrics, Holding, NewsItem, PriceHistory, QuoteSnapshot
from app.db.repositories import HoldingsRepository, InvestmentAdviceCacheRepository, StockDetailRepository
from app.services import InvestmentAdviceService
from app.services.investment_advice_types import GeneratedInvestmentAdvice, InvestmentAdviceProviderError
from app.services.providers import build_investment_advice_provider


class StubInvestmentAdviceService(InvestmentAdviceService):
    def __init__(self, stock_response=None, holding_response=None, history_items=None, watchlist_labels=None, error=None):
        self._stock_response = stock_response
        self._holding_response = holding_response
        self._history_items = history_items or []
        self._watchlist_labels = watchlist_labels or []
        self._error = error

    def generate_for_stock(self, security_id: int, *, use_cache: bool = True):
        if self._error is not None:
            raise self._error
        return self._stock_response

    def generate_for_holding(self, holding_id: int, *, use_cache: bool = True):
        if self._error is not None:
            raise self._error
        return self._holding_response

    def list_recent_history(self):
        return self._history_items

    def list_watchlist_labels(self, *, use_cache: bool = False):
        return self._watchlist_labels



def seed_advice_context(session, seeded_security):
    session.add(
        QuoteSnapshot(
            security_id=seeded_security.id,
            last_price=Decimal("10.3000"),
            change_amount=Decimal("0.3000"),
            change_percent=Decimal("3.0000"),
            snapshot_time=datetime(2026, 3, 10, 15, 0, 0),
        )
    )
    session.add(
        Announcement(
            security_id=seeded_security.id,
            title="2025 annual results released",
            source="SZSE",
            url="https://example.com/announcements/1",
            summary="Net profit increased year over year.",
            published_at=datetime(2026, 3, 9, 18, 0),
        )
    )
    session.add(
        NewsItem(
            security_id=seeded_security.id,
            title="Broker raises target price",
            source="Market News",
            url="https://example.com/news/1",
            summary="Analyst cited improving fundamentals.",
            published_at=datetime(2026, 3, 10, 8, 30),
        )
    )
    session.add(
        PriceHistory(
            security_id=seeded_security.id,
            trade_date=date(2026, 3, 10),
            open_price=Decimal("10.5000"),
            high_price=Decimal("10.8000"),
            low_price=Decimal("10.4000"),
            close_price=Decimal("10.7000"),
            volume=Decimal("1000000.0000"),
            amount=Decimal("10700000.0000"),
        )
    )
    session.add(
        FinancialMetrics(
            security_id=seeded_security.id,
            report_period="2025Q4",
            revenue=Decimal("1000000000.0000"),
            net_profit=Decimal("100000000.0000"),
            eps=Decimal("1.2500"),
            roe=Decimal("0.150000"),
            debt_to_asset_ratio=Decimal("0.450000"),
        )
    )
    session.add(
        CompanyProfile(
            security_id=seeded_security.id,
            full_name="平安银行股份有限公司",
            english_name="Ping An Bank Co., Ltd.",
            registered_capital=Decimal("19405918198.0000"),
            establishment_date=date(1987, 12, 22),
            website="https://bank.pingan.com",
            main_business="商业银行业务",
            employees=35000,
        )
    )
    session.commit()



def test_generate_stock_advice_returns_advice_payload(client, override_dependency) -> None:
    response_payload = {
        "advice_id": 1,
        "target_type": "stock",
        "target_id": 7,
        "security_id": 7,
        "holding_id": None,
        "market": "SZ",
        "code": "000001",
        "name": "Ping An Bank",
        "recommendation": "hold",
        "confidence": "medium",
        "summary": "Fundamentals are stable but upside looks moderate.",
        "thesis_points": ["Core banking metrics remain steady"],
        "risk_points": ["Macro slowdown can pressure margins"],
        "position_notes": [],
        "recent_catalysts": ["Annual results release"],
        "full_analysis": "Long-form analysis.",
        "warnings": [],
        "generated_at": "2026-03-22T15:00:00Z",
        "cached": False,
        "disclaimer": "Model-generated content, not financial advice.",
    }
    override_dependency(
        get_investment_advice_service,
        lambda: StubInvestmentAdviceService(stock_response=response_payload),
    )

    response = client.post("/api/ai/stocks/7/advice")

    assert response.status_code == 200
    assert response.json() == response_payload



def test_generate_holding_advice_returns_404_when_missing(client, override_dependency) -> None:
    from app.services import InvestmentAdviceTargetNotFoundError

    override_dependency(
        get_investment_advice_service,
        lambda: StubInvestmentAdviceService(error=InvestmentAdviceTargetNotFoundError("holding not found")),
    )

    response = client.post("/api/ai/holdings/999/advice")

    assert response.status_code == 404
    assert response.json() == {"detail": "holding not found"}



def test_list_advice_history_returns_recent_items(client, override_dependency) -> None:
    history_item = {
        "advice_id": 2,
        "target_type": "holding",
        "target_id": 1,
        "security_id": 7,
        "holding_id": 1,
        "market": "SZ",
        "code": "000001",
        "name": "Ping An Bank",
        "recommendation": "accumulate",
        "confidence": "medium",
        "summary": "Position can be added on pullbacks.",
        "thesis_points": ["Valuation remains acceptable"],
        "risk_points": ["Short-term volatility remains elevated"],
        "position_notes": ["Average cost is below spot"],
        "recent_catalysts": ["Broker target hike"],
        "full_analysis": "Detailed view.",
        "warnings": [],
        "generated_at": "2026-03-22T16:00:00Z",
        "cached": True,
        "disclaimer": "Model-generated content, not financial advice.",
    }
    override_dependency(
        get_investment_advice_service,
        lambda: StubInvestmentAdviceService(history_items=[history_item]),
    )

    response = client.get("/api/ai/history")

    assert response.status_code == 200
    assert response.json() == {"items": [history_item]}



def test_list_watchlist_labels_returns_cached_labels(client, override_dependency) -> None:
    labels = [
        {
            "security_id": 7,
            "holding_id": 1,
            "target_type": "holding",
            "recommendation": "accumulate",
            "confidence": "medium",
            "summary": "Position can be added on pullbacks.",
            "generated_at": "2026-03-22T16:00:00Z",
            "cached": True,
            "has_holding_context": True,
            "warnings": [],
        },
        {
            "security_id": 8,
            "holding_id": None,
            "target_type": "stock",
            "recommendation": None,
            "confidence": None,
            "summary": None,
            "generated_at": None,
            "cached": True,
            "has_holding_context": False,
            "warnings": [],
        },
    ]
    override_dependency(
        get_investment_advice_service,
        lambda: StubInvestmentAdviceService(watchlist_labels=labels),
    )

    response = client.get("/api/ai/watchlist-labels")

    assert response.status_code == 200
    assert response.json() == {"items": labels}



def test_generate_stock_advice_uses_cache_and_caps_history(session, seeded_security):
    seed_advice_context(session, seeded_security)
    session.add(
        Holding(
            security_id=seeded_security.id,
            quantity=Decimal("80.0000"),
            average_cost=Decimal("10.0000"),
            notes="base position",
            target_horizon="long_term",
        )
    )
    session.commit()
    cache_repository = InvestmentAdviceCacheRepository(session)

    class RecordingProvider:
        def __init__(self):
            self.calls = 0

        def generate(self, context):
            self.calls += 1
            return GeneratedInvestmentAdvice(
                recommendation="hold",
                confidence="medium",
                summary=f"summary {self.calls}",
                thesis_points=[f"thesis {self.calls}"],
                risk_points=[f"risk {self.calls}"],
                position_notes=[f"note {self.calls}"],
                recent_catalysts=[f"catalyst {self.calls}"],
                full_analysis=f"analysis {self.calls}",
                warnings=[],
                disclaimer="Model-generated content, not financial advice.",
            )

    provider = RecordingProvider()
    service = InvestmentAdviceService(
        settings=Settings(database_url="sqlite://", ai_cache_limit=20),
        stock_detail_repository=StockDetailRepository(session),
        holdings_repository=HoldingsRepository(session),
        cache_repository=cache_repository,
        provider=provider,
    )

    first = service.generate_for_stock(seeded_security.id, use_cache=True)
    second = service.generate_for_stock(seeded_security.id, use_cache=True)

    assert provider.calls == 1
    assert first.cached is False
    assert second.cached is True
    assert second.summary == first.summary

    for _ in range(25):
        service.generate_for_stock(seeded_security.id, use_cache=False)

    history = service.list_recent_history()
    assert len(history) == 20



def test_build_investment_advice_provider_supports_kimi_alias() -> None:
    provider = build_investment_advice_provider(
        settings=Settings(
            database_url="sqlite://",
            ai_provider="kimi",
            ai_api_key="test-key",
            ai_api_url="https://coding.dashscope.aliyuncs.com/apps/anthropic",
            ai_model="kimi-k2.5",
        )
    )

    assert provider.__class__.__name__ == "AnthropicInvestmentAdviceProvider"



def test_build_investment_advice_provider_supports_openai_compatible_alias() -> None:
    provider = build_investment_advice_provider(
        settings=Settings(
            database_url="sqlite://",
            ai_provider="openai_compatible",
            ai_api_key="test-key",
            ai_api_url="http://127.0.0.1:8317",
            ai_model="gpt-5.4",
        )
    )

    assert provider.__class__.__name__ == "OpenAICompatibleInvestmentAdviceProvider"



def test_build_investment_advice_provider_rejects_unsupported_provider() -> None:
    try:
        build_investment_advice_provider(
            settings=Settings(
                database_url="sqlite://",
                ai_provider="unsupported",
                ai_api_key="test-key",
            )
        )
    except InvestmentAdviceProviderError as exc:
        assert str(exc) == "Unsupported AI provider: unsupported"
    else:
        raise AssertionError("Expected unsupported provider to raise")


def test_cached_advice_and_label_serialize_utc_after_database_roundtrip(client, session, seeded_security):
    from app.db.models import InvestmentAdviceCache, WatchlistItem

    session.add(WatchlistItem(security_id=seeded_security.id))
    session.add(InvestmentAdviceCache(
        target_type="stock", target_id=seeded_security.id, security_id=seeded_security.id,
        target_market="SZ", target_code="000001", target_name="Synthetic",
        recommendation="hold", confidence="medium", summary="cached analysis",
        thesis_points_json="[]", risk_points_json="[]", position_notes_json="[]",
        recent_catalysts_json="[]", warnings_json="[]", full_analysis="analysis",
        disclaimer="test", generated_at=datetime(2026, 9, 12, 14, 5),
    ))
    session.commit()
    session.expire_all()
    history = client.get("/api/ai/history")
    labels = client.get("/api/ai/watchlist-labels", params={"use_cache": True})
    assert history.status_code == labels.status_code == 200
    assert history.json()["items"][0]["generated_at"] == "2026-09-12T14:05:00Z"
    assert labels.json()["items"][0]["generated_at"] == "2026-09-12T14:05:00Z"
