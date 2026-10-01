import {
  categories,
  instrumentTypes,
  syncOutcomes,
  type DataCategory,
  type DataSource,
  type MetadataDraft,
  type PriceSource,
  type SecurityData,
  type SyncResult,
} from '../types/dataCenter'

export class DataCenterError extends Error {
  constructor(
    public readonly code:
      | 'network'
      | 'invalid'
      | 'notFound'
      | 'unavailable'
      | 'request'
      | 'payload',
  ) {
    super(code)
  }
}
type ObjectValue = Record<string, unknown>
function object(value: unknown): ObjectValue {
  if (!value || typeof value !== 'object' || Array.isArray(value))
    throw new DataCenterError('payload')
  return value as ObjectValue
}
function str(value: unknown) {
  if (typeof value !== 'string') throw new DataCenterError('payload')
}
function num(value: unknown) {
  if (
    typeof value !== 'number' ||
    !Number.isFinite(value) ||
    !Number.isInteger(value) ||
    value < 0
  )
    throw new DataCenterError('payload')
}
function bool(value: unknown) {
  if (typeof value !== 'boolean') throw new DataCenterError('payload')
}
function nullable(value: unknown, check = str) {
  if (value !== null) check(value)
}
function array(value: unknown, check: (v: unknown) => void) {
  if (!Array.isArray(value)) throw new DataCenterError('payload')
  value.forEach(check)
}
function choice(value: unknown, choices: readonly string[]) {
  if (typeof value !== 'string' || !choices.includes(value))
    throw new DataCenterError('payload')
}
function strings(o: ObjectValue, keys: string[]) {
  keys.forEach((k) => str(o[k]))
}
function nullStrings(o: ObjectValue, keys: string[]) {
  keys.forEach((k) => nullable(o[k]))
}
function decimal(value: unknown) {
  str(value)
  if (!/^-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?$/.test(value as string))
    throw new DataCenterError('payload')
}
function attempt(value: unknown) {
  const o = object(value)
  ;[
    'id',
    'security_id',
    'records_received',
    'records_written',
    'records_rejected',
  ].forEach((k) => num(o[k]))
  strings(o, [
    'provider_key',
    'category',
    'status',
    'state',
    'started_at',
    'persisted_coverage',
    'write_attribution',
  ])
  nullStrings(o, ['finished_at', 'error_code'])
}
export function validateSource(value: unknown): DataSource {
  const o = object(value)
  strings(o, ['vendor_key', 'name', 'scope_note'])
  bool(o.enabled)
  bool(o.configurable)
  array(o.managed_categories, str)
  if (o.index_context_disclosures !== undefined) array(o.index_context_disclosures, str)
  array(o.endpoints, (value) => {
    const e = object(value)
    strings(e, [
      'key',
      'category',
      'payload_format',
      'endpoint_url',
      'frequency',
      'time_rule',
      'price_basis',
    ])
    choice(e.integration_scope, [
      'managed_security',
      'untracked_homepage/lookup',
      'planned',
    ])
    array(e.limitations, str)
    array(e.fields, (value) => {
      const f = object(value)
      strings(f, [
        'raw_field',
        'target_field',
        'raw_type',
        'raw_unit',
        'normalized_unit',
        'normalized_type',
        'conversion',
        'missing_rule',
      ])
      choice(f.verification, ['parser_contract', 'sample_verified', 'unverified'])
    })
  })
  const r = object(o.runtime)
  choice(r.state, ['unknown', 'failed', 'attempted'])
  array(r.recent_attempts, attempt)
  nullable(r.latest_attempt, attempt)
  nullable(r.last_succeeded_attempt, attempt)
  return value as DataSource
}
export function validateSecurityData(value: unknown): SecurityData {
  const o = object(value),
    s = object(o.security)
  num(s.id)
  strings(s, ['code', 'market', 'name', 'status', 'created_at', 'updated_at'])
  nullable(s.industry)
  const m = object(o.metadata)
  choice(m.instrument_type, instrumentTypes)
  choice(m.effective_instrument_type, instrumentTypes)
  strings(m, ['classification_origin', 'provenance_note'])
  nullStrings(m, [
    'benchmark_code',
    'benchmark_name',
    'manager',
    'assets_as_of',
    'source_key',
    'as_of',
    'provider_fields_source',
    'publication_at',
  ])
  nullable(m.source_id, num)
  array(m.overlay_scope, str)
  ;['management_fee', 'custody_fee', 'fund_assets'].forEach((k) =>
    nullable(m[k], decimal),
  )
  const datasets = object(o.categories)
  categories.forEach((k) => {
    const d = object(datasets[k])
    choice(d.health, [
      'healthy',
      'stale',
      'partial',
      'failed',
      'unknown',
      'not_applicable',
    ])
    nullStrings(d, [
      'source_key',
      'unit',
      'frequency',
      'observation_at',
      'fetched_at',
      'coverage_start',
      'coverage_end',
    ])
    strings(d, [
      'price_basis',
      'observation_time_note',
      'freshness',
      'coverage',
      'unit_provenance',
      'freshness_basis',
    ])
    choice(d.observation_precision, ['unknown', 'date', 'datetime'])
    nullable(d.freshness_threshold_days, num)
    array(d.context_disclosures, str)
    array(d.recent_attempts, attempt)
    nullable(d.latest_attempt, attempt)
    array(d.unresolved_issues, (v) => {
      const i = object(v)
      num(i.id)
      nullable(i.run_id, num)
      strings(i, ['code', 'severity', 'message', 'created_at'])
      nullable(i.resolved_at)
    })
    ;[
      'valuation_basis',
      'received_count_unit',
      'written_count_unit',
      'publication_at',
    ].forEach((k) => {
      if (d[k] !== undefined) nullable(d[k])
    })
  })
  array(o.nav_observations, (v) => {
    const n = object(v)
    strings(n, ['nav_date', 'fetched_at', 'source_key'])
    nullable(n.published_at)
    decimal(n.value)
    choice(n.nav_kind, ['unit_nav', 'cumulative_nav', 'iopv'])
  })
  num(o.nav_limit)
  const c = object(o.calendar)
  bool(c.verified)
  str(c.note)
  return value as SecurityData
}
function validateSync(value: unknown): SyncResult {
  const o = object(value)
  num(o.security_id)
  array(o.warnings, str)
  const data = validateSecurityData(o.data)
  if (data.security.id !== o.security_id) throw new DataCenterError('payload')
  const outcomes = object(o.category_outcomes)
  Object.entries(outcomes).forEach(([key, value]) => {
    choice(key, categories)
    const r = object(value)
    choice(r.outcome, syncOutcomes)
    ;['received', 'written'].forEach((k) => {
      if (r[k] !== undefined) nullable(r[k], num)
    })
    ;['reason', 'received_count_unit', 'written_count_unit'].forEach((k) => {
      if (r[k] !== undefined) nullable(r[k])
    })
    if (r.resolved_instrument_type !== undefined && r.resolved_instrument_type !== null)
      choice(r.resolved_instrument_type, instrumentTypes)
  })
  return value as SyncResult
}
async function request<T>(
  path: string,
  validate: (v: unknown) => T,
  signal?: AbortSignal,
  method = 'GET',
  body?: unknown,
): Promise<T> {
  let response: Response
  try {
    response = await fetch(`/api/data/${path}`, {
      method,
      signal,
      cache: 'no-store',
      ...(body === undefined
        ? {}
        : {
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
          }),
    })
  } catch (error) {
    if (signal?.aborted || (error instanceof DOMException && error.name === 'AbortError'))
      throw error
    throw new DataCenterError('network')
  }
  if (!response.ok)
    throw new DataCenterError(
      response.status === 404
        ? 'notFound'
        : response.status === 422
          ? 'invalid'
          : response.status === 503
            ? 'unavailable'
            : 'request',
    )
  let value: unknown
  try {
    value = await response.json()
  } catch {
    throw new DataCenterError('payload')
  }
  return validate(value)
}
function id(value: number) {
  if (!Number.isInteger(value) || value <= 0) throw new DataCenterError('invalid')
  return value
}
export function fetchDataSources(signal?: AbortSignal) {
  return request(
    'sources',
    (v) => {
      const o = object(v)
      if (!Array.isArray(o.sources)) throw new DataCenterError('payload')
      return o.sources.map(validateSource)
    },
    signal,
  )
}
export function saveDataSource(key: string, enabled: boolean, signal?: AbortSignal) {
  if (
    !['eastmoney', 'sina', 'netease', 'tencent', 'ifeng'].includes(key) ||
    typeof enabled !== 'boolean'
  )
    throw new DataCenterError('invalid')
  return request(
    `sources/${key}`,
    (value) => {
      const source = validateSource(value)
      if (source.vendor_key !== key) throw new DataCenterError('payload')
      return source
    },
    signal,
    'PUT',
    { enabled },
  )
}
export function fetchSecurityData(securityId: number, signal?: AbortSignal) {
  return request(
    `securities/${id(securityId)}`,
    (v) => {
      const data = validateSecurityData(v)
      if (data.security.id !== securityId) throw new DataCenterError('payload')
      return data
    },
    signal,
  )
}
export function syncSecurityData(
  securityId: number,
  category: DataCategory,
  priceSource?: PriceSource,
  signal?: AbortSignal,
) {
  if (
    !categories.includes(category) ||
    (priceSource !== undefined &&
      (category !== 'price_history' ||
        !['eastmoney', 'sina', 'netease'].includes(priceSource)))
  )
    throw new DataCenterError('invalid')
  return request(
    `securities/${id(securityId)}/sync`,
    (v) => {
      const result = validateSync(v)
      if (
        result.security_id !== securityId ||
        !result.category_outcomes[category] ||
        Object.keys(result.category_outcomes).some((key) => key !== category)
      )
        throw new DataCenterError('payload')
      return result
    },
    signal,
    'POST',
    { categories: [category], ...(priceSource ? { price_source: priceSource } : {}) },
  )
}
export function saveSecurityMetadata(
  securityId: number,
  draft: MetadataDraft,
  signal?: AbortSignal,
) {
  if (
    !instrumentTypes.includes(draft.instrument_type) ||
    (draft.benchmark_code !== null && !/^(SH|SZ):\d{6}$/.test(draft.benchmark_code)) ||
    (draft.benchmark_name !== null &&
      (typeof draft.benchmark_name !== 'string' || draft.benchmark_name.length > 500))
  )
    throw new DataCenterError('invalid')
  return request(
    `securities/${id(securityId)}/metadata`,
    (v) => {
      const d = validateSecurityData(v)
      if (d.security.id !== securityId) throw new DataCenterError('payload')
      return d
    },
    signal,
    'PUT',
    {
      instrument_type: draft.instrument_type,
      benchmark_code: draft.benchmark_code,
      benchmark_name: draft.benchmark_name,
    },
  )
}
// Fees are fractions in the normalized contract. Quote/ROE percentage values are handled separately.
export function feePercentage(value: string | null): string {
  if (value === null) return '—'
  const match = /^([+-]?)(\d+)(?:\.(\d+))?(?:[eE]([+-]?\d+))?$/.exec(value)
  if (!match) throw new DataCenterError('payload')
  const [, sign, whole, fraction = '', exponent = '0'] = match
  const digits = whole + fraction
  const point = BigInt(whole.length + 2) + BigInt(exponent)
  // Preserve exact values without expanding arbitrarily large exponent payloads.
  if (point > 1000n || point < -1000n) {
    return `${sign}${whole}${fraction ? `.${fraction}` : ''}e${BigInt(exponent) + 2n}%`
  }
  const position = Number(point)
  const expanded =
    position <= 0
      ? `0.${'0'.repeat(-position)}${digits}`
      : position >= digits.length
        ? digits + '0'.repeat(position - digits.length)
        : `${digits.slice(0, position)}.${digits.slice(position)}`
  const [integer, decimalPart = ''] = expanded.split('.')
  const integerTrimmed = integer.replace(/^0+(?=\d)/, '')
  const decimalTrimmed = decimalPart.replace(/0+$/, '')
  return `${sign === '-' ? '-' : ''}${integerTrimmed}${decimalTrimmed ? `.${decimalTrimmed}` : ''}%`
}
