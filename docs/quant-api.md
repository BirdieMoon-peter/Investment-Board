# Quantitative workspace API

All routes use `/api/quant`. GET reads saved local objects only. Dates are ISO dates; timestamps carry timezone. Prices, quantities, costs, cash, weights and return ratios are exact decimal **strings**. Imports contain raw CNY OHLC and share volume. No live broker integration. Legacy adjusted history and actual holdings remain separate.

## Object envelope and routes

Objects flatten their frozen payload alongside `id`, `created_at`, `fingerprint` where present. Strategy revisions have `parent_id`; runs have `strategy_id` and `dataset_id`; accounts have `version`, `strategy_id`, `dataset_id`; annotations have `run_id`, `kind`, `research_project_id`.

| Method | Path | Body / response |
|---|---|---|
| GET | `/templates` | `{templates:[{key,name,parameters:{field:{minimum,maximum,default}},instrument_types}],source_contract,limits,mode}` |
| GET | `/datasets?limit=20` | Array summaries: name/source/retrieved_at/instruments/warnings/bar_count/session_count/coverage_start/coverage_end. No raw bars in list. |
| POST | `/datasets/import` | Dataset below; saved immutable full object, 201; same canonical content deduplicates. |
| POST | `/datasets/acquire` | Acquisition below; explicit bounded Eastmoney fqt0 request. Honors source-center Eastmoney disable; never writes legacy prices. |
| GET | `/datasets/{id}` | Full frozen dataset including bars/calendar/actions/warnings. |
| GET | `/strategies?limit=20&security_id=1` | Array frozen strategy revisions. Optional security filter within latest bounded page. |
| POST | `/strategies` | Strategy below, creates immutable revision (201). Editing passes parent_id. |
| GET | `/strategies/{id}` | Frozen strategy. |
| GET | `/runs?limit=20&security_id=1` | Array summaries: status/strategy/warnings/metrics/holdout_start. |
| POST | `/runs` | Experiment request below; full immutable completed experiment (201). |
| GET | `/runs/{id}` | Full experiment plus latest100 append-only annotations. |
| GET | `/runs/{id}/holdings-comparison` | Local informational actual-v-target, no orders or AI; rows with saved quote timestamps/known denominator/missing IDs. |
| POST | `/runs/{id}/research` | `{critique:false}`; frozen experiment-only explicit AI annotation (201), completed or failed safe error. |
| POST | `/runs/{id}/review` | `{status:"reviewed",note:"...",research_project_id:1,hypothesis:"..."}`; status unreviewed/reviewed/invalidated, note/hypothesis max4000; optional existing project must belong to universe. Append-only annotation with frozen project version and invalidation_flag. |
| GET | `/accounts?limit=20` | Array forward paper account states. |
| POST | `/accounts` | Experiment request plus name, without holdout_date; cash-only forward account (201). |
| GET | `/accounts/{id}` | Account plus append-only `steps:[{id,account_id,session_date,equity,signal,fills,rejections,actions,state,created_at}]`. |
| POST | `/accounts/{id}/advance` | `{expected_version:1,dataset_id:2}`; compatible later snapshot, account plus steps. Same snapshot is idempotent with current version. |
| GET | `/summary` | accounts/awaiting_future_data/active_accounts/latest_account_session/failed_runs/window/mode. Latest100 objects only. |

Lists accept limit1..100. Controlled errors:404 missing object/security,409 stale account version,422 invalid fields/dataset/strategy/prefix,502 disabled/unavailable/invalid acquisition. No provider body or credentials are exposed.

## Dataset import

Dataset imports remain bounded to8 instruments,600 explicit sorted unique sessions,4800 unique bars,100 actions and2000000 encoded JSON bytes. Generated immutable run reports have a separate32000000-byte ceiling to support full8×600 trace reports with accepted high-precision price strings and an early holdout; it remains a finite ceiling; account states, individual ledger steps and annotations retain2000000-byte ceilings. GET templates exposes max_json_bytes (dataset), max_run_json_bytes, max_account_json_bytes and max_annotation_json_bytes. Existing active Security master ID/market/code must match; names/types/rules are user assumptions. Future bars or naive/future retrieval timestamps are rejected. Positive finite Decimal strings only for OHLC; low<=open/close<=high; volume>=0. Missing bars and zero-volume sessions cannot fill.

```json
{
  "name":"Observed raw window", "source":"user_import", "retrieved_at":"2026-10-01T00:00:00Z",
  "price_basis":"raw", "currency":"CNY", "volume_unit":"shares",
  "calendar":["2026-09-01","2026-09-02","2026-09-03"],
  "calendar_provenance":"user_declared_observed_sessions",
  "instruments":[{"security_id":1,"market":"SH","code":"510300","name":"沪深300ETF","instrument_type":"etf","lot_size":100,"settlement_lag":1,"limit_pct":"0.10"}],
  "bars":[
    {"security_id":1,"date":"2026-09-01","open":"4.00","high":"4.10","low":"3.90","close":"4.05","volume":"1000000"},
    {"security_id":1,"date":"2026-09-02","open":"4.05","high":"4.15","low":"4.00","close":"4.10","volume":"1000000"},
    {"security_id":1,"date":"2026-09-03","open":"4.10","high":"4.20","low":"4.05","close":"4.15","volume":"1000000"}
  ],
  "corporate_action_coverage":"unknown", "actions":[]
}
```

