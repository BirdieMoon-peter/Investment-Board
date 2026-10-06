"""Pure Decimal close-to-next-open engine. No model, provider, holdings or DB access."""
from copy import deepcopy
from decimal import Decimal, localcontext, ROUND_FLOOR

ENGINE_VERSION = 'quant-daily-1'
D = Decimal
ZERO = D('0')


def plain(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [plain(v) for v in value]
    return value


def maps(dataset):
    return ({(b['date'], b['security_id']): b for b in dataset['bars']}, {i['security_id']: i for i in dataset['instruments']})


def signal(dataset, strategy, index, quantities=None, baseline=False):
    with localcontext() as ctx:
        ctx.prec = 40
        return _signal(dataset, strategy, index, quantities, baseline)


def _signal(dataset, strategy, index, quantities=None, baseline=False):
    calendar = dataset['calendar']; bars, _ = maps(dataset)
    universe = strategy['universe']; params = strategy['parameters']; day = calendar[index]
    window = params.get('lookback', params.get('ma_window', 20))
    first = index - window if strategy['template'] == 'etf_momentum' else index - window + 1
    if first < 0:
        return {'date': day, 'status': 'warmup', 'target_weights': {}, 'reason': 'insufficient_prior_closes'}
    histories = {}
    for sid in universe:
        history = [bars.get((d, sid)) for d in calendar[first:index + 1]]
        if any(b is None for b in history):
            return {'date': day, 'status': 'unavailable', 'target_weights': {}, 'reason': 'missing_signal_bar'}
        adjusted = []
        for date_value, bar in zip(calendar[first:index + 1], history):
            close = D(bar['close'])
            for action in dataset['actions']:
                if action['security_id'] == sid and date_value < action['date'] <= day:
                    close = close / D(action['value']) if action['kind'] == 'split' else close - D(action['value'])
            if close <= 0:
                return {'date': day, 'status': 'unavailable', 'target_weights': {}, 'reason': 'invalid_action_price_adjustment'}
            adjusted.append(close)
        histories[sid] = adjusted
    if baseline:
        selected = universe
    elif strategy['template'] == 'etf_momentum':
        ranked = sorted(universe, key=lambda sid: (-(histories[sid][-1] / histories[sid][0] - 1), sid))
        selected = [sid for sid in ranked if histories[sid][-1] > histories[sid][0]][:params['top_k']]
    elif strategy['template'] == 'ma_trend':
        selected = [sid for sid, h in histories.items() if h[-1] > sum(h) / len(h)]
    else:
        selected = []
        for sid, h in histories.items():
            deviation = h[-1] / (sum(h) / len(h)) - 1
            if deviation <= D(params['entry_deviation']) or ((quantities or {}).get(sid, ZERO) > 0 and deviation < D(params['exit_deviation'])):
                selected.append(sid)
    weight = D(strategy['max_exposure']) / len(selected) if selected else ZERO
    inputs = []
    for sid, history in histories.items():
        average = sum(history) / len(history)
        detail = {'security_id': sid, 'window_start': calendar[first], 'window_end': day, 'sample_count': len(history), 'raw_latest_close': bars[(day, sid)]['close'], 'adjusted_latest_close': str(history[-1]), 'selected': sid in selected, 'action_basis': 'declared_actions_known_at_signal_date_only'}
        if strategy['template'] == 'etf_momentum':
            detail.update(adjusted_first_close=str(history[0]), momentum_return=str(history[-1] / history[0] - 1))
        else:
            detail.update(moving_average=str(average), deviation=str(history[-1] / average - 1))
        if strategy['template'] == 'etf_mean_reversion':
            detail.update(entry_deviation=params['entry_deviation'], exit_deviation=params['exit_deviation'])
        inputs.append(detail)
    return {'date': day, 'status': 'ready', 'target_weights': {str(sid): str(weight if sid in selected else ZERO) for sid in universe}, 'inputs': inputs, 'reason': 'same_universe_hold_baseline' if baseline else strategy['template']}


def scheduled_signal(dataset, strategy, index, held=None, baseline=False):
    """One fixed observed-calendar clock, independent of advance request partitioning."""
    if not baseline and index % strategy['parameters']['rebalance_every'] != 0:
        return None
    current = signal(dataset, strategy, index, held, baseline)
    return current if current['status'] == 'ready' else None


def initial_state(cash, last_date=None):
    return {'cash': str(cash), 'positions': {}, 'last_prices': {}, 'receivables': [], 'applied_actions': [], 'pending_signal': None, 'last_date': last_date, 'fees_paid': '0', 'traded_notional': '0'}


def quantities(state):
    return {int(sid): sum((D(lot['quantity']) for lot in lots), ZERO) for sid, lots in state['positions'].items()}


def net_value(state, prices):
    return D(state['cash']) + sum((q * prices.get(sid, ZERO) for sid, q in quantities(state).items()), ZERO) + sum((D(r['amount']) for r in state['receivables']), ZERO)


def round_lot(qty, size):
    return (qty / size).to_integral_value(rounding=ROUND_FLOOR) * size


def simulate(dataset, strategy, cash, costs, *, start_index=0, state=None, baseline=False, seed_previous=False):
    """When supplied state, append sessions only; signal warmup still reads frozen prefix."""
    with localcontext() as ctx:
        ctx.prec = 40
        return _simulate(dataset, strategy, cash, costs, start_index=start_index, state=state, baseline=baseline, seed_previous=seed_previous)


def _simulate(dataset, strategy, cash, costs, *, start_index, state, baseline, seed_previous):
    has_saved_state = state is not None
    state = deepcopy(state) if has_saved_state else initial_state(cash)
    calendar = dataset['calendar']; bars, instruments = maps(dataset)
    if seed_previous and start_index > 0 and not has_saved_state:
        state['pending_signal'] = scheduled_signal(dataset, strategy, start_index - 1, quantities(state), baseline)
    equity = []; signals = []; fills = []; rejected = []; action_events = []; steps = []
    for index in range(start_index, len(calendar)):
        day = calendar[index]; daily_fills = []; daily_rejected = []; daily_actions = []
        before = quantities(state)
        for action in dataset['actions']:
            key = f"{action['date']}:{action['security_id']}:{action['kind']}"
            if action['date'] != day or key in state['applied_actions']:
                continue
            sid = str(action['security_id']); qty = before.get(action['security_id'], ZERO)
            if action['kind'] == 'split':
                for lot in state['positions'].get(sid, []):
                    lot['quantity'] = str(D(lot['quantity']) * D(action['value']))
                if sid in state['last_prices']:
                    state['last_prices'][sid] = str(D(state['last_prices'][sid]) / D(action['value']))
                event = {'date': day, 'security_id': action['security_id'], 'kind': 'split', 'ratio': action['value'], 'eligible_quantity': str(qty)}
            else:
                amount = qty * D(action['value'])
                # The stored last-known cum-dividend price must move to the ex-date
                # reference even if this session has no bar. A supplied raw bar below
                # replaces this reference, so it is never adjusted twice.
                if sid in state['last_prices']:
                    adjusted = D(state['last_prices'][sid]) - D(action['value'])
                    if adjusted <= 0:
                        raise ValueError('dividend exceeds last-known raw price reference')
                    state['last_prices'][sid] = str(adjusted)
                state['receivables'].append({'amount': str(amount), 'available_date': action['cash_available_date']})
                event = {'date': day, 'security_id': action['security_id'], 'kind': 'cash_dividend', 'amount': str(amount), 'available_date': action['cash_available_date'], 'eligible_quantity': str(qty)}
            state['applied_actions'].append(key); daily_actions.append(event)
        matured = [r for r in state['receivables'] if r['available_date'] <= day]
        state['cash'] = str(D(state['cash']) + sum((D(r['amount']) for r in matured), ZERO))
        state['receivables'] = [r for r in state['receivables'] if r['available_date'] > day]
        open_prices = {int(k): D(v) for k, v in state['last_prices'].items()}
        for sid in strategy['universe']:
            bar = bars.get((day, sid))
            if bar:
                open_prices[sid] = D(bar['open'])
        pending = state['pending_signal']
        if pending is not None:
            nav_open = net_value(state, open_prices)
            targets = pending['target_weights']; held = quantities(state)
            intents = []
            for sid in strategy['universe']:
                bar = bars.get((day, sid)); weight = D(targets.get(str(sid), '0')); rules = instruments[sid]; size = D(rules['lot_size'])
                if not bar:
                    daily_rejected.append({'date': day, 'signal_date': pending['date'], 'security_id': sid, 'reason': 'missing_open_bar'}); continue
                desired = round_lot(nav_open * weight / D(bar['open']), size)
                delta = desired - held.get(sid, ZERO)
                if delta:
                    intents.append((delta > 0, sid, abs(delta)))
            for buy, sid, requested in sorted(intents):
                rules = instruments[sid]; bar = bars[(day, sid)]; size = D(rules['lot_size']); direction = 'buy' if buy else 'sell'
                def reject(reason, quantity=requested):
                    daily_rejected.append({'date': day, 'signal_date': pending['date'], 'security_id': sid, 'side': direction, 'quantity': str(quantity), 'reason': reason})
                volume = D(bar['volume'])
                if volume == 0:
                    reject('zero_volume_halt'); continue
                previous_bar = bars.get((calendar[index - 1], sid)) if index > 0 else None
                if previous_bar is None:
                    reject('missing_previous_bar_for_capacity'); continue
                if rules['limit_pct'] is not None:
                    if previous_bar is None:
                        reject('missing_previous_close_for_limit'); continue
                    previous_close = D(previous_bar['close'])
                    # Splits are accounted before matching the raw-price limit reference.
                    for action in dataset['actions']:
                        if action['date'] == day and action['security_id'] == sid:
                            previous_close = previous_close / D(action['value']) if action['kind'] == 'split' else previous_close - D(action['value'])
                    limit = D(rules['limit_pct'])
                    if (buy and D(bar['open']) >= previous_close * (1 + limit)) or (not buy and D(bar['open']) <= previous_close * (1 - limit)):
                        reject('one_sided_price_limit'); continue
                qty = round_lot(min(requested, D(previous_bar['volume']) * D(costs['volume_cap'])), size)
                if qty < round_lot(requested, size):
                    reject('volume_cap_partial', requested - qty)
                if not buy:
                    eligible = sum((D(lot['quantity']) for lot in state['positions'].get(str(sid), []) if rules['settlement_lag'] == 0 or lot['buy_date'] < day), ZERO)
                    if qty > eligible:
                        reject('settlement_lag_partial', qty - eligible)
                        qty = round_lot(eligible, size)
                price = D(bar['open']) * (1 + D(costs['slippage']) if buy else 1 - D(costs['slippage']))
                def fee(q):
                    if q <= 0:
                        return ZERO
                    return max(D(costs['minimum_commission']), q * price * D(costs['commission_rate'])) + (ZERO if buy else q * price * D(costs['sell_tax']) if rules['instrument_type'] == 'a_share' else ZERO)
                if buy and qty * price + fee(qty) > D(state['cash']):
                    # Solve piecewise minimum/rate commission bound, then at most one lot correction.
                    maximum = min((D(state['cash']) - D(costs['minimum_commission'])) / price, D(state['cash']) / (price * (1 + D(costs['commission_rate']))))
                    affordable = max(ZERO, round_lot(maximum, size))
                    reject('insufficient_cash_partial', max(ZERO, qty - affordable)); qty = min(qty, affordable)
                if qty <= 0:
                    reject('below_lot_or_unavailable_cash'); continue
                paid = fee(qty); notional = qty * price
                if not buy and D(state['cash']) + notional < paid:
                    reject('insufficient_cash_for_sell_fee'); continue
                state['cash'] = str(D(state['cash']) - notional - paid if buy else D(state['cash']) + notional - paid)
                if buy:
                    state['positions'].setdefault(str(sid), []).append({'quantity': str(qty), 'buy_date': day})
                else:
                    remaining = qty
                    for lot in state['positions'].get(str(sid), []):
                        if rules['settlement_lag'] and lot['buy_date'] >= day:
                            continue
                        taken = min(remaining, D(lot['quantity'])); lot['quantity'] = str(D(lot['quantity']) - taken); remaining -= taken
                    state['positions'][str(sid)] = [lot for lot in state['positions'][str(sid)] if D(lot['quantity']) > 0]
                state['fees_paid'] = str(D(state['fees_paid']) + paid)
                state['traded_notional'] = str(D(state['traded_notional']) + notional)
                daily_fills.append({'date': day, 'signal_date': pending['date'], 'security_id': sid, 'side': direction, 'quantity': str(qty), 'price': str(price), 'notional': str(notional), 'fee': str(paid), 'cash_after': state['cash']})
        stale = []
        for sid in strategy['universe']:
            bar = bars.get((day, sid))
            if bar:
                state['last_prices'][str(sid)] = bar['close']
            elif quantities(state).get(sid, ZERO):
                stale.append(sid)
        nav = net_value(state, {int(k): D(v) for k, v in state['last_prices'].items()})
        invested = nav - D(state['cash']) - sum((D(r['amount']) for r in state['receivables']), ZERO)
        point = {'date': day, 'nav': str(nav), 'cash': state['cash'], 'exposure': str(invested / nav if nav else ZERO), 'stale_security_ids': stale}
        current = signal(dataset, strategy, index, quantities(state), baseline)
        should_trade = (index % strategy['parameters']['rebalance_every'] == 0) or baseline
        # Baseline is initial hold/equal-weight, no daily rebalance after its initial allocation.
        if baseline and (quantities(state) or any(fills) or any(daily_fills)):
            should_trade = False
        state['pending_signal'] = current if should_trade and current['status'] == 'ready' else None
        state['last_date'] = day
        equity.append(point); signals.append(current); fills.extend(daily_fills); rejected.extend(daily_rejected); action_events.extend(daily_actions)
        steps.append((day, {'equity': point, 'signal': current, 'fills': daily_fills, 'rejections': daily_rejected, 'actions': daily_actions, 'state': deepcopy(state)}))
    return {'state': state, 'equity': equity, 'signals': signals, 'fills': fills, 'rejections': rejected, 'actions': action_events, 'metrics': metrics(equity, cash, state), 'steps': steps}


def metrics(equity, cash, state):
    values = [D(cash)] + [D(p['nav']) for p in equity]
    returns = [b / a - 1 for a, b in zip(values, values[1:]) if a > 0]
    peak = values[0]; drawdown = ZERO
    for value in values:
        peak = max(peak, value)
        if peak > 0:
            drawdown = max(drawdown, 1 - value / peak)
    volatility = None
    if len(returns) > 1:
        mean = sum(returns) / len(returns)
        variance = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
        volatility = str((variance * 252).sqrt())
    return {'net_return': str(values[-1] / D(cash) - 1), 'annualized_sample_volatility': volatility, 'max_drawdown': str(drawdown), 'turnover': str(D(state['traded_notional']) / D(cash)), 'average_exposure': str(sum((D(p['exposure']) for p in equity), ZERO) / len(equity) if equity else ZERO), 'fees_paid': state['fees_paid'], 'sample_count': len(equity), 'end_nav': str(values[-1])}


def result_only(result):
    return {k: v for k, v in result.items() if k not in {'steps', 'state'}}


def experiment(dataset, strategy, cash, costs, holdout_date=None):
    calendar = dataset['calendar']
    split = holdout_date or calendar[max(1, min(len(calendar) - 2, int(len(calendar) * 0.7)))]
    if split not in calendar or calendar.index(split) < 1 or calendar.index(split) >= len(calendar) - 1:
        raise ValueError('holdout must leave training and at least two held-out sessions')
    start = calendar.index(split)
    full = simulate(dataset, strategy, cash, costs)
    costless = dict(costs, commission_rate='0', minimum_commission='0', sell_tax='0', slippage='0')
    gross = simulate(dataset, strategy, cash, costless)
    baseline = simulate(dataset, strategy, cash, costs, baseline=True)
    oos = simulate(dataset, strategy, cash, costs, start_index=start, seed_previous=True)
    oos_baseline = simulate(dataset, strategy, cash, costs, start_index=start, baseline=True, seed_previous=True)
    doubled = {k: str(D(v) * 2) if k != 'volume_cap' else v for k, v in costs.items()}
    cost_test = simulate(dataset, strategy, cash, doubled, start_index=start, seed_previous=True)
    key = 'lookback' if strategy['template'] == 'etf_momentum' else 'ma_window'
    neighbors = []
    for change in [-1, 1]:
        candidate = deepcopy(strategy); candidate['parameters'][key] = max(2, min(252, candidate['parameters'][key] + change))
        if candidate['parameters'][key] == strategy['parameters'][key]:
            continue
        tested = simulate(dataset, candidate, cash, costs, start_index=start, seed_previous=True)
        neighbors.append({'parameter': key, 'value': candidate['parameters'][key], 'metrics': tested['metrics']})
    full['metrics']['gross_return'] = gross['metrics']['net_return']
    return {'engine_version': ENGINE_VERSION, 'status': 'completed', 'strategy': deepcopy(strategy), 'assumptions': {'initial_cash': str(cash), 'costs': deepcopy(costs), 'calendar': dataset['calendar_provenance'], 'corporate_action_coverage': dataset['corporate_action_coverage'], 'instrument_rules': deepcopy(dataset['instruments']), 'execution': 'close_signal_next_session_open', 'volume_capacity': 'previous_session_observed_shares', 'halt_check': 'current_session_zero_volume_ex_post_execution_approximation', 'sell_tax': 'constant_user_assumption_a_shares_only_etf_lof_exempt_not_historical_policy_certification', 'signal_action_basis': 'causal_backward_price_adjustment_for_declared_actions_only', 'return_label': 'research_price_return' if dataset['corporate_action_coverage'] == 'unknown' else 'user_declared_action_accounted_return'}, 'result': result_only(full), 'baseline': result_only(baseline), 'holdout': {'start_date': split, 'initial_cash': str(cash), 'warmup': 'prior_closes_only_independent_cash', 'result': result_only(oos), 'baseline': result_only(oos_baseline)}, 'robustness': {'segment': 'same_chronological_holdout', 'parameter_neighbors': neighbors, 'doubled_costs': {'costs': doubled, 'metrics': cost_test['metrics']}, 'interpretation': 'diagnostic_not_optimized_alpha'}}
