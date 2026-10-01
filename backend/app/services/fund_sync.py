"""Explicit ETF/LOF acquisition using source-owned adapters and shared savepoints."""
from app.db.models.data_management import FundNavObservation, SecurityResearchMetadata
from app.db.models.timestamps import utc_now
from app.services.data_ingestion import DataIngestionRecorder
from app.services.providers.fetch_provenance import safe_error_code


class FundSyncService:
    def __init__(self, session, repository, policy, nav_source, profile_source):
        self.session, self.repository, self.policy = session, repository, policy
        self.nav_source, self.profile_source = nav_source, profile_source
        self.recorder = DataIngestionRecorder(repository)

    def sync(self, security, category, *, manual=False):
        alias = 'eastmoney_' + category
        if not self.policy.effective_enabled('eastmoney', alias):
            return dict(outcome='disabled', received=0, written=0)
        fetch, persisted = None, []
        started = utc_now()
        finished = started
        issues = []
        try:
            fetch = (self.nav_source if category == 'fund_nav' else self.profile_source).fetch(security.code, security.market)
            finished = utc_now()
            if any(a.state == 'failed' for a in fetch.attempts):
                outcome = 'failed_fetch'
                error = next((a.error_code for a in fetch.attempts if a.state == 'failed'), 'provider_unavailable')
            elif (not fetch.items if category == 'fund_nav' else fetch.item is None):
                outcome, error = 'empty', None
            else:
                issues.extend(getattr(fetch,'quality_issues',()))
                if category == 'fund_nav':
                    if fetch.truncated:
                        issues.append('truncated_nav_coverage')
                    if fetch.truncated is None:
                        issues.append('nav_coverage_unknown')
                else:
                    # A successful unresolved profile supersedes lookup hints too,
                    # even before the first provider metadata row exists.
                    if not manual and fetch.item.instrument_type == 'unknown':
                        issues.append('fund_classification_unresolved')
                    if any(getattr(fetch.item,f) is None for f in ('manager','management_fee','custody_fee','fund_assets','assets_as_of','benchmark_name')):
                        issues.append('missing_profile_fields')
                outcome, error = ('partial' if issues else 'succeeded'), None
                connection = self.session.connection()
                if connection.dialect.name == 'sqlite' and not connection.connection.driver_connection.in_transaction:
                    connection.exec_driver_sql('BEGIN')
                try:
                    with self.session.begin_nested():
                        source = self.recorder.source(fetch.source_key)
                        if category == 'fund_nav':
                            persisted = [self.repository.upsert_nav(FundNavObservation(security_id=security.id,source_id=source.id,
                                nav_date=row.nav_date,nav_kind=row.nav_kind,value=row.value,published_at=row.published_at,fetched_at=finished),commit=False) for row in fetch.items]
                        else:
                            metadata = self.repository.get_metadata(security.id)
                            values = metadata.model_dump(exclude={'id'})
                            for field in ('manager','management_fee','custody_fee','benchmark_code','benchmark_name'):
                                if manual and field in {'benchmark_code','benchmark_name'}:
                                    continue
                                value = getattr(fetch.item,field)
                                if value is not None:
                                    values[field] = value
                            if fetch.item.fund_assets is not None:
                                values['fund_assets'] = fetch.item.fund_assets
                                values['assets_as_of'] = fetch.item.assets_as_of
                            if not manual:
                                # A missing/unknown refresh cannot downgrade a previously
                                # corroborated type; manual unknown is also never inferred.
                                if fetch.item.instrument_type != 'unknown':
                                    values['instrument_type'] = fetch.item.instrument_type
                                values['source_id'] = source.id
                            persisted = [self.repository.upsert_metadata(SecurityResearchMetadata(**values),commit=False)]
                        self.recorder.record(security.id, category, outcome=outcome, fetch=fetch,persisted=persisted,
                            fetched_at=finished,issues=tuple(issues),started_at=started,finished_at=finished)
                except Exception as exc:
                    persisted = []
                    outcome, error = 'failed_persist', safe_error_code(exc)
        except Exception as exc:
            outcome, error = 'failed_fetch', safe_error_code(exc)
            finished = utc_now()
        if not persisted:
            try:
                self.recorder.record(security.id,category,outcome=outcome,fetch=fetch,issues=tuple(issues),error_code=error,started_at=started,finished_at=finished)
            except Exception:
                self.session.rollback()
                return dict(outcome='failed_persist', received=getattr(fetch,'received_count',0),written=0)
        try:
            self.session.commit()
        except Exception:
            self.session.rollback()
            return dict(outcome='failed_persist', received=getattr(fetch,'received_count',0),written=0)
        return dict(outcome=outcome,received=getattr(fetch,'received_count',0),written=len(persisted),
                    received_count_unit='raw_nav_date_records' if category=='fund_nav' else 'profile_records',
                    written_count_unit='nav_kind_observations' if category=='fund_nav' else 'metadata_records',
                    resolved_instrument_type=fetch.item.instrument_type if category=='fund_profile' and fetch and fetch.item else None)
