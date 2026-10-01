from dataclasses import FrozenInstanceError
from datetime import date, datetime, UTC
from decimal import Decimal

import httpx
import pytest

from app.services.providers.eastmoney_fund_data import EastmoneyFundNavSource, EastmoneyFundProfileSource


def row(day='2026-09-30', unit='0.9567', cumulative='1.9134'):
    return {'FSRQ': day, 'DWJZ': unit, 'LJJZ': cumulative}


def payload(rows, total=None, **extra):
    return {'Data': {'LSJZList': rows}, 'TotalCount': len(rows) if total is None else total, 'ErrCode': 0, **extra}


def nav(handler, **kwargs):
    return EastmoneyFundNavSource(transport=httpx.MockTransport(handler), **kwargs).fetch('515980', 'SH')


def profile(body, code='515980', market='SH'):
    return EastmoneyFundProfileSource(transport=httpx.MockTransport(lambda r: httpx.Response(200, text=body))).fetch(code, market)


def html(fields='', title='人工智能基金(515980)基金基本概况'):
    return f'<html><title>{title}</title><table>{fields}</table></html>'


def cells(label, value):
    return f'<tr><th>{label}</th><td>{value}</td></tr>'


def test_nav_exact_observations_real_attempt_and_unknown_publication():
    before = datetime.now(UTC)
    result = nav(lambda r: httpx.Response(200, json=payload([row()])))
    assert [(x.nav_date, x.nav_kind, x.value) for x in result.items] == [(date(2026,9,30),'unit_nav',Decimal('.9567')), (date(2026,9,30),'cumulative_nav',Decimal('1.9134'))]
    assert all(x.published_at is None for x in result.items)
    assert result.received_count == 1 and result.attempts[0].count == 1
    assert result.source_key == 'eastmoney_fund_nav'
    assert before <= result.attempts[0].started_at <= result.attempts[0].finished_at <= datetime.now(UTC)
    assert result.attempts[0].observed_at is None
    assert result.truncated is False
    with pytest.raises(FrozenInstanceError):
        result.items[0].value = Decimal(1)


def test_pagination_cap_and_truncation():
    requests = []
    def handler(r):
        requests.append(dict(r.url.params))
        index = int(r.url.params['pageIndex'])
        return httpx.Response(200, json=payload([row(f'2026-09-{index:02}')]*100, 400))
    result = nav(handler)
    assert len(requests) == 3 and result.received_count == 300 and result.truncated
    assert [x['pageIndex'] for x in requests] == ['1','2','3']
    assert all(x['fundCode']=='515980' and x['pageSize']=='100' for x in requests)
    assert len(result.items) == 6
    assert [x.nav_date for x in result.items][::2] == [date(2026,9,i) for i in (1,2,3)]


@pytest.mark.parametrize('value', ['', '--', None])
def test_missing_nav_never_zero(value):
    result = nav(lambda r: httpx.Response(200, json=payload([row(unit=value)])))
    assert len(result.items) == 1 and result.items[0].nav_kind == 'cumulative_nav'


@pytest.mark.parametrize('bad', [row('bad'),row(unit='NaN'),row(unit='Infinity'),row(unit='0'),row(unit='-1'),row(cumulative='oops'), None])
def test_malformed_nav_entire_fetch_fails(bad):
    result = nav(lambda r: httpx.Response(200, json=payload([row(), bad])))
    assert result.items == () and result.attempts[0].state == 'failed'
    assert result.attempts[0].error_code == 'invalid_data' and result.received_count == 2


def test_later_page_error_cannot_certify_first_page():
    result = nav(lambda r: httpx.Response(200, json=payload([row()]*100, 101) if r.url.params['pageIndex']=='1' else payload([row(unit='NaN')],101)))
    assert result.items == () and result.received_count == 101 and result.attempts[0].error_code == 'invalid_data'


@pytest.mark.parametrize('status,error', [(401,'authentication_error'),(429,'rate_limited')])
def test_safe_http_failures(status,error):
    result = nav(lambda r: httpx.Response(status,text='secret upstream text'))
    assert result.attempts[0].error_code == error and 'secret' not in repr(result)


