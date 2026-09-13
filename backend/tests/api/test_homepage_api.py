from datetime import datetime
from decimal import Decimal

from app.api.homepage import get_homepage_overview_service
from app.services.homepage_overview import (
    HomepageMacroItem,
    HomepageOverview,
    HomepageOverviewService,
    HomepageOverviewWarning,
    MarketIndexSnapshot,
)


class StubHomepageOverviewService(HomepageOverviewService):
    def __init__(self, overview: HomepageOverview):
        self._overview = overview

    def get_overview(self) -> HomepageOverview:
        return self._overview


def test_get_homepage_overview_returns_indexes_and_macro(client, override_dependency) -> None:
    overview = HomepageOverview(
        indexes=[
            MarketIndexSnapshot(
                key="shanghai_composite",
                name="上证指数",
                market="SH",
                last_value=Decimal("3957.0500"),
                change_amount=Decimal("-49.5000"),
                change_percent=Decimal("-1.2400"),
                snapshot_time=datetime(2026, 3, 22, 15, 0, 0),
            )
        ],
        macro=[
            HomepageMacroItem(
                key="cpi",
                title="CPI",
                category="inflation",
                value="1.3",
                unit="%",
                change_text="环比1%",
                published_at=datetime(2026, 2, 1, 0, 0, 0),
                importance="high",
                summary="2026年02月份",
            )
        ],
        updated_at=datetime(2026, 3, 22, 15, 0, 0),
        warnings=[],
    )
    override_dependency(
        get_homepage_overview_service,
        lambda: StubHomepageOverviewService(overview),
    )

    response = client.get("/api/homepage/overview")

    assert response.status_code == 200
    assert response.json() == {
        "indexes": [
            {
                "key": "shanghai_composite",
                "name": "上证指数",
                "market": "SH",
                "last_value": "3957.0500",
                "change_amount": "-49.5000",
                "change_percent": "-1.2400",
                "snapshot_time": "2026-03-22T15:00:00",
            }
        ],
        "macro": [
            {
                "key": "cpi",
                "title": "CPI",
                "category": "inflation",
                "value": "1.3",
                "unit": "%",
                "change_text": "环比1%",
                "published_at": "2026-02-01T00:00:00",
                "importance": "high",
                "summary": "2026年02月份",
            }
        ],
        "updated_at": "2026-03-22T15:00:00",
        "warnings": [],
    }


def test_get_homepage_overview_returns_partial_warning_state(client, override_dependency) -> None:
    overview = HomepageOverview(
        indexes=[],
        macro=[
            HomepageMacroItem(
                key="manufacturing_pmi",
                title="制造业PMI",
                category="activity",
                value="49",
                unit=None,
                change_text="较上月-2.39%",
                published_at=datetime(2026, 2, 1, 0, 0, 0),
                importance="high",
                summary="2026年02月份",
            )
        ],
        updated_at=datetime(2026, 2, 1, 0, 0, 0),
        warnings=[HomepageOverviewWarning(section="indexes", message="upstream timeout")],
    )
    override_dependency(
        get_homepage_overview_service,
        lambda: StubHomepageOverviewService(overview),
    )

    response = client.get("/api/homepage/overview")

    assert response.status_code == 200
    assert response.json()["indexes"] == []
    assert response.json()["warnings"] == [{"section": "indexes", "message": "upstream timeout"}]


def test_get_homepage_overview_returns_empty_defaults(client, override_dependency) -> None:
    overview = HomepageOverview(indexes=[], macro=[], updated_at=None, warnings=[])
    override_dependency(
        get_homepage_overview_service,
        lambda: StubHomepageOverviewService(overview),
    )

    response = client.get("/api/homepage/overview")

    assert response.status_code == 200
    assert response.json() == {
        "indexes": [],
        "macro": [],
        "updated_at": None,
        "warnings": [],
    }
