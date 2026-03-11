from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.db.models import NewsItem
from app.services.providers.raw_types import RawNewsItem


class NewsProvider(Protocol):
    def fetch_for_security(
        self, security_id: int, *, since: datetime | None = None
    ) -> Iterable[NewsItem]: ...


class RawNewsSource(Protocol):
    def fetch(
        self,
        stock_code: str,
        market: str,
        *,
        since: datetime | None = None,
    ) -> Iterable[RawNewsItem]: ...


@dataclass(frozen=True)
class NewsSourceAdapter:
    name: str
    provider: NewsProvider


@dataclass(frozen=True)
class RawNewsSourceAdapter:
    name: str
    provider: RawNewsSource
