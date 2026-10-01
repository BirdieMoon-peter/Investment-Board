import json
from dataclasses import FrozenInstanceError

import httpx
import pytest

from app.services.data_sources import get_source_module, list_source_modules, get_endpoint


def test_registry_is_fresh_immutable_json_safe_and_offline(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('catalog must not access network')
    monkeypatch.setattr(httpx.Client, 'send', forbidden)
    first, second = list_source_modules(), list_source_modules()
    assert {m.key for m in first} == {'eastmoney', 'sina', 'netease', 'tencent', 'ifeng'}
    assert first is not second and first[0] is not second[0]
    pairs = [(m.key, e.key, e.category) for m in first for e in m.endpoints]
    assert len(pairs) == len(set(pairs))
    for module in first:
        assert isinstance(module.endpoints, tuple)
        with pytest.raises(FrozenInstanceError):
            module.name = 'changed'
        payload = module.to_dict()
        json.dumps(payload)
        payload['endpoints'].clear()
        assert module.endpoints
        for endpoint in module.endpoints:
            assert isinstance(endpoint.fields, tuple)
            assert isinstance(endpoint.limitations, tuple)


@pytest.mark.parametrize('key', ['', 'Eastmoney', 'unknown'])
def test_unknown_vendor_rejected(key):
    with pytest.raises(KeyError):
        get_source_module(key)


def test_unknown_endpoint_rejected():
    with pytest.raises(KeyError):
        get_endpoint('sina', 'sina', 'financial_metrics')


def by_target(vendor, provider, category, target):
    return [f for f in get_endpoint(vendor, provider, category).fields if f.target_field == target]


def test_history_native_units_and_real_aggregate_conversion():
    from decimal import Decimal
    from app.services.providers.eastmoney_price_history import _parse_kline
    from app.services.providers.sina_price_history import _parse_row
    from app.services.providers.stock_data_providers import AggregatePriceHistoryProvider, RawPriceHistorySourceAdapter
    east = _parse_kline('2026-09-30,1.00,1.01,1.02,0.99,1100748,1000000')
    sina = _parse_row(dict(day='2026-09-30', open='1', close='1.01', high='1.02', low='.99', volume='110074800'))
    class Source:
        volume_unit = 'lots'
        price_basis = 'forward_adjusted'
        amount_available = True
        def fetch(self, *args, **kwargs): return [east]
    result = AggregatePriceHistoryProvider(raw_sources=[RawPriceHistorySourceAdapter('eastmoney', Source())]).fetch_for_security(1, stock_code='515980', market='SH')
    assert result.items[0].volume == sina.volume == Decimal('110074800')
    contract = by_target('eastmoney', 'eastmoney', 'price_history', 'volume')[0]
    assert (contract.raw_unit, contract.normalized_unit, contract.verification) == ('lots', 'shares', 'sample_verified')
    assert '100' in contract.conversion
    assert sina.amount == 0
    amount = by_target('sina', 'sina', 'price_history', 'amount')[0]
    assert amount.normalized_unit == 'unavailable' and 'never' in amount.missing_rule
    netease = get_endpoint('netease', 'netease', 'price_history')
    assert netease.price_basis == 'unknown'
    assert all(f.verification == 'unverified' for f in netease.fields if f.target_field in ('volume', 'amount'))


def test_financial_percent_parent_profit_and_capital_samples():
    from decimal import Decimal
    from app.services.providers.eastmoney_financial_metrics import _parse_metric_row
    from app.services.providers.eastmoney_company_profile import _optional_decimal
    metrics = _parse_metric_row(dict(DATATYPE='2026半年报', TOTAL_OPERATE_INCOME=92278072083.21, PARENT_NETPROFIT=44516880421.86, BASIC_EPS=35.57, WEIGHTAVG_ROE=16.75))
    assert metrics.net_profit == Decimal('44516880421.86')
    assert metrics.roe == Decimal('16.75')
    assert by_target('eastmoney', 'eastmoney', 'financial_metrics', 'roe')[0].normalized_unit == 'percentage_value'
    assert '归母净利润' in by_target('eastmoney', 'eastmoney', 'financial_metrics', 'net_profit')[0].conversion
    assert _optional_decimal('12.50亿') == Decimal('1250000000')
    capitals = by_target('eastmoney', 'eastmoney', 'company_profile', 'registered_capital')
    assert [(f.verification, f.normalized_unit) for f in capitals] == [('sample_verified', 'CNY'), ('unverified', 'unverified')]


def test_quote_percent_and_precision_match_real_parser():
    from decimal import Decimal
    from app.services.providers.eastmoney_quote_snapshot import _parse_quote_snapshot
    quote = _parse_quote_snapshot({'data': {'f43':1234, 'f59':3, 'f169':12, 'f170':123, 'f124':1790730000}})
    assert quote.last_price == Decimal('1.234')
    assert quote.change_percent == Decimal('1.23')
    percent = by_target('eastmoney', 'eastmoney', 'quote_snapshot', 'change_percent')[0]
    assert percent.raw_type == 'number|string'
    assert percent.normalized_type == 'Decimal'
    assert percent.normalized_unit == 'percentage_value'
    assert '/ 100' in percent.conversion


@pytest.mark.parametrize('factory,expected', [
    ('get_aggregate_announcement_provider', ['eastmoney', 'sina']),
    ('get_aggregate_news_provider', ['eastmoney', 'sina']),
    ('get_aggregate_price_history_provider', ['sina', 'eastmoney', 'netease']),
    ('get_aggregate_quote_snapshot_provider', ['eastmoney_intraday', 'eastmoney', 'sina_fund']),
    ('get_aggregate_financial_metrics_provider', ['eastmoney']),
    ('get_aggregate_company_profile_provider', ['eastmoney']),
])
def test_stock_factory_order_freshness_and_constructor_compatibility(monkeypatch, factory, expected):
    from app.api import stocks
    # Avoid real client allocation and demonstrate legacy stocks symbols remain patchable.
    for name in ('EastmoneyAnnouncementSource', 'SinaAnnouncementSource', 'EastmoneyNewsSource', 'SinaNewsSource', 'SinaPriceHistorySource', 'EastmoneyPriceHistorySource', 'NetEasePriceHistorySource', 'EastmoneyIntradayQuoteSnapshotSource', 'EastmoneyQuoteSnapshotSource', 'SinaFundQuoteSnapshotSource', 'EastmoneyFinancialMetricsSource', 'EastmoneyCompanyProfileSource'):
        monkeypatch.setattr(stocks, name, type(name, (), {}))
    first = getattr(stocks, factory)().raw_sources
    second = getattr(stocks, factory)().raw_sources
    assert [s.name for s in first] == expected
    assert all(a is not b and a.provider is not b.provider for a,b in zip(first,second))


def test_planned_nav_and_fees_do_not_advertise_integration():
    nav = get_endpoint('eastmoney', 'eastmoney_fund_nav', 'fund_nav')
    profile = get_endpoint('eastmoney', 'eastmoney_fund_profile', 'fund_profile')
    assert nav.integration_scope == profile.integration_scope == 'planned'
    assert by_target('eastmoney', 'eastmoney_fund_nav', 'fund_nav', 'unit_nav')[0].normalized_unit == 'CNY/fund_unit'
    assert by_target('eastmoney', 'eastmoney_fund_profile', 'fund_profile', 'management_fee')[0].normalized_unit == 'fraction'
    assert all(f.verification == 'unverified' for e in (nav,profile) for f in e.fields)
    assert any('not reinvested total return' in limitation for limitation in nav.limitations)


def test_invalid_contract_values_and_nested_mutable_inputs():
    from app.services.data_sources.contracts import FieldContract, SourceModule, endpoint, field
    with pytest.raises(ValueError):
        FieldContract('x','x','string','text','text','identity','None','healthy')
    fields, limitations = [field('x','x')], ['one']
    item = endpoint('vendor', 'category', 'https://example.invalid', fields, limitations=limitations)
    fields.clear(); limitations.clear()
    assert len(item.fields) == len(item.limitations) == 1
    with pytest.raises(ValueError):
        SourceModule('vendor','Vendor', (item,item))


def test_sina_news_matches_json_parser_and_unverified_source_time():
    from app.services.providers.sina_news import _extract_rows, _parse_row
    row = dict(title='News', ctime='2026-09-30 09:00:00', url='/news.html')
    assert _extract_rows({'result': {'data': [row]}}) == [row]
    assert _extract_rows({'data': [row]}) == [row]
    assert _parse_row(row, index=0).published_at.utcoffset().total_seconds() == 0
    item = get_endpoint('sina','sina','news')
    assert 'no JSONP decoding' in item.payload_format
    assert by_target('sina','sina','news','published_at')[0].verification == 'unverified'
    for invalid in ([row], 'var news={"data": []};'):
        with pytest.raises(ValueError):
            _extract_rows(invalid)


def test_contracts_reject_mutable_nested_non_contract_values():
    from app.services.data_sources.contracts import SourceModule, endpoint
    with pytest.raises(TypeError):
        endpoint('vendor','category','url',[{}])
    with pytest.raises(TypeError):
        SourceModule('vendor','Vendor',[{}])


def test_intraday_fallback_boundary_matches_real_parser():
    from app.services.providers.eastmoney_intraday_quote_snapshot import EastmoneyIntradayQuoteSnapshotSource
    quote_data = dict(f43=1234, f59=3, f169=12, f170=123, f124=1790730000, prePrice='1.2')
    def source(rows):
        return EastmoneyIntradayQuoteSnapshotSource(transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={'data': dict(quote_data, klines=rows)})
        ))
    # A malformed selected string row raises even when a valid fallback quote exists.
    with pytest.raises(ValueError):
        source(['malformed']).fetch('515980', 'SH')
    assert str(source([]).fetch('515980', 'SH').last_price) == '1.234'
    assert str(source([None, '']).fetch('515980', 'SH').last_price) == '1.234'
    contract = get_endpoint('eastmoney', 'eastmoney_intraday', 'quote_snapshot')
    assert 'only when no nonempty string' in contract.fields[0].missing_rule
    assert any('Malformed selected rows raise' in item for item in contract.limitations)