@pytest.mark.parametrize('body', [{'ErrCode':1,'ErrMsg':'secret'}, {'Data':{}},payload([],ErrCode='2'),payload([],TotalCount='NaN')])
def test_reject_provider_errors_and_shapes(body):
    result = nav(lambda r: httpx.Response(200,json=body))
    assert result.attempts[0].error_code == 'invalid_data'


def test_conflicting_duplicate_rejected_identical_deduplicated():
    assert len(nav(lambda r: httpx.Response(200,json=payload([row(),row()]))).items)==2
    result = nav(lambda r: httpx.Response(200,json=payload([row(),row(unit='1')])))
    assert result.items == () and result.attempts[0].error_code == 'invalid_data'


@pytest.mark.parametrize('code,market', [('51598','SH'),('515980?secret','SH'),('５１５９８０','SH'),('515980','US')])
def test_invalid_identifiers_no_network(code,market):
    calls=[]
    source=EastmoneyFundNavSource(transport=httpx.MockTransport(lambda r: calls.append(r)))
    with pytest.raises(ValueError): source.fetch(code,market)
    assert calls == []


@pytest.mark.parametrize('kwargs', [{'max_pages':4},{'max_pages':0},{'page_size':101},{'page_size':0}])
def test_constructor_bounds(kwargs):
    with pytest.raises(ValueError): EastmoneyFundNavSource(**kwargs)


def test_profile_nested_html_entities_exact_units_and_classification():
    body=html(cells('基金全称','<b>华富中证人工智能产业交易型开放式指数证券投资基金</b>')+cells('基金管理人','<a>华富&nbsp;基金</a>')+cells('基金托管人','其他托管人')+cells('管理费率','0.50%（每年）')+cells('托管费率','0.10%（每年）')+cells('资产规模','72.86亿元（截止日期：2026年06月30日）')+cells('业绩比较基准','中证人工智能产业指数收益率'))
    result=profile(body)
    item=result.item
    assert item.instrument_type=='etf' and item.manager=='华富 基金'
    assert item.management_fee==Decimal('.005') and item.custody_fee==Decimal('.001')
    assert item.fund_assets==Decimal('7286000000') and item.assets_as_of==date(2026,6,30)
    assert item.benchmark_name=='中证人工智能产业指数收益率' and item.benchmark_code is None
    assert result.attempts[0].source_key=='eastmoney_fund_profile' and result.attempts[0].observed_at is None


@pytest.mark.parametrize('name,kind', [('普通指数基金','unknown'),('某上市开放式基金','lof'),('某基金（LOF）','lof'),('某ETF基金','etf')])
def test_explicit_classification_only(name,kind):
    assert profile(html(cells('基金全称',name))).item.instrument_type==kind


def test_missing_profile_fields_remain_unknown():
    item=profile(html(cells('基金全称','普通基金'))).item
    assert item.manager is item.management_fee is item.custody_fee is item.fund_assets is item.assets_as_of is None


@pytest.mark.parametrize('assets,expected', [('1.25万元',Decimal('12500')),('12元',Decimal('12')),('72.86',None),('--',None)])
def test_asset_units(assets,expected):
    assert profile(html(cells('基金全称','普通基金')+cells('资产规模',assets))).item.fund_assets==expected


@pytest.mark.parametrize('label,value', [('管理费率','NaN%'),('管理费率','101%'),('管理费率','-1%'),('托管费率','oops'),('资产规模','NaN亿元'),('资产规模','-1亿元'),('资产规模','2亿元（截止日期：2026年13月01日）')])
def test_bad_numeric_profile_fails(label,value):
    result=profile(html(cells(label,value)))
    assert result.item is None and result.attempts[0].error_code=='invalid_data'


@pytest.mark.parametrize('body', [html(title='其他基金(123456)基金基本概况'),'<script>var code="515980"</script>',html(cells('基金代码','123456'))])
def test_profile_identity_requires_recognized_corroboration(body):
    assert profile(body).attempts[0].error_code=='invalid_data'


