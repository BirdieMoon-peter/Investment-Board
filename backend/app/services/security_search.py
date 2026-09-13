from typing import Protocol

from app.db.models import Security
from app.db.repositories.security_repository import SecurityRepository
from app.services.providers.raw_types import RawSecurityLookup


class SecuritySearchSource(Protocol):
    def search(self, query: str, limit: int = 20) -> list[RawSecurityLookup]: ...


class SecuritySearchService:
    def __init__(self, *, repository: SecurityRepository, source: SecuritySearchSource):
        self.repository = repository
        self.source = source

    def search(self, query: str, limit: int = 20) -> list[Security]:
        local_results = self.repository.search(query, limit=limit)
        if local_results or limit <= 0:
            return local_results

        try:
            raw_results = self.source.search(query, limit=limit)
        except Exception:
            return []

        if not raw_results:
            return []

        persisted = self.repository.upsert_many(
            [
                Security(
                    market=item.market.strip().upper(),
                    code=item.code.strip(),
                    name=item.name,
                    industry=item.industry,
                    status=item.status,
                )
                for item in raw_results
            ]
        )
        return persisted[:limit]
