from dataclasses import dataclass
from datetime import datetime

from app.api.stocks import (
    get_aggregate_announcement_provider,
    get_aggregate_company_profile_provider,
    get_aggregate_financial_metrics_provider,
    get_aggregate_news_provider,
    get_aggregate_price_history_provider,
    get_aggregate_quote_snapshot_provider,
    get_stock_sync_service,
)
from app.services import StockSyncResult
from app.db.repositories import (
    AnnouncementRepository,
    CompanyProfileRepository,
    FinancialMetricsRepository,
    NewsRepository,
    PriceHistoryRepository,
    QuoteSnapshotRepository,
)
from app.services.providers import (
    AggregateAnnouncementProvider,
    AggregateCompanyProfileProvider,
    AggregateFinancialMetricsProvider,
    AggregateNewsProvider,
    AggregatePriceHistoryProvider,
    AggregateQuoteSnapshotProvider,
    EastmoneyAnnouncementSource,
    EastmoneyCompanyProfileSource,
    EastmoneyFinancialMetricsSource,
    EastmoneyIntradayQuoteSnapshotSource,
    EastmoneyNewsSource,
    EastmoneyPriceHistorySource,
    EastmoneyQuoteSnapshotSource,
    SinaAnnouncementSource,
    SinaNewsSource,
)
from app.services.providers.sina_price_history import SinaPriceHistorySource


@dataclass
class StubStockSyncService:
    result: StockSyncResult
    security_ids: list[int]
    stock_codes: list[str]
    markets: list[str]
    synced_ats: list[datetime | None]

    def sync_security(
        self,
        security_id: int,
        *,
        stock_code: str,
        market: str,
        industry: str | None = None,
        synced_at: datetime | None = None,
    ) -> StockSyncResult:
        self.security_ids.append(security_id)
        self.stock_codes.append(stock_code)
        self.markets.append(market)
        self.synced_ats.append(synced_at)
        return self.result

def test_get_stock_sync_service_builds_real_aggregate_providers(session) -> None:
    service = get_stock_sync_service(
        session=session,
        aggregate_announcement_provider=get_aggregate_announcement_provider(),
        aggregate_news_provider=get_aggregate_news_provider(),
        aggregate_price_history_provider=get_aggregate_price_history_provider(),
        aggregate_financial_metrics_provider=get_aggregate_financial_metrics_provider(),
        aggregate_quote_snapshot_provider=get_aggregate_quote_snapshot_provider(),
        aggregate_company_profile_provider=get_aggregate_company_profile_provider(),
    )

    assert isinstance(service.announcement_provider, AggregateAnnouncementProvider)
    assert isinstance(service.news_provider, AggregateNewsProvider)
    assert isinstance(service.price_history_provider, AggregatePriceHistoryProvider)
    assert isinstance(service.financial_metrics_provider, AggregateFinancialMetricsProvider)
    assert isinstance(service.quote_snapshot_provider, AggregateQuoteSnapshotProvider)
    assert isinstance(service.company_profile_provider, AggregateCompanyProfileProvider)
    assert isinstance(service.announcement_repository, AnnouncementRepository)
    assert isinstance(service.news_repository, NewsRepository)
    assert isinstance(service.price_history_repository, PriceHistoryRepository)
    assert isinstance(service.financial_metrics_repository, FinancialMetricsRepository)
    assert isinstance(service.quote_snapshot_repository, QuoteSnapshotRepository)
    assert isinstance(service.company_profile_repository, CompanyProfileRepository)
    assert service.announcement_provider.sources == []
    assert [adapter.name for adapter in service.announcement_provider.raw_sources] == [
        "eastmoney",
        "sina",
    ]
    assert isinstance(
        service.announcement_provider.raw_sources[0].provider,
        EastmoneyAnnouncementSource,
    )
    assert isinstance(
        service.announcement_provider.raw_sources[1].provider,
        SinaAnnouncementSource,
    )
    assert service.news_provider.sources == []
    assert [adapter.name for adapter in service.news_provider.raw_sources] == [
        "eastmoney",
        "sina",
    ]
    assert isinstance(service.news_provider.raw_sources[0].provider, EastmoneyNewsSource)
    assert isinstance(service.news_provider.raw_sources[1].provider, SinaNewsSource)
    assert [adapter.name for adapter in service.price_history_provider.raw_sources] == [
        "sina",
        "eastmoney",
        "netease",
    ]
    assert service.price_history_provider._fallback_enabled is False
    assert isinstance(
        service.price_history_provider.raw_sources[0].provider,
        SinaPriceHistorySource,
    )
    assert [adapter.name for adapter in service.financial_metrics_provider.raw_sources] == [
        "eastmoney",
    ]
    assert isinstance(
        service.financial_metrics_provider.raw_sources[0].provider,
        EastmoneyFinancialMetricsSource,
    )
    assert [adapter.name for adapter in service.quote_snapshot_provider.raw_sources] == [
        "eastmoney_intraday",
        "eastmoney",
        "sina_fund",
    ]
    assert isinstance(
        service.quote_snapshot_provider.raw_sources[0].provider,
        EastmoneyIntradayQuoteSnapshotSource,
    )
    assert isinstance(
        service.quote_snapshot_provider.raw_sources[1].provider,
        EastmoneyQuoteSnapshotSource,
    )
    assert [adapter.name for adapter in service.company_profile_provider.raw_sources] == [
        "eastmoney",
    ]
    assert isinstance(
        service.company_profile_provider.raw_sources[0].provider,
        EastmoneyCompanyProfileSource,
    )


