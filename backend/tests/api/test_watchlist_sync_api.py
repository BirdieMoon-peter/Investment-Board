from dataclasses import dataclass
from datetime import datetime

from app.api.watchlist import get_stock_sync_service
from app.db.models import Security
from app.services import StockSyncResult


@dataclass
class StubWatchlistStockSyncService:
    result_by_security_id: dict[int, StockSyncResult | Exception]
    calls: list[tuple[int, str, str, datetime | None]]

    def sync_security(
        self,
        security_id: int,
        *,
        stock_code: str,
        market: str,
        industry: str | None = None,
        synced_at: datetime | None = None,
    ) -> StockSyncResult:
        self.calls.append((security_id, stock_code, market, synced_at))
        result = self.result_by_security_id[security_id]
        if isinstance(result, Exception):
            raise result
        return result


def test_post_watchlist_sync_returns_aggregate_summary(
    client,
    seeded_security,
    session,
    override_dependency,
) -> None:
    second_security = Security(
        market="SZ",
        code="002594",
        name="BYD",
        industry="Auto",
        status="active",
    )
    session.add(second_security)
    session.commit()
    session.refresh(second_security)

    client.post("/api/watchlist/items", json={"security_id": seeded_security.id})
    client.post("/api/watchlist/items", json={"security_id": second_security.id})
    second_security_id = second_security.id

    calls: list[tuple[int, str, str, datetime | None]] = []
    override_dependency(
        get_stock_sync_service,
        lambda: StubWatchlistStockSyncService(
            {
                seeded_security.id: StockSyncResult(
                    synced=True,
                    announcements_upserted=2,
                    news_items_upserted=1,
                    price_bars_upserted=5,
                    financial_metrics_upserted=1,
                    quote_snapshot_updated=True,
                    company_profile_updated=False,
                    warnings=["warn-a"],
                    synced_at=datetime(2026, 3, 22, 9, 0, 0),
                ),
                second_security_id: StockSyncResult(
                    synced=True,
                    announcements_upserted=3,
                    news_items_upserted=4,
                    price_bars_upserted=6,
                    financial_metrics_upserted=2,
                    quote_snapshot_updated=False,
                    company_profile_updated=True,
                    warnings=["warn-b"],
                    synced_at=datetime(2026, 3, 22, 9, 0, 0),
                ),
            },
            calls,
        ),
    )

    response = client.post("/api/watchlist/sync")

    assert response.status_code == 200
    payload = response.json()
    assert payload["security_ids"] == [seeded_security.id, second_security_id]
    assert payload["synced_count"] == 2
    assert payload["announcements_upserted"] == 5
    assert payload["news_items_upserted"] == 5
    assert payload["price_bars_upserted"] == 11
    assert payload["financial_metrics_upserted"] == 3
    assert payload["quote_snapshots_updated"] == 1
    assert payload["company_profiles_updated"] == 1
    assert payload["warnings"] == ["warn-a", "warn-b"]
    assert payload["synced_at"].startswith("2026-")
    assert len(calls) == 2
    assert calls[0][0] == seeded_security.id
    assert calls[0][1] == seeded_security.code
    assert calls[0][2] == seeded_security.market
    assert calls[0][3] is not None


def test_post_watchlist_sync_returns_empty_summary_for_empty_watchlist(client) -> None:
    response = client.post("/api/watchlist/sync")

    assert response.status_code == 200
    assert response.json()["security_ids"] == []
    assert response.json()["synced_count"] == 0
    assert response.json()["announcements_upserted"] == 0
    assert response.json()["news_items_upserted"] == 0
    assert response.json()["price_bars_upserted"] == 0
    assert response.json()["financial_metrics_upserted"] == 0
    assert response.json()["quote_snapshots_updated"] == 0
    assert response.json()["company_profiles_updated"] == 0
    assert response.json()["warnings"] == []



def test_post_watchlist_sync_continues_when_one_security_sync_raises(
    client,
    seeded_security,
    session,
    override_dependency,
) -> None:
    second_security = Security(
        market="SZ",
        code="002594",
        name="BYD",
        industry="Auto",
        status="active",
    )
    session.add(second_security)
    session.commit()
    session.refresh(second_security)

    client.post("/api/watchlist/items", json={"security_id": seeded_security.id})
    client.post("/api/watchlist/items", json={"security_id": second_security.id})

    calls: list[tuple[int, str, str, datetime | None]] = []
    override_dependency(
        get_stock_sync_service,
        lambda: StubWatchlistStockSyncService(
            {
                seeded_security.id: StockSyncResult(
                    synced=True,
                    announcements_upserted=2,
                    news_items_upserted=1,
                    price_bars_upserted=5,
                    financial_metrics_upserted=1,
                    quote_snapshot_updated=True,
                    company_profile_updated=False,
                    warnings=[],
                    synced_at=datetime(2026, 3, 22, 9, 0, 0),
                ),
                second_security.id: RuntimeError("sync pipeline failed"),
            },
            calls,
        ),
    )

    response = client.post("/api/watchlist/sync")

    assert response.status_code == 200
    payload = response.json()
    assert payload["synced_count"] == 1
    assert payload["announcements_upserted"] == 2
    assert payload["news_items_upserted"] == 1
    assert payload["quote_snapshots_updated"] == 1
    assert any("sync failed security_id=" in warning for warning in payload["warnings"])
