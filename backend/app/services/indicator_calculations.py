"""Pure deterministic calculations. Inputs are never fetched or rounded here."""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
import re
from collections.abc import Sequence

from app.schemas.indicators import IndicatorResult

D = Decimal
KNOWN_PRICE_BASES = {'unadjusted', 'forward_adjusted', 'backward_adjusted'}


@dataclass(frozen=True)
class PriceObservation:
    day: date
    close: Decimal
    volume: Decimal | None = None


@dataclass(frozen=True)
class PriceContext:
    basis: str = 'unknown'
    unit: str | None = None
    frequency: str | None = None
    verified: bool = False
    volume_unit: str | None = None


def finite(value, *, positive=False):
    return isinstance(value, Decimal) and value.is_finite() and (not positive or value > 0)


def result(key, label, formula, window, unit='fraction', *, rows=(), basis='unknown', value=None, warnings=()):
    return IndicatorResult(key=key, label=label, formula=formula, window=window, unit=unit,
                           as_of=rows[-1].day if rows else None, sample_count=len(rows), price_basis=basis,
                           value=value, status='ready' if value is not None else 'unavailable', warnings=list(warnings))


def validate_prices(rows: Sequence[PriceObservation], ctx: PriceContext, *, total_return=False):
    if not rows:
        return ['missing_price_observations']
    if any(not finite(row.close, positive=True) for row in rows):
        return ['invalid_price']
    if any(a.day >= b.day for a, b in zip(rows, rows[1:])):
        return ['dates_not_strictly_ascending']
    bases = {'total_return'} if total_return else KNOWN_PRICE_BASES
    if not ctx.verified or ctx.basis not in bases:
        return ['unverified_or_mixed_price_basis']
    if ctx.unit not in {'CNY', 'index_points'}:
        return ['unverified_price_unit']
    if ctx.frequency != 'daily':
        return ['unverified_daily_frequency']
    return []


def coverage_warnings(rows):
    # Holidays cannot be distinguished from suspensions without a verified calendar.
    warnings = ['calendar_unverified', 'price_return_excludes_dividend_reinvestment']
    if any((b.day - a.day).days > 7 for a, b in zip(rows, rows[1:])):
        warnings.append('date_gap_possible_suspension')
    return warnings


def sample_std(values):
    mean = sum(values, D(0)) / len(values)
    return (sum(((value - mean) ** 2 for value in values), D(0)) / (len(values) - 1)).sqrt()


def daily_returns(rows):
    return [b.close / a.close - 1 for a, b in zip(rows, rows[1:])]


def price_metrics(rows: Sequence[PriceObservation], ctx: PriceContext):
    error = validate_prices(rows, ctx)
    output = {}

    def add(key, label, formula, size, calculate, unit='fraction', minimum=None):
        selected = list(rows[-size:]) if size else list(rows)
        needed = minimum if minimum is not None else size
        warnings = error or (['insufficient_observations'] if len(selected) < needed else [])
        value = None if warnings else calculate(selected)
        output[key] = result(key, label, formula, f'last_{size}_observations' if size else 'stored_bounded_window', unit,
                             rows=selected, basis=ctx.basis, value=value,
                             warnings=warnings + ([] if error else coverage_warnings(selected)))

    for sessions in (20, 60, 252):
        add(f'price_return_{sessions}', f'{sessions}交易观察日价格收益率', 'P_last / P_first - 1', sessions + 1,
            lambda selected: selected[-1].close / selected[0].close - 1)
    def drawdown(selected):
        peak = selected[0].close
        worst = D(0)
        for row in selected:
            peak = max(peak, row.close)
            worst = min(worst, row.close / peak - 1)
        return worst
    add('max_drawdown', '观察窗口最大回撤', 'min(P_t / max(P_0..P_t) - 1)', 0, drawdown, minimum=2)
    add('annualized_volatility', '价格收益年化样本波动率', 'sample_stdev(daily_simple_price_returns) * sqrt(252)', 0,
        lambda selected: sample_std(daily_returns(selected)) * D(252).sqrt(), minimum=21)
    for size in (20, 60):
        add(f'ma_{size}', f'MA{size}', 'sum(close) / observation_count', size,
            lambda selected: sum((r.close for r in selected), D(0)) / len(selected), ctx.unit or 'unknown')
        add(f'ma_deviation_{size}', f'价格偏离MA{size}', 'P_last / MA - 1', size,
            lambda selected: selected[-1].close / (sum((r.close for r in selected), D(0)) / len(selected)) - 1)
    selected = list(rows[-21:])
    warnings = list(error)
    if len(selected) < 21:
        warnings.append('insufficient_observations')
    if ctx.volume_unit != 'shares' or any(not finite(r.volume) or r.volume < 0 for r in selected):
        warnings.append('unverified_uniform_share_volume')
    prior = sum((r.volume for r in selected[:-1] if finite(r.volume)), D(0))
    if prior <= 0:
        warnings.append('nonpositive_prior_volume')
    output['volume_ratio_20'] = result('volume_ratio_20', '最新成交量/此前20观察日均量', 'V_last / mean(V_previous_20)',
        'latest_and_previous_20_observations', 'ratio', rows=selected, basis=ctx.basis,
        value=None if warnings else selected[-1].volume / (prior / 20), warnings=warnings + coverage_warnings(selected))
    return output


