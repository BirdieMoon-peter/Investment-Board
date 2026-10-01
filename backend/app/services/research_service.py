"""Immutable generations plus deterministic, credential-free rechecks."""
from decimal import Decimal, InvalidOperation
import operator
import re
from app.db.repositories.research_repository import ResearchRepository, json_object
from app.schemas.research import ResearchOutput, CritiqueOutput
from app.services.research_evidence import ResearchEvidenceBuilder,canonical
from app.services.providers.research_provider import ResearchProvider,ResearchProviderError,PROMPT_VERSION


def build_configured_provider():
    # This boundary is reached only by an explicit generation action.
    from app.core.settings import Settings
    from app.core.ai_settings_store import load_effective_ai_settings,AISettingsStoreError
    try:
        settings=load_effective_ai_settings(Settings())
    except AISettingsStoreError:
        raise ResearchProviderError('not_configured') from None
    if not settings.ai_api_key: raise ResearchProviderError('not_configured')
    return ResearchProvider(settings)


def finite_decimal(value):
    if not isinstance(value,str) or len(value)>100: return None
    try:
        number=Decimal(value)
        return number if number.is_finite() else None
    except InvalidOperation: return None


def audit(snapshot,output):
    evidence={e['evidence_id']:e for e in snapshot['ledger']}
    metrics={m['key']:m for m in snapshot['metrics']}
    diagnostics=[]
    for index,claim in enumerate(output['claims']):
        refs=claim['evidence_ids']+claim['counter_evidence_ids']
        if any(ref not in evidence for ref in refs) or any(ref['metric_key'] not in metrics for ref in claim['metric_refs']):
            raise ResearchProviderError('invalid_references')
        codes=[]
        if claim['kind']=='fact' and not claim['evidence_ids'] and not claim['metric_refs']: codes.append('unsupported_fact')
        if claim['kind']=='fact' and re.search(r'\d',claim['statement']) and claim['evidence_ids'] and all(evidence[r]['title_only'] for r in claim['evidence_ids']) and not claim['metric_refs']:
            codes.append('title_only_numeric_fact_unsupported')
        for ref in claim['metric_refs']:
            metric=metrics[ref['metric_key']]
            if metric['status']!='ready': codes.append('metric_unavailable')
            if ref['reported_value'] is not None:
                supplied=finite_decimal(ref['reported_value']); actual=finite_decimal(metric['value'])
                if supplied is None or actual is None or supplied!=actual: codes.append('numeric_mismatch')
        diagnostics.append(dict(claim_index=index,reference_check='passed',numeric_check='mismatch' if 'numeric_mismatch' in codes else 'not_reported' if not any(r['reported_value'] is not None for r in claim['metric_refs']) else 'matched',semantic_support='not_assessed',codes=codes))
    return diagnostics


