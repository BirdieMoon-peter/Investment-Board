"""Orchestration of immutable experiments and independent forward paper accounts."""
from datetime import datetime
from decimal import Decimal
from sqlmodel import select
from app.db.models import Security, Holding, QuoteSnapshot
from app.db.models.quant import QuantDataset, QuantStrategy, QuantRun, QuantAccount
from app.db.models.research import ResearchProject
from app.db.repositories.quant_repository import QuantRepository, QuantConflict
from app.db.repositories.data_management_repository import DataManagementRepository
from app.services.quant.contracts import DatasetImport, StrategyCreate, RunCreate, AccountCreate, Acquire, Review, today
from app.services.quant.acquisition import RawDailySource, AcquisitionError
from app.services.quant.engine import experiment, simulate, initial_state, signal, scheduled_signal, quantities, ENGINE_VERSION


def warnings(dataset):
    result = ['instrument_rules_are_user_assumptions_not_certified_historical_rules', 'calendar_is_observed_or_user_declared_not_certified_exchange_history', 'daily_open_fill_and_zero_volume_halt_are_execution_approximations', 'constant_a_share_tax_assumption_not_historical_policy_schedule']
    if dataset['corporate_action_coverage'] == 'unknown':
        result.append('unknown_corporate_actions_research_price_return_only')
    else:
        result.append('corporate_action_coverage_is_user_declaration_not_verified_total_return')
    if any(i['limit_pct'] is None for i in dataset['instruments']):
        result.append('some_price_limit_assumptions_unspecified')
    pairs = {(b['date'], b['security_id']) for b in dataset['bars']}
    if len(pairs) < len(dataset['calendar']) * len(dataset['instruments']):
        result.append('missing_bars_not_tradable_last_known_valuation_stale')
    return result


