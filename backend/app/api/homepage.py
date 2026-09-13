from fastapi import APIRouter, Depends

from app.schemas.homepage import HomepageOverviewResponse
from app.services.homepage_overview import HomepageOverviewService, MarketIndexSnapshot
from app.services.providers.eastmoney_homepage_overview import (
    EastmoneyMacroSnapshotSource,
    EastmoneyMarketIndexSource,
)
from app.services.providers.sina_market_index import SinaMarketIndexSource
from app.services.providers.tencent_market_index import TencentMarketIndexSource

router = APIRouter()


class PublicMarketIndexSource:
    """Try multiple real public sources, never return fabricated data."""

    def __init__(self):
        self._sources = [
            TencentMarketIndexSource(),
            SinaMarketIndexSource(),
            EastmoneyMarketIndexSource(),
        ]

    def fetch(self) -> list[MarketIndexSnapshot]:
        failures: list[str] = []
        for source in self._sources:
            try:
                results = source.fetch()
                if results:
                    return results
                failures.append(f"{source.__class__.__name__} returned no data")
            except Exception as exc:
                failures.append(f"{source.__class__.__name__}: {type(exc).__name__}: {exc}")
        raise RuntimeError("; ".join(failures) or "all public index sources failed")


def get_homepage_overview_service() -> HomepageOverviewService:
    return HomepageOverviewService(
        market_index_source=PublicMarketIndexSource(),
        macro_snapshot_source=EastmoneyMacroSnapshotSource(),
    )


@router.get("/overview", response_model=HomepageOverviewResponse)
def get_homepage_overview(
    homepage_overview_service: HomepageOverviewService = Depends(get_homepage_overview_service),
) -> HomepageOverviewResponse:
    return HomepageOverviewResponse.from_service_model(homepage_overview_service.get_overview())
