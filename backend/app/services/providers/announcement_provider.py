from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.db.models import Announcement
from app.services.providers.raw_types import RawAnnouncement


class AnnouncementProvider(Protocol):
    def fetch_for_security(
        self, security_id: int, *, since: datetime | None = None
    ) -> Iterable[Announcement]: ...


class RawAnnouncementSource(Protocol):
    def fetch(
        self,
        stock_code: str,
        market: str,
        *,
        since: datetime | None = None,
    ) -> Iterable[RawAnnouncement]: ...


@dataclass(frozen=True)
class AnnouncementSourceAdapter:
    name: str
    provider: AnnouncementProvider


@dataclass(frozen=True)
class RawAnnouncementSourceAdapter:
    name: str
    provider: RawAnnouncementSource
