from datetime import datetime
from decimal import Decimal
from typing import Literal

from sqlmodel import SQLModel

from app.schemas.timestamps import UTCDateTime

from app.db.models import InvestmentAdviceCache
from app.db.repositories import HoldingRow, StockDetail
from app.db.repositories.investment_advice_cache_repository import InvestmentAdviceCacheRepository

AdviceTargetType = Literal["stock", "holding"]
AdviceRecommendation = Literal["buy", "accumulate", "hold", "trim", "sell", "watch"]
AdviceConfidence = Literal["high", "medium", "low"]


class InvestmentAdviceResponse(SQLModel):
    advice_id: int | None = None
    target_type: AdviceTargetType
    target_id: int
    security_id: int
    holding_id: int | None = None
    market: str
    code: str
    name: str
    recommendation: AdviceRecommendation
    confidence: AdviceConfidence
    summary: str
    thesis_points: list[str]
    risk_points: list[str]
    position_notes: list[str]
    recent_catalysts: list[str]
    full_analysis: str
    warnings: list[str]
    generated_at: UTCDateTime
    cached: bool
    disclaimer: str

    @classmethod
    def from_cache_model(
        cls,
        entry: InvestmentAdviceCache,
        *,
        repository: InvestmentAdviceCacheRepository,
        cached: bool,
    ) -> "InvestmentAdviceResponse":
        return cls(
            advice_id=entry.id,
            target_type=entry.target_type,
            target_id=entry.target_id,
            security_id=entry.security_id,
            holding_id=entry.holding_id,
            market=entry.target_market,
            code=entry.target_code,
            name=entry.target_name,
            recommendation=entry.recommendation,
            confidence=entry.confidence,
            summary=entry.summary,
            thesis_points=repository.decode_list(entry.thesis_points_json),
            risk_points=repository.decode_list(entry.risk_points_json),
            position_notes=repository.decode_list(entry.position_notes_json),
            recent_catalysts=repository.decode_list(entry.recent_catalysts_json),
            full_analysis=entry.full_analysis,
            warnings=repository.decode_list(entry.warnings_json),
            generated_at=entry.generated_at,
            cached=cached,
            disclaimer=entry.disclaimer,
        )


class InvestmentAdviceHistoryResponse(SQLModel):
    items: list[InvestmentAdviceResponse]


class HomepageAdviceLabel(SQLModel):
    security_id: int
    holding_id: int | None = None
    target_type: AdviceTargetType
    recommendation: AdviceRecommendation | None = None
    confidence: AdviceConfidence | None = None
    summary: str | None = None
    generated_at: UTCDateTime | None = None
    cached: bool = True
    has_holding_context: bool = False
    warnings: list[str]


class HomepageAdviceLabelsResponse(SQLModel):
    items: list[HomepageAdviceLabel]


class AdviceSecurityContext(SQLModel):
    security_id: int
    market: str
    code: str
    name: str
    industry: str | None = None
    status: str


class AdviceHoldingContext(SQLModel):
    holding_id: int
    quantity: Decimal
    average_cost: Decimal
    notes: str | None = None
    target_horizon: str | None = None


class InvestmentAdviceContext(SQLModel):
    target_type: AdviceTargetType
    target_id: int
    security: AdviceSecurityContext
    holding: AdviceHoldingContext | None = None
    latest_price: Decimal | None = None
    latest_change_percent: Decimal | None = None
    latest_snapshot_time: datetime | None = None
    price_history_closes: list[str]
    announcement_titles: list[str]
    news_titles: list[str]
    financial_metric_points: list[str]
    company_profile_summary: str | None = None
    macro_context: list[str] = []
    market_index_context: list[str] = []

    @classmethod
    def from_sources(
        cls,
        *,
        target_type: AdviceTargetType,
        target_id: int,
        detail: StockDetail,
        holding: HoldingRow | None,
        macro_context: list[str] | None = None,
        market_index_context: list[str] | None = None,
    ) -> "InvestmentAdviceContext":
        latest_quote = detail.price_context[0] if detail.price_context else None
        return cls(
            target_type=target_type,
            target_id=target_id,
            security=AdviceSecurityContext(
                security_id=detail.security.id,
                market=detail.security.market,
                code=detail.security.code,
                name=detail.security.name,
                industry=detail.security.industry,
                status=detail.security.status,
            ),
            holding=(
                AdviceHoldingContext(
                    holding_id=holding.holding_id,
                    quantity=holding.quantity,
                    average_cost=holding.average_cost,
                    notes=holding.notes,
                    target_horizon=holding.target_horizon,
                )
                if holding is not None
                else None
            ),
            latest_price=(latest_quote.last_price if latest_quote is not None else None),
            latest_change_percent=(latest_quote.change_percent if latest_quote is not None else None),
            latest_snapshot_time=(latest_quote.snapshot_time if latest_quote is not None else None),
            price_history_closes=[
                f"{bar.trade_date.isoformat()}: close {bar.close_price}"
                for bar in detail.price_history[:10]
            ],
            announcement_titles=[item.title for item in detail.announcements[:5]],
            news_titles=[item.title for item in detail.news[:5]],
            financial_metric_points=[
                f"{metric.report_period}: revenue={metric.revenue}, net_profit={metric.net_profit}, eps={metric.eps}, roe={metric.roe}"
                for metric in detail.financial_metrics[:4]
            ],
            company_profile_summary=(
                None
                if detail.company_profile is None
                else (
                    f"full_name={detail.company_profile.full_name}; main_business={detail.company_profile.main_business}; employees={detail.company_profile.employees}"
                )
            ),
            macro_context=macro_context or [],
            market_index_context=market_index_context or [],
        )