def test_code_field_can_corroborate_without_title():
    assert profile('<table>'+cells('基金代码','515980（主代码）')+cells('基金全称','普通基金')+'</table>').item is not None


def test_lazy_builders_and_contracts_match_parsers():
    from app.services.data_sources.eastmoney import build_fund_nav_source,build_fund_profile_source,get_module
    assert isinstance(build_fund_nav_source(),EastmoneyFundNavSource)
    assert build_fund_nav_source() is not build_fund_nav_source()
    assert isinstance(build_fund_profile_source(),EastmoneyFundProfileSource)
    endpoints={x.category:x for x in get_module().endpoints if x.category.startswith('fund_')}
    assert endpoints['fund_nav'].integration_scope=='planned'
    assert {f.target_field for f in endpoints['fund_profile'].fields} >= {'fund_assets','assets_as_of','benchmark_name','instrument_type'}


def test_missing_nav_disclosed_and_no_usable_values_fail():
    one = nav(lambda r: httpx.Response(200,json=payload([row(unit=None)])))
    assert one.missing_nav_count == 1
    assert 'missing_nav_value' in one.quality_issues
    empty = nav(lambda r: httpx.Response(200,json=payload([row(unit=None,cumulative='--')])))
    assert empty.attempts[0].state == 'failed' and empty.attempts[0].count == 1
    assert empty.attempts[0].error_code == 'invalid_data'


def test_genuine_empty_and_unknown_total_coverage():
    empty = nav(lambda r: httpx.Response(200,json=payload([])))
    assert empty.attempts[0].state == 'empty' and empty.received_count == 0
    result = nav(lambda r: httpx.Response(200,json={'Data':{'LSJZList':[row()]},'ErrCode':0}))
    assert result.truncated is None


@pytest.mark.parametrize('status,error', [(401,'authentication_error'),(429,'rate_limited')])
def test_profile_safe_http_errors(status,error):
    source=EastmoneyFundProfileSource(transport=httpx.MockTransport(lambda r: httpx.Response(status,text='private-secret')))
    result=source.fetch('515980')
    assert result.item is None and result.attempts[0].error_code==error
    assert 'private-secret' not in repr(result)


def test_numeric_json_nav_keeps_all_decimal_digits():
    result = nav(lambda r: httpx.Response(200, text='{"ErrCode":0,"TotalCount":1,"Data":{"LSJZList":[{"FSRQ":"2026-09-30","DWJZ":0.123456789012345678901234567,"LJJZ":"1"}]}}'))
    assert result.items[0].value == Decimal('0.123456789012345678901234567')


def test_total_smaller_than_received_is_invalid():
    result = nav(lambda r: httpx.Response(200,json=payload([row(),row()],1)))
    assert result.attempts[0].error_code == 'invalid_data'


def test_empty_later_page_with_remaining_total_is_truncated():
    result=nav(lambda r: httpx.Response(200,json=payload([row()]*100,101) if r.url.params['pageIndex']=='1' else payload([],101)))
    assert result.truncated is True and result.received_count == 100


@pytest.mark.parametrize('value', ['1万元oops','1,2万元','2亿元（截止日期：bad）'])
def test_recognized_assets_invalid_suffix_or_grouping_rejected(value):
    assert profile(html(cells('资产规模',value))).attempts[0].error_code=='invalid_data'


def test_duplicate_dates_cannot_certify_distinct_date_coverage():
    result=nav(lambda r: httpx.Response(200,json=payload([row(),row()],2)))
    assert result.received_count==2 and len(result.items)==2
    assert result.truncated is True and 'duplicate_nav_date' in result.quality_issues


def test_duplicates_across_pages_keep_raw_count_but_not_complete_coverage():
    result=nav(lambda r: httpx.Response(200,json=payload([row()]*100,101) if r.url.params['pageIndex']=='1' else payload([row()],101)))
    assert result.received_count==101 and result.truncated is True


