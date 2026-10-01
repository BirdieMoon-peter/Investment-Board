import {
  categories,
  type AcquisitionAttempt,
  type DataSource,
  type SecurityData,
} from '../types/dataCenter'
export const attemptFixture: AcquisitionAttempt = {
  id: 1,
  provider_key: 'eastmoney_price_history',
  security_id: 1,
  category: 'price_history',
  status: 'failed',
  state: 'failed',
  started_at: '2026-10-01T01:00:00Z',
  finished_at: '2026-10-01T01:00:01Z',
  records_received: 0,
  records_written: 0,
  records_rejected: 0,
  error_code: 'fetch_error',
  persisted_coverage: 'unknown',
  write_attribution: 'unknown',
}
export function sourceFixture(vendor_key = 'eastmoney', configurable = true): DataSource {
  return {
    vendor_key,
    name: vendor_key === 'eastmoney' ? 'Eastmoney' : vendor_key,
    enabled: true,
    configurable,
    managed_categories: configurable ? ['price_history'] : [],
    scope_note: 'managed only',
    endpoints: [
      {
        key: `${vendor_key}_prices`,
        category: 'price_history',
        payload_format: 'JSON',
        endpoint_url: 'https://example.test/history',
        frequency: 'daily',
        time_rule: 'date only',
        price_basis: 'qfq',
        integration_scope: configurable
          ? 'managed_security'
          : 'untracked_homepage/lookup',
        limitations: ['Bounded source'],
        fields: [
          {
            raw_field: 'close',
            target_field: 'close_price',
            raw_type: 'string',
            raw_unit: 'CNY',
            normalized_unit: 'CNY',
            normalized_type: 'Decimal',
            conversion: 'identity',
            missing_rule: 'None if absent',
            verification: 'parser_contract',
          },
        ],
      },
    ],
    runtime: {
      state: 'unknown',
      recent_attempts: [],
      latest_attempt: null,
      last_succeeded_attempt: null,
    },
  }
}
export function securityFixture(id = 1): SecurityData {
  return {
    security: {
      id,
      market: 'SH',
      code: '510300',
      name: `Security ${id}`,
      industry: 'ETF',
      status: 'active',
      created_at: '2026-09-01T00:00:00Z',
      updated_at: '2026-10-01T00:00:00Z',
    },
    metadata: {
      instrument_type: 'etf',
      effective_instrument_type: 'etf',
      classification_origin: 'fund_profile',
      benchmark_code: null,
      benchmark_name: null,
      manager: null,
      management_fee: '0.005',
      custody_fee: '0.001',
      fund_assets: null,
      assets_as_of: null,
      source_id: null,
      source_key: null,
      as_of: null,
      overlay_scope: [],
      provider_fields_source: null,
      publication_at: null,
      provenance_note: 'Manual scope only',
    },
    categories: Object.fromEntries(
      categories.map((k) => [
        k,
        {
          health: 'unknown',
          source_key: null,
          unit: null,
          frequency: null,
          price_basis: 'unknown',
          observation_at: null,
          observation_precision: 'unknown',
          observation_time_note: 'unavailable',
          fetched_at: null,
          coverage_start: null,
          coverage_end: null,
          recent_attempts: [],
          unresolved_issues: [],
          latest_attempt: null,
          freshness: 'unknown',
          coverage: 'unknown',
          context_disclosures: [],
          unit_provenance: 'persisted_or_unknown',
          freshness_threshold_days: null,
          freshness_basis: 'elapsed_no_calendar',
        },
      ]),
    ) as unknown as SecurityData['categories'],
    nav_observations: [],
    nav_limit: 100,
    calendar: { verified: false, note: 'No calendar' },
  }
}
export const catalogFixture = ['eastmoney', 'sina', 'netease', 'tencent', 'ifeng'].map(
  (k) => sourceFixture(k, !['tencent', 'ifeng'].includes(k)),
)
export const watchlistFixture = [1, 2].map((security_id) => ({
  security_id,
  market: 'SH',
  code: '510300',
  name: `Security ${security_id}`,
  industry: 'ETF',
  last_price: null,
  change_percent: null,
  snapshot_time: null,
}))
export function deferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (error: unknown) => void
  const promise = new Promise<T>((yes, no) => {
    resolve = yes
    reject = no
  })
  return { promise, resolve, reject }
}
export const jsonResponse = (value: unknown) => ({
  ok: true,
  status: 200,
  json: async () => value,
})
