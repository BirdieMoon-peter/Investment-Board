from datetime import date, timedelta
from decimal import Decimal as D
import pytest
from app.services.indicator_calculations import (
    PriceObservation, PriceContext, price_metrics, financial_metrics, premium,
    tracking_error, normalize_period,
)


def prices(values, **kwargs):
    return [PriceObservation(date(2026, 1, 1) + timedelta(days=i), D(str(v)), D(i + 1)) for i, v in enumerate(values)]


def context(**kwargs):
    return PriceContext(basis='unadjusted', unit='CNY', frequency='daily', verified=True, volume_unit='shares', **kwargs)


def test_returns_require_sessions_plus_one_and_exact_endpoint():
    result = price_metrics(prices(range(1, 254)), context())
    assert result['price_return_252'].value == D(252)
    assert result['price_return_20'].value == D(253) / D(233) - 1
    assert result['price_return_252'].sample_count == 253
    assert price_metrics(prices(range(1, 253)), context())['price_return_252'].value is None


def test_drawdown_and_ma_hand_calculation():
    result = price_metrics(prices([100, 120, 90, 110]), context())
    assert result['max_drawdown'].value == D('-.25')
    assert result['ma_20'].value is None
    result = price_metrics(prices([10] * 20), context())
    assert result['ma_20'].value == 10
    assert result['ma_deviation_20'].value == 0


def test_volatility_constant_returns_and_volume_excludes_latest():
    rows = prices([D(2) ** i for i in range(21)])
    result = price_metrics(rows, context())
    assert result['annualized_volatility'].value == 0
    assert result['volume_ratio_20'].value == D(21) / D('10.5')


@pytest.mark.parametrize('values', [[1, 0], [1, -2], [1, 'NaN'], [1, 'Infinity']])
def test_invalid_prices_never_produce_results(values):
    assert all(r.value is None for r in price_metrics(prices(values), context()).values())


def test_duplicate_and_unsorted_dates_are_rejected():
    rows = prices([1, 2])
    for invalid in [[rows[0], rows[0]], rows[::-1]]:
        assert price_metrics(invalid, context())['max_drawdown'].value is None


@pytest.mark.parametrize('ctx', [PriceContext(), PriceContext(basis='mixed', unit='CNY', frequency='daily', verified=True), PriceContext(basis='unadjusted',unit='CNY',frequency='weekly',verified=True)])
def test_unknown_mixed_or_nondaily_context_is_unavailable(ctx):
    assert price_metrics(prices(range(1, 254)), ctx)['price_return_252'].value is None


def test_gap_and_calendar_disclosure():
    rows = prices([1] * 21)
    rows[-1] = PriceObservation(date(2026, 3, 1), D(1), D(1))
    result = price_metrics(rows, context())['price_return_20']
    assert 'calendar_unverified' in result.warnings
    assert 'date_gap_possible_suspension' in result.warnings


@pytest.mark.parametrize('raw,expected', [('2025Q1','2025Q1'),('2025年三季报','2025Q3'),('2025年年度报告','2025Q4'),('2025-09-30',None),('2025 report',None)])
def test_explicit_financial_periods_only(raw, expected):
    assert normalize_period(raw) == expected


def test_same_quarter_yoy_and_parent_margin():
    rows = [dict(report_period='2025Q3',revenue=D(150),net_profit=D(15),roe=D('16.75')), dict(report_period='2024Q3',revenue=D(100),net_profit=D(10)), dict(report_period='2025Q2',revenue=D(90),net_profit=D(9))]
    result = financial_metrics(rows, verified=True)
    assert result['revenue_yoy'].value == D('.5')
    assert result['parent_profit_revenue_ratio'].value == D('.1')
    assert result['roe'].value == D('16.75')
    assert result['roe'].unit == 'percentage_value'
    assert result['debt_to_asset_ratio'].value is None


def test_loss_baseline_and_missing_same_quarter():
    rows = [dict(report_period='2025Q1',revenue=D(100),net_profit=D(5)),dict(report_period='2024Q1',revenue=D(0),net_profit=D(-5))]
    result = financial_metrics(rows, verified=True)
    assert result['revenue_yoy'].value is None
    assert 'turnaround_or_loss_baseline' in result['parent_profit_yoy'].warnings
    assert financial_metrics(rows[:1],verified=True)['revenue_yoy'].value is None


def test_premium_same_date_raw_price_only():
    row = prices([12])[0]
    assert premium(row,row.day,D(10),context(),nav_verified=True).value == D('.2')
    assert premium(row,row.day + timedelta(days=1),D(10),context(),nav_verified=True).value is None
    ctx = PriceContext(basis='forward_adjusted',unit='CNY',frequency='daily',verified=True)
    assert premium(row,row.day,D(10),ctx,nav_verified=True).value is None
    assert premium(row,row.day,D(0),context(),nav_verified=True).value is None


def test_tracking_error_requires_verified_total_returns_and_alignment():
    rows = prices([D('1.01') ** i for i in range(61)])
    ctx = PriceContext(basis='total_return',unit='index_points',frequency='daily',verified=True)
    assert tracking_error(rows, rows, ctx, ctx).value == 0
    assert tracking_error(rows, rows, context(),ctx).value is None
    assert tracking_error(rows[:60],rows[:60],ctx,ctx).value is None
    assert tracking_error(rows,rows[1:],ctx,ctx).value is None


def test_missing_prior_sample_count_counts_real_records():
    output=financial_metrics([dict(report_period='2025Q1',revenue=D(10),net_profit=D(1))],verified=True)
    assert output['revenue_yoy'].sample_count == 1


def test_native_explicit_report_label_without_year_separator():
    assert normalize_period('2025三季报') == '2025Q3'


def test_nonconstant_sample_volatility_independently_checked():
    # 20 returns alternating 0 and 1; mean .5, sample variance 5/19.
    values=[D(1)]
    for i in range(20): values.append(values[-1] * (2 if i%2 else 1))
    output=price_metrics(prices(values),context())
    expected=(D(5)/19).sqrt()*D(252).sqrt()
    assert abs(output['annualized_volatility'].value-expected)<D('1e-24')


def test_volume_invalid_and_zero_prior_are_unavailable():
    rows=[PriceObservation(r.day,r.close,D(0)) for r in prices([1]*21)]
    assert price_metrics(rows,context())['volume_ratio_20'].value is None
    assert price_metrics(prices([1]*21),PriceContext(basis='unadjusted',unit='CNY',frequency='daily',verified=True))['volume_ratio_20'].value is None
