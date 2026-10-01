export const categories = [
  'announcements',
  'news',
  'price_history',
  'quote_snapshot',
  'financial_metrics',
  'company_profile',
  'fund_nav',
  'fund_profile',
] as const
export type DataCategory = (typeof categories)[number]
export const instrumentTypes = ['unknown', 'stock', 'etf', 'lof', 'index'] as const
export type InstrumentType = (typeof instrumentTypes)[number]
export type PriceSource = 'eastmoney' | 'sina' | 'netease'
export interface AcquisitionAttempt {
  id: number
  provider_key: string
  security_id: number
  category: string
  status: string
  state: string
  started_at: string
  finished_at: string | null
  records_received: number
  records_written: number
  records_rejected: number
  error_code: string | null
  persisted_coverage: string
  write_attribution: string
}
export interface NativeField {
  raw_field: string
  target_field: string
  raw_type: string
  raw_unit: string
  normalized_unit: string
  normalized_type: string
  conversion: string
  missing_rule: string
  verification: 'parser_contract' | 'sample_verified' | 'unverified'
}
export interface SourceEndpoint {
  key: string
  category: string
  payload_format: string
  endpoint_url: string
  frequency: string
  time_rule: string
  price_basis: string
  fields: NativeField[]
  integration_scope: 'managed_security' | 'untracked_homepage/lookup' | 'planned'
  limitations: string[]
}
export interface DataSource {
  vendor_key: string
  name: string
  enabled: boolean
  configurable: boolean
  managed_categories: string[]
  endpoints: SourceEndpoint[]
  scope_note: string
  index_context_disclosures?: string[]
  runtime: {
    state: 'unknown' | 'failed' | 'attempted'
    recent_attempts: AcquisitionAttempt[]
    latest_attempt: AcquisitionAttempt | null
    last_succeeded_attempt: AcquisitionAttempt | null
  }
}
export interface DatasetHealth {
  health: 'healthy' | 'stale' | 'partial' | 'failed' | 'unknown' | 'not_applicable'
  source_key: string | null
  unit: string | null
  frequency: string | null
  price_basis: string
  observation_at: string | null
  observation_precision: 'unknown' | 'date' | 'datetime'
  observation_time_note: string
  fetched_at: string | null
  coverage_start: string | null
  coverage_end: string | null
  recent_attempts: AcquisitionAttempt[]
  latest_attempt: AcquisitionAttempt | null
  unresolved_issues: {
    id: number
    run_id: number | null
    code: string
    severity: string
    message: string
    created_at: string
    resolved_at: string | null
  }[]
  freshness: string
  coverage: string
  context_disclosures: string[]
  unit_provenance: string
  freshness_threshold_days: number | null
  freshness_basis: string
  valuation_basis?: string | null
  received_count_unit?: string | null
  written_count_unit?: string | null
  publication_at?: string | null
}
export interface SecurityMetadata {
  instrument_type: InstrumentType
  effective_instrument_type: InstrumentType
  classification_origin: string
  benchmark_code: string | null
  benchmark_name: string | null
  manager: string | null
  management_fee: string | null
  custody_fee: string | null
  fund_assets: string | null
  assets_as_of: string | null
  source_id: number | null
  source_key: string | null
  as_of: string | null
  overlay_scope: string[]
  provider_fields_source: string | null
  publication_at: string | null
  provenance_note: string
}
export interface SecurityData {
  security: {
    id: number
    code: string
    market: string
    name: string
    industry: string | null
    status: string
    created_at: string
    updated_at: string
  }
  metadata: SecurityMetadata
  categories: Record<DataCategory, DatasetHealth>
  nav_observations: {
    nav_date: string
    nav_kind: 'unit_nav' | 'cumulative_nav' | 'iopv'
    value: string
    fetched_at: string
    published_at: string | null
    source_key: string
  }[]
  nav_limit: number
  calendar: { verified: boolean; note: string }
}
export const syncOutcomes = [
  'succeeded',
  'partial',
  'empty',
  'skipped',
  'failed_fetch',
  'failed_persist',
  'disabled',
  'not_applicable',
  'unavailable',
] as const
export interface SyncResult {
  security_id: number
  category_outcomes: Partial<
    Record<
      DataCategory,
      {
        outcome: (typeof syncOutcomes)[number]
        reason?: string | null
        received?: number | null
        written?: number | null
        received_count_unit?: string | null
        written_count_unit?: string | null
        resolved_instrument_type?: InstrumentType | null
      }
    >
  >
  warnings: string[]
  data: SecurityData
}
export interface MetadataDraft {
  instrument_type: InstrumentType
  benchmark_code: string | null
  benchmark_name: string | null
}