def test_post_stock_sync_returns_sync_summary(
    client,
    seeded_security,
    override_dependency,
) -> None:
    security_ids: list[int] = []
    stock_codes: list[str] = []
    markets: list[str] = []
    synced_ats: list[datetime | None] = []
    override_dependency(
        get_stock_sync_service,
        lambda: StubStockSyncService(
            StockSyncResult(
                synced=True,
                announcements_upserted=2,
                news_items_upserted=3,
                price_bars_upserted=10,
                financial_metrics_upserted=4,
                quote_snapshot_updated=True,
                company_profile_updated=True,
                warnings=[],
                synced_at=datetime(2026, 3, 11, 13, 0, 0),
            ),
            security_ids,
            stock_codes,
            markets,
            synced_ats,
        ),
    )

    response = client.post(f"/api/stocks/{seeded_security.id}/sync")

    assert response.status_code == 200
    assert response.json() == {
        "security_id": seeded_security.id,
        "synced": True,
        "announcements_upserted": 2,
        "news_items_upserted": 3,
        "price_bars_upserted": 10,
        "financial_metrics_upserted": 4,
        "quote_snapshot_updated": True,
        "company_profile_updated": True,
        "warnings": [],
        "synced_at": "2026-03-11T13:00:00Z",
    }
    assert security_ids == [seeded_security.id]
    assert stock_codes == [seeded_security.code]
    assert markets == [seeded_security.market]
    assert len(synced_ats) == 1
    assert synced_ats[0] is not None


def test_post_stock_sync_returns_warning_aware_summary(
    client,
    seeded_security,
    override_dependency,
) -> None:
    security_ids: list[int] = []
    stock_codes: list[str] = []
    markets: list[str] = []
    synced_ats: list[datetime | None] = []
    override_dependency(
        get_stock_sync_service,
        lambda: StubStockSyncService(
            StockSyncResult(
                synced=True,
                announcements_upserted=2,
                news_items_upserted=3,
                price_bars_upserted=8,
                financial_metrics_upserted=2,
                quote_snapshot_updated=False,
                company_profile_updated=False,
                warnings=["announcement source B failed", "news source A timeout"],
                synced_at=datetime(2026, 3, 11, 14, 0, 0),
            ),
            security_ids,
            stock_codes,
            markets,
            synced_ats,
        ),
    )

    response = client.post(f"/api/stocks/{seeded_security.id}/sync")

    assert response.status_code == 200
    assert response.json() == {
        "security_id": seeded_security.id,
        "synced": True,
        "announcements_upserted": 2,
        "news_items_upserted": 3,
        "price_bars_upserted": 8,
        "financial_metrics_upserted": 2,
        "quote_snapshot_updated": False,
        "company_profile_updated": False,
        "warnings": ["announcement source B failed", "news source A timeout"],
        "synced_at": "2026-03-11T14:00:00Z",
    }
    assert security_ids == [seeded_security.id]
    assert stock_codes == [seeded_security.code]
    assert markets == [seeded_security.market]
    assert len(synced_ats) == 1
    assert synced_ats[0] is not None



def test_post_stock_sync_returns_404_for_unknown_security(client) -> None:
    response = client.post("/api/stocks/999999/sync")

    assert response.status_code == 404
    assert response.json() == {"detail": "security not found"}
