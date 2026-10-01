"""Safe acquisition facts, independent of persistence and user-visible records."""
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

import httpx

SAFE_ERRORS = frozenset({'ingestion_error', 'network_error', 'timeout', 'rate_limited', 'authentication_error', 'provider_unavailable', 'invalid_data'})


def safe_error_code(exc: Exception) -> str:
    if isinstance(exc, httpx.TimeoutException):
        return 'timeout'
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        return {401: 'authentication_error', 403: 'authentication_error', 429: 'rate_limited'}.get(status, 'provider_unavailable')
    if isinstance(exc, httpx.RequestError):
        return 'network_error'
    if isinstance(exc, (ValueError, TypeError, ArithmeticError)):
        return 'invalid_data'
    return 'ingestion_error'


@dataclass(frozen=True)
class SourceAttempt:
    source_key: str
    state: Literal['succeeded', 'empty', 'failed']
    count: int = 0
    error_code: str | None = None
    observed_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None

    def __post_init__(self):
        if not self.source_key.strip() or self.state not in {'succeeded', 'empty', 'failed'}:
            raise ValueError('Invalid source attempt')
        if type(self.count) is not int or self.count < 0 or (self.state == 'empty' and self.count):
            raise ValueError('Invalid attempt count')
        if self.error_code is not None and self.error_code not in SAFE_ERRORS:
            object.__setattr__(self, 'error_code', 'ingestion_error')


class RejectedSourceData(ValueError):
    """Validation failure carrying only a safe count, never the response."""
    def __init__(self, count: int):
        super().__init__("Invalid source data")
        self.received_count = count
