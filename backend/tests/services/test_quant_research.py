from copy import deepcopy
from app.services.quant.service import QuantService
from app.services.quant.research import generate
from app.services.providers.research_provider import ResearchProviderError


def output():
    return {'executive_summary':'Synthetic inference','claims':[],'risks':['Unknown actions'],'data_gaps':[],'invalidation_conditions':[],'next_checks':[]}


class MockProvider:
    model_name='synthetic-mock-only'
    def __init__(self,body=None):self.body=body or output();self.calls=[];self.snapshot=None
    def generate(self,snapshot):
        self.calls.append('generate');self.snapshot=deepcopy(snapshot);snapshot['scope']='mutated'
        return deepcopy(self.body)
    def critique(self,snapshot,body):
        self.calls.append('critique');raise RuntimeError('secret response must not leak')


def run(service,data,strategy,costs):
    d=service.import_dataset(data);s=service.create_strategy(strategy)
    return service.create_run({'strategy_id':s.id,'dataset_id':d.id,'initial_cash':'10000','costs':costs})


def test_frozen_experiment_only_no_holdings_and_optional_failure(session,quant_dataset,quant_strategy,quant_costs):
    provider=MockProvider();service=QuantService(session,provider_factory=lambda:provider)
    r=run(service,quant_dataset,quant_strategy,quant_costs)
    annotation=service.repo.decode(generate(service,r.id,critique=True))
    assert annotation['status']=='completed' and provider.calls==['generate','critique']
    assert annotation['input_snapshot']['scope']=='frozen_experiment_only_no_actual_holdings'
    assert 'holdings' not in provider.snapshot and 'api_key' not in str(provider.snapshot)
    assert annotation['model_review']['status']=='unavailable'
    service.provider_factory=lambda:(_ for _ in ()).throw(AssertionError('GET must not call provider'))
    assert service.repo.require(type(r),r.id).payload_json==r.payload_json
    assert len(service.repo.annotations(r.id))==1


def test_strict_references_and_numeric_diagnostics(session,quant_dataset,quant_strategy,quant_costs):
    service=QuantService(session);r=run(service,quant_dataset,quant_strategy,quant_costs)
    body=output();body['claims']=[{'kind':'fact','statement':'Unsupported','evidence_ids':['foreign'],'counter_evidence_ids':[],'metric_refs':[]}]
    service.provider_factory=lambda:MockProvider(body)
    assert service.repo.decode(generate(service,r.id))['error_code']=='invalid_references'
    body['claims'][0]['evidence_ids']=[f'experiment:{r.id}'];body['claims'][0]['metric_refs']=[{'metric_key':'full.net_return','reported_value':'999'}]
    result=service.repo.decode(generate(service,r.id))
    assert result['status']=='completed' and result['diagnostics'][0]['numeric_check']=='mismatch'
    assert result['diagnostics'][0]['semantic_support']=='not_assessed'


def test_frozen_metrics_preserve_cash_count_and_ratio_units(session,quant_dataset,quant_strategy,quant_costs):
    from app.services.quant.research import frozen_snapshot
    service=QuantService(session);r=run(service,quant_dataset,quant_strategy,quant_costs)
    metrics={m['key']:m for m in frozen_snapshot(r)['metrics']}
    assert metrics['full.fees_paid']['unit']=='CNY'
    assert metrics['full.end_nav']['unit']=='CNY'
    assert metrics['full.sample_count']['unit']=='count'
    assert metrics['full.net_return']['unit']=='ratio'
