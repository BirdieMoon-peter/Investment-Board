from datetime import UTC, datetime
from typing import Annotated

from pydantic import PlainSerializer


def _serialize_utc_timestamp(value: datetime) -> str:
    # These fields are stored as UTC; SQLite discards timezone metadata.
    aware = value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
    return aware.isoformat().replace("+00:00", "Z")


UTCDateTime = Annotated[
    datetime,
    PlainSerializer(_serialize_utc_timestamp, return_type=str, when_used="json"),
]
