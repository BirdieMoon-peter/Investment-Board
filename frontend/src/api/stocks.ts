import type { StockDetailPageData } from '../types/watchlist'

export interface StockSyncResponse {
  security_id: number
  synced: boolean
  announcements_upserted: number
  news_items_upserted: number
  warnings: string[]
  synced_at: string
}

export async function fetchStockDetail(securityId: number): Promise<StockDetailPageData> {
  const response = await fetch(`/api/stocks/${securityId}`)

  if (response.status === 404) {
    throw new Error('not-found')
  }

  if (!response.ok) {
    throw new Error('Unable to load stock detail right now.')
  }

  return (await response.json()) as StockDetailPageData
}

export async function syncStock(securityId: number): Promise<StockSyncResponse> {
  const response = await fetch(`/api/stocks/${securityId}/sync`, {
    method: 'POST',
  })

  if (response.status === 404) {
    throw new Error('The requested stock could not be found.')
  }

  if (!response.ok) {
    throw new Error('Unable to sync stock information right now.')
  }

  return (await response.json()) as StockSyncResponse
}