def test_financial_report_name_preserved_and_datatype_only_normalized():
    from app.services.providers.eastmoney_financial_metrics import _parse_metric_row
    named = _parse_metric_row(dict(REPORT_DATE_NAME='  2026年半年报（原标签）  ', DATATYPE='2026半年报'))
    unnamed = _parse_metric_row(dict(REPORT_DATE_NAME=' ', DATATYPE='2026半年报'))
    assert named.report_period == '2026年半年报（原标签）'
    assert unnamed.report_period == '2026Q2'
    contract = by_target('eastmoney', 'eastmoney', 'financial_metrics', 'report_period')[0]
    assert 'preserved verbatim' in contract.conversion


def test_macro_display_types_and_quote_scaling_metadata_are_explicit():
    from app.services.providers.eastmoney_homepage_overview import _parse_macro_row
    assert _parse_macro_row('cpi', dict(NATIONAL_SAME=1.23, NATIONAL_SEQUENTIAL='0.5'))[:3] == ('1.23', '%', '环比0.5%')
    macro = get_endpoint('eastmoney', 'eastmoney', 'macro')
    assert all(f.raw_type == 'number|string' and f.normalized_type == 'string' for f in macro.fields[:3])
    precision = get_endpoint('eastmoney', 'eastmoney', 'quote_snapshot').fields[2]
    assert precision.normalized_type == 'int'
    assert 'nonpersisted' in precision.target_field
