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
  announcements: StockDetailAnnouncement[]
  news: StockDetailNewsItem[]
}

export type StockDetailPageViewState = 'loading' | 'error' | 'not-found' | 'ready'

export function toStockDetailPageData(item: WatchlistItem): StockDetailPageData {
  return {
    security: {
      security_id: item.security_id,
      market: 'Unknown market',
      code: item.code,
      name: item.name,
      industry: item.industry,
      status: 'active',
    },
    price_context: [],
    announcements: [],
    news: [],
  }
}
