"""Catalog-backed source settings and bounded acquisition facts; no network access."""
from copy import copy
from datetime import UTC

from sqlalchemy import and_, or_
from sqlmodel import select

from app.db.models.data_management import DataSource, IngestionRun, SecurityDataset
from app.services.data_sources.registry import get_source_module, list_source_modules
from app.services.providers.fetch_provenance import SAFE_ERRORS


class SourceWriteError(Exception):
    pass


class DataSourceManagementService:
    def __init__(self, session):
        self.session = session

    def enabled(self, key):
        source = self.session.exec(select(DataSource).where(DataSource.source_key == key)).first()
        return source.enabled if source else True

    def effective_enabled(self, vendor_key, provider_key):
        return self.enabled(vendor_key) and self.enabled(provider_key)

    def detail(self, vendor_key, limit=20):
        module = get_source_module(vendor_key)
        categories = sorted({e.category for e in module.endpoints if e.integration_scope == 'managed_security'})
        pairs = {(e.key, e.category) for e in module.endpoints}
        query = (select(IngestionRun, DataSource, SecurityDataset)
                 .join(DataSource, DataSource.id == IngestionRun.source_id)
                 .join(SecurityDataset, SecurityDataset.id == IngestionRun.dataset_id)
                 .where(or_(*(and_(DataSource.source_key == key, SecurityDataset.category == category) for key, category in pairs))))
        ordered = query.order_by(IngestionRun.started_at.desc(), IngestionRun.id.desc())
        recent = [self._attempt(*row) for row in self.session.exec(ordered.limit(limit)).all()]
        successful = self.session.exec(ordered.where(IngestionRun.status == 'succeeded').limit(1)).first()
        return dict(vendor_key=module.key, name=module.name, enabled=self.enabled(module.key),
                    configurable=bool(categories), managed_categories=categories,
                    endpoints=[e.to_dict() for e in module.endpoints],
                    scope_note='Controls apply only to managed_security endpoints; homepage/lookup are untracked and planned endpoints are not integrated.',
                    runtime=dict(state='unknown' if not recent else 'failed' if recent[0]['state'] == 'failed' else 'attempted',
                                 recent_attempts=recent, latest_attempt=recent[0] if recent else None,
                                 last_succeeded_attempt=self._attempt(*successful) if successful else None))

    @staticmethod
    def _attempt(run, source, dataset):
        def utc(value):
            return (value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)) if value else None
        return dict(id=run.id, provider_key=source.source_key, security_id=dataset.security_id,
                    category=dataset.category, status=run.status,
                    state='empty' if run.status == 'succeeded' and run.records_received == 0 else run.status,
                    started_at=utc(run.started_at), finished_at=utc(run.finished_at),
                    records_received=run.records_received, records_written=run.records_written,
                    records_rejected=run.records_rejected,
                    error_code=run.error_message if run.error_message in SAFE_ERRORS else 'ingestion_error' if run.error_message else None,
                    persisted_coverage='attributed_write' if run.records_written else 'unknown',
                    write_attribution='selected_source' if run.records_written else 'unknown')

    def update(self, vendor_key, enabled):
        module = get_source_module(vendor_key)
        if not any(e.integration_scope == 'managed_security' for e in module.endpoints):
            raise ValueError('source is not configurable')
        try:
            source = self.session.exec(select(DataSource).where(DataSource.source_key == vendor_key)).first()
            if source is None:
                source = DataSource(source_key=vendor_key, name=module.name, access_mode='public', enabled=enabled)
            else:
                source.enabled = enabled
            self.session.add(source)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise SourceWriteError('source settings could not be saved') from None
        return self.detail(vendor_key)

    def apply_policy(self, provider, category, *, preferred_source=None):
        """Clone adapter lists; anonymous/custom providers retain compatibility.

        Optional known history preference is applied only to a known enabled source.
        Factory ordering remains unchanged when no preference is supplied.
        """
        if provider is None or not hasattr(provider, 'raw_sources'):
            return provider, False
        owners = {e.key: m.key for m in list_source_modules() for e in m.endpoints
                  if e.category == category and e.integration_scope == 'managed_security'}
        raw = [copy(a) for a in provider.raw_sources if a.name not in owners or self.effective_enabled(owners[a.name], a.name)]
        legacy = [copy(a) for a in getattr(provider, 'sources', []) if a.name not in owners or self.effective_enabled(owners[a.name], a.name)]
        if preferred_source in owners:
            raw.sort(key=lambda a: a.name != preferred_source)
        clone = copy(provider)
        clone.raw_sources = raw
        if hasattr(provider, 'sources'):
            clone.sources = legacy
        disabled = not raw and not legacy
        return clone, disabled
