from collections.abc import Iterable
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.api.dependencies import get_session
from app.db.models import Announcement, NewsItem
from app.db.models.timestamps import utc_now
from app.db.repositories import SecurityRepository, StockDetailRepository
from app.db.repositories.announcement_repository import AnnouncementRepository
from app.db.repositories.news_repository import NewsRepository
from app.schemas import StockDetailResponse, StockSyncResponse
from app.services import StockSyncService
from app.services.providers import (
    AggregateAnnouncementProvider,
    AggregateNewsProvider,
    EastmoneyAnnouncementSource,
    EastmoneyNewsSource,
    RawAnnouncementSourceAdapter,
    RawNewsSourceAdapter,
    SinaAnnouncementSource,
    SinaNewsSource,
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
            RawAnnouncementSourceAdapter("eastmoney", EastmoneyAnnouncementSource()),
            RawAnnouncementSourceAdapter("sina", SinaAnnouncementSource()),
        ]
    )



def get_aggregate_news_provider() -> AggregateNewsProvider:
    return AggregateNewsProvider(
        raw_sources=[
            RawNewsSourceAdapter("eastmoney", EastmoneyNewsSource()),
            RawNewsSourceAdapter("sina", SinaNewsSource()),
        ]
    )



def get_stock_sync_service(
    session: Session = Depends(get_session),
    aggregate_announcement_provider: AggregateAnnouncementProvider = Depends(
        get_aggregate_announcement_provider
    ),
    aggregate_news_provider: AggregateNewsProvider = Depends(get_aggregate_news_provider),
) -> StockSyncService:
    return StockSyncService(
        announcement_provider=aggregate_announcement_provider,
        news_provider=aggregate_news_provider,
        announcement_repository=AnnouncementRepository(session),
        news_repository=NewsRepository(session),
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
        warnings=result.warnings,
        synced_at=result.synced_at,
    )
