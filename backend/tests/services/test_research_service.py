import copy
import pytest
from app.db.repositories.research_repository import ResearchRepository,json_object
from app.services.research_service import ResearchService,audit
from app.services.providers.research_provider import ResearchProviderError


def output():
    return dict(executive_summary='Uncertain',claims=[],risks=['risk'],data_gaps=['gap'],invalidation_conditions=[],next_checks=['check'])


class Fake:
    model_name='synthetic-model'
    def __init__(self,body=None,fail=False): self.calls=[]; self.body=body or output(); self.fail=fail
    def generate(self,snapshot):
        self.calls.append('generate')
        snapshot['security']['name']='provider mutation'
        if self.fail: raise ResearchProviderError('timeout')
        return copy.deepcopy(self.body)
    def critique(self,snapshot,primary):
        self.calls.append('critique')
        raise RuntimeError('secret provider body')


def project(session,security):
    return ResearchRepository(session).create_project(security_id=security.id,question='Question')


def test_frozen_primary_critique_failure_and_history(session,seeded_security):
    p=project(session,seeded_security); fake=Fake(); service=ResearchService(session,provider_factory=lambda:fake)
    run=service.generate(p.id,critique=True)
    assert run.status=='completed' and fake.calls==['generate','critique']
    assert json_object(run.input_snapshot_json)['security']['name']==seeded_security.name
    assert json_object(run.output_json)['model_review']['status']=='unavailable'
    assert run.model_name=='synthetic-model'
    failed=ResearchService(session,provider_factory=lambda:Fake(fail=True)).generate(p.id)
    assert failed.error_code=='timeout' and failed.output_json is None
    assert service.repo.get_run(run.id).output_json==run.output_json


def test_checks_no_provider_dedup_and_archived(session,seeded_security):
    p=project(session,seeded_security); service=ResearchService(session,provider_factory=lambda:Fake())
    run=service.generate(p.id)
    def forbidden(): raise AssertionError('must not create provider')
    service.provider_factory=forbidden
    assert service.check(p.id)['status']=='unchanged'
    service.repo.update_project(p.id,expected_version=1,question='changed')
    first=service.check(p.id); second=service.check(p.id)
    assert first['status']=='needs_review' and first['events'][0].id==second['events'][0].id
    assert service.repo.get_run(run.id).project_version==1
    service.repo.archive_project(p.id,expected_version=2)
    with pytest.raises(ValueError): service.generate(p.id)


def test_deterministic_audit_separates_numeric_and_semantics():
    snap=dict(ledger=[dict(evidence_id='e_title',title_only=True)],metrics=[dict(key='return',value='0.1',status='ready')])
    body=output(); body['claims']=[dict(kind='fact',statement='Revenue rose 30%',evidence_ids=['e_title'],counter_evidence_ids=[],metric_refs=[]),dict(kind='inference',statement='Higher',evidence_ids=[],counter_evidence_ids=[],metric_refs=[dict(metric_key='return',reported_value='0.2')])]
    diag=audit(snap,body)
    assert diag[0]['codes']==['title_only_numeric_fact_unsupported']
    assert diag[1]['numeric_check']=='mismatch' and diag[1]['semantic_support']=='not_assessed'
    body['claims'][0]['evidence_ids']=['foreign']
    with pytest.raises(ResearchProviderError): audit(snap,body)


def test_conditions_finite_known_ready_only(session,seeded_security):
    p=project(session,seeded_security)
    body=output(); body['invalidation_conditions']=[dict(description='ready',metric_key='m',operator='gt',threshold='1'),dict(description='malformed',metric_key='m',operator='gt',threshold='NaN'),dict(description='unknown',metric_key='unknown',operator='eq',threshold='1'),dict(description='qualitative',metric_key=None,operator=None,threshold=None)]
    class Builder:
        def build(self,p):
            from app.services.research_evidence import canonical,digest
            snap=dict(security={'name':'synthetic'},as_of_snapshot='2026-10-01',ledger=[],metrics=[dict(key='m',status='ready',value='2',as_of='2026-09-30')])
            return dict(snapshot=snap,input_snapshot_json=canonical(snap),input_fingerprint=digest(snap))
    service=ResearchService(session,provider_factory=lambda:Fake(body),evidence_builder=Builder()); service.generate(p.id)
    check=service.check(p.id)
    assert [c['status'] for c in check['conditions']]==['triggered','uncheckable','uncheckable','uncheckable']
    assert check['events'][0].reason_code=='condition_triggered'


