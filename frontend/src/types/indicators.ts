export interface IndicatorResult {
  key: string; label: string; value: string | null; status: 'ready' | 'unavailable'
  formula: string; formula_version: string; window: string; unit: string
  as_of: string | null; sample_count: number; price_basis: string
  input_refs: Record<string, unknown>[]; warnings: string[]
}
export interface SecurityIndicators {
  security_id: number; instrument_type: string; metrics: IndicatorResult[]
  data_context: Record<string, unknown>
}
export interface PositionIndicators {
  holding_id: number; security_id: number; quantity: string; average_cost: string
  valuation_at: string | null; metrics: IndicatorResult[]; warnings: string[]
}
export interface HoldingsIndicators {
  positions: PositionIndicators[]; missing_price_security_ids: number[]
  valuation_complete: boolean; denominator: 'known_valued_positions_only'
  metrics: IndicatorResult[]; warnings: string[]
}
