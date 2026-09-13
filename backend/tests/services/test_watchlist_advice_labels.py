from datetime import datetime
from decimal import Decimal

import pytest

from app.core.settings import Settings
from app.db.models import Holding, InvestmentAdviceCache, WatchlistItem
from app.db.repositories import HoldingsRepository, InvestmentAdviceCacheRepository, StockDetailRepository, WatchlistViewRepository
from app.services.investment_advice import InvestmentAdviceService


@pytest.mark.parametrize("cache_scope", ["none", "stock", "holding", "deleted_holding"])
def test_cached_holding_badge_describes_selected_analysis(session, seeded_security, cache_scope):
    session.add(WatchlistItem(security_id=seeded_security.id))
    holding = Holding(security_id=seeded_security.id, quantity=Decimal("10"), average_cost=Decimal("8"))
    session.add(holding)
    session.commit()
    if cache_scope != "none":
        session.add(InvestmentAdviceCache(
            target_type="stock" if cache_scope == "stock" else "holding",
            target_id=seeded_security.id if cache_scope == "stock" else holding.id,
            security_id=seeded_security.id,
            holding_id=holding.id if cache_scope == "holding" else None,
            target_market="SZ", target_code="000001", target_name="Ping An Bank",
            recommendation="hold", confidence="medium", summary="cached analysis",
            thesis_points_json="[]", risk_points_json="[]", position_notes_json="[]",
            recent_catalysts_json="[]", warnings_json="[]", full_analysis="analysis",
            disclaimer="test", generated_at=datetime(2026, 9, 11, 7),
        ))
        session.commit()

    class NeverGenerate:
        def generate(self, context):
            pytest.fail("cache reads must not call a provider")

    service = InvestmentAdviceService(
        settings=Settings(database_url="sqlite://"),
        stock_detail_repository=StockDetailRepository(session),
        holdings_repository=HoldingsRepository(session),
        cache_repository=InvestmentAdviceCacheRepository(session),
        watchlist_view_repository=WatchlistViewRepository(session),
        provider=NeverGenerate(),
    )
    label, = service.list_watchlist_labels(use_cache=True)
    assert label.has_holding_context is (cache_scope == "holding")
    assert label.recommendation == ("hold" if cache_scope in {"stock", "holding"} else None)
    if cache_scope == "stock":
        assert label.target_type == "stock"
        assert label.holding_id is None