def normalize_period(raw):
    """Recognize explicit report labels only; dates/names never imply a quarter."""
    if not isinstance(raw, str):
        return None
    value = raw.strip()
    if re.fullmatch(r'[0-9]{4}Q[1-4]', value):
        return value
    match = re.fullmatch(r'([0-9]{4})年?(一季报|第一季度报告|中报|半年报|半年度报告|三季报|第三季度报告|年报|年度报告)', value)
    if not match:
        return None
    quarter = {'一季报':1, '第一季度报告':1, '中报':2, '半年报':2, '半年度报告':2,
               '三季报':3, '第三季度报告':3, '年报':4, '年度报告':4}[match[2]]
    return f'{match[1]}Q{quarter}'


def financial_metrics(rows, *, verified=False):
    normalized = {}
    invalid = False
    for row in rows:
        period = normalize_period(row['report_period'])
        if period is None or period in normalized:
            invalid = True
        else:
            normalized[period] = row
    latest = max(normalized, default=None)
    current = normalized.get(latest, {})
    prior_period = f'{int(latest[:4])-1}Q{latest[-1]}' if latest else None
    prior = normalized.get(prior_period, {})
    base_errors = [] if verified and latest and not invalid else ['unverified_financial_period_or_source']
    output = {}
    def add(key,label,formula,value,warnings=(),unit='fraction',count=1):
        errors = base_errors + list(warnings)
        r = result(key,label,formula, f'{latest or "unknown"}_cumulative_YTD' + (f'_vs_{prior_period}' if count == 2 else ''),
            unit, value=value if not errors else None, warnings=errors)
        r.as_of = latest
        r.sample_count = int(bool(current)) + (int(bool(prior)) if count == 2 else 0)
        output[key] = r
    for field,key,label in [('revenue','revenue_yoy','营业收入同比（同季度累计）'),('net_profit','parent_profit_yoy','归母净利润同比（同季度累计）')]:
        numerator, denominator = current.get(field), prior.get(field)
        warnings = []
        value = None
        if not finite(numerator) or not finite(denominator):
            warnings = ['missing_same_quarter_comparison']
        elif denominator <= 0:
            warnings = ['turnaround_or_loss_baseline' if field == 'net_profit' else 'nonpositive_revenue_baseline']
        else:
            value = (numerator - denominator) / denominator
        add(key,label,'(current_YTD - prior_same_quarter_YTD) / prior_same_quarter_YTD',value,warnings,count=2)
    revenue, profit = current.get('revenue'), current.get('net_profit')
    valid = finite(revenue,positive=True) and finite(profit)
    add('parent_profit_revenue_ratio','归母净利润/营业收入','PARENT_NETPROFIT / revenue',profit/revenue if valid else None,
        [] if valid else ['missing_or_nonpositive_revenue'])
    for field,label in [('roe','来源披露ROE'),('debt_to_asset_ratio','来源披露资产负债率')]:
        value = current.get(field)
        add(field,label,'source_supplied_percentage_value',value if finite(value) else None,
            [] if finite(value) else ['source_field_unavailable'],unit='percentage_value')
    return output


def premium(close, nav_date, nav, ctx, *, nav_verified=False):
    rows = [close] if close else []
    warnings = validate_prices(rows, ctx)
    if ctx.basis != 'unadjusted' or ctx.unit != 'CNY':
        warnings.append('premium_requires_verified_unadjusted_CNY_per_fund_unit_close')
    if not nav_verified or not finite(nav,positive=True):
        warnings.append('official_unit_nav_unverified_or_missing')
    if close is None or close.day != nav_date:
        warnings.append('no_same_date_completed_close_and_unit_nav')
    return result('fund_premium','同日收盘价相对官方单位净值溢价','unadjusted_close / official_unit_nav - 1',
        'same_valuation_date',rows=rows,basis=ctx.basis,value=None if warnings else close.close / nav - 1,warnings=warnings)


def tracking_error(fund, benchmark, fund_context, benchmark_context):
    warnings = validate_prices(fund,fund_context,total_return=True) + validate_prices(benchmark,benchmark_context,total_return=True)
    if [r.day for r in fund] != [r.day for r in benchmark]:
        warnings.append('unaligned_total_return_dates')
    if len(fund) < 61:
        warnings.append('requires_60_aligned_total_returns')
    value = None
    if not warnings:
        value = sample_std([a-b for a,b in zip(daily_returns(fund),daily_returns(benchmark))]) * D(252).sqrt()
    return result('tracking_error','年化跟踪误差（总收益）','sample_stdev(fund_daily_total_return - benchmark_daily_total_return) * sqrt(252)',
        'at_least_60_aligned_daily_returns', rows=fund,basis=fund_context.basis,value=value,warnings=warnings)
