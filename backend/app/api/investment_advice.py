from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlmodel import Session

from app.api.dependencies import get_session
from app.api.homepage import PublicMarketIndexSource
from app.core.settings import Settings
from app.core.ai_settings_store import AISettingsStoreError, load_effective_ai_settings
from app.db.repositories import (
    HoldingsRepository,
    InvestmentAdviceCacheRepository,
    StockDetailRepository,
    WatchlistViewRepository,
)
from app.schemas import (
    HomepageAdviceLabelsResponse,
    InvestmentAdviceHistoryResponse,
    InvestmentAdviceResponse,
)
from app.services import InvestmentAdviceService, InvestmentAdviceTargetNotFoundError
from app.services.investment_advice_types import InvestmentAdviceProviderError
from app.services.providers import build_investment_advice_provider
from app.services.homepage_overview import HomepageOverviewService
from app.services.providers.eastmoney_homepage_overview import EastmoneyMacroSnapshotSource

router = APIRouter()



def get_investment_advice_service(
    request: Request,
    session: Session = Depends(get_session),
) -> InvestmentAdviceService:
    settings = Settings()
    try:
        settings = load_effective_ai_settings(settings)
    except AISettingsStoreError as exc:
        # Read-only history/cache browsing remains available during recovery.
        history_only = request.method == 'GET' and request.url.path.endswith('/history')
        cached_labels_only = (
            request.method == 'GET' and request.url.path.endswith('/watchlist-labels')
            and request.query_params.get('use_cache', '').lower() in {'true', '1', 'yes', 'on'}
        )
        if not (history_only or cached_labels_only):
            raise HTTPException(status_code=503, detail=str(exc)) from None
    return InvestmentAdviceService(
        settings=settings,
        stock_detail_repository=StockDetailRepository(session),
        holdings_repository=HoldingsRepository(session),
        cache_repository=InvestmentAdviceCacheRepository(session),
        provider=build_investment_advice_provider(settings=settings),
        watchlist_view_repository=WatchlistViewRepository(session),
        homepage_overview_service=HomepageOverviewService(
            market_index_source=PublicMarketIndexSource(),
            macro_snapshot_source=EastmoneyMacroSnapshotSource(),
        ),
    )


@router.post("/stocks/{security_id}/advice", response_model=InvestmentAdviceResponse)
def generate_stock_advice(
    security_id: int,
    use_cache: bool = Query(default=True),
    investment_advice_service: InvestmentAdviceService = Depends(get_investment_advice_service),
) -> InvestmentAdviceResponse:
    try:
        return investment_advice_service.generate_for_stock(security_id, use_cache=use_cache)
    except InvestmentAdviceTargetNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvestmentAdviceProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/holdings/{holding_id}/advice", response_model=InvestmentAdviceResponse)
def generate_holding_advice(
    holding_id: int,
    use_cache: bool = Query(default=True),
    investment_advice_service: InvestmentAdviceService = Depends(get_investment_advice_service),
) -> InvestmentAdviceResponse:
    try:
        return investment_advice_service.generate_for_holding(holding_id, use_cache=use_cache)
    except InvestmentAdviceTargetNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvestmentAdviceProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/history", response_model=InvestmentAdviceHistoryResponse)
def list_recent_advice_history(
    investment_advice_service: InvestmentAdviceService = Depends(get_investment_advice_service),
) -> InvestmentAdviceHistoryResponse:
    return InvestmentAdviceHistoryResponse(items=investment_advice_service.list_recent_history())


@router.get("/watchlist-labels", response_model=HomepageAdviceLabelsResponse)
def list_watchlist_labels(
    use_cache: bool = Query(default=False),
    investment_advice_service: InvestmentAdviceService = Depends(get_investment_advice_service),
) -> HomepageAdviceLabelsResponse:
    try:
        return HomepageAdviceLabelsResponse(items=investment_advice_service.list_watchlist_labels(use_cache=use_cache))
    except InvestmentAdviceTargetNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvestmentAdviceProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
