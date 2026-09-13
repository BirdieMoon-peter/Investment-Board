export interface HomepageMarketIndex {
  key: string
  name: string
  market: string | null
  last_value: string | null
  change_amount: string | null
  change_percent: string | null
  snapshot_time: string | null
}

export interface HomepageMacroItem {
  key: string
  title: string
  category: string
  value: string | null
  unit: string | null
  change_text: string | null
  published_at: string | null
  importance: string
  summary: string | null
}

export interface HomepageOverviewWarning {
  section: string
  message: string
}

export interface HomepageOverview {
  indexes: HomepageMarketIndex[]
  macro: HomepageMacroItem[]
  updated_at: string | null
  warnings: HomepageOverviewWarning[]
}
