from sqlmodel import SQLModel

from app.db.models import Security


class SecuritySearchResult(SQLModel):
    security_id: int
    market: str
    code: str
    name: str
    industry: str | None = None
    status: str

    @classmethod
    def from_model(cls, security: Security) -> "SecuritySearchResult":
        return cls(
            security_id=security.id,
            market=security.market,
            code=security.code,
            name=security.name,
            industry=security.industry,
            status=security.status,
        )