Use actual master IDs returned by existing security search. All prices/dates/IDs in the JSON example above are synthetic format illustrations, not acquired market evidence. Coverage enum unknown/declared_complete/declared_none. Dividend value is entitlement per share held at the previous close; same-day dividends are applied before splitting that entitlement base. Actions `{security_id,date,kind:"split",value:"2"}` or `{security_id,date,kind:"cash_dividend",value:"0.1",cash_available_date:"2026-09-03"}`. Action and cash availability dates must be observed calendar sessions. Unknown coverage is research price return only. Declared coverage does not establish certified total return.

Acquisition body `{name,instruments,start_date,end_date,corporate_action_coverage:"unknown",actions:[],calendar?:[...]}`. Range <=1500 days/non-future; independently cap retained latest600 sessions even when vendor ignores lmt. Source returns observed union calendar unless explicitly supplied. Adapter has no retries,5-second per-request timeout,20-second portfolio deadline and2MB response bound per security. Source raw units and normalization are disclosed by GET templates.

## Strategy and experiment

```json
{"name":"ETF momentum","template":"etf_momentum","universe":[1],"parameters":{"lookback":20,"top_k":1,"rebalance_every":5},"max_exposure":"1","parent_id":null}
```

`etf_momentum`:lookback2..252/top_k1..8/rebalance_every1..60. `ma_trend`:ma_window2..252/rebalance_every1..60. `etf_mean_reversion`:ma_window2..252/rebalance_every1..60/entry_deviation decimal[-0.5,-0.001]/exit_deviation decimal[0,0.5]. Defaults come from GET templates. No arbitrary fields/code. ETF templates require explicit ETF instrument types.

```json
{"strategy_id":1,"dataset_id":1,"initial_cash":"100000","costs":{"commission_rate":"0.0003","minimum_commission":"5","sell_tax":"0.0005","slippage":"0.0005","volume_cap":"0.05"},"holdout_date":"2026-09-15"}
```

An experiment with no scheduled ready close before a following execution session is rejected (422) without saving a fake zero run. Holdout defaults to chronological70% boundary (clamped for short windows), leaving training and at least2 held-out sessions. Costs/rules are frozen user assumptions; sell tax applies A shares only, ETF/LOF exempt. Historical policy schedules are not inferred. Next-session opening fills use previous-session volume capacity, current zero-volume halt as an execution approximation, lots/settlement/price-limit/cash guards. Declared actions apply once; stale last-known prices are adjusted on dividend/split ex-dates even when the bar is missing, so dividend cash or receivables cannot double-count value; a supplied raw bar replaces the adjusted reference. causal backward action adjustments prevent known raw jumps from becoming momentum signals.

Full run fields: `engine_version,status,strategy,dataset_fingerprint,strategy_fingerprint,warnings,assumptions,result,baseline,holdout,robustness`. `result`/`baseline` contain `metrics,equity,signals,fills,rejections,actions`. Metrics:net_return/gross_return(full only),annualized_sample_volatility(null if insufficient),max_drawdown,turnover,average_exposure,fees_paid,sample_count,end_nav. Gross return uses a separate costless rerun. Equity `{date,nav,cash,exposure,stale_security_ids}`; signals `{date,status,target_weights,reason,inputs?}` with weights keyed by security ID strings. Ready signals expose per-security inputs: security_id/window_start/window_end/sample_count/raw_latest_close/adjusted_latest_close/selected/action_basis plus momentum_return/adjusted_first_close or moving_average/deviation and mean-reversion thresholds. Fill `{date,signal_date,security_id,side,quantity,price,notional,fee,cash_after}`; rejections include reason. Holdout starts independent cash with prior closes for warmup only; both held-out seeding and paper orders obey the same fixed observed-calendar rebalance clock. An existing paper pending signal is preserved between advances; daily or batched advances produce identical ledger entries. A held-out window without a scheduled ready close before execution is marked unavailable. Robustness same held-out segment has parameter_neighbors and doubled_costs diagnostics, no optimized alpha claim.

Paper `activation_date=max(current Shanghai date, snapshot latest date)` and cash-only initial state. Later imported pre-activation history is warmup only, never books fills/NAV/profits. Future paper sessions must be strictly after activation and <=current Shanghai date. Account preserves frozen strategy/costs and compatible calendar/bars/actions/rules prefixes. Modified historical data cannot rewrite ledger. Versions advance atomically with steps. Status awaiting_future_data is expected immediately after creation.

AI annotations store bounded frozen experiment metrics/assumptions/robustness, safe provider result and strict reference/numeric diagnostics. AI output is labeled model inference; deterministic metrics remain authoritative. GET and review have no model/network effects. Holdings never enter AI snapshot.
