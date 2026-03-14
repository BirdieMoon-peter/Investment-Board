import type { SecuritySearchResult, WatchlistItem } from '../types/watchlist'

export async function searchSecurities(query: string): Promise<SecuritySearchResult[]> {
  const trimmedQuery = query.trim()

  if (!trimmedQuery) {
    return []
  }

  const response = await fetch(
    `/api/watchlist/securities/search?query=${encodeURIComponent(trimmedQuery)}`,
  )

  if (!response.ok) {
    throw new Error('Unable to search securities right now.')
  }

  return (await response.json()) as SecuritySearchResult[]
}

export async function fetchWatchlist(): Promise<WatchlistItem[]> {
  const response = await fetch('/api/watchlist/items')

  if (!response.ok) {
    throw new Error('Unable to load your watchlist right now.')
  }

  return (await response.json()) as WatchlistItem[]
}

export async function addWatchlistItem(securityId: number): Promise<{ security_id: number }> {
  const response = await fetch('/api/watchlist/items', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ security_id: securityId }),
  })

  if (!response.ok) {
    throw new Error('Unable to add that security to your watchlist right now.')
  }

  return (await response.json()) as { security_id: number }
}

export async function addCustomWatchlistItem(
  market: string,
  code: string,
): Promise<{ security_id: number; security: SecuritySearchResult }> {
  const response = await fetch('/api/watchlist/items/custom', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ market, code }),
  })

  if (!response.ok) {
    throw new Error('Unable to add that custom stock right now.')
  }

  return (await response.json()) as { security_id: number; security: SecuritySearchResult }
}

export async function removeWatchlistItem(
  securityId: number,
): Promise<{ removed: boolean; security_id: number }> {
  const response = await fetch(`/api/watchlist/items/${securityId}`, {
    method: 'DELETE',
  })

  if (!response.ok) {
    throw new Error('Unable to remove that security from your watchlist right now.')
  }

  return (await response.json()) as { removed: boolean; security_id: number }
}
