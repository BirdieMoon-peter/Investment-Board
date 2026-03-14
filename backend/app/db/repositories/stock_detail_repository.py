from dataclasses import dataclass

from sqlmodel import Session

from app.db.models import CompanyProfile, FinancialMetrics, PriceHistory, Security
from app.db.repositories.announcement_repository import AnnouncementRepository
from app.db.repositories.company_profile_repository import CompanyProfileRepository
from app.db.repositories.financial_metrics_repository import FinancialMetricsRepository
from app.db.repositories.news_repository import NewsRepository
from app.db.repositories.price_context_repository import PriceContextRepository
from app.db.repositories.price_history_repository import PriceHistoryRepository
from app.db.repositories.security_repository import SecurityRepository


@dataclass(frozen=True)
class StockDetailSecurity:
    id: int
    market: str
    code: str
    name: str
    industry: str | None
    status: str


@dataclass(frozen=True)
class StockDetail:
    security: StockDetailSecurity
    price_context: list
    announcements: list
    news: list
    price_history: list[PriceHistory]
    financial_metrics: list[FinancialMetrics]
    company_profile: CompanyProfile | None


class StockDetailRepository:
    def __init__(self, session: Session):
        self.session = session
        self.security_repository = SecurityRepository(session)
        self.price_context_repository = PriceContextRepository(session)
        self.announcement_repository = AnnouncementRepository(session)
        self.news_repository = NewsRepository(session)
        self.price_history_repository = PriceHistoryRepository(session)
        self.financial_metrics_repository = FinancialMetricsRepository(session)
        self.company_profile_repository = CompanyProfileRepository(session)

    def get_by_security_id(self, security_id: int) -> StockDetail | None:
        security = self.security_repository.get_by_id(security_id)
        if security is None:
            return None

        return StockDetail(
            security=self._to_detail_security(security),
            price_context=self.price_context_repository.list_recent_by_security_id(security_id),
            announcements=self.announcement_repository.list_recent_by_security_id(security_id),
            news=self.news_repository.list_recent_by_security_id(security_id),
            price_history=self.price_history_repository.list_recent_by_security_id(security_id),
            financial_metrics=self.financial_metrics_repository.list_recent_by_security_id(security_id),
            company_profile=self.company_profile_repository.get_by_security_id(security_id),
        )

    def _to_detail_security(self, security: Security) -> StockDetailSecurity:
        return StockDetailSecurity(
            id=security.id,
            market=security.market,
            code=security.code,
            name=security.name,
            industry=security.industry,
            status=security.status,
        )
