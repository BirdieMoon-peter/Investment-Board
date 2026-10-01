"""Record attempts separately from the last successfully persisted dataset snapshot."""
from datetime import UTC, datetime, time
from typing import Any

from sqlmodel import select

from app.db.models import FinancialMetrics

from app.db.models.data_management import DataQualityIssue, DataSource, IngestionRun, SecurityDataset
from app.db.models.timestamps import utc_now
from app.db.repositories.data_management_repository import DataManagementRepository


class DataIngestionRecorder:
    OWNED_ISSUES = frozenset({"failed_fetch", "failed_persist", "partial_fetch", "empty", "skipped", "not_applicable", "mixed_source_write_attribution_unknown", "volume_unit_unknown", "amount_unavailable", "price_basis_unknown", "incomplete_price_refresh", "negative_revenue", "missing_nav_value", "duplicate_nav_date", "truncated_nav_coverage", "nav_coverage_unknown", "missing_profile_fields", "fund_classification_unresolved", "unit_unverified", "index_volume_context_unverified", "index_adjustment_context_unverified"})

    def __init__(self, repository: DataManagementRepository):
        self.repository = repository

    def source(self, key: str):
        existing = self.repository.get_source(key)
        return existing or self.repository.upsert_source(DataSource(source_key=key, name=key,
            access_mode='unknown' if key == 'unknown' else 'internal' if key.startswith('aggregate:') else 'public'), commit=False)

    def record(self, security_id: int, category: str, *, outcome: str, fetch: Any = None,
               persisted: list[Any] = (), fetched_at=None, price_basis=None,
               issues: tuple[str, ...] = (), error_code: str | None = None,
               started_at=None, finished_at=None):
        existing = self.repository.get_dataset(security_id, category)
        values = existing.model_dump(exclude={'id'}) if existing else dict(security_id=security_id, category=category)
        selected = getattr(fetch, 'source_key', None)
        attempts = tuple(getattr(fetch, 'attempts', ()))
        if outcome in {'succeeded', 'partial'} and persisted:
            dates, observations = [], []
            for row in persisted:
                observed = getattr(row, 'snapshot_time', None) or getattr(row, 'published_at', None)
                day = getattr(row, 'trade_date', None) or getattr(row, 'nav_date', None)
                if day:
                    dates.append(day)
                    observed = datetime.combine(day, time(), tzinfo=UTC)
                if observed:
                    observations.append(observed.replace(tzinfo=UTC) if observed.tzinfo is None else observed.astimezone(UTC))
            old_start, old_end = values.get('coverage_start'), values.get('coverage_end')
            values.update(source_id=self.source(selected).id if selected else None,
                          fetched_at=fetched_at or utc_now(),
                          observation_at=max(observations) if observations else None,
                          unit=getattr(fetch, 'unit', None), frequency=getattr(fetch, 'frequency', None),
                          price_basis=price_basis or getattr(fetch, 'price_basis', 'unknown'))
            if dates:
                values['coverage_start'] = min(dates + ([old_start] if old_start else []))
                values['coverage_end'] = max(dates + ([old_end] if old_end else []))
        dataset = self.repository.upsert_dataset(SecurityDataset(**values), commit=False)
        finished = finished_at or utc_now()
        started = started_at or finished
        # Multiple successful financial/news sources have no trustworthy row-to-source
        # mapping after deduplication. Per-source attempts report received counts only;
        # an explicitly internal summary holds actual total written count.
        successes = [a for a in attempts if a.state == 'succeeded']
        attributable = selected is not None
        for attempt in attempts:
            written = len(persisted) if attributable and attempt.source_key == selected and outcome in {'succeeded', 'partial'} else 0
            failed_write = outcome.startswith("failed") and attempt.state == "succeeded"
            status = 'failed' if attempt.state == 'failed' or failed_write else 'succeeded'
            self.repository.record_run(IngestionRun(dataset_id=dataset.id, source_id=self.source(attempt.source_key).id,
                status=status, started_at=attempt.started_at or started, finished_at=attempt.finished_at or finished, records_received=attempt.count,
                records_written=written, records_rejected=attempt.count if attempt.state == "failed" and attempt.error_code == "invalid_data" else 0, error_message=(error_code or 'ingestion_error') if failed_write else attempt.error_code), commit=False)
        received_count = len(fetch) if isinstance(fetch, (list, tuple)) else len(getattr(fetch, "items", ())) if fetch is not None and hasattr(fetch, "items") else int(getattr(fetch, "item", None) is not None)
        if (not attempts or (not attributable and successes)) and outcome not in {"skipped", "not_applicable"}:
            key = 'aggregate:' + category if successes else selected or 'unknown'
            self.repository.record_run(IngestionRun(dataset_id=dataset.id, source_id=self.source(key).id,
                status='failed' if outcome.startswith('failed') else 'partial' if outcome == 'partial' else 'succeeded',
                started_at=started, finished_at=finished,
                records_received=received_count,
                records_written=len(persisted), error_message=error_code if outcome.startswith('failed') else None), commit=False)
        codes = list(issues)
        if category == "financial_metrics" and outcome in {"succeeded", "partial"} and persisted:
            # This warning describes the retained dataset, not just today's subset.
            # Query after the business repository flush within the same savepoint.
            negative = self.repository.session.exec(
                select(FinancialMetrics.id).where(
                    FinancialMetrics.security_id == security_id,
                    FinancialMetrics.revenue < 0,
                ).limit(1)
            ).first()
            codes = [code for code in codes if code != "negative_revenue"]
            if negative is not None:
                codes.append("negative_revenue")
        if outcome == "partial":
            codes.append("partial_fetch")
        if outcome not in {'succeeded', 'partial'}:
            codes.append(outcome)
        if successes and not attributable:
            codes.append('mixed_source_write_attribution_unknown')
        if outcome in {"succeeded", "partial"} and persisted:
            for old_issue in self.repository.list_quality_issues(dataset.id, unresolved_only=True):
                if old_issue.code in self.OWNED_ISSUES and old_issue.code not in codes:
                    old_issue.resolved_at = finished
                    self.repository.session.add(old_issue)
        for code in dict.fromkeys(codes):
            self.repository.record_quality_issue(DataQualityIssue(dataset_id=dataset.id, code=code,
                severity='error' if code.startswith('failed') else 'info' if code in {'empty', 'skipped', 'not_applicable', 'mixed_source_write_attribution_unknown'} else 'warning',
                message=code.replace('_', ' ')), commit=False)
        return dataset