def test_actual_profile_net_assets_label_and_cutoff_phrase():
    body=html(cells('基金代码','515980（主代码）')+cells('基金全称','华富中证人工智能产业交易型开放式指数证券投资基金')+cells('基金管理人','华富基金')+cells('管理费率','0.50%（每年）')+cells('托管费率','0.10%（每年）')+cells('净资产规模','72.86亿元（截止至：2026年06月30日）'),title='人工智能ETF华富(515980)基金基本概况')
    result=profile(body)
    assert result.item.fund_assets==Decimal('7286000000')
    assert result.item.assets_as_of==date(2026,6,30)


def test_asset_cutoff_iso_date_and_alias_conflict():
    result=profile(html(cells('净资产规模','72.86亿元（截止至：2026-06-30）')))
    assert result.item.assets_as_of==date(2026,6,30)
    conflict=profile(html(cells('净资产规模','72亿元')+cells('资产规模','73亿元')))
    assert conflict.attempts[0].error_code=='invalid_data'


def test_zero_fund_assets_rejected_but_zero_fee_is_valid():
    assert profile(html(cells('净资产规模','0亿元'))).attempts[0].error_code=='invalid_data'
    assert profile(html(cells('管理费率','0%（每年）'))).item.management_fee==Decimal(0)


def test_profile_identity_only_cannot_report_healthy_metadata():
    for body in (html(), html(cells('基金代码','515980')), html(cells('净资产规模','--'))):
        result=profile(body)
        assert result.item is None and result.attempts[0].error_code=='invalid_data'
        assert result.received_count==1


def test_actual_profile_optional_cell_end_tags_preserve_labels_and_values():
    # Exact public-page structures supplied by the parent's read-only acceptance.
    body=html('<tr><th>基金代码</th><td>515980（主代码）<th>基金类型</th><td>指数型-股票</td></tr>'
              '<tr><th>净资产规模</th><td>72.86亿元（截止至：2026年06月30日）<th>份额规模</th><td><a href="gmbd_515980.html">56.0313亿份</a>（截止至：2026年06月30日）</td></tr>'
              +cells('基金全称','华富中证人工智能产业交易型开放式指数证券投资基金'),
              title='人工智能ETF华富(515980)基金基本概况')
    result=profile(body)
    assert result.attempts[0].state=='succeeded'
    assert result.item.fund_assets==Decimal('7286000000')
    assert result.item.assets_as_of==date(2026,6,30)
    assert result.item.instrument_type=='etf'


@pytest.mark.parametrize('ending', ['</tr></table>','</table>',''])
def test_optional_last_cell_and_row_ends(ending):
    body='<table><tr><th>基金代码<td>515980（主代码）<tr><th>基金全称<td><b>普通&nbsp;基金</b><script>515980 fake text</script>'+ending
    result=profile(body)
    assert result.attempts[0].state=='succeeded'
    assert result.item.full_name=='普通 基金'


def test_optional_cell_end_tags_still_reject_conflicting_duplicate_labels():
    body=html('<tr><th>基金代码<td>515980<tr><th>基金代码<td>123456<tr><th>基金全称<td>普通基金')
    result=profile(body)
    assert result.item is None and result.attempts[0].error_code=='invalid_data'


def test_nav_valuation_basis_separate_from_market_adjustment_enum():
    result=nav(lambda r:httpx.Response(200,json=payload([row()])))
    assert result.price_basis=='unknown'
    assert result.valuation_basis=='official_nav'


@pytest.mark.parametrize('name', [
    '某沪深300ETF联接证券投资基金',
    '某交易型开放式指数证券投资基金联接基金',
    'Example ETF Feeder Fund',
    'Example etf feeder fund',
])
def test_explicit_feeder_name_is_not_evidence_for_etf(name):
    result=profile(html(cells('基金全称',name)))
    assert result.attempts[0].state=='succeeded'
    assert result.item.instrument_type=='unknown'


def test_feeder_exclusion_preserves_independent_lof_marker():
    result=profile(html(cells('基金全称','某ETF联接基金（LOF）')))
    assert result.item.instrument_type=='lof'
