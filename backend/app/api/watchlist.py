from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.api.dependencies import get_session
from app.db.repositories.security_repository import SecurityRepository
from app.db.repositories.watchlist_repository import WatchlistRepository
from app.db.repositories.watchlist_view_repository import WatchlistViewRepository
from app.schemas import (
    SecuritySearchResult,
    WatchlistAddRequest,
    WatchlistItemResponse,
    WatchlistListRow,
    WatchlistRemoveResponse,
)

router = APIRouter()


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
