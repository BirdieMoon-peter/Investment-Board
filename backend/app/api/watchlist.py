from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.api.dependencies import get_session
from app.api.stocks import get_stock_sync_service
from app.db.models.timestamps import utc_now
from app.db.repositories.security_repository import SecurityRepository
from app.db.repositories.watchlist_repository import WatchlistRepository
from app.db.repositories.watchlist_view_repository import WatchlistViewRepository
from app.schemas import (
    SecuritySearchResult,
    WatchlistAddRequest,
    WatchlistCustomAddRequest,
    WatchlistCustomAddResponse,
    WatchlistItemResponse,
    WatchlistListRow,
    WatchlistRemoveResponse,
    WatchlistSyncResponse,
)
from app.services import SecurityLookupService, StockSyncService
from app.services.security_lookup import SecurityLookupNotFoundError, SecurityLookupProviderError
from app.services.security_search import SecuritySearchService
from app.services.providers import EastmoneySecurityLookupSource, EastmoneySecuritySearchSource

router = APIRouter()



def get_security_lookup_service(
    session: Session = Depends(get_session),
) -> SecurityLookupService:
    return SecurityLookupService(
        repository=SecurityRepository(session),
        source=EastmoneySecurityLookupSource(),
    )


def get_security_search_service(
    session: Session = Depends(get_session),
) -> SecuritySearchService:
    return SecuritySearchService(
        repository=SecurityRepository(session),
        source=EastmoneySecuritySearchSource(),
    )


@router.get("/securities/search", response_model=list[SecuritySearchResult])
def search_securities(
    query: str = Query(min_length=1),
    session: Session = Depends(get_session),
    security_search_service: SecuritySearchService = Depends(get_security_search_service),
) -> list[SecuritySearchResult]:
    if not query.strip():
        raise HTTPException(status_code=422, detail="query must not be blank")

    return [SecuritySearchResult.from_model(security) for security in security_search_service.search(query)]


@router.get("/items", response_model=list[WatchlistListRow])
def list_watchlist_items(
    session: Session = Depends(get_session),
) -> list[WatchlistListRow]:
    repository = WatchlistViewRepository(session)
    return [WatchlistListRow.model_validate(row) for row in repository.list_rows()]


@router.post("/items", response_model=WatchlistItemResponse)
def add_watchlist_item(
    payload: WatchlistAddRequest,
    session: Session = Depends(get_session),
) -> WatchlistItemResponse:
    security_repository = SecurityRepository(session)
    security = security_repository.get_by_id(payload.security_id)
    if security is None:
        raise HTTPException(status_code=404, detail="security not found")

    watchlist_repository = WatchlistRepository(session)
    item = watchlist_repository.add(payload.security_id)
    return WatchlistItemResponse(security_id=item.security_id)


@router.post("/items/custom", response_model=WatchlistCustomAddResponse)
def add_watchlist_item_by_market_code(
    payload: WatchlistCustomAddRequest,
    session: Session = Depends(get_session),
    security_lookup_service: SecurityLookupService = Depends(get_security_lookup_service),
) -> WatchlistCustomAddResponse:
    if payload.market.strip().upper() not in {"SH", "SZ"}:
        raise HTTPException(status_code=422, detail="market must be SH or SZ")

    if not payload.code.strip():
        raise HTTPException(status_code=422, detail="code must not be blank")

    try:
        security = security_lookup_service.lookup_or_create(payload.market, payload.code)
    except SecurityLookupNotFoundError as exc:
        raise HTTPException(status_code=404, detail="security not found") from exc
    except SecurityLookupProviderError as exc:
        raise HTTPException(status_code=502, detail="security lookup unavailable") from exc

    watchlist_repository = WatchlistRepository(session)
    watchlist_repository.add(security.id)
    return WatchlistCustomAddResponse(
        security_id=security.id,
        security=SecuritySearchResult.from_model(security),
    )


@router.post("/sync", response_model=WatchlistSyncResponse)
def sync_watchlist(
    session: Session = Depends(get_session),
    stock_sync_service: StockSyncService = Depends(get_stock_sync_service),
) -> WatchlistSyncResponse:
    watchlist_repository = WatchlistRepository(session)
    watchlist_rows = watchlist_repository.list_security_rows()
    security_ids = [row.security_id for row in watchlist_rows]
    synced_at = utc_now()

    announcements_upserted = 0
    news_items_upserted = 0
    price_bars_upserted = 0
    financial_metrics_upserted = 0
    quote_snapshots_updated = 0
    company_profiles_updated = 0
    warnings: list[str] = []

    for row in watchlist_rows:
        try:
            result = stock_sync_service.sync_security(
                row.security_id,
                stock_code=row.code,
                market=row.market,
                industry=row.industry,
                synced_at=synced_at,
            )
        except Exception as exc:
            warnings.append(f"watchlist sync failed security_id={row.security_id}: {type(exc).__name__}: {exc}")
            continue
        announcements_upserted += result.announcements_upserted
        news_items_upserted += result.news_items_upserted
        price_bars_upserted += result.price_bars_upserted
        financial_metrics_upserted += result.financial_metrics_upserted
        quote_snapshots_updated += 1 if result.quote_snapshot_updated else 0
        company_profiles_updated += 1 if result.company_profile_updated else 0
        warnings.extend(result.warnings)

    synced_count = len(security_ids) - len(
        [warning for warning in warnings if warning.startswith("watchlist sync failed security_id=")]
    )

    return WatchlistSyncResponse(
        security_ids=security_ids,
        synced_count=synced_count,
        announcements_upserted=announcements_upserted,
        news_items_upserted=news_items_upserted,
        price_bars_upserted=price_bars_upserted,
        financial_metrics_upserted=financial_metrics_upserted,
        quote_snapshots_updated=quote_snapshots_updated,
        company_profiles_updated=company_profiles_updated,
        warnings=warnings,
        synced_at=synced_at,
    )


@router.delete("/items/{security_id}", response_model=WatchlistRemoveResponse)
def remove_watchlist_item(
    security_id: int,
    session: Session = Depends(get_session),
) -> WatchlistRemoveResponse:
    repository = WatchlistRepository(session)
    removed = repository.remove_by_security_id(security_id)
    if not removed:
        raise HTTPException(status_code=404, detail="watchlist item not found")

    return WatchlistRemoveResponse(removed=True, security_id=security_id)