def test_generation_rejects_refs_and_does_not_replace_success(session,seeded_security):
    p=project(session,seeded_security); service=ResearchService(session,provider_factory=lambda:Fake())
    success=service.generate(p.id)
    body=output();body['claims']=[dict(kind='fact',statement='fake',evidence_ids=['foreign'],counter_evidence_ids=[],metric_refs=[])]
    service.provider_factory=lambda:Fake(body)
    failed=service.generate(p.id)
    assert failed.status=='failed' and failed.error_code=='invalid_references'
    assert service.repo.latest_completed_run(p.id).id==success.id


def test_project_version_frozen_before_provider(session,seeded_security):
    p=project(session,seeded_security)
    class EditingFake(Fake):
        def generate(self,snapshot):
            ResearchRepository(session).update_project(p.id,expected_version=1,question='revised while generating')
            return output()
    run=ResearchService(session,provider_factory=lambda:EditingFake()).generate(p.id)
    assert run.project_version==1 and json_object(run.input_snapshot_json)['project']['version']==1


def test_readable_changes_and_missing_ready_metric_event(session,seeded_security):
    p=project(session,seeded_security)
    class Builder:
        value='2'
        def build(self,p):
            from app.services.research_evidence import canonical,digest
            snap=dict(security={'name':'synthetic'},as_of_snapshot='2026-10-01',ledger=[],metrics=[dict(key='m',status='ready' if self.value else 'unavailable',value=self.value,as_of='2026-09-30')])
            return dict(snapshot=snap,input_snapshot_json=canonical(snap),input_fingerprint=digest(snap))
    builder=Builder();service=ResearchService(session,provider_factory=lambda:Fake(),evidence_builder=builder);service.generate(p.id)
    builder.value=None;result=service.check(p.id)
    assert {e.reason_code for e in result['events']}=={'data_changed','data_unavailable'}
    details=json_object(result['events'][0].details_json)
    assert details['changed_fields'][0]['previous']['value']=='2'
    assert details['changed_fields'][0]['current']['value'] is None


def test_optional_critique_success_one_call_each(session,seeded_security):
    p=project(session,seeded_security)
    body=output();body['claims']=[dict(kind='hypothesis',statement='Hypothesis',evidence_ids=[],counter_evidence_ids=[],metric_refs=[])]
    class Reviewer(Fake):
        def critique(self,snapshot,primary):
            self.calls.append('critique')
            primary['executive_summary']='mutated review input'
            return dict(claims=[dict(claim_index=0,support='uncertain',explanation='Need stronger evidence')])
    provider=Reviewer(body);run=ResearchService(session,provider_factory=lambda:provider).generate(p.id,critique=True)
    saved=json_object(run.output_json)
    assert provider.calls==['generate','critique']
    assert saved['research']['executive_summary']=='Uncertain'
    assert saved['model_review']['status']=='available' and saved['model_review']['label']=='model_review_not_verification'


def test_metadata_changes_include_values_and_relevant_observation_dates(session,seeded_security):
    from datetime import date
    from decimal import Decimal
    from app.db.models.data_management import SecurityResearchMetadata
    metadata=SecurityResearchMetadata(security_id=seeded_security.id,instrument_type='etf',manager='Old manager',fund_assets=Decimal('100'),as_of=date(2026,9,1),assets_as_of=date(2026,8,31))
    session.add(metadata);session.commit()
    p=project(session,seeded_security);service=ResearchService(session,provider_factory=lambda:Fake())
    saved=service.generate(p.id)
    assert saved.status=='completed'
    metadata.manager='New manager';metadata.fund_assets=Decimal('200');metadata.as_of=date(2026,10,1);metadata.assets_as_of=date(2026,9,30)
    session.add(metadata);session.commit()
    result=service.check(p.id)
    assert result['changed'] is True
    fields={c['field']:c for c in json_object(result['events'][0].details_json)['changed_fields'] if c['kind']=='metadata'}
    assert fields['manager']['previous']=={'value':'Old manager','observed_at':'2026-09-01'}
    assert fields['manager']['current']=={'value':'New manager','observed_at':'2026-10-01'}
    assert fields['fund_assets']['previous']=={'value':'100','observed_at':'2026-08-31'}
    assert fields['fund_assets']['current']=={'value':'200','observed_at':'2026-09-30'}
    assert json_object(saved.input_snapshot_json)['metadata']['manager']=='Old manager'
