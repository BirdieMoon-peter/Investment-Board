from typing import Protocol

from app.db.models import Security
from app.db.repositories.security_repository import SecurityRepository
from app.services.providers.raw_types import RawSecurityLookup


class SecurityLookupError(Exception):
    """Base error for custom security lookup failures."""


class SecurityLookupNotFoundError(SecurityLookupError):
    """Raised when a requested market/code cannot be found."""


class SecurityLookupProviderError(SecurityLookupError):
    """Raised when the upstream lookup provider is unavailable."""


class SecurityLookupSource(Protocol):
    def fetch(self, market: str, code: str) -> RawSecurityLookup: ...


class SecurityLookupService:
    def __init__(self, *, repository: SecurityRepository, source: SecurityLookupSource):
        self.repository = repository
        self.source = source

    def lookup_or_create(self, market: str, code: str) -> Security:
        normalized_market = market.strip().upper()
        normalized_code = code.strip()

        existing = self.repository.get_by_market_code(normalized_market, normalized_code)
        if existing is not None:
            return existing

        try:
            raw_security = self.source.fetch(normalized_market, normalized_code)
        except ValueError as exc:
            raise SecurityLookupNotFoundError("security not found") from exc
        except SecurityLookupError:
            raise
        except Exception as exc:
            raise SecurityLookupProviderError("security lookup unavailable") from exc

        provider_market = raw_security.market.strip().upper()
        provider_code = raw_security.code.strip()
        if provider_market != normalized_market or provider_code != normalized_code:
            raise SecurityLookupNotFoundError("security not found")

        persisted = self.repository.upsert_many(
            [
                Security(
                    market=normalized_market,
                    code=normalized_code,
                    name=raw_security.name,
                    industry=raw_security.industry,
                    status=raw_security.status,
                )
            ]
        )
        return persisted[0]
