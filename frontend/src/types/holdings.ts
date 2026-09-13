import type { SecuritySearchResult } from './watchlist'

export type HoldingTargetHorizon = 'swing' | 'medium_term' | 'long_term'

export interface HoldingResponse {
  holding_id: number
  security_id: number
  security: SecuritySearchResult
  quantity: string
  average_cost: string
  notes: string | null
  target_horizon: HoldingTargetHorizon | null
}

export interface HoldingUpsertRequest {
  security_id: number
  quantity: string
  average_cost: string
  notes?: string | null
  target_horizon?: HoldingTargetHorizon | null
}

export interface HoldingRemoveResponse {
  removed: boolean
  holding_id: number
}
