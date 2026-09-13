export type HomepageAdviceTargetType = 'stock' | 'holding'
export type HomepageAdviceRecommendation = 'buy' | 'accumulate' | 'hold' | 'trim' | 'sell' | 'watch'
export type HomepageAdviceConfidence = 'high' | 'medium' | 'low'

export interface HomepageAdviceLabel {
  security_id: number
  holding_id: number | null
  target_type: HomepageAdviceTargetType
  recommendation: HomepageAdviceRecommendation | null
  confidence: HomepageAdviceConfidence | null
  summary: string | null
  generated_at: string | null
  cached: boolean
  has_holding_context: boolean
  warnings: string[]
}

export interface HomepageAdviceLabelsResponse {
  items: HomepageAdviceLabel[]
}
