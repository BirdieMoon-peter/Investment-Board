import app.services.research_service as service_module
from app.services.providers.research_provider import ResearchProviderError


def test_project_api_version_archive_history_and_no_credentials(client,seeded_security,monkeypatch):
    def forbidden(): raise AssertionError('credential/provider access')
    monkeypatch.setattr(service_module,'build_configured_provider',forbidden)
    body=dict(security_id=seeded_security.id,question='Why?')
    response=client.post('/api/research/projects',json=body); assert response.status_code==201
    p=response.json(); base=f"/api/research/projects/{p['id']}"
    assert client.get(base).json()['question']=='Why?'
    assert client.get('/api/research/projects').status_code==200
    assert client.get(base+'/runs').json()==[]
    assert client.get(base+'/events').json()==[]
    assert client.post(base+'/check').json()['status']=='no_completed_run'
    assert client.put(base,json={'expected_version':1,'question':'New'}).json()['version']==2
    assert client.put(base,json={'expected_version':1,'question':'Stale'}).status_code==409
    assert client.post(base+'/archive',json={'expected_version':2}).json()['status']=='archived'
    assert client.post(base+'/runs',json={}).status_code==422
    assert client.get('/api/research/projects/9999').status_code==404
    assert client.post('/api/research/projects',json={'security_id':9999,'question':'x'}).status_code==404
    assert client.post('/api/research/projects',json={**body,'question':'x'*2001}).status_code==422


def test_failure_saved_safe_and_saved_run_read(client,seeded_security,monkeypatch):
    def unavailable(): raise ResearchProviderError('not_configured')
    monkeypatch.setattr(service_module,'build_configured_provider',unavailable)
    p=client.post('/api/research/projects',json={'security_id':seeded_security.id,'question':'Why?'}).json(); base=f"/api/research/projects/{p['id']}"
    response=client.post(base+'/runs',json={}); assert response.status_code==201
    run=response.json(); assert run['status']=='failed' and run['error_code']=='not_configured'
    assert run['output'] is None and run['input_snapshot']['security']['id']==seeded_security.id
    assert client.get(base+f"/runs/{run['id']}").json()==run
    assert client.get(base+'/runs').json()[0]==run


def test_generation_events_resolve_and_saved_snapshot_independent_of_changes(client,seeded_security,monkeypatch):
    class Fake:
        model_name='synthetic'
        def generate(self,snapshot): return dict(executive_summary='Synthetic',claims=[],risks=[],data_gaps=[],invalidation_conditions=[],next_checks=[])
    monkeypatch.setattr(service_module,'build_configured_provider',lambda:Fake())
    p=client.post('/api/research/projects',json={'security_id':seeded_security.id,'question':'Why?'}).json();base=f"/api/research/projects/{p['id']}"
    old=client.post(base+'/runs',json={}).json()
    client.put(base,json={'expected_version':1,'question':'Different'})
    check=client.post(base+'/check').json(); event=check['events'][0]
    assert event['details']['changed_fields'][0]['previous']=='Why?'
    resolved=client.post(f"/api/research/events/{event['id']}/resolve").json()
    assert resolved['status']=='resolved' and resolved['resolved_at']
    assert client.get(base+f"/runs/{old['id']}").json()==old
    assert client.get(base+'/events').json()[0]['status']=='resolved'
    assert client.post('/api/research/events/99999/resolve').status_code==404
