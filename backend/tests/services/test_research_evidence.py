from app.services.research_evidence import ResearchEvidenceBuilder
from app.db.repositories.research_repository import ResearchRepository


def test_stable_fingerprint_and_scope(session, seeded_security):
    project=ResearchRepository(session).create_project(security_id=seeded_security.id,question='Why?')
    builder=ResearchEvidenceBuilder(session)
    first=builder.build(project); second=builder.build(project)
    assert first['input_fingerprint']==second['input_fingerprint']
    assert 'holdings' not in first['snapshot']
    assert first['snapshot']['metrics']


def test_bounded_documents_publication_and_title_boundary(session,seeded_security):
    from datetime import UTC,datetime,timedelta
    from app.db.models import NewsItem,Security,PriceHistory,FinancialMetrics
    from decimal import Decimal
    now=datetime(2026,9,1,tzinfo=UTC)
    other=Security(market='SH',code='600001',name='foreign');session.add(other);session.flush()
    for i in range(25):
        session.add(NewsItem(security_id=seeded_security.id,title=f'title {i}',source='synthetic',url='https://example.test',published_at=now+timedelta(days=i),summary='x'*5000 if i else None))
    session.add(NewsItem(security_id=other.id,title='foreign secret',published_at=now))
    for i in range(35):
        session.add(PriceHistory(security_id=seeded_security.id,trade_date=(now+timedelta(days=i)).date(),open_price=Decimal(1),high_price=Decimal(1),low_price=Decimal(1),close_price=Decimal(1),volume=Decimal(1),amount=Decimal(1)))
    for i in range(14): session.add(FinancialMetrics(security_id=seeded_security.id,report_period=f'{2020+i}-Q1',revenue=Decimal(100)))
    session.commit()
    p=ResearchRepository(session).create_project(security_id=seeded_security.id,question='x');snapshot=ResearchEvidenceBuilder(session).build(p)['snapshot']
    docs=[e for e in snapshot['ledger'] if e['kind']=='document']
    assert len(docs)==20 and all(len(e['content']['excerpt'])<=4000 for e in docs)
    assert all(e['published_at'] and e['retrieved_at'] for e in docs)
    assert len([e for e in snapshot['ledger'] if e['kind']=='price_history'])==30
    assert len([e for e in snapshot['ledger'] if e['kind']=='financial_metrics'])==12
    assert 'foreign secret' not in str(snapshot)
    assert all(not e['provenance_known'] and e['source_name'] is None for e in snapshot['ledger'] if e['kind']=='price_history')


def test_refetch_timestamps_and_attempts_do_not_change_fingerprint(session,seeded_security):
    from datetime import UTC,datetime,timedelta
    from app.db.models.data_management import DataSource,SecurityDataset,IngestionRun
    source=DataSource(source_key='eastmoney',name='Eastmoney',access_mode='public');session.add(source);session.flush()
    ds=SecurityDataset(security_id=seeded_security.id,category='price_history',source_id=source.id,unit='CNY',price_basis='forward_adjusted',frequency='daily',observation_at=datetime(2026,9,30,tzinfo=UTC),fetched_at=datetime(2026,9,30,tzinfo=UTC));session.add(ds);session.flush()
    session.add(IngestionRun(dataset_id=ds.id,source_id=source.id,status='succeeded',records_received=1,records_written=1));session.commit()
    p=ResearchRepository(session).create_project(security_id=seeded_security.id,question='x');builder=ResearchEvidenceBuilder(session)
    initial=builder.build(p)
    ds.fetched_at=ds.fetched_at+timedelta(hours=1);session.add(ds)
    session.add(IngestionRun(dataset_id=ds.id,source_id=source.id,status='succeeded',records_received=1,records_written=1));session.commit()
    assert builder.build(p)['input_fingerprint']==initial['input_fingerprint']


def test_actual_nav_source_and_mixed_attribution_unknown(session,seeded_security):
    from datetime import UTC,datetime,date
    from decimal import Decimal
    from app.db.models.data_management import DataSource,SecurityDataset,IngestionRun,FundNavObservation,DataQualityIssue
    current=DataSource(source_key='eastmoney_fund_nav',name='Current',access_mode='public'); old=DataSource(source_key='old_nav',name='Actual old source',access_mode='public');session.add_all([current,old]);session.flush()
    ds=SecurityDataset(security_id=seeded_security.id,category='fund_nav',source_id=current.id,unit='CNY/fund_unit',frequency='daily',fetched_at=datetime(2026,9,30,tzinfo=UTC),observation_at=datetime(2026,9,30,tzinfo=UTC));session.add(ds);session.flush()
    session.add(IngestionRun(dataset_id=ds.id,source_id=current.id,status='succeeded',records_written=1))
    session.add(DataQualityIssue(dataset_id=ds.id,code='mixed_source_write_attribution_unknown',severity='warning',message='mixed'))
    for i in range(8):session.add(FundNavObservation(security_id=seeded_security.id,source_id=old.id,nav_date=date(2026,9,20+i),value=Decimal('1.23')))
    session.commit();p=ResearchRepository(session).create_project(security_id=seeded_security.id,question='x')
    navs=[e for e in ResearchEvidenceBuilder(session).build(p)['snapshot']['ledger'] if e['kind']=='fund_nav']
    assert len(navs)==5
    assert all(e['source_name']=='Actual old source' and not e['provenance_known'] and e['published_at'] is None for e in navs)
