export type AdviceTargetType = 'stock' | 'holding'
export type AdviceRecommendation = 'buy' | 'accumulate' | 'hold' | 'trim' | 'sell' | 'watch'
export type AdviceConfidence = 'high' | 'medium' | 'low'

export interface InvestmentAdviceResponse {
  advice_id: number | null
  target_type: AdviceTargetType
  target_id: number
  security_id: number
  holding_id: number | null
  market: string
  code: string
  name: string
  recommendation: AdviceRecommendation
  confidence: AdviceConfidence
  summary: string
  thesis_points: string[]
  risk_points: string[]
  position_notes: string[]
  recent_catalysts: string[]
  full_analysis: string
  warnings: string[]
  generated_at: string
  cached: boolean
  disclaimer: string
}

export interface InvestmentAdviceHistoryResponse {
  items: InvestmentAdviceResponse[]
}