class QuantService:
    def __init__(self, session, source=None, provider_factory=None, clock=None):
        self.session = session; self.repo = QuantRepository(session)
        self.source = source or RawDailySource()
        self.provider_factory = provider_factory
        self.clock = clock or today

    def validate_instruments(self, instruments):
        for instrument in instruments:
            values = instrument.model_dump() if hasattr(instrument, 'model_dump') else instrument
            security = self.session.get(Security, values['security_id'])
            if security is None:
                raise KeyError('security not found')
            if security.status != 'active' or (security.market, security.code) != (values['market'], values['code']):
                raise ValueError('instrument identity must match active security master')
            # Instrument type/name and historic rules remain explicit user assumptions.

    def import_dataset(self, body):
        validated = DatasetImport.model_validate(body)
        self.validate_instruments(validated.instruments)
        payload = validated.model_dump(mode='json')
        payload['warnings'] = warnings(payload)
        return self.repo.dataset(payload)

    def acquire_dataset(self, body):
        request = Acquire.model_validate(body); self.validate_instruments(request.instruments)
        source = DataManagementRepository(self.session).get_source('eastmoney')
        if source is not None and not source.enabled:
            raise AcquisitionError('Eastmoney source is disabled in source center')
        return self.import_dataset(self.source.acquire(request))

    def create_strategy(self, body):
        strategy = StrategyCreate.model_validate(body)
        for sid in strategy.universe:
            security = self.session.get(Security, sid)
            if security is None:
                raise KeyError('security not found')
            if security.status != 'active':
                raise ValueError('inactive security')
        payload = strategy.model_dump(mode='json', exclude={'parent_id'})
        return self.repo.strategy(payload, parent_id=strategy.parent_id)

    def inputs(self, body):
        strategy_row = self.repo.require(QuantStrategy, body.strategy_id)
        dataset_row = self.repo.require(QuantDataset, body.dataset_id)
        strategy = self.repo.decode(strategy_row); dataset = self.repo.decode(dataset_row)
        rules = {i['security_id']: i for i in dataset['instruments']}
        if any(sid not in rules for sid in strategy['universe']):
            raise ValueError('strategy universe not covered by dataset')
        if strategy['template'] in {'etf_momentum', 'etf_mean_reversion'} and any(rules[sid]['instrument_type'] != 'etf' for sid in strategy['universe']):
            raise ValueError('ETF template requires explicitly declared ETF universe')
        if dataset['calendar'][-1] > self.clock().isoformat():
            raise ValueError('future dataset')
        return strategy_row, dataset_row, strategy, dataset

    def create_run(self, body):
        request = RunCreate.model_validate(body)
        s, d, strategy, dataset = self.inputs(request)
        costs = request.costs.model_dump(mode='json')
        if not any(index % strategy['parameters']['rebalance_every'] == 0 and signal(dataset, strategy, index)['status'] == 'ready' for index in range(len(dataset['calendar']) - 1)):
            raise ValueError('insufficient signal history before an executable next session')
        result = experiment(dataset, strategy, request.initial_cash, costs, request.holdout_date.isoformat() if request.holdout_date else None)
        result.update(dataset_fingerprint=d.fingerprint, strategy_fingerprint=s.fingerprint, warnings=list(dataset['warnings']))
        if not any(item['status'] == 'ready' for item in result['result']['signals'][:-1]):
            raise ValueError('insufficient signal history before an executable next session')
        holdout_start = dataset['calendar'].index(result['holdout']['start_date'])
        if not any(scheduled_signal(dataset, strategy, index) is not None for index in range(max(0, holdout_start - 1), len(dataset['calendar']) - 1)):
            result['warnings'].append('holdout_insufficient_signal_history_robustness_unavailable')
            result['robustness']['status'] = 'unavailable'
        else:
            result['robustness']['status'] = 'diagnostic'
        return self.repo.run(s.id, d.id, result)

    def create_account(self, body):
        request = AccountCreate.model_validate(body)
        s, d, strategy, dataset = self.inputs(request)
        state = initial_state(request.initial_cash, dataset['calendar'][-1])
        state['pending_signal'] = scheduled_signal(dataset, strategy, len(dataset['calendar']) - 1)
        activation = max(self.clock().isoformat(), dataset['calendar'][-1])
        payload = {'name': request.name, 'engine_version': ENGINE_VERSION, 'strategy': strategy, 'strategy_fingerprint': s.fingerprint, 'initial_cash': str(request.initial_cash), 'costs': request.costs.model_dump(mode='json'), 'activation_date': activation, 'snapshot_as_of': dataset['calendar'][-1], 'status': 'awaiting_future_data', 'warnings': dataset['warnings'], 'state': state}
        return self.repo.account(s.id, d.id, payload)

    @staticmethod
    def compatible(old, new):
        if new['calendar'][:len(old['calendar'])] != old['calendar']:
            raise ValueError('paper calendar prefix changed')
        for key in ('source', 'price_basis', 'currency', 'volume_unit', 'instruments', 'corporate_action_coverage', 'calendar_provenance'):
            if old[key] != new[key]:
                raise ValueError('paper rules or provenance changed')
        cutoff = old['calendar'][-1]
        for key in ('bars', 'actions'):
            before = [item for item in old[key] if item['date'] <= cutoff]
            common = [item for item in new[key] if item['date'] <= cutoff]
            if before != common:
                raise ValueError('paper historical bars/actions prefix changed')
        if datetime.fromisoformat(new['retrieved_at'].replace('Z', '+00:00')) < datetime.fromisoformat(old['retrieved_at'].replace('Z', '+00:00')):
            raise ValueError('new snapshot retrieval precedes prior snapshot')

    def advance_account(self, account_id, body):
        account = self.repo.require(QuantAccount, account_id)
        self.session.refresh(account)
        # SQL CAS still protects races following this early validation.
        if account.version != body.expected_version:
            raise QuantConflict('paper account version conflict')
        new_row = self.repo.require(QuantDataset, body.dataset_id)
        new = self.repo.decode(new_row); old = self.repo.decode(self.repo.require(QuantDataset, account.dataset_id))
        self.compatible(old, new)
        if new['calendar'][-1] > self.clock().isoformat():
            raise ValueError('cannot advance into future sessions')
        payload = self.repo.decode(account)
        if account.dataset_id == new_row.id:
            return account
        if len(new['calendar']) == len(old['calendar']):
            # Equal canonical market prefix with only operational metadata differences is idempotent.
            return account
        cutoff = max(payload['activation_date'], payload['state']['last_date'])
        eligible = [i for i, day in enumerate(new['calendar']) if day > cutoff]
        if eligible:
            # Persisted pending orders belong to the last processed close. Only
            # newly appended pre-activation history needs a fresh scheduled seed.
            if eligible[0] > len(old['calendar']):
                payload['state']['pending_signal'] = scheduled_signal(new, payload['strategy'], eligible[0] - 1, quantities(payload['state']))
            result = simulate(new, payload['strategy'], payload['initial_cash'], payload['costs'], start_index=eligible[0], state=payload['state'])
            payload['state'] = result['state']; payload['status'] = 'active'; steps = result['steps']
        else:
            # Newly acquired pre-activation history is warmup only: no retrospective fills/NAV.
            payload['state']['last_date'] = new['calendar'][-1]
            payload['state']['pending_signal'] = scheduled_signal(new, payload['strategy'], len(new['calendar']) - 1, quantities(payload['state']))
            payload['status'] = 'awaiting_future_data'; steps = []
        payload['snapshot_as_of'] = new['calendar'][-1]
        return self.repo.advance(account.id, body.expected_version, new_row.id, payload, steps)

    def review(self, run_id, body):
        review = Review.model_validate(body); run = self.repo.require(QuantRun, run_id)
        payload = review.model_dump(mode='json')
        if review.research_project_id is not None:
            project = self.repo.require(ResearchProject, review.research_project_id)
            if project.security_id not in self.repo.decode(run)['strategy']['universe']:
                raise ValueError('hypothesis security outside run universe')
            payload['linked_project_snapshot'] = {'id': project.id, 'version': project.version, 'question': project.question, 'hypothesis': project.hypothesis, 'security_id': project.security_id}
        payload['invalidation_flag'] = review.status == 'invalidated'
        return self.repo.annotate(run_id, 'review', payload, research_project_id=review.research_project_id)

    def compare_holdings(self, run_id):
        run = self.repo.require(QuantRun, run_id); payload = self.repo.decode(run)
        last = payload['result']['signals'][-1]
        targets = last['target_weights']
        rows = []; total = Decimal('0'); missing = []
        for holding in self.session.exec(select(Holding)):
            quote = self.session.exec(select(QuoteSnapshot).where(QuoteSnapshot.security_id == holding.security_id).order_by(QuoteSnapshot.snapshot_time.desc(), QuoteSnapshot.id.desc()).limit(1)).first()
            value = holding.quantity * quote.last_price if quote and quote.last_price is not None else None
            if value is not None:
                total += value
            else:
                missing.append(holding.security_id)
            rows.append({'security_id': holding.security_id, 'quantity': str(holding.quantity), 'saved_market_value': str(value) if value is not None else None, 'quote_as_of': quote.snapshot_time.isoformat() if quote else None, '_value': value})
        actual = {row['security_id']: row for row in rows}
        for sid in sorted(set(actual) | set(payload['strategy']['universe'])):
            if sid not in actual:
                rows.append({'security_id': sid, 'quantity': '0', 'saved_market_value': '0', 'quote_as_of': None, '_value': Decimal('0')})
        for row in rows:
            value = row.pop('_value'); row['actual_weight'] = str(value / total) if value is not None and total else None
            row['target_weight'] = targets.get(str(row['security_id']), '0') if last['status'] == 'ready' else None
        return {'run_id': run_id, 'signal_date': last['date'], 'target_status': last['status'], 'rows': rows, 'known_valuation_total': str(total), 'missing_security_ids': missing, 'interpretation': 'local_saved_holdings_informational_only_no_orders', 'warnings': ['saved_quote_freshness_not_certified', 'weights_over_known_valuations_only']}
