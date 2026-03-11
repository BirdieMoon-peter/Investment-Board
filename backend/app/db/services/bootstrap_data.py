from datetime import datetime
from decimal import Decimal

from sqlmodel import Session

from app.db.models import QuoteSnapshot, Security
from app.db.repositories import SecurityRepository

SECURITY_KEYS = {"market", "code", "name", "industry", "status"}
REQUIRED_SECURITY_KEYS = {"market", "code", "name"}
QUOTE_SNAPSHOT_KEYS = {
    "market",
    "code",
    "last_price",
    "change_amount",
    "change_percent",
    "snapshot_time",
}
REQUIRED_QUOTE_SNAPSHOT_KEYS = {
    "market",
    "code",
    "last_price",
    "change_amount",
    "change_percent",
    "snapshot_time",
}



def _validate_record_keys(
    record: dict,
    *,
    allowed_keys: set[str],
    required_keys: set[str],
    record_type: str,
) -> None:
    missing_keys = sorted(required_keys - set(record))
    if missing_keys:
        raise ValueError(f"Missing required keys in {record_type}: {missing_keys}")

    extra_keys = sorted(set(record) - allowed_keys)
    if extra_keys:
        raise ValueError(f"Unexpected keys in {record_type}: {extra_keys}")



def bootstrap_market_data(
    session: Session,
    *,
    securities: list[dict],
    quote_snapshots: list[dict],
) -> None:
    try:
        for item in securities:
            _validate_record_keys(
                item,
                allowed_keys=SECURITY_KEYS,
                required_keys=REQUIRED_SECURITY_KEYS,
                record_type="securities",
            )
        for item in quote_snapshots:
            _validate_record_keys(
                item,
                allowed_keys=QUOTE_SNAPSHOT_KEYS,
                required_keys=REQUIRED_QUOTE_SNAPSHOT_KEYS,
                record_type="quote_snapshots",
            )

        security_repository = SecurityRepository(session)
        security_rows = security_repository.upsert_many(
            [
                Security(
                    market=item["market"],
                    code=item["code"],
                    name=item["name"],
                    industry=item.get("industry"),
                    status=item.get("status", "active"),
                )
                for item in securities
            ],
            commit=False,
        )

        security_lookup = {(security.market, security.code): security for security in security_rows}
        missing_keys = [
            (item["market"], item["code"])
            for item in quote_snapshots
            if (item["market"], item["code"]) not in security_lookup
        ]
        if missing_keys:
            for security in security_repository.list_by_market_code(missing_keys):
                security_lookup[(security.market, security.code)] = security

        unresolved_keys = sorted({key for key in missing_keys if key not in security_lookup})
        if unresolved_keys:
            raise ValueError(f"Unknown security keys in quote_snapshots: {unresolved_keys}")

        for item in quote_snapshots:
            security = security_lookup[(item["market"], item["code"])]
            session.add(
                QuoteSnapshot(
                    security_id=security.id,
                    last_price=Decimal(item["last_price"]),
                    change_amount=Decimal(item["change_amount"]),
                    change_percent=Decimal(item["change_percent"]),
                    snapshot_time=datetime.fromisoformat(item["snapshot_time"]),
                )
            )

        session.commit()
    except Exception:
        session.rollback()
        raise
