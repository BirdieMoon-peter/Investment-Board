export interface SecuritySearchResult {
  security_id: number
  market: string
  code: string
  name: string
  industry: string | null
  status: string
}

export interface WatchlistItem {
  security_id: number
  market: string
  code: string
  name: string
  industry: string | null
  last_price: string | null
  change_percent: string | null
  snapshot_time: string | null
}

export interface StockDetailPageSecurity {
  security_id: number
  market: string
  code: string
  name: string
  industry: string | null
  status: string
}

export interface StockDetailPriceBar {
  trade_date: string
  open_price: string
  high_price: string
  low_price: string
  close_price: string
  volume: string
}

export interface StockDetailPriceHistoryBar {
  trade_date: string
  open_price: string
  high_price: string
  low_price: string
  close_price: string
  volume: string
  amount: string
}

export interface StockDetailFinancialMetric {
  report_period: string
  revenue: string | null
  net_profit: string | null
  eps: string | null
  roe: string | null
  debt_to_asset_ratio: string | null
}

export interface StockDetailCompanyProfile {
  full_name: string | null
  english_name: string | null
  registered_capital: string | null
  establishment_date: string | null
  website: string | null
  main_business: string | null
  employees: number | null
}

export interface StockDetailAnnouncement {
  title: string
  source: string | null
  url: string | null
  summary: string | null
  published_at: string
}

export interface StockDetailNewsItem {
  title: string
  source: string | null
  url: string | null
  summary: string | null
  published_at: string
}

export interface StockDetailPageData {
  security: StockDetailPageSecurity
  price_context: StockDetailPriceBar[]
  price_history: StockDetailPriceHistoryBar[]
  financial_metrics: StockDetailFinancialMetric[]
  company_profile: StockDetailCompanyProfile | null
  announcements: StockDetailAnnouncement[]
  news: StockDetailNewsItem[]
}

export type StockDetailPageViewState = 'loading' | 'error' | 'not-found' | 'ready'

export function toStockDetailPageData(item: WatchlistItem): StockDetailPageData {
  return {
    security: {
      security_id: item.security_id,
      market: item.market,
      code: item.code,
      name: item.name,
      industry: item.industry,
      status: 'active',
    },
    price_context: [],
    price_history: [],
    financial_metrics: [],
    company_profile: null,
    announcements: [],
    news: [],
  }
}
