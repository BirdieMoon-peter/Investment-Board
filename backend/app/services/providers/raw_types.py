from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class RawAnnouncement:
    title: str
    published_at: datetime
    source: str
    url: str | None = None
    summary: str | None = None


@dataclass(frozen=True)
class RawNewsItem:
    title: str
    published_at: datetime
    source: str
    url: str | None = None
    summary: str | None = None
