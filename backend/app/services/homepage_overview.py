from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from typing import Protocol


@dataclass(frozen=True)
class MarketIndexSnapshot:
    key: str
    name: str
    market: str | None
    last_value: Decimal | None
    change_amount: Decimal | None
    change_percent: Decimal | None
    snapshot_time: datetime | None


@dataclass(frozen=True)
class HomepageMacroItem:
    key: str
    title: str
    category: str
    value: str | None
    unit: str | None
    change_text: str | None
    published_at: datetime | None
    importance: str
    summary: str | None


@dataclass(frozen=True)
class HomepageOverviewWarning:
    section: str
    message: str


@dataclass(frozen=True)
class HomepageOverview:
    indexes: list[MarketIndexSnapshot]
    macro: list[HomepageMacroItem]
    updated_at: datetime | None
    warnings: list[HomepageOverviewWarning]


class MarketIndexSource(Protocol):
    def fetch(self) -> list[MarketIndexSnapshot]: ...


class MacroSnapshotSource(Protocol):
    def fetch(self) -> list[HomepageMacroItem]: ...


class HomepageOverviewService:
    def __init__(
        self,
        *,
        market_index_source: MarketIndexSource,
        macro_snapshot_source: MacroSnapshotSource,
    ):
        self._market_index_source = market_index_source
        self._macro_snapshot_source = macro_snapshot_source

    def get_overview(self) -> HomepageOverview:
        warnings: list[HomepageOverviewWarning] = []
        indexes: list[MarketIndexSnapshot] = []
        macro: list[HomepageMacroItem] = []

        try:
            indexes = self._market_index_source.fetch()
        except Exception as exc:
            warnings.append(HomepageOverviewWarning(section="indexes", message=str(exc)))

        try:
            macro = self._macro_snapshot_source.fetch()
        except Exception as exc:
            warnings.append(HomepageOverviewWarning(section="macro", message=str(exc)))

        timestamps = [
            item.snapshot_time for item in indexes if item.snapshot_time is not None
        ] + [item.published_at for item in macro if item.published_at is not None]

        return HomepageOverview(
            indexes=indexes,
            macro=macro,
            updated_at=max(timestamps) if timestamps else None,
            warnings=warnings,
        )