class ResearchService:
    def __init__(self,session,provider_factory=None,evidence_builder=None):
        self.repo=ResearchRepository(session)
        self.builder=evidence_builder or ResearchEvidenceBuilder(session)
        self.provider_factory=provider_factory or build_configured_provider

    def project(self,project_id,active=False):
        project=self.repo.get_project(project_id)
        if project is None: raise KeyError('project not found')
        if active and project.status!='active': raise ValueError('project archived')
        return project

    def generate(self,project_id,critique=False):
        project=self.project(project_id,active=True)
        frozen=self.builder.build(project)
        project_version=project.version
        model='unavailable'
        try:
            provider=self.provider_factory()
            model=provider.model_name
            # Deserialize the frozen canonical bytes; provider mutation cannot alter history.
            output=ResearchOutput.model_validate(provider.generate(json_object(frozen['input_snapshot_json']))).model_dump(mode='json')
            diagnostics=audit(frozen['snapshot'],output)
            review={'status':'not_requested','label':'model_review_not_verification'}
            if critique:
                try:
                    reviewed=CritiqueOutput.model_validate(provider.critique(json_object(frozen['input_snapshot_json']),json_object(canonical(output)))).model_dump(mode='json')
                    if any(item['claim_index']>=len(output['claims']) for item in reviewed['claims']): raise ValueError('invalid critique index')
                    review={'status':'available','label':'model_review_not_verification',**reviewed}
                except Exception:
                    review={'status':'unavailable','label':'model_review_not_verification','error_code':'review_unavailable'}
            saved=dict(research=output,diagnostics=diagnostics,model_review=review)
            raw=canonical(saved); json_object(raw)
            status='completed'; code=None
        except ResearchProviderError as exc:
            code=exc.code; status='failed'; raw=None
        except Exception:
            code='invalid_output'; status='failed'; raw=None
        return self.repo.append_run(project_id=project.id,project_version=project_version,status=status,
            input_snapshot_json=frozen['input_snapshot_json'],input_fingerprint=frozen['input_fingerprint'],output_json=raw,
            model_name=model,prompt_version=PROMPT_VERSION,error_code=code)

    def check(self,project_id):
        project=self.project(project_id,active=True)
        run=self.repo.latest_completed_run(project_id)
        if run is None: return dict(run_id=None,changed=False,events=[],conditions=[],status='no_completed_run')
        current=self.builder.build(project)
        previous=json_object(run.input_snapshot_json)
        conditions=json_object(run.output_json)['research']['invalidation_conditions']
        metrics={m['key']:m for m in current['snapshot']['metrics']}
        checks=[]; triggered=[]; unavailable=[]
        operations={'lt':operator.lt,'lte':operator.le,'gt':operator.gt,'gte':operator.ge,'eq':operator.eq,'ne':operator.ne}
        for index,condition in enumerate(conditions):
            key=condition.get('metric_key'); metric=metrics.get(key); threshold=finite_decimal(condition.get('threshold')); op=condition.get('operator')
            value=finite_decimal(metric.get('value')) if metric and metric['status']=='ready' else None
            if threshold is None or op not in operations or value is None:
                checks.append(dict(index=index,status='uncheckable',metric_key=key))
                if metric and metric['status']!='ready': unavailable.append(key)
            else:
                hit=operations[op](value,threshold)
                checks.append(dict(index=index,status='triggered' if hit else 'not_triggered',metric_key=key,previous_value=next((m['value'] for m in previous['metrics'] if m['key']==key),None),current_value=metric['value'],as_of=metric['as_of']))
                if hit: triggered.append(index)
        prior_metrics={m['key']:m for m in previous['metrics']}
        unavailable += [k for k,m in metrics.items() if m['status']!='ready' and k in prior_metrics and prior_metrics[k]['status']=='ready']
        changed=current['input_fingerprint']!=run.input_fingerprint
        events=[]
        reasons=[]
        if changed: reasons.append('data_changed')
        if triggered: reasons.append('condition_triggered')
        if unavailable: reasons.append('data_unavailable')
        # A bounded readable delta records factual inputs, not a thesis verdict.
        previous_ledger={e['evidence_id']:e for e in previous['ledger']}
        current_ledger={e['evidence_id']:e for e in current['snapshot']['ledger']}
        changes=[]
        for field in ('question','hypothesis','horizon','version'):
            old=previous.get('project',{}).get(field); new=current['snapshot'].get('project',{}).get(field)
            if old!=new: changes.append(dict(kind='project',field=field,previous=old,current=new))
        previous_metadata=previous.get('metadata',{})
        current_metadata=current['snapshot'].get('metadata',{})
        # Preserve the bounded metadata facts and their actual valuation/observation
        # dates. Acquisition timestamps are not substituted for source dates.
        for field in ('instrument_type','effective_instrument_type','classification_origin',
                      'benchmark_code','benchmark_name','manager','management_fee',
                      'custody_fee','fund_assets','assets_as_of','as_of','source_key',
                      'provider_fields_source','overlay_scope'):
            old=previous_metadata.get(field); new=current_metadata.get(field)
            if old!=new:
                date_field='assets_as_of' if field in {'fund_assets','assets_as_of'} else 'as_of'
                changes.append(dict(kind='metadata',field=field,
                    previous=dict(value=old,observed_at=previous_metadata.get(date_field)),
                    current=dict(value=new,observed_at=current_metadata.get(date_field))))
        for category,health in current['snapshot'].get('context',{}).get('categories',{}).items():
            old_health=previous.get('context',{}).get('categories',{}).get(category,{})
            for field in ('health','unit','price_basis','observation_at','source_key'):
                if old_health.get(field)!=health.get(field):
                    changes.append(dict(kind='data_context',category=category,field=field,previous=old_health.get(field),current=health.get(field)))
        for key,m in metrics.items():
            old=prior_metrics.get(key)
            if old and (old['value'],old['status'],old.get('as_of')) != (m['value'],m['status'],m.get('as_of')):
                changes.append(dict(kind='metric',metric_key=key,previous=dict(value=old['value'],status=old['status'],observed_at=old.get('as_of')),current=dict(value=m['value'],status=m['status'],observed_at=m.get('as_of'))))
        for label,items,other in [('removed',previous_ledger,current_ledger),('added',current_ledger,previous_ledger)]:
            for key,item in items.items():
                if key not in other:
                    changes.append(dict(kind='evidence_'+label,evidence_id=key,evidence_kind=item['kind'],content=item['content'],observed_at=item.get('observed_at'),published_at=item.get('published_at')))
        changes=changes[:30]
        details=canonical(dict(changed_fields=changes,previous_fingerprint=run.input_fingerprint,current_fingerprint=current['input_fingerprint'],previous_as_of=previous['as_of_snapshot'],current_as_of=current['snapshot']['as_of_snapshot'],previous_evidence_ids=[e['evidence_id'] for e in previous['ledger']][:100],current_evidence_ids=[e['evidence_id'] for e in current['snapshot']['ledger']][:100],previous_metrics=previous['metrics'],current_metrics=current['snapshot']['metrics'],conditions=checks,unavailable_metrics=sorted(set(unavailable)),interpretation='needs_review_not_thesis_disproved'))
        for reason in reasons:
            events.append(self.repo.record_event(project_id=project.id,run_id=run.id,input_fingerprint=current['input_fingerprint'],reason_code=reason,details_json=details,commit=False))
        if events:
            self.repo.session.commit()
            for event in events: self.repo.session.refresh(event)
        return dict(run_id=run.id,changed=changed,events=events,conditions=checks,status='needs_review' if events else 'unchanged')
