from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, create_engine, select

from app.db.models import Holding, Security, WatchlistItem
from app.db.models.data_management import (
    DataSource, SecurityDataset, IngestionRun, DataQualityIssue,
    SecurityResearchMetadata, FundNavObservation,
)
from app.db.repositories.data_management_repository import DataManagementRepository
from app.db.session import create_db_and_tables


@pytest.fixture
def repo(session):
    return DataManagementRepository(session)


@pytest.fixture
def dataset(repo, seeded_security):
    source = repo.upsert_source(DataSource(source_key="fixture", name="Fixture", access_mode="public"))
    return repo.upsert_dataset(SecurityDataset(security_id=seeded_security.id, category="daily_price", source_id=source.id))


def test_populated_legacy_bootstrap_is_additive_and_idempotent(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    # Build only the existing business tables, as an installation predating this increment.
    for model in (Security, Holding, WatchlistItem):
        model.__table__.create(engine)
    with Session(engine) as session:
        security = Security(market="SH", code="510300", name="Old fund")
        session.add(security)
        session.flush()
        session.add(Holding(security_id=security.id, quantity=Decimal("10"), average_cost=Decimal("3.14")))
        session.add(WatchlistItem(security_id=security.id))
        session.commit()
        security_id = security.id
        old_rows = {table: session.exec(text(f"SELECT * FROM {table}")).all() for table in ("securities", "holdings", "watchlist_items")}
        old_schema = {table: session.exec(text(f"SELECT sql FROM sqlite_master WHERE name='{table}'")).one() for table in old_rows}
    create_db_and_tables(engine)
    create_db_and_tables(engine)
    with Session(engine) as session:
        for table, rows in old_rows.items():
            assert session.exec(text(f"SELECT * FROM {table}")).all() == rows
            assert session.exec(text(f"SELECT sql FROM sqlite_master WHERE name='{table}'")).one() == old_schema[table]
        repo = DataManagementRepository(session)
        assert repo.get_metadata(security_id).instrument_type == "unknown"
        assert session.exec(select(SecurityResearchMetadata)).all() == []
    assert {m.__tablename__ for m in (DataSource, SecurityDataset, IngestionRun, DataQualityIssue, SecurityResearchMetadata, FundNavObservation)} <= set(inspect(engine).get_table_names())


def test_upserts_preserve_unique_identity(repo, dataset):
    source = repo.get_source("fixture")
    assert repo.upsert_source(DataSource(source_key="fixture", name="Changed", access_mode="manual")).id == source.id
    updated = repo.upsert_dataset(SecurityDataset(security_id=dataset.security_id, category=dataset.category, source_id=source.id, unit="CNY"))
    assert updated.id == dataset.id
    assert updated.unit == "CNY"
    assert updated.price_basis == "unknown"
    assert repo.get_dataset(dataset.security_id, dataset.category).id == dataset.id


@pytest.mark.parametrize("model,kwargs", [
    (SecurityDataset, {"security_id": 999, "category": "price"}),
    (IngestionRun, {"dataset_id": 999, "source_id": 999}),
    (DataQualityIssue, {"dataset_id": 999, "code": "missing", "severity": "error", "message": "Missing"}),
    (SecurityResearchMetadata, {"security_id": 999}),
    (FundNavObservation, {"security_id": 999, "source_id": 999, "nav_date": date(2026, 1, 1), "value": Decimal("1")}),
])
def test_database_rejects_orphans(session, model, kwargs):
    session.add(model(**kwargs))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


@pytest.mark.parametrize("model", [DataSource, SecurityDataset, SecurityResearchMetadata, FundNavObservation])
def test_unique_constraints_at_database_boundary(session, repo, dataset, model):
    values = {
        DataSource: dict(source_key="fixture", name="duplicate", access_mode="public"),
        SecurityDataset: dict(security_id=dataset.security_id, category=dataset.category),
        SecurityResearchMetadata: dict(security_id=dataset.security_id),
        FundNavObservation: dict(security_id=dataset.security_id, source_id=dataset.source_id, nav_date=date(2026, 1, 1), value=Decimal("1")),
    }[model]
    if model in (SecurityResearchMetadata, FundNavObservation):
        session.add(model(**values))
        session.commit()
    session.add(model(**values))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


@pytest.mark.parametrize("field,value", [("price_basis", "bogus")])
def test_invalid_dataset_update_is_atomic(repo, dataset, session, field, value):
    with pytest.raises(ValueError):
        repo.upsert_dataset(SecurityDataset(security_id=dataset.security_id, category=dataset.category, source_id=dataset.source_id, **{field: value}))
    session.expire_all()
    assert repo.get_dataset(dataset.security_id, dataset.category).price_basis == "unknown"


@pytest.mark.parametrize("field,value", [("status", "bogus"), ("records_received", -1), ("records_written", -1), ("records_rejected", -1), ("records_written", 1.5)])
def test_invalid_runs_rejected(repo, dataset, field, value):
    with pytest.raises(ValueError):
        repo.record_run(IngestionRun(dataset_id=dataset.id, source_id=dataset.source_id, **{field: value}))
    assert repo.list_runs(dataset.id) == []


def test_runs_issues_ordering_safe_errors_and_no_false_freshness(repo, dataset):
    stamp = datetime(2026, 1, 1, tzinfo=UTC)
    for status in ("failed", "partial"):
        repo.record_run(IngestionRun(dataset_id=dataset.id, source_id=dataset.source_id, status=status, started_at=stamp, error_message='Bearer sk-secret password=hidden {"raw_response": "secret"}'))
    runs = repo.list_runs(dataset.id)
    assert [r.id for r in runs] == sorted([r.id for r in runs], reverse=True)
    assert all(r.error_message == "ingestion_error" for r in runs)
    assert repo.get_dataset(dataset.security_id, dataset.category).fetched_at is None
    for code in ("missing", "stale"):
        repo.record_quality_issue(DataQualityIssue(dataset_id=dataset.id, run_id=runs[0].id, code=code, severity="warning", message="Synthetic issue"))
    issues = repo.list_quality_issues(dataset.id)
    assert [i.code for i in issues] == ["stale", "missing"]
    issues[0].resolved_at = stamp
    repo.session.commit()
    assert [i.code for i in repo.list_quality_issues(dataset.id, unresolved_only=True)] == ["missing"]


def test_source_and_issue_run_consistency(repo, dataset):
    other = repo.upsert_source(DataSource(source_key="other", name="Other", access_mode="public"))
    failed_attempt = repo.record_run(IngestionRun(dataset_id=dataset.id, source_id=other.id, status="failed"))
    assert failed_attempt.source_id == other.id
    assert repo.get_dataset(dataset.security_id, dataset.category).source_id == dataset.source_id
    unknown = repo.upsert_dataset(SecurityDataset(security_id=dataset.security_id, category="unknown"))
    assert repo.record_run(IngestionRun(dataset_id=unknown.id, source_id=other.id)).source_id == other.id
    run = repo.record_run(IngestionRun(dataset_id=dataset.id, source_id=dataset.source_id))
    other_dataset = repo.upsert_dataset(SecurityDataset(security_id=dataset.security_id, category="nav", source_id=other.id))
    with pytest.raises(ValueError):
        repo.record_quality_issue(DataQualityIssue(dataset_id=other_dataset.id, run_id=run.id, code="bad", severity="error", message="Mismatch"))
    with pytest.raises(ValueError):
        repo.record_quality_issue(DataQualityIssue(dataset_id=dataset.id, code="bad", severity="bogus", message="Invalid"))


@pytest.mark.parametrize("field,value", [("instrument_type", "bond"), ("management_fee", Decimal("-0.1")), ("custody_fee", Decimal("1.01")), ("management_fee", Decimal("NaN")), ("custody_fee", Decimal("Infinity"))])
def test_metadata_create_and_update_validation(repo, dataset, field, value):
    for existing in (False, True):
        if existing:
            repo.upsert_metadata(SecurityResearchMetadata(security_id=dataset.security_id, instrument_type="etf", management_fee=Decimal("0.00123456789123456789")))
        with pytest.raises(ValueError):
            repo.upsert_metadata(SecurityResearchMetadata(security_id=dataset.security_id, **{field: value}))
        if existing:
            assert repo.get_metadata(dataset.security_id).management_fee == Decimal("0.00123456789123456789")


@pytest.mark.parametrize("value", [Decimal("0"), Decimal("-1"), Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")])
def test_nav_create_and_update_validation(repo, dataset, value):
    kwargs = dict(security_id=dataset.security_id, source_id=dataset.source_id, nav_date=date(2026, 1, 1))
    with pytest.raises(ValueError):
        repo.upsert_nav(FundNavObservation(**kwargs, value=value))
    repo.upsert_nav(FundNavObservation(**kwargs, value=Decimal("1.123456789123456789")))
    with pytest.raises(ValueError):
        repo.upsert_nav(FundNavObservation(**kwargs, value=value))
    assert repo.list_nav(dataset.security_id)[0].value == Decimal("1.123456789123456789")
    with pytest.raises(ValueError):
        repo.upsert_nav(FundNavObservation(**kwargs, value=Decimal("1"), nav_kind="bad"))


def test_nav_precision_distinct_kind_source_and_order(repo, dataset):
    other = repo.upsert_source(DataSource(source_key="other", name="Other", access_mode="public"))
    value = Decimal("1.123456789123456789")
    for nav_date, kind, source in [(date(2026, 1, 1), "unit_nav", dataset.source_id), (date(2026, 1, 2), "unit_nav", dataset.source_id), (date(2026, 1, 2), "cumulative_nav", dataset.source_id), (date(2026, 1, 2), "iopv", other.id)]:
        repo.upsert_nav(FundNavObservation(security_id=dataset.security_id, source_id=source, nav_date=nav_date, nav_kind=kind, value=value))
    rows = repo.list_nav(dataset.security_id)
    assert len(rows) == 4
    assert all(row.value == value for row in rows)
    assert rows[-1].nav_date == date(2026, 1, 1)
    assert len(repo.list_nav(dataset.security_id, nav_kind="unit_nav", source_id=dataset.source_id)) == 2
    row = repo.upsert_nav(FundNavObservation(security_id=dataset.security_id, source_id=dataset.source_id, nav_date=date(2026, 1, 1), value=Decimal("2")))
    assert row.id == rows[-1].id


def test_caller_rollback_and_failed_write_isolation(repo, session, seeded_security):
    repo.upsert_source(DataSource(source_key="uncommitted", name="U", access_mode="public"), commit=False)
    session.rollback()
    assert repo.get_source("uncommitted") is None
    repo.upsert_source(DataSource(source_key="pending", name="P", access_mode="public"), commit=False)
    with pytest.raises(IntegrityError):
        repo.upsert_dataset(SecurityDataset(security_id=999, category="orphan"), commit=False)
    assert repo.get_source("pending") is not None
    session.commit()
    assert repo.get_source("pending") is not None
    assert session.exec(select(SecurityDataset)).all() == []


@pytest.mark.parametrize("value", [Decimal("0"), Decimal("-1"), Decimal("NaN"), Decimal("Infinity")])
def test_invalid_fund_assets_create_update(repo, dataset, value):
    with pytest.raises(ValueError):
        repo.upsert_metadata(SecurityResearchMetadata(security_id=dataset.security_id, fund_assets=value))
    repo.upsert_metadata(SecurityResearchMetadata(security_id=dataset.security_id, fund_assets=Decimal("1000000.123456789123"), benchmark_name="Disclosed benchmark", assets_as_of=date(2026, 1, 1)))
    with pytest.raises(ValueError):
        repo.upsert_metadata(SecurityResearchMetadata(security_id=dataset.security_id, fund_assets=value))
    saved = repo.get_metadata(dataset.security_id)
    assert saved.fund_assets == Decimal("1000000.123456789123")
    assert saved.benchmark_code is None
    assert saved.benchmark_name == "Disclosed benchmark"


def test_whole_ingestion_can_be_rolled_back(repo, session, seeded_security):
    source = repo.upsert_source(DataSource(source_key="batch", name="Batch"), commit=False)
    dataset = repo.upsert_dataset(SecurityDataset(security_id=seeded_security.id, category="nav", source_id=source.id), commit=False)
    run = repo.record_run(IngestionRun(dataset_id=dataset.id, source_id=source.id, status="partial"), commit=False)
    repo.record_quality_issue(DataQualityIssue(dataset_id=dataset.id, run_id=run.id, code="missing", severity="error", message="Missing"), commit=False)
    repo.upsert_metadata(SecurityResearchMetadata(security_id=seeded_security.id, instrument_type="lof"), commit=False)
    repo.upsert_nav(FundNavObservation(security_id=seeded_security.id, source_id=source.id, nav_date=date(2026, 1, 1), value=Decimal("1.234")), commit=False)
    session.rollback()
    for model in (DataSource, SecurityDataset, IngestionRun, DataQualityIssue, SecurityResearchMetadata, FundNavObservation):
        assert session.exec(select(model)).all() == []
    assert session.get(Security, seeded_security.id) is not None


def test_database_rejects_raw_provider_errors(session, dataset):
    session.add(IngestionRun(dataset_id=dataset.id, source_id=dataset.source_id, error_message="token=secret raw response"))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


@pytest.mark.parametrize("model,values", [
    (SecurityDataset, dict(category="new", price_basis="bad")),
    (IngestionRun, dict(status="bad")),
    (IngestionRun, dict(records_written=-1)),
    (SecurityResearchMetadata, dict(instrument_type="bad")),
    (SecurityResearchMetadata, dict(management_fee=Decimal("1.1"))),
    (FundNavObservation, dict(value=Decimal("-1"))),
    (FundNavObservation, dict(value=Decimal("1"), nav_kind="bad")),
])
def test_database_check_constraints(session, dataset, model, values):
    base = {SecurityDataset: dict(security_id=dataset.security_id), IngestionRun: dict(dataset_id=dataset.id, source_id=dataset.source_id), SecurityResearchMetadata: dict(security_id=dataset.security_id), FundNavObservation: dict(security_id=dataset.security_id, source_id=dataset.source_id, nav_date=date(2026, 1, 1))}[model]
    session.add(model(**base, **values))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_positive_decimals_do_not_underflow_through_sqlite_float_checks(repo, dataset):
    tiny = Decimal("1e-400")
    nav = repo.upsert_nav(FundNavObservation(security_id=dataset.security_id, source_id=dataset.source_id, nav_date=date(2026, 1, 1), value=tiny))
    metadata = repo.upsert_metadata(SecurityResearchMetadata(security_id=dataset.security_id, fund_assets=tiny))
    assert nav.value == tiny
    assert metadata.fund_assets == tiny


@pytest.mark.parametrize("field,value,error", [("source_id", 999, IntegrityError), ("price_basis", "bad", ValueError)])
def test_failed_managed_dataset_update_preserves_outer_work(repo, dataset, field, value, error):
    original = dataset.source_id
    repo.upsert_source(DataSource(source_key="outer", name="Outer"), commit=False)
    setattr(dataset, field, value)
    with pytest.raises(error):
        repo.upsert_dataset(dataset, commit=False)
    assert repo.get_source("outer") is not None
    assert repo.get_dataset(dataset.security_id, dataset.category).source_id == original
    assert repo.get_dataset(dataset.security_id, dataset.category).price_basis == "unknown"
    repo.session.commit()
    assert repo.get_source("outer") is not None


def test_valid_managed_dataset_update_stays_inside_caller_transaction(repo, dataset):
    dataset.unit = "CNY"
    result = repo.upsert_dataset(dataset, commit=False)
    assert result.id == dataset.id
    assert result.unit == "CNY"
    repo.session.rollback()
    assert repo.get_dataset(dataset.security_id, dataset.category).unit is None


@pytest.mark.parametrize("field,value", [("instrument_type", "bad"), ("management_fee", Decimal("-0.01"))])
def test_failed_managed_metadata_update_restores_original_and_outer_work(repo, dataset, field, value):
    metadata = repo.upsert_metadata(SecurityResearchMetadata(security_id=dataset.security_id, instrument_type="etf", management_fee=Decimal("0.001")))
    repo.upsert_source(DataSource(source_key="outer", name="Outer"), commit=False)
    setattr(metadata, field, value)
    with pytest.raises(ValueError):
        repo.upsert_metadata(metadata, commit=False)
    assert repo.get_source("outer") is not None
    original = repo.get_metadata(dataset.security_id)
    assert original.instrument_type == "etf"
    assert original.management_fee == Decimal("0.001")
    repo.session.commit()


def test_managed_issue_validation_does_not_autoflush_invalid_dataset(repo, dataset):
    run = repo.record_run(IngestionRun(dataset_id=dataset.id, source_id=dataset.source_id))
    issue = repo.record_quality_issue(DataQualityIssue(dataset_id=dataset.id, run_id=run.id, code="missing", severity="error", message="Missing"))
    repo.upsert_source(DataSource(source_key="outer", name="Outer"), commit=False)
    issue.run_id = 999
    with pytest.raises(IntegrityError):
        repo.record_quality_issue(issue, commit=False)
    assert repo.get_source("outer") is not None
    assert repo.session.get(DataQualityIssue, issue.id).run_id == run.id
    repo.session.commit()
