import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { addCustomWatchlistItem, addWatchlistItem, fetchWatchlist, fetchWatchlistWithMetadata, removeWatchlistItem } from './watchlist'

const cacheKey = 'investment-board-watchlist-cache'
const now = new Date('2026-09-12T12:00:00Z').getTime()
const items = [{
  security_id: 7, market: 'SZ', code: '000001', name: 'Ping An Bank',
  industry: 'Banking', last_price: '10.2000', change_percent: '2.0000',
  snapshot_time: '2026-09-12T11:59:00Z',
}]

function saveCache(timestamp = now) {
  window.localStorage.setItem(cacheKey, JSON.stringify({ items, timestamp }))
}

describe('watchlist cache fallback', () => {
  const fetchMock = vi.fn()

  beforeEach(() => {
    window.localStorage.clear()
    vi.spyOn(Date, 'now').mockReturnValue(now)
    fetchMock.mockReset()
    vi.stubGlobal('fetch', fetchMock)
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
    window.localStorage.clear()
  })

  it('returns a fresh cached watchlist when the network rejects the request', async () => {
    saveCache()
    fetchMock.mockRejectedValue(new TypeError('Failed to fetch'))
    await expect(fetchWatchlist()).resolves.toEqual(items)
  })

  it('returns a fresh cached watchlist for an HTTP failure', async () => {
    saveCache()
    fetchMock.mockResolvedValue({ ok: false })
    await expect(fetchWatchlist()).resolves.toEqual(items)
  })

  it('reports the original saved timestamp for a cached result', async () => {
    const savedAt = now - 10 * 60_000
    saveCache(savedAt)
    fetchMock.mockRejectedValue(new TypeError('Offline'))
    await expect(fetchWatchlistWithMetadata()).resolves.toEqual({
      items, source: 'cache', fetchedAt: new Date(savedAt).toISOString(),
    })
  })

  it('reports a new network timestamp without changing the legacy loader result', async () => {
    fetchMock.mockResolvedValue({ ok: true, json: async () => items })
    await expect(fetchWatchlistWithMetadata()).resolves.toEqual({
      items, source: 'network', fetchedAt: new Date(now).toISOString(),
    })
    await expect(fetchWatchlist()).resolves.toEqual(items)
  })

  it('keeps the existing thirty-minute cache boundary', async () => {
    saveCache(now - 30 * 60 * 1000)
    fetchMock.mockResolvedValue({ ok: false })
    await expect(fetchWatchlist()).resolves.toEqual(items)
    saveCache(now - 30 * 60 * 1000 - 1)
    await expect(fetchWatchlist()).rejects.toThrow('Unable to load your watchlist right now.')
    expect(window.localStorage.getItem(cacheKey)).toBeNull()
  })

  it.each([
    ['invalid JSON', '{'],
    ['null entry', 'null'],
    ['missing timestamp', JSON.stringify({ items })],
    ['invalid timestamp', JSON.stringify({ items, timestamp: 'yesterday' })],
    ['future timestamp', JSON.stringify({ items, timestamp: now + 1 })],
    ['invalid items', JSON.stringify({ items: {}, timestamp: now })],
    ['null item', JSON.stringify({ items: [null], timestamp: now })],
    ['incomplete item', JSON.stringify({ items: [{ security_id: 7 }], timestamp: now })],
  ])('rejects and removes a malformed cache with %s', async (_name, rawValue) => {
    window.localStorage.setItem(cacheKey, rawValue)
    fetchMock.mockResolvedValue({ ok: false })
    await expect(fetchWatchlist()).rejects.toThrow('Unable to load your watchlist right now.')
    expect(window.localStorage.getItem(cacheKey)).toBeNull()
  })

  it('returns successful network data even when cache writes are denied', async () => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('Storage denied') })
    fetchMock.mockResolvedValue({ ok: true, json: async () => items })
    await expect(fetchWatchlist()).resolves.toEqual(items)
  })

  it('reports the load error if cache reads are denied after an HTTP failure', async () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => { throw new Error('Storage denied') })
    fetchMock.mockResolvedValue({ ok: false })
    await expect(fetchWatchlist()).rejects.toThrow('Unable to load your watchlist right now.')
  })

  it('reports the load error if expired cache cleanup is denied', async () => {
    saveCache(now - 30 * 60 * 1000 - 1)
    vi.spyOn(Storage.prototype, 'removeItem').mockImplementation(() => { throw new Error('Storage denied') })
    fetchMock.mockResolvedValue({ ok: false })
    await expect(fetchWatchlist()).rejects.toThrow('Unable to load your watchlist right now.')
  })

  const mutations = [
    ['add', () => addWatchlistItem(7)],
    ['custom add', () => addCustomWatchlistItem('SZ', '000001')],
    ['remove', () => removeWatchlistItem(7)],
  ] as const

  it.each(mutations)('invalidates the old cache after successful %s before an offline reload', async (_name, mutate) => {
    saveCache()
    fetchMock.mockResolvedValueOnce({ ok: true, json: async () => ({ security_id: 7 }) })
    await mutate()
    expect(window.localStorage.getItem(cacheKey)).toBeNull()
    fetchMock.mockRejectedValue(new TypeError('Failed to fetch'))
    await expect(fetchWatchlist()).rejects.toThrow('Unable to load your watchlist right now.')
  })

  it.each(mutations)('preserves the cache after a failed %s', async (_name, mutate) => {
    saveCache()
    fetchMock.mockResolvedValue({ ok: false })
    await expect(mutate()).rejects.toThrow()
    await expect(fetchWatchlist()).resolves.toEqual(items)
  })

  it('does not fail a successful mutation if cache invalidation is denied', async () => {
    vi.spyOn(Storage.prototype, 'removeItem').mockImplementation(() => { throw new Error('Storage denied') })
    fetchMock.mockResolvedValue({ ok: true, json: async () => ({ removed: true, security_id: 7 }) })
    await expect(removeWatchlistItem(7)).resolves.toEqual({ removed: true, security_id: 7 })
  })
})
