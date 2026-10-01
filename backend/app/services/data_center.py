"""Read-only data health and narrowly scoped manual security metadata."""
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from sqlmodel import select

from app.db.models import Security
from app.db.models.data_management import DataSource, SecurityDataset, IngestionRun, DataQualityIssue, FundNavObservation
from app.db.repositories.data_management_repository import DataManagementRepository
from app.services.data_source_management import DataSourceManagementService, SourceWriteError

CATEGORIES = ('announcements','news','price_history','quote_snapshot','financial_metrics','company_profile','fund_nav','fund_profile')
# Only exact positive lookup labels are recognized. Arbitrary manual industry text
# and names/code prefixes are not an instrument classifier.
LOOKUP_TYPES = {'ETF':'etf', 'LOF':'lof', 'ETF基金':'etf', 'LOF基金':'lof', '指数':'index', 'A股':'stock', '沪A':'stock', '深A':'stock'}


def utc(value):
    return (value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)) if value else None


def serial(values):
    return {k: format(v,'f') if isinstance(v, Decimal) else utc(v) if isinstance(v, datetime) else v for k,v in values.items()}


class SecurityDataCenterService:
    def __init__(self, session):
        self.session = session
        self.repository = DataManagementRepository(session)

    def security(self, security_id):
        row = self.session.get(Security, security_id)
        if row is None:
            raise KeyError('security not found')
        return row

    def classification(self, security):
        metadata = self.repository.get_metadata(security.id)
        source = self.session.get(DataSource, metadata.source_id) if metadata.source_id else None
        if source and source.source_key == 'manual':
            return metadata.instrument_type, 'manual', True
        profile = self.repository.get_dataset(security.id, 'fund_profile')
        if profile:
            unresolved = self.session.exec(select(DataQualityIssue.id).where(DataQualityIssue.dataset_id == profile.id, DataQualityIssue.code == 'fund_classification_unresolved', DataQualityIssue.resolved_at.is_(None)).limit(1)).first()
            if unresolved is not None:
                return 'unknown', 'fund_profile_unresolved', False
        if metadata.instrument_type != 'unknown':
            return metadata.instrument_type, 'fund_profile', False
        kind = LOOKUP_TYPES.get((security.industry or '').strip(), 'unknown')
        return kind, 'exact_security_type_label' if kind != 'unknown' else 'unresolved', False

    def detail(self, security_id, limit=20):
        security = self.security(security_id)
        metadata = self.repository.get_metadata(security_id)
        kind, origin, manual = self.classification(security)
        source = self.session.get(DataSource, metadata.source_id) if metadata.source_id else None
        categories = {}
        for category in CATEGORIES:
            key = category
            dataset = self.repository.get_dataset(security_id, key)
            applicable = not (kind in {'etf','lof','index','unknown'} and category in {'announcements','financial_metrics','company_profile'})
            if category in {'fund_nav','fund_profile'}:
                applicable = kind in {'etf','lof'} or (category == 'fund_profile' and (security.industry == '基金' or origin == 'fund_profile_unresolved') and not manual)
            categories[category] = self._dataset(dataset, applicable, limit, instrument_type=kind)
        nav = self.session.exec(select(FundNavObservation, DataSource).join(DataSource, DataSource.id == FundNavObservation.source_id)
            .where(FundNavObservation.security_id == security_id).order_by(FundNavObservation.nav_date.desc(), FundNavObservation.id.desc()).limit(100)).all()
        return dict(security=serial(security.model_dump()), metadata=dict(**serial(metadata.model_dump(exclude={'id','security_id'})),
            source_key=source.source_key if source else None, overlay_scope=['instrument_type','benchmark_code','benchmark_name'] if manual else [],
            effective_instrument_type=kind, classification_origin=origin,
            provider_fields_source=categories['fund_profile']['source_key'], publication_at=None,
            provenance_note='Manual source applies only to classification and benchmark. Provider fees, assets and manager use fund_profile provenance.'),
            categories=categories, nav_observations=[dict(**serial(row.model_dump(exclude={'id','security_id','source_id'})), source_key=s.source_key) for row,s in nav],
            nav_limit=100, calendar=dict(verified=False, note='No verified exchange/fund calendar; freshness is an elapsed-time estimate, not a latest-session guarantee.'))

    def _dataset(self, dataset, applicable, limit, *, instrument_type=None):
        base = dict(health='unknown' if applicable else 'not_applicable', source_key=None, unit=None, frequency=None,
                    price_basis='unknown', observation_at=None, fetched_at=None, coverage_start=None, coverage_end=None,
                    recent_attempts=[], unresolved_issues=[], latest_attempt=None, freshness='unknown',
                    coverage='unknown', context_disclosures=[], unit_provenance='persisted_acquisition_metadata_or_unknown', observation_precision='unknown', observation_time_note='Source observation clock unavailable', freshness_threshold_days=None, freshness_basis='estimated_elapsed_time_no_calendar')
        if dataset is None:
            return base
        source = self.session.get(DataSource, dataset.source_id) if dataset.source_id else None
        attempts = self.session.exec(select(IngestionRun, DataSource).join(DataSource, DataSource.id == IngestionRun.source_id)
            .where(IngestionRun.dataset_id == dataset.id).order_by(IngestionRun.started_at.desc(), IngestionRun.id.desc()).limit(limit)).all()
        recent = [DataSourceManagementService._attempt(run,s,dataset) for run,s in attempts]
        issues = self.session.exec(select(DataQualityIssue).where(DataQualityIssue.dataset_id == dataset.id,
            DataQualityIssue.resolved_at.is_(None)).order_by(DataQualityIssue.created_at.desc(), DataQualityIssue.id.desc()).limit(limit)).all()
        base.update(serial(dataset.model_dump(exclude={'id','security_id','category','source_id'})))
        base.update(observation_precision='date' if dataset.category in {'price_history','fund_nav'} and dataset.observation_at else 'datetime' if dataset.observation_at else 'unknown', observation_time_note='Date represented at UTC midnight; not a publication clock' if dataset.category in {'price_history','fund_nav'} else 'Source publication timezone may be unverified; see vendor contract' if dataset.category in {'news','announcements'} else 'Source observation clock unavailable' if not dataset.observation_at else 'Source observation clock normalized to UTC')
        base.update(source_key=source.source_key if source else None, recent_attempts=recent, latest_attempt=recent[0] if recent else None,
                    unresolved_issues=[serial(i.model_dump(exclude={'dataset_id'})) for i in issues])
        thresholds = {'quote_snapshot':3, 'price_history':7, 'fund_nav':7, 'financial_metrics':180, 'fund_profile':180, 'company_profile':365, 'news':30, 'announcements':90}
        successful = self.session.exec(select(IngestionRun.id).where(IngestionRun.dataset_id == dataset.id, IngestionRun.status.in_(['succeeded','partial']), IngestionRun.records_written > 0).limit(1)).first()
        if dataset.fetched_at and source and successful:
            days = thresholds.get(dataset.category,30)
            # Date-bearing series use real observation dates; undated profile uses
            # acquisition age only and discloses observation unknown.
            reference = utc(dataset.observation_at) or utc(dataset.fetched_at)
            stale = datetime.now(UTC) - reference > timedelta(days=days)
            base.update(freshness='stale' if stale else 'within_estimated_threshold', freshness_threshold_days=days,
                        health='stale' if stale else 'healthy', coverage='bounded_observed_range' if dataset.coverage_start else 'unknown')
            partial_issue = self.session.exec(select(DataQualityIssue.id).where(DataQualityIssue.dataset_id == dataset.id, DataQualityIssue.resolved_at.is_(None), DataQualityIssue.code.not_in(['failed_fetch','failed_persist'])).limit(1)).first()
            if partial_issue is not None:
                base['health'] = 'partial'
        elif not dataset.fetched_at and recent and recent[0]['status'] == 'failed':
            base['health'] = 'failed'
        if not applicable:
            base['health'] = 'not_applicable'
        if instrument_type == 'index' and dataset.category in {'price_history','quote_snapshot'}:
            from app.services.data_sources.registry import normalized_context_unit
            context_unit = normalized_context_unit(source.source_key if source else None, dataset.category, 'index')
            if dataset.unit != 'index_points' or context_unit is None:
                base['unit'] = None
                base['unit_provenance'] = 'unverified_index_context'
                base['context_disclosures'].append('Retained unit is not verified for resolved index context; local records are unchanged')
                if base['health'] == 'healthy':
                    base['health'] = 'partial'
            else:
                base['unit_provenance'] = 'source_owned_contract_and_resolved_index_classification'
            base['price_basis'] = 'unknown'
            base['context_disclosures'].append('Index corporate adjustment and component-volume comparability are unverified')
        if dataset.category == 'fund_nav':
            base.update(valuation_basis='official_nav', received_count_unit='raw_nav_date_records', written_count_unit='nav_kind_observations', publication_at=None)
        return base

    def update_metadata(self, security_id, body):
        security = self.security(security_id)
        try:
            metadata = self.repository.get_metadata(security_id)
            values = metadata.model_dump(exclude={'id'})
            effective_type, _, already_manual = self.classification(security)
            if not already_manual and 'instrument_type' not in body.model_fields_set:
                # The first benchmark-only overlay records today's effective
                # classification, not an older provider type retained for history.
                values['instrument_type'] = effective_type
            values.update(body.model_dump(exclude_unset=True))
            values['source_id'] = self.repository.upsert_source(DataSource(source_key='manual',name='Manual overlay',access_mode='manual'),commit=False).id
            self.repository.upsert_metadata(type(metadata)(**values),commit=False)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise SourceWriteError('security metadata could not be saved') from None
        return self.detail(security_id)
