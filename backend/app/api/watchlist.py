from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.api.dependencies import get_session
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
)
from app.services import SecurityLookupService
from app.services.security_lookup import SecurityLookupNotFoundError, SecurityLookupProviderError
from app.services.providers import EastmoneySecurityLookupSource

router = APIRouter()



def get_security_lookup_service(
    session: Session = Depends(get_session),
) -> SecurityLookupService:
    return SecurityLookupService(
        repository=SecurityRepository(session),
        source=EastmoneySecurityLookupSource(),
    )


@router.get("/securities/search", response_model=list[SecuritySearchResult])
def search_securities(
    query: str = Query(min_length=1),
    session: Session = Depends(get_session),
) -> list[SecuritySearchResult]:
    if not query.strip():
        raise HTTPException(status_code=422, detail="query must not be blank")

    repository = SecurityRepository(session)
    return [SecuritySearchResult.from_model(security) for security in repository.search(query)]


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
