from collections.abc import Sequence

from sqlalchemy import case, or_, tuple_
from sqlmodel import Session, select

from app.db.models import Security, utc_now


class SecurityRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, security_id: int) -> Security | None:
        return self.session.get(Security, security_id)

    def list_by_market_code(self, keys: Sequence[tuple[str, str]]) -> list[Security]:
        if not keys:
            return []

        unique_keys = list(dict.fromkeys(keys))
        return self.session.exec(
            select(Security).where(tuple_(Security.market, Security.code).in_(unique_keys))
        ).all()

    def upsert_many(self, items: Sequence[Security], *, commit: bool = True) -> list[Security]:
        if not items:
            return []

        latest_by_key: dict[tuple[str, str], Security] = {}
        for item in items:
            latest_by_key[(item.market, item.code)] = item

        keys = set(latest_by_key)
        existing_rows = self.list_by_market_code(keys)
        existing_by_key = {(row.market, row.code): row for row in existing_rows}

        persisted: list[Security] = []
        for key, item in latest_by_key.items():
            existing = existing_by_key.get(key)
            if existing is None:
                new_row = Security(
                    market=item.market,
                    code=item.code,
                    name=item.name,
                    industry=item.industry,
                    status=item.status,
                )
                self.session.add(new_row)
                self.session.flush()
                existing_by_key[key] = new_row
                persisted.append(new_row)
                continue

            existing.name = item.name
            existing.industry = item.industry
            existing.status = item.status
            existing.updated_at = utc_now()
            persisted.append(existing)

        if commit:
            self.session.commit()
        else:
            self.session.flush()
        for row in persisted:
            self.session.refresh(row)
        return persisted

    def search(self, query: str, limit: int = 20) -> list[Security]:
        normalized_query = query.strip()
        if not normalized_query or limit <= 0:
            return []

        code_prefix_match = Security.code.startswith(normalized_query, autoescape=True)
        name_contains_match = Security.name.contains(normalized_query, autoescape=True)

        exact_code_rank = case((Security.code == normalized_query, 0), else_=1)
        exact_name_rank = case((Security.name == normalized_query, 0), else_=1)
        code_prefix_rank = case((code_prefix_match, 0), else_=1)
        name_contains_rank = case((name_contains_match, 0), else_=1)

        statement = (
            select(Security)
            .where(
                Security.status == "active",
                or_(
                    Security.code == normalized_query,
                    Security.name == normalized_query,
                    code_prefix_match,
                    name_contains_match,
                ),
            )
            .order_by(
                exact_code_rank,
                exact_name_rank,
                code_prefix_rank,
                name_contains_rank,
                Security.code,
                Security.market,
            )
            .limit(limit)
        )

        seen: set[tuple[str, str]] = set()
        results: list[Security] = []
        for security in self.session.exec(statement):
            key = (security.market, security.code)
            if key in seen:
                continue
            seen.add(key)
            results.append(security)
        return results
