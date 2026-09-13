from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from app.schemas.investment_advice import AdviceConfidence, AdviceRecommendation, InvestmentAdviceContext


@dataclass(frozen=True)
class GeneratedInvestmentAdvice:
    recommendation: AdviceRecommendation
    confidence: AdviceConfidence
    summary: str
    thesis_points: list[str]
    risk_points: list[str]
    position_notes: list[str]
    recent_catalysts: list[str]
    full_analysis: str
    warnings: list[str]
    disclaimer: str


class InvestmentAdviceProvider(Protocol):
    def generate(self, context: InvestmentAdviceContext) -> GeneratedInvestmentAdvice: ...


class InvestmentAdviceProviderError(RuntimeError):
    pass



def recommendation_rank(value: AdviceRecommendation) -> int:
    ranks = {
        "buy": 5,
        "accumulate": 4,
        "hold": 3,
        "watch": 2,
        "trim": 1,
        "sell": 0,
    }
    return ranks[value]



def movement_label(change_percent: Decimal | None) -> str:
    if change_percent is None:
        return "flat"
    if change_percent > 0:
        return "up"
    if change_percent < 0:
        return "down"
    return "flat"
