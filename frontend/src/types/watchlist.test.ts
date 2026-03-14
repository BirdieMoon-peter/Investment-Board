import { describe, expect, it } from 'vitest'

import { toStockDetailPageData, type StockDetailPageData, type WatchlistItem } from './watchlist'

describe('toStockDetailPageData', () => {
  it('provides the backend-aligned stock detail contract defaults for watchlist navigation', () => {
    const item: WatchlistItem = {
      security_id: 1,
      market: 'sz',
      code: '000001',
      name: 'Ping An Bank',
      industry: 'Banking',
      last_price: '12.34',
      change_percent: '1.23',
      snapshot_time: '2026-03-13T09:30:00Z',
    }

    const result: StockDetailPageData = toStockDetailPageData(item)

    expect(result).toEqual({
      security: {
        security_id: 1,
        market: 'sz',
        code: '000001',
        name: 'Ping An Bank',
        industry: 'Banking',
        status: 'active',
      },
      price_context: [],
      price_history: [],
      financial_metrics: [],
      company_profile: null,
      announcements: [],
      news: [],
    })
  })
})
