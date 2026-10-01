"""Read-only indicators from acquired local records and reviewed source context."""
from decimal import Decimal
import re
from sqlmodel import Session, select

from app.db.models import QuoteSnapshot, Security
from app.db.models.data_management import DataQualityIssue, FundNavObservation, IngestionRun
from app.db.repositories.holdings_repository import HoldingsRepository
from app.db.repositories.price_history_repository import PriceHistoryRepository
from app.db.repositories.financial_metrics_repository import FinancialMetricsRepository
from app.services.data_center import SecurityDataCenterService, utc
from app.services.data_sources.registry import list_source_modules
from app.services.indicator_calculations import (
    PriceContext, PriceObservation, finite, financial_metrics, premium, price_metrics, result,
)
from app.schemas.indicators import HoldingsIndicatorsResponse, PositionIndicators, SecurityIndicatorsResponse

PRICE_LIMIT = 253
FINANCIAL_LIMIT = 8
INTEGRITY_CODES = {'incomplete_price_refresh','mixed_source_write_attribution_unknown','price_basis_unknown','unit_unverified'}


class SecurityIndicatorsService:
    def __init__(self, session: Session):
        self.session = session
        self.center = SecurityDataCenterService(session)

    def _contract(self, category, source_key):
        return next((endpoint for module in list_source_modules() for endpoint in module.endpoints
                     if endpoint.key == source_key and endpoint.category == category), None)

    def _verified(self, security_id, category, health, *, codes=INTEGRITY_CODES):
        dataset = self.center.repository.get_dataset(security_id,category)
        if dataset is None or dataset.source_id is None or not dataset.fetched_at or not health['source_key']:
            return False
        if self._contract(category,health['source_key']) is None:
            return False
        written = self.session.exec(select(IngestionRun.id).where(
            IngestionRun.dataset_id == dataset.id, IngestionRun.source_id == dataset.source_id,
            IngestionRun.status.in_(['succeeded','partial']), IngestionRun.records_written > 0).limit(1)).first()
        bad = self.session.exec(select(DataQualityIssue.id).where(
            DataQualityIssue.dataset_id == dataset.id, DataQualityIssue.resolved_at.is_(None),
            DataQualityIssue.code.in_(codes)).limit(1)).first()
        return written is not None and bad is None

    def _price_context(self, security_id, health, kind):
        contract = self._contract('price_history',health['source_key'])
        price_field = next((f for f in contract.fields if f.target_field == 'close_price'),None) if contract else None
        verified = (self._verified(security_id,'price_history',health) and kind in {'stock','etf','lof'}
                    and health['unit'] == 'CNY' and price_field is not None and price_field.normalized_unit == 'CNY')
        # Source contracts own adjustment and volume. A retained metadata enum by
        # itself cannot upgrade an unknown-basis source into a certified one.
        if contract is None or not contract.price_basis.startswith(health['price_basis']) or health['price_basis'] == 'unknown':
            verified = False
        volume = next((f for f in contract.fields if f.target_field == 'volume'),None) if contract else None
        dataset = self.center.repository.get_dataset(security_id,'price_history')
        volume_bad = self.session.exec(select(DataQualityIssue.id).where(
            DataQualityIssue.dataset_id == dataset.id, DataQualityIssue.resolved_at.is_(None),
            DataQualityIssue.code.in_(['volume_unit_unknown','index_volume_context_unverified'])).limit(1)).first() if dataset else True
        return PriceContext(basis=health['price_basis'],unit=health['unit'],frequency=health['frequency'],verified=verified,
                            volume_unit='shares' if kind != 'index' and volume and volume.normalized_unit == 'shares' and volume.verification != 'unverified' and volume_bad is None else None)

    @staticmethod
    def _ref(category, health, rows):
        return dict(category=category,source_key=health['source_key'],unit=health['unit'],frequency=health['frequency'],
                    price_basis=health['price_basis'],observation_at=health['observation_at'],fetched_at=health['fetched_at'],
                    coverage_start=health['coverage_start'],coverage_end=health['coverage_end'],freshness=health['freshness'],
                    health=health['health'],row_ids=[r.id for r in rows],observation_count=len(rows),
                    context_disclosures=health['context_disclosures'])

    @staticmethod
    def _attach(metrics, refs, health):
        for metric in metrics:
            metric.input_refs = refs
            if health['freshness'] in {'stale','unknown'}:
                metric.warnings.append(f"input_freshness_{health['freshness']}")
            if health['health'] in {'partial','unknown'}:
                metric.warnings.append(f"input_health_{health['health']}")

    def security(self, security_id):
        detail = self.center.detail(security_id)
        kind = detail['metadata']['effective_instrument_type']
        categories = detail['categories']
        health = categories['price_history']
        raw = list(reversed(PriceHistoryRepository(self.session).list_recent_by_security_id(security_id,limit=PRICE_LIMIT)))
        rows = [PriceObservation(r.trade_date,r.close_price,r.volume) for r in raw]
        ctx = self._price_context(security_id,health,kind)
        output = list(price_metrics(rows,ctx).values())
        price_ref = self._ref('price_history',health,raw)
        self._attach(output,[price_ref],health)

        financial = FinancialMetricsRepository(self.session).list_recent_by_security_id(security_id,limit=FINANCIAL_LIMIT)
        financial_health = categories['financial_metrics']
        contract = self._contract('financial_metrics',financial_health['source_key'])
        field_contracts = {f.target_field:f for f in contract.fields} if contract else {}
        verified = (kind == 'stock' and self._verified(security_id,'financial_metrics',financial_health)
                    and financial_health['frequency']=='quarterly' and
                    all(name in field_contracts and field_contracts[name].normalized_unit == 'CNY' for name in ('revenue','net_profit')))
        fundamentals = list(financial_metrics([r.model_dump() for r in financial],verified=verified).values())
        # No debt ratio is synthesized from another field; source-owned field
        # availability also prevents legacy zero from masquerading as disclosure.
        for metric in fundamentals:
            if metric.key in {'roe','debt_to_asset_ratio'}:
                field = field_contracts.get(metric.key)
                if field is None or field.raw_field == '(absent)' or field.verification == 'unverified':
                    metric.value = None; metric.status = 'unavailable'
                    metric.warnings.append('source_field_unavailable')
        self._attach(fundamentals,[self._ref('financial_metrics',financial_health,financial)],financial_health)
        output.extend(fundamentals)

        nav_health = categories['fund_nav']
        nav_dataset = self.center.repository.get_dataset(security_id,'fund_nav')
        latest = rows[-1] if rows else None
        nav = self.session.exec(select(FundNavObservation).where(
            FundNavObservation.security_id==security_id,FundNavObservation.nav_kind=='unit_nav',
            FundNavObservation.source_id==nav_dataset.source_id,
            FundNavObservation.nav_date==latest.day).limit(1)).first() if latest and nav_dataset and nav_dataset.source_id else None
        nav_verified = kind in {'etf','lof'} and nav_health['unit']=='CNY/fund_unit' and self._verified(security_id,'fund_nav',nav_health)
        fund_premium = premium(latest,nav.nav_date if nav else None,nav.value if nav else None,ctx,nav_verified=nav_verified)
        if kind not in {'etf','lof'}:
            fund_premium.warnings.append('not_applicable_to_instrument_type')
            fund_premium.value = None; fund_premium.status = 'unavailable'
        self._attach([fund_premium],[price_ref,self._ref('fund_nav',nav_health,[nav] if nav else [])],nav_health)
        output.append(fund_premium)

        benchmark_code = detail['metadata']['benchmark_code']
        benchmark = None
        qualified_benchmark = bool(benchmark_code and re.fullmatch(r'(SH|SZ):[0-9]{6}',benchmark_code))
        if qualified_benchmark:
            market,code = benchmark_code.split(':')
            benchmark = self.session.exec(select(Security).where(Security.market==market,Security.code==code).limit(1)).first()
        benchmark_reason = ('explicit_benchmark_mapping_missing' if not benchmark_code else
                            'benchmark_mapping_not_market_qualified' if not qualified_benchmark else
                            'benchmark_not_acquired' if benchmark is None else
                            'verified_dividend_total_return_inputs_unavailable')
        output.extend([
            result('total_return','分红再投资总收益率','verified_dividend_reinvested_last / first - 1','unavailable',warnings=['verified_dividend_total_return_inputs_unavailable']),
            result('benchmark_comparison','相对明确基准的总收益','fund_total_return - benchmark_total_return','aligned_total_return_window',warnings=[benchmark_reason]),
            result('tracking_error','年化跟踪误差（总收益）','sample_stdev(fund_daily_total_return - benchmark_daily_total_return) * sqrt(252)','at_least_60_aligned_daily_returns',warnings=[benchmark_reason]),
        ])
        for metric in output[-3:]:
            metric.input_refs = [dict(benchmark_code=benchmark_code,benchmark_security_id=benchmark.id if benchmark else None,
                                     note='Existing price/index/cumulative NAV records do not certify dividend reinvestment')]
        return SecurityIndicatorsResponse(security_id=security_id,instrument_type=kind,metrics=output,
            data_context=dict(categories=categories,calendar=detail['calendar'],classification_origin=detail['metadata']['classification_origin'],
                              benchmark_code=benchmark_code,benchmark_security_id=benchmark.id if benchmark else None,
                              price_observation_limit=PRICE_LIMIT,financial_observation_limit=FINANCIAL_LIMIT))

    def holdings(self):
        positions = []
        missing = []
        values = []
        for holding in HoldingsRepository(self.session).list_rows():
            detail = self.center.detail(holding.security_id)
            health = detail['categories']['quote_snapshot']
            kind = detail['metadata']['effective_instrument_type']
            quote = self.session.exec(select(QuoteSnapshot).where(QuoteSnapshot.security_id==holding.security_id)
                .order_by(QuoteSnapshot.snapshot_time.desc(),QuoteSnapshot.id.desc()).limit(1)).first()
            contract = self._contract('quote_snapshot',health['source_key'])
            price_field = next((f for f in contract.fields if f.target_field=='last_price'),None) if contract else None
            usable = (kind in {'stock','etf','lof'} and health['unit']=='CNY' and price_field and price_field.normalized_unit=='CNY'
                      and self._verified(holding.security_id,'quote_snapshot',health) and quote
                      and utc(quote.snapshot_time) == health['observation_at'] and finite(quote.last_price,positive=True)
                      and finite(holding.quantity,positive=True) and finite(holding.average_cost) and holding.average_cost>=0)
            warnings = [] if usable else ['verified_cash_security_quote_unavailable']
            value = holding.quantity * quote.last_price if usable else None
            pnl = holding.quantity * (quote.last_price - holding.average_cost) if usable else None
            cost = holding.quantity * holding.average_cost
            specs = [('market_value','当前持仓市值','quantity * last_price','CNY',value,[]),
                     ('unrealized_pnl','未实现盈亏','quantity * (last_price - average_cost)','CNY',pnl,[]),
                     ('unrealized_pnl_percent','未实现盈亏比例','(last_price - average_cost) / average_cost','fraction',pnl/cost if usable and cost>0 else None,[] if cost>0 else ['nonpositive_cost_baseline'])]
            position_metrics=[]
            for key,label,formula,unit,number,extra in specs:
                metric=result(key,label,formula,'current_position',unit,value=number,warnings=warnings+extra)
                metric.as_of=utc(quote.snapshot_time).isoformat() if usable else None
                self._attach([metric],[self._ref('quote_snapshot',health,[quote] if quote else [])],health)
                position_metrics.append(metric)
            positions.append(PositionIndicators(holding_id=holding.holding_id,security_id=holding.security_id,
                quantity=holding.quantity,average_cost=holding.average_cost,valuation_at=utc(quote.snapshot_time) if usable else None,
                metrics=position_metrics,warnings=warnings))
            if value is None:
                missing.append(holding.security_id)
            else:
                values.append(value)
        total=sum(values,Decimal(0))
        aggregate_warnings=['valuation_excludes_missing_positions'] if missing else []
        aggregate_warnings += ['current_positions_only_no_historical_or_realized_returns','valuation_dates_may_differ'] if positions else []
        weights=[]
        for position in positions:
            value=position.metrics[0].value
            weight=value/total if value is not None and total>0 else None
            metric=result('known_valued_weight','已知可估值持仓权重','position_value / sum(known_valued_position_values)',
                          'current_known_valued_positions','fraction',value=weight,warnings=aggregate_warnings + ([] if weight is not None else ['no_positive_valuation_denominator']))
            metric.as_of=position.valuation_at.isoformat() if position.valuation_at else None
            metric.input_refs=position.metrics[0].input_refs
            position.metrics.append(metric)
            if weight is not None:weights.append(weight)
        aggregate=[result('known_market_value','已知可估值持仓总市值','sum(known_valued_position_values)','current_known_valued_positions','CNY',value=total,warnings=aggregate_warnings),
                   result('concentration_hhi','已知可估值持仓集中度','sum(known_valued_weight ** 2)','current_known_valued_positions','dimensionless',
                          value=sum((w*w for w in weights),Decimal(0)) if weights else None,
                          warnings=aggregate_warnings+([] if weights else ['no_positive_valuation_denominator']))]
        for metric in aggregate:
            metric.sample_count=len(values)
            metric.input_refs=[dict(holding_id=p.holding_id,security_id=p.security_id,valuation_at=p.valuation_at) for p in positions if p.valuation_at]
        return HoldingsIndicatorsResponse(positions=positions,missing_price_security_ids=missing,
            valuation_complete=not missing,metrics=aggregate,warnings=aggregate_warnings)
