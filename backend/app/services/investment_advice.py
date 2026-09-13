from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.core.settings import Settings
from app.db.models import InvestmentAdviceCache
from app.db.repositories import (
    HoldingRow,
    HoldingsRepository,
    InvestmentAdviceCacheRepository,
    StockDetailRepository,
    WatchlistViewRepository,
)
from app.schemas.investment_advice import (
    HomepageAdviceLabel,
    InvestmentAdviceContext,
    InvestmentAdviceResponse,
)
from app.services.investment_advice_types import GeneratedInvestmentAdvice, InvestmentAdviceProvider, InvestmentAdviceProviderError
from app.services.homepage_overview import HomepageOverviewService

if TYPE_CHECKING:
    from app.schemas.homepage import HomepageOverview


class InvestmentAdviceTargetNotFoundError(RuntimeError):
    pass


@dataclass(frozen=True)
class AdviceTarget:
    target_type: str
    target_id: int
    security_id: int
    holding_id: int | None
    holding: HoldingRow | None


class InvestmentAdviceService:
    def __init__(
        self,
        *,
        settings: Settings,
        stock_detail_repository: StockDetailRepository,
        holdings_repository: HoldingsRepository,
        cache_repository: InvestmentAdviceCacheRepository,
        provider: InvestmentAdviceProvider,
        watchlist_view_repository: WatchlistViewRepository | None = None,
        homepage_overview_service: HomepageOverviewService | None = None,
    ):
        self._settings = settings
        self._stock_detail_repository = stock_detail_repository
        self._holdings_repository = holdings_repository
        self._cache_repository = cache_repository
        self._provider = provider
        self._watchlist_view_repository = watchlist_view_repository
        self._homepage_overview_service = homepage_overview_service

    def generate_for_stock(self, security_id: int, *, use_cache: bool = True) -> InvestmentAdviceResponse:
        target = AdviceTarget(
            target_type="stock",
            target_id=security_id,
            security_id=security_id,
            holding_id=None,
            holding=self._holdings_repository.get_row_by_security_id(security_id),
        )
        return self._generate(target, use_cache=use_cache)

    def generate_for_holding(self, holding_id: int, *, use_cache: bool = True) -> InvestmentAdviceResponse:
        holding = self._holdings_repository.get_row_by_id(holding_id)
        if holding is None:
            raise InvestmentAdviceTargetNotFoundError("holding not found")
        target = AdviceTarget(
            target_type="holding",
            target_id=holding_id,
            security_id=holding.security_id,
            holding_id=holding.holding_id,
            holding=holding,
        )
        return self._generate(target, use_cache=use_cache)

    def list_recent_history(self) -> list[InvestmentAdviceResponse]:
        return [
            InvestmentAdviceResponse.from_cache_model(
                entry,
                repository=self._cache_repository,
                cached=True,
            )
            for entry in self._cache_repository.list_recent(limit=self._settings.ai_cache_limit)
        ]

    def list_watchlist_labels(self, *, use_cache: bool = False) -> list[HomepageAdviceLabel]:
        if self._watchlist_view_repository is None:
            return []

        watchlist_rows = self._watchlist_view_repository.list_rows()
        if not watchlist_rows:
            return []

        holdings_by_security_id = {
            row.security_id: row for row in self._holdings_repository.list_rows()
        }

        labels: list[HomepageAdviceLabel] = []
        if use_cache:
            cached_entries = self._cache_repository.list_recent_for_security_ids(
                [row.security_id for row in watchlist_rows]
            )

            latest_holding_entry_by_holding_id: dict[int, InvestmentAdviceCache] = {}
            latest_stock_entry_by_security_id: dict[int, InvestmentAdviceCache] = {}
            for entry in cached_entries:
                if entry.target_type == "holding" and entry.holding_id is not None:
                    latest_holding_entry_by_holding_id.setdefault(entry.holding_id, entry)
                elif entry.target_type == "stock":
                    latest_stock_entry_by_security_id.setdefault(entry.security_id, entry)

            for row in watchlist_rows:
                holding = holdings_by_security_id.get(row.security_id)
                cached_entry = (
                    latest_holding_entry_by_holding_id.get(holding.holding_id)
                    if holding is not None
                    else None
                )
                if cached_entry is None:
                    cached_entry = latest_stock_entry_by_security_id.get(row.security_id)

                if cached_entry is None:
                    labels.append(
                        HomepageAdviceLabel(
                            security_id=row.security_id,
                            holding_id=holding.holding_id if holding is not None else None,
                            target_type="holding" if holding is not None else "stock",
                            recommendation=None,
                            confidence=None,
                            summary=None,
                            generated_at=None,
                            cached=True,
                            has_holding_context=False,
                            warnings=[],
                        )
                    )
                    continue

                response = InvestmentAdviceResponse.from_cache_model(
                    cached_entry,
                    repository=self._cache_repository,
                    cached=True,
                )
                labels.append(
                    HomepageAdviceLabel(
                        security_id=row.security_id,
                        holding_id=response.holding_id,
                        target_type=response.target_type,
                        recommendation=response.recommendation,
                        confidence=response.confidence,
                        summary=response.summary,
                        generated_at=response.generated_at,
                        cached=response.cached,
                        has_holding_context=(
                            holding is not None
                            and response.target_type == "holding"
                            and response.holding_id == holding.holding_id
                            and response.security_id == holding.security_id
                        ),
                        warnings=response.warnings,
                    )
                )
            return labels

        for row in watchlist_rows:
            holding = holdings_by_security_id.get(row.security_id)
            try:
                response = (
                    self.generate_for_holding(holding.holding_id, use_cache=False)
                    if holding is not None
                    else self.generate_for_stock(row.security_id, use_cache=False)
                )
                labels.append(
                    HomepageAdviceLabel(
                        security_id=row.security_id,
                        holding_id=response.holding_id,
                        target_type=response.target_type,
                        recommendation=response.recommendation,
                        confidence=response.confidence,
                        summary=response.summary,
                        generated_at=response.generated_at,
                        cached=response.cached,
                        has_holding_context=holding is not None,
                        warnings=response.warnings,
                    )
                )
            except (InvestmentAdviceTargetNotFoundError, InvestmentAdviceProviderError) as exc:
                labels.append(
                    HomepageAdviceLabel(
                        security_id=row.security_id,
                        holding_id=holding.holding_id if holding is not None else None,
                        target_type="holding" if holding is not None else "stock",
                        recommendation=None,
                        confidence=None,
                        summary=None,
                        generated_at=None,
                        cached=False,
                        has_holding_context=holding is not None,
                        warnings=[str(exc)],
                    )
                )

        return labels

    def _generate(self, target: AdviceTarget, *, use_cache: bool) -> InvestmentAdviceResponse:
        if use_cache:
            cached_entry = self._cache_repository.get_latest_for_target(target.target_type, target.target_id)
            if cached_entry is not None:
                return InvestmentAdviceResponse.from_cache_model(
                    cached_entry,
                    repository=self._cache_repository,
                    cached=True,
                )

        detail = self._stock_detail_repository.get_by_security_id(target.security_id)
        if detail is None:
            raise InvestmentAdviceTargetNotFoundError("security not found")

        latest_price = detail.price_context[0].last_price if detail.price_context else None
        if latest_price is None or latest_price <= 0:
            raise InvestmentAdviceProviderError("Price data is not available for AI analysis")

        macro_context = []
        market_index_context = []
        if self._homepage_overview_service is not None:
            try:
                from app.schemas.homepage import HomepageOverview
                overview: HomepageOverview = self._homepage_overview_service.get_overview()
                macro_context = [
                    f"{item.title}: {item.value}{item.unit or ''} ({item.change_text})"
                    for item in overview.macro
                ]
                market_index_context = [
                    f"{item.name}: {item.last_value} ({item.change_percent}%)"
                    for item in overview.indexes
                ]
            except Exception:
                pass

        context = InvestmentAdviceContext.from_sources(
            target_type=target.target_type,
            target_id=target.target_id,
            detail=detail,
            holding=target.holding,
            macro_context=macro_context,
            market_index_context=market_index_context,
        )
        generated = self._provider.generate(context)
        persisted = self._persist_generated(target=target, detail=detail, generated=generated)
        return InvestmentAdviceResponse.from_cache_model(
            persisted,
            repository=self._cache_repository,
            cached=False,
        )

    def _persist_generated(
        self,
        *,
        target: AdviceTarget,
        detail,
        generated: GeneratedInvestmentAdvice,
    ) -> InvestmentAdviceCache:
        return self._cache_repository.create(
            InvestmentAdviceCache(
                target_type=target.target_type,
                target_id=target.target_id,
                security_id=target.security_id,
                holding_id=target.holding_id,
                target_market=detail.security.market,
                target_code=detail.security.code,
                target_name=detail.security.name,
                recommendation=generated.recommendation,
                confidence=generated.confidence,
                summary=generated.summary,
                thesis_points_json=self._cache_repository.encode_list(generated.thesis_points),
                risk_points_json=self._cache_repository.encode_list(generated.risk_points),
                position_notes_json=self._cache_repository.encode_list(generated.position_notes),
                recent_catalysts_json=self._cache_repository.encode_list(generated.recent_catalysts),
                warnings_json=self._cache_repository.encode_list(generated.warnings),
                full_analysis=generated.full_analysis,
                disclaimer=generated.disclaimer,
            ),
            limit=self._settings.ai_cache_limit,
        )
