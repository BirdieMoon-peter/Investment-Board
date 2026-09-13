import type { SecuritySearchResult, WatchlistItem, WatchlistSyncResponse } from '../types/watchlist'

const WATCHLIST_CACHE_KEY = 'investment-board-watchlist-cache'
const WATCHLIST_CACHE_MAX_AGE_MS = 30 * 60 * 1000 // 30 minutes

interface WatchlistCacheEntry {
  items: WatchlistItem[]
  timestamp: number
}

export interface WatchlistLoadResult {
  items: WatchlistItem[]
  source: 'network' | 'cache'
  fetchedAt: string
}

function clearWatchlistCache(): void {
  try {
    if (typeof window !== 'undefined') {
      window.localStorage.removeItem(WATCHLIST_CACHE_KEY)
    }
  } catch {
    // Browser storage is optional; it must not break a network operation.
  }
}

function getCachedWatchlist(): WatchlistCacheEntry | null {
  if (typeof window === 'undefined') {
    return null
  }

  try {
    const rawValue = window.localStorage.getItem(WATCHLIST_CACHE_KEY)
    if (!rawValue) {
      return null
    }

    const entry = JSON.parse(rawValue) as WatchlistCacheEntry
    const isValid = entry && Number.isFinite(entry.timestamp) &&
      Array.isArray(entry.items) && entry.items.every((item) =>
        item && Number.isFinite(item.security_id) &&
        typeof item.market === 'string' && typeof item.code === 'string' &&
        typeof item.name === 'string' &&
        [item.industry, item.last_price, item.change_percent, item.snapshot_time]
          .every((value) => value === null || typeof value === 'string'),
      )
    const age = isValid ? Date.now() - entry.timestamp : -1
    if (!isValid || age < 0 || age > WATCHLIST_CACHE_MAX_AGE_MS) {
      clearWatchlistCache()
      return null
    }
    return entry
  } catch {
    clearWatchlistCache()
    return null
  }
}

function cacheWatchlist(items: WatchlistItem[], timestamp: number): void {
  if (typeof window === 'undefined') {
    return
  }

  const entry: WatchlistCacheEntry = {
    items,
    timestamp,
  }
  try {
    window.localStorage.setItem(WATCHLIST_CACHE_KEY, JSON.stringify(entry))
  } catch {
    // Keep successful network data usable when storage is unavailable or full.
  }
}

function getCachedWatchlistDebugInfo(): { cached: boolean; ageSeconds?: number } | null {
  if (typeof window === 'undefined') {
    return null
  }

  const rawValue = window.localStorage.getItem(WATCHLIST_CACHE_KEY)
  if (!rawValue) {
    return { cached: false }
  }

  try {
    const entry = JSON.parse(rawValue) as WatchlistCacheEntry
    const ageSeconds = (Date.now() - entry.timestamp) / 1000
    return { cached: true, ageSeconds }
  } catch {
    return { cached: false }
  }
}

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
  return (await fetchWatchlistWithMetadata()).items
}

export async function fetchWatchlistWithMetadata(): Promise<WatchlistLoadResult> {
  try {
    const response = await fetch('/api/watchlist/items')
    if (!response.ok) {
      throw new Error('Unable to load your watchlist right now.')
    }

    const items = (await response.json()) as WatchlistItem[]
    const fetchedAt = Date.now()
    cacheWatchlist(items, fetchedAt)
    return { items, source: 'network', fetchedAt: new Date(fetchedAt).toISOString() }
  } catch {
    const cached = getCachedWatchlist()
    if (cached !== null) {
      return { items: cached.items, source: 'cache', fetchedAt: new Date(cached.timestamp).toISOString() }
    }
    throw new Error('Unable to load your watchlist right now.')
  }
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

  clearWatchlistCache()
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

  clearWatchlistCache()
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

  clearWatchlistCache()
  return (await response.json()) as { removed: boolean; security_id: number }
}

export async function syncWatchlist(): Promise<WatchlistSyncResponse> {
  const response = await fetch('/api/watchlist/sync', {
    method: 'POST',
  })

  if (!response.ok) {
    throw new Error('Unable to sync your homepage board right now.')
  }

  return (await response.json()) as WatchlistSyncResponse
}
