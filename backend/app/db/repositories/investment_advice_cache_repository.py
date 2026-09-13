import json

from sqlmodel import Session, select

from app.db.models import InvestmentAdviceCache


class InvestmentAdviceCacheRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_latest_for_target(self, target_type: str, target_id: int) -> InvestmentAdviceCache | None:
        statement = (
            select(InvestmentAdviceCache)
            .where(
                InvestmentAdviceCache.target_type == target_type,
                InvestmentAdviceCache.target_id == target_id,
            )
            .order_by(InvestmentAdviceCache.generated_at.desc(), InvestmentAdviceCache.id.desc())
            .limit(1)
        )
        if target_type == "holding":
            # SQLite can recycle IDs; detached history is not a current cache hit.
            statement = statement.where(InvestmentAdviceCache.holding_id == target_id)
        return self.session.exec(statement).first()

    def list_recent(self, limit: int = 20) -> list[InvestmentAdviceCache]:
        if limit <= 0:
            return []

        statement = (
            select(InvestmentAdviceCache)
            .order_by(InvestmentAdviceCache.generated_at.desc(), InvestmentAdviceCache.id.desc())
            .limit(limit)
        )
        return self.session.exec(statement).all()

    def list_recent_for_security_ids(self, security_ids: list[int]) -> list[InvestmentAdviceCache]:
        if not security_ids:
            return []

        statement = (
            select(InvestmentAdviceCache)
            .where(InvestmentAdviceCache.security_id.in_(security_ids))
            .order_by(InvestmentAdviceCache.generated_at.desc(), InvestmentAdviceCache.id.desc())
        )
        return self.session.exec(statement).all()

    def create(self, entry: InvestmentAdviceCache, *, limit: int = 20) -> InvestmentAdviceCache:
        self.session.add(entry)
        self.session.flush()
        self._prune(limit)
        self.session.commit()
        self.session.refresh(entry)
        return entry

    def encode_list(self, values: list[str]) -> str:
        return json.dumps(values, ensure_ascii=False)

    def decode_list(self, value: str) -> list[str]:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return [item for item in parsed if isinstance(item, str)]
        return []

    def _prune(self, limit: int) -> None:
        if limit <= 0:
            overflow_items = self.session.exec(select(InvestmentAdviceCache)).all()
        else:
            overflow_statement = (
                select(InvestmentAdviceCache)
                .order_by(InvestmentAdviceCache.generated_at.desc(), InvestmentAdviceCache.id.desc())
                .offset(limit)
            )
            overflow_items = self.session.exec(overflow_statement).all()

        for item in overflow_items:
            self.session.delete(item)
