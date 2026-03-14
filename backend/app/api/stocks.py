from collections.abc import Iterable
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.api.dependencies import get_session
from app.db.models import Announcement, NewsItem
from app.db.models.timestamps import utc_now
from app.db.repositories import SecurityRepository, StockDetailRepository
from app.db.repositories.announcement_repository import AnnouncementRepository
from app.db.repositories.company_profile_repository import CompanyProfileRepository
from app.db.repositories.financial_metrics_repository import FinancialMetricsRepository
from app.db.repositories.news_repository import NewsRepository
from app.db.repositories.price_history_repository import PriceHistoryRepository
from app.schemas import StockDetailResponse, StockSyncResponse
from app.services import StockSyncService
from app.services.providers import (
    AggregateAnnouncementProvider,
    AggregateCompanyProfileProvider,
    AggregateFinancialMetricsProvider,
    AggregateNewsProvider,
    AggregatePriceHistoryProvider,
    EastmoneyAnnouncementSource,
    EastmoneyCompanyProfileSource,
    EastmoneyFinancialMetricsSource,
    EastmoneyPriceHistorySource,
    IfengNewsSource,
    RawAnnouncementSourceAdapter,
    RawCompanyProfileSourceAdapter,
    RawFinancialMetricsSourceAdapter,
    RawNewsSourceAdapter,
    RawPriceHistorySourceAdapter,
    SinaAnnouncementSource,
)

router = APIRouter()


class EmptyAnnouncementProvider:
    def fetch_for_security(
        self, security_id: int, *, since=None
    ) -> Iterable[Announcement]:
        return []


class EmptyNewsProvider:
    def fetch_for_security(self, security_id: int, *, since=None) -> Iterable[NewsItem]:
        return []



def get_aggregate_announcement_provider() -> AggregateAnnouncementProvider:
    return AggregateAnnouncementProvider(
        raw_sources=[
            # Eastmoney announcement API returns fund/trust announcements, not stock announcements
            # RawAnnouncementSourceAdapter("eastmoney", EastmoneyAnnouncementSource()),
            RawAnnouncementSourceAdapter("sina", SinaAnnouncementSource()),
        ]
    )



def get_aggregate_news_provider() -> AggregateNewsProvider:
    return AggregateNewsProvider(
        raw_sources=[
            # Ifeng news API returns 404 - endpoint may have changed
            # RawNewsSourceAdapter("ifeng", IfengNewsSource()),
        ]
    )



def get_aggregate_price_history_provider() -> AggregatePriceHistoryProvider:
    return AggregatePriceHistoryProvider(
        raw_sources=[
            RawPriceHistorySourceAdapter("eastmoney", EastmoneyPriceHistorySource()),
        ]
    )



def get_aggregate_financial_metrics_provider() -> AggregateFinancialMetricsProvider:
    return AggregateFinancialMetricsProvider(
        raw_sources=[
            # Eastmoney financial metrics API endpoint has changed and no longer works
            # RawFinancialMetricsSourceAdapter(
            #     "eastmoney",
            #     EastmoneyFinancialMetricsSource(),
            # ),
        ]
    )



def get_aggregate_company_profile_provider() -> AggregateCompanyProfileProvider:
    return AggregateCompanyProfileProvider(
        raw_sources=[
            # Eastmoney company profile API endpoint has changed and no longer works
            # RawCompanyProfileSourceAdapter("eastmoney", EastmoneyCompanyProfileSource()),
        ]
    )



def get_stock_sync_service(
    session: Session = Depends(get_session),
    aggregate_announcement_provider: AggregateAnnouncementProvider = Depends(
        get_aggregate_announcement_provider
    ),
    aggregate_news_provider: AggregateNewsProvider = Depends(get_aggregate_news_provider),
    aggregate_price_history_provider: AggregatePriceHistoryProvider = Depends(
        get_aggregate_price_history_provider
    ),
    aggregate_financial_metrics_provider: AggregateFinancialMetricsProvider = Depends(
        get_aggregate_financial_metrics_provider
    ),
    aggregate_company_profile_provider: AggregateCompanyProfileProvider = Depends(
        get_aggregate_company_profile_provider
    ),
) -> StockSyncService:
    return StockSyncService(
        announcement_provider=aggregate_announcement_provider,
        news_provider=aggregate_news_provider,
        announcement_repository=AnnouncementRepository(session),
        news_repository=NewsRepository(session),
        price_history_provider=aggregate_price_history_provider,
        financial_metrics_provider=aggregate_financial_metrics_provider,
        company_profile_provider=aggregate_company_profile_provider,
        price_history_repository=PriceHistoryRepository(session),
        financial_metrics_repository=FinancialMetricsRepository(session),
        company_profile_repository=CompanyProfileRepository(session),
    )


@router.get("/{security_id}", response_model=StockDetailResponse)
def get_stock_detail(
    security_id: int,
    session: Session = Depends(get_session),
) -> StockDetailResponse:
    repository = StockDetailRepository(session)
    detail = repository.get_by_security_id(security_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="security not found")

    return StockDetailResponse.from_repository_model(detail)


@router.post("/{security_id}/sync", response_model=StockSyncResponse)
def sync_stock(
    security_id: int,
    session: Session = Depends(get_session),
    stock_sync_service: StockSyncService = Depends(get_stock_sync_service),
) -> StockSyncResponse:
    security_repository = SecurityRepository(session)
    security = security_repository.get_by_id(security_id)
    if security is None:
        raise HTTPException(status_code=404, detail="security not found")

    result = stock_sync_service.sync_security(
        security_id,
        stock_code=security.code,
        market=security.market,
        synced_at=utc_now(),
    )
    return StockSyncResponse.from_service_result(
        security_id=security_id,
        synced=result.synced,
        announcements_upserted=result.announcements_upserted,
        news_items_upserted=result.news_items_upserted,
        price_bars_upserted=result.price_bars_upserted,
        financial_metrics_upserted=result.financial_metrics_upserted,
        company_profile_updated=result.company_profile_updated,
        warnings=result.warnings,
        synced_at=result.synced_at,
    )
