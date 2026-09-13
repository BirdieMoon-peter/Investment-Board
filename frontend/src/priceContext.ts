import type { StockDetailPriceBar } from './types/watchlist'

function toTimestamp(snapshotTime: string) {
  const parsed = new Date(snapshotTime)
  const timestamp = parsed.getTime()
  return Number.isNaN(timestamp) ? Number.NEGATIVE_INFINITY : timestamp
}

export function sortPriceContext(priceContext: StockDetailPriceBar[]) {
  return [...priceContext].sort((left, right) => toTimestamp(right.snapshot_time) - toTimestamp(left.snapshot_time))
}

export function getLatestPriceContextBar(priceContext: StockDetailPriceBar[]) {
  return sortPriceContext(priceContext)[0] ?? null
}
