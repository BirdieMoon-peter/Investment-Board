"""Persistence boundaries for data provenance; callers retain transaction control."""
from decimal import Decimal, InvalidOperation

from sqlalchemy import inspect

from sqlmodel import Session, select

from app.db.models import Security
from app.db.models.data_management import (
    DataQualityIssue,
    DataSource,
    FundNavObservation,
    IngestionRun,
    SecurityDataset,
    SecurityResearchMetadata,
)


class DataManagementRepository:
    SAFE_ERRORS = frozenset({
        "ingestion_error", "network_error", "timeout", "rate_limited",
        "authentication_error", "provider_unavailable", "invalid_data",
    })

    def __init__(self, session: Session):
        self.session = session

    def _one(self, model, **keys):
        return self.session.exec(select(model).filter_by(**keys)).first()

    @staticmethod
    def _enum(value, choices, field):
        if value not in choices:
            raise ValueError(f"Invalid {field}")

    @staticmethod
    def _decimal(value, field, *, fraction=False):
        try:
            number = Decimal(str(value))
        except (InvalidOperation, ValueError):
            raise ValueError(f"Invalid {field}") from None
        if (
            not number.is_finite()
            or (not fraction and number <= 0)
            or (fraction and not 0 <= number <= 1)
        ):
            raise ValueError(f"Invalid {field}")
        return number

    def _validate(self, item):
        if isinstance(item, DataSource):
            if not item.source_key.strip() or not item.name.strip() or not item.access_mode.strip():
                raise ValueError("Source key, name and access mode are required")
        elif isinstance(item, SecurityDataset):
            if not item.category.strip():
                raise ValueError("Dataset category is required")
            self._enum(
                item.price_basis,
                {"unknown", "unadjusted", "forward_adjusted", "backward_adjusted"},
                "price_basis",
            )
            if item.coverage_start and item.coverage_end and item.coverage_start > item.coverage_end:
                raise ValueError("Invalid coverage interval")
        elif isinstance(item, IngestionRun):
            self._enum(
                item.status, {"pending", "running", "succeeded", "partial", "failed"}, "status"
            )
            for field in ("records_received", "records_written", "records_rejected"):
                value = getattr(item, field)
                if type(value) is not int or value < 0:
                    raise ValueError(f"Invalid {field}")
            if item.error_message is not None:
                item.error_message = (
                    item.error_message
                    if item.error_message in self.SAFE_ERRORS
                    else "ingestion_error"
                )
        elif isinstance(item, DataQualityIssue):
            self._enum(item.severity, {"info", "warning", "error"}, "severity")
            if not item.code.strip() or not item.message.strip():
                raise ValueError("Quality issue code and message are required")
            run = (
                self.session.get(IngestionRun, item.run_id)
                if item.run_id is not None else None
            )
            if run and run.dataset_id != item.dataset_id:
                raise ValueError("Issue run must match dataset")
        elif isinstance(item, SecurityResearchMetadata):
            self._enum(
                item.instrument_type, {"unknown", "stock", "etf", "lof", "index"},
                "instrument_type",
            )
            for field in ("management_fee", "custody_fee", "fund_assets"):
                value = getattr(item, field)
                if value is not None:
                    setattr(item, field, self._decimal(value, field, fraction=field != "fund_assets"))
        elif isinstance(item, FundNavObservation):
            self._enum(item.nav_kind, {"unit_nav", "cumulative_nav", "iopv"}, "nav_kind")
            item.value = self._decimal(item.value, "NAV")

    def _snapshot_for_write(self, item):
        # begin_nested() flushes managed dirty objects before its savepoint.
        # Copy the proposal, then restore this managed object's database state
        # before validation or any query can autoflush the proposal outside it.
        with self.session.no_autoflush:
            values = {
                field: getattr(item, field) for field in type(item).model_fields
            }
            state = inspect(item)
            if state.session is self.session:
                if state.persistent and state.modified:
                    self.session.refresh(item)
                elif state.pending:
                    self.session.expunge(item)
            return type(item)(**values)

    def _write(self, item, *, keys=None, commit=True):
        item = self._snapshot_for_write(item)
        with self.session.no_autoflush:
            self._validate(item)
        identity = {key: getattr(item, key) for key in keys} if keys else None
        # Python's SQLite legacy transaction mode does not BEGIN for SELECT/SAVEPOINT.
        # Establish the outer transaction so releasing our savepoint cannot commit
        # a caller's commit=False write implicitly.
        connection = self.session.connection()
        if (
            connection.dialect.name == "sqlite"
            and not connection.connection.driver_connection.in_transaction
        ):
            connection.exec_driver_sql("BEGIN")
        with self.session.begin_nested():
            row = self._one(type(item), **identity) if identity else None
            if row is None:
                row = type(item)(**item.model_dump(exclude={"id"}))
                self.session.add(row)
            else:
                for field, value in item.model_dump(exclude={"id"}).items():
                    setattr(row, field, value)
            self.session.flush()
        if commit:
            self.session.commit()
        self.session.refresh(row)
        return row

    def get_source(self, source_key: str) -> DataSource | None:
        return self._one(DataSource, source_key=source_key)

    def upsert_source(self, item: DataSource, *, commit: bool = True) -> DataSource:
        return self._write(item, keys=("source_key",), commit=commit)

    def get_dataset(self, security_id: int, category: str) -> SecurityDataset | None:
        return self._one(SecurityDataset, security_id=security_id, category=category)

    def upsert_dataset(self, item: SecurityDataset, *, commit: bool = True) -> SecurityDataset:
        return self._write(
            item,
            keys=("security_id", "category"),
            commit=commit,
        )

    def record_run(self, item: IngestionRun, *, commit: bool = True) -> IngestionRun:
        # An attempt is separate from successfully fetched dataset provenance.
        return self._write(item, commit=commit)

    def list_runs(self, dataset_id: int) -> list[IngestionRun]:
        statement = (
            select(IngestionRun)
            .where(IngestionRun.dataset_id == dataset_id)
            .order_by(IngestionRun.started_at.desc(), IngestionRun.id.desc())
        )
        return list(self.session.exec(statement).all())

    def record_quality_issue(self, item: DataQualityIssue, *, commit: bool = True) -> DataQualityIssue:
        return self._write(item, commit=commit)

    def list_quality_issues(self, dataset_id: int, *, unresolved_only: bool = False) -> list[DataQualityIssue]:
        statement = select(DataQualityIssue).where(DataQualityIssue.dataset_id == dataset_id)
        if unresolved_only:
            statement = statement.where(DataQualityIssue.resolved_at.is_(None))
        statement = statement.order_by(
            DataQualityIssue.created_at.desc(), DataQualityIssue.id.desc()
        )
        return list(self.session.exec(statement).all())

    def get_metadata(self, security_id: int) -> SecurityResearchMetadata | None:
        row = self._one(SecurityResearchMetadata, security_id=security_id)
        if row is None and self.session.get(Security, security_id) is not None:
            return SecurityResearchMetadata(security_id=security_id)
        return row

    def upsert_metadata(self, item: SecurityResearchMetadata, *, commit: bool = True) -> SecurityResearchMetadata:
        return self._write(item, keys=("security_id",), commit=commit)

    def upsert_nav(self, item: FundNavObservation, *, commit: bool = True) -> FundNavObservation:
        return self._write(
            item, keys=("security_id", "nav_date", "nav_kind", "source_id"),
            commit=commit,
        )

    def list_nav(self, security_id: int, *, nav_kind: str | None = None, source_id: int | None = None) -> list[FundNavObservation]:
        statement = select(FundNavObservation).where(FundNavObservation.security_id == security_id)
        if nav_kind is not None:
            statement = statement.where(FundNavObservation.nav_kind == nav_kind)
        if source_id is not None:
            statement = statement.where(FundNavObservation.source_id == source_id)
        statement = statement.order_by(
            FundNavObservation.nav_date.desc(), FundNavObservation.id.desc()
        )
        return list(self.session.exec(statement).all())
