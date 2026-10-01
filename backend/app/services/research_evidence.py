"""Single-security evidence snapshots from local records only."""
import hashlib
import json
from datetime import date,datetime
from decimal import Decimal
from sqlmodel import select
from app.db.models import Security, QuoteSnapshot, PriceHistory, FinancialMetrics, Announcement, NewsItem, CompanyProfile, utc_now
from app.db.models.data_management import FundNavObservation, DataSource
from app.db.repositories.research_repository import json_object
from app.services.data_center import SecurityDataCenterService, utc
from app.services.security_indicators import SecurityIndicatorsService


def plain(value):
    if isinstance(value,Decimal): return format(value,'f')
    if isinstance(value,datetime): return utc(value).isoformat()
    if isinstance(value,date): return value.isoformat()
    if isinstance(value,dict): return {k:plain(v) for k,v in value.items()}
    if isinstance(value,(tuple,list)): return [plain(v) for v in value]
    return value


def canonical(value):
    return json.dumps(plain(value),ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)


def meaningful(value):
    if isinstance(value,dict):
        return {k:meaningful(v) for k,v in value.items() if k not in {'as_of_snapshot','retrieved_at','fetched_at','created_at','updated_at','recent_attempts','latest_attempt','recent_runs','latest_runs','last_success','last_successful_run','runs','started_at','finished_at','run_id'}}
    if isinstance(value,list): return [meaningful(v) for v in value]
    return value


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


class ResearchEvidenceBuilder:
    def __init__(self,session): self.session=session

    def build(self,project):
        security=self.session.get(Security,project.security_id)
        if security is None: raise KeyError('security not found')
        center=SecurityDataCenterService(self.session).detail(security.id)
        indicator_service=SecurityIndicatorsService(self.session)
        indicators=indicator_service.security(security.id).model_dump(mode='json')
        if indicators['instrument_type'] not in {'stock','etf','lof','unknown'}:
            raise ValueError('research supports stocks ETF and LOF')
        ledger=[]
        def add(kind,content,category,observed=None,published=None,retrieved=None,source=None,url=None,title_only=False,row_source_key=None):
            health=center['categories'][category]
            contract=indicator_service._contract(category,row_source_key or health['source_key'])
            known=indicator_service._verified(security.id,category,health) and health['health'] not in {'partial','unknown','failed'}
            if row_source_key and row_source_key != health['source_key']: known=False
            fields={f.target_field:f.normalized_unit for f in contract.fields if f.verification!='unverified'} if contract else {}
            # Legacy series have no per-row attribution. Dataset context is disclosed
            # separately; only complete acquisition with no mixed-attribution issues
            # can establish context, never a vendor label for an opaque retained row.
            source_key=row_source_key or (health['source_key'] if known else None)
            item=plain(dict(kind=kind,content=content,source_name=source or source_key,source_url=url,
                dataset_source_key=health['source_key'],field_units=fields if known else {},
                source_time_note=contract.time_rule if contract else 'Publication or observation timezone/precision unverified',
                provenance_warnings=[] if known else ['row_attribution_or_units_unverified'],health=health['health'],context_disclosures=health['context_disclosures'],
                observed_at=observed,published_at=published,retrieved_at=retrieved,unit=health['unit'],price_basis=health['price_basis'],
                provenance_known=bool(known and contract),title_only=title_only))
            item['evidence_id']='e_'+digest(meaningful(item))
            ledger.append(item)
        specs=[(QuoteSnapshot,'quote_snapshot','snapshot_time',1),(PriceHistory,'price_history','trade_date',30),
               (FinancialMetrics,'financial_metrics','report_period',12),(CompanyProfile,'company_profile','id',1)]
        for cls,category,sort,limit in specs:
            rows=self.session.exec(select(cls).where(cls.security_id==security.id).order_by(getattr(cls,sort).desc(),cls.id.desc()).limit(limit)).all()
            for row in rows:
                content=row.model_dump(exclude={'id','security_id','created_at','updated_at'})
                add(category,content,category,observed=content.get(sort) if sort!='id' else None,retrieved=center['categories'][category]['fetched_at'])
        nav_dates=self.session.exec(select(FundNavObservation.nav_date).where(FundNavObservation.security_id==security.id).distinct().order_by(FundNavObservation.nav_date.desc()).limit(5)).all()
        if nav_dates:
            rows=self.session.exec(select(FundNavObservation).where(FundNavObservation.security_id==security.id,FundNavObservation.nav_date.in_(nav_dates)).order_by(FundNavObservation.nav_date.desc(),FundNavObservation.id.desc()).limit(30)).all()
            for row in rows:
                source=self.session.get(DataSource,row.source_id)
                add('fund_nav',dict(nav_kind=row.nav_kind,value=row.value,source_id=row.source_id),'fund_nav',row.nav_date,row.published_at,row.fetched_at,source=source.name if source else None,row_source_key=source.source_key if source else 'unknown')
        docs=[]
        for cls,category in [(Announcement,'announcements'),(NewsItem,'news')]:
            for row in self.session.exec(select(cls).where(cls.security_id==security.id).order_by(cls.published_at.desc(),cls.id.desc()).limit(20)):
                docs.append((row,category))
        docs.sort(key=lambda pair:(utc(pair[0].published_at),pair[0].id,pair[1]),reverse=True)
        for row,category in docs[:20]:
            excerpt=(row.summary or row.title)[:4000]
            add('document',dict(title=row.title[:1000],excerpt=excerpt,content_type='summary' if row.summary else 'title'),category,
                published=row.published_at,retrieved=row.created_at,source=row.source,url=row.url,title_only=not bool(row.summary))
        gaps=[f"{m['key']}: "+','.join(m['warnings']) for m in indicators['metrics'] if m['status']!='ready']
        snapshot=plain(dict(snapshot_version='1',as_of_snapshot=utc_now(),project=dict(id=project.id,version=project.version,question=project.question,hypothesis=project.hypothesis,horizon=project.horizon),
            security=dict(id=security.id,market=security.market,code=security.code,name=security.name),metadata=center['metadata'],
            ledger=ledger,metrics=indicators['metrics'],data_gaps=gaps,context=indicators['data_context']))
        raw=canonical(snapshot); json_object(raw)
        return dict(snapshot=json.loads(raw),input_snapshot_json=raw,input_fingerprint=digest(meaningful(snapshot)))
