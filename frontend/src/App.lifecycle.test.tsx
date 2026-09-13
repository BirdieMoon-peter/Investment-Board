import { StrictMode } from 'react'
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import App from './App'
import { DEFAULT_HOMEPAGE_SETTINGS, HOMEPAGE_SETTINGS_STORAGE_KEY } from './homepageSettings'

const watchlist = [{
  security_id: 7,
  market: 'SZ',
  code: '000001',
  name: 'Ping An Bank',
  industry: 'Banking',
  last_price: '10.2000',
  change_percent: '2.0000',
  snapshot_time: '2026-03-10T10:00:00',
}]

function response(data: unknown) {
  return { ok: true, json: async () => data }
}

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((resolvePromise) => { resolve = resolvePromise })
  return { promise, resolve }
}

function mockHomepage() {
  const fetchItems = vi.fn().mockResolvedValue(response(watchlist))
  const syncItems = vi.fn().mockResolvedValue(response({
    synced_at: '2026-09-12T10:00:00', warnings: [],
  }))
  vi.stubGlobal('fetch', vi.fn((url: string) => {
    if (url === '/api/watchlist/items') return fetchItems()
    if (url === '/api/watchlist/sync') return syncItems()
    if (url === '/api/homepage/overview') {
      return Promise.resolve(response({ indexes: [], macro: [], updated_at: null, warnings: [] }))
    }
    if (url === '/api/ai/watchlist-labels?use_cache=true') {
      return Promise.resolve(response({ items: [] }))
    }
    throw new Error(`Unexpected request: ${url}`)
  }))
  return { fetchItems, syncItems }
}

describe('App background lifecycle', () => {
  beforeEach(() => {
    window.localStorage.clear()
    vi.useFakeTimers()
  })

  afterEach(() => {
    cleanup()
    vi.useRealTimers()
    vi.unstubAllGlobals()
    window.localStorage.clear()
  })

  it.each(['en', 'zh'] as const)('labels an offline watchlist with its saved time and clears the label on recovery in %s', async (language) => {
    vi.setSystemTime(new Date('2026-09-12T12:00:00Z'))
    window.localStorage.setItem(HOMEPAGE_SETTINGS_STORAGE_KEY, JSON.stringify({
      ...DEFAULT_HOMEPAGE_SETTINGS, language,
    }))
    const savedAt = Date.now() - 10 * 60_000
    window.localStorage.setItem('investment-board-watchlist-cache', JSON.stringify({
      items: watchlist, timestamp: savedAt,
    }))
    const { fetchItems } = mockHomepage()
    fetchItems.mockRejectedValue(new TypeError('Offline'))
    await act(async () => { render(<App />) })

    const label = language === 'en' ? /Cached watchlist, saved/ : /自选股本地缓存，保存于/
    const initialLabel = screen.getByText(label).textContent
    await act(async () => { await vi.advanceTimersByTimeAsync(60_000) })
    expect(screen.getByText(label).textContent).toBe(initialLabel)
    expect(JSON.parse(window.localStorage.getItem('investment-board-watchlist-cache')!).timestamp).toBe(savedAt)

    fetchItems.mockResolvedValue(response(watchlist))
    await act(async () => { await vi.advanceTimersByTimeAsync(60_000) })
    expect(screen.queryByText(label)).not.toBeInTheDocument()
    expect(screen.getByText(language === 'en' ? /Last refresh/ : /上次刷新/)).toBeInTheDocument()
  })

  it('keeps the three-minute sync schedule through successful one-minute refreshes', async () => {
    const { fetchItems, syncItems } = mockHomepage()
    await act(async () => { render(<App />) })

    for (let minute = 1; minute <= 6; minute += 1) {
      const pendingRefresh = deferred<ReturnType<typeof response>>()
      fetchItems.mockReturnValueOnce(pendingRefresh.promise)
      await act(async () => { await vi.advanceTimersByTimeAsync(60_000) })
      expect(fetchItems).toHaveBeenCalledTimes(minute + 1)
      await act(async () => { pendingRefresh.resolve(response(watchlist)) })
      expect(syncItems).toHaveBeenCalledTimes(Math.floor(minute / 3))
    }
  })

  it('does not overlap refresh requests when interval and focus events occur while a refresh is pending', async () => {
    const { fetchItems } = mockHomepage()
    await act(async () => { render(<App />) })
    const pendingRefresh = deferred<ReturnType<typeof response>>()
    fetchItems.mockReturnValueOnce(pendingRefresh.promise)
    await act(async () => {
      await vi.advanceTimersByTimeAsync(60_000)
      window.dispatchEvent(new Event('focus'))
      window.dispatchEvent(new Event('focus'))
    })
    await act(async () => { await vi.advanceTimersByTimeAsync(60_000) })
    expect(fetchItems).toHaveBeenCalledTimes(2)

    await act(async () => { pendingRefresh.resolve(response(watchlist)) })
    await act(async () => { window.dispatchEvent(new Event('focus')) })
    expect(fetchItems).toHaveBeenCalledTimes(3)
  })

  it('does not overlap sync requests and resumes on the next interval after completion', async () => {
    window.localStorage.setItem(HOMEPAGE_SETTINGS_STORAGE_KEY, JSON.stringify({
      ...DEFAULT_HOMEPAGE_SETTINGS, autoRefreshEnabled: false,
    }))
    const { syncItems } = mockHomepage()
    await act(async () => { render(<App />) })
    const pendingSync = deferred<ReturnType<typeof response>>()
    syncItems.mockReturnValueOnce(pendingSync.promise)
    await act(async () => { await vi.advanceTimersByTimeAsync(180_000) })
    expect(screen.getByRole('button', { name: /syncing/i })).toBeDisabled()
    await act(async () => { await vi.advanceTimersByTimeAsync(180_000) })
    expect(syncItems).toHaveBeenCalledTimes(1)

    await act(async () => {
      pendingSync.resolve(response({ synced_at: '2026-09-12T10:00:00', warnings: [] }))
    })
    await act(async () => { await vi.advanceTimersByTimeAsync(180_000) })
    expect(syncItems).toHaveBeenCalledTimes(2)
  })

  it('preserves persisted settings on a StrictMode mount and saves edits across a remount', async () => {
    const savedSettings = {
      ...DEFAULT_HOMEPAGE_SETTINGS,
      language: 'zh',
      density: 'comfortable',
      showMarketIndexes: false,
      homepageMode: 'focused',
    }
    window.localStorage.setItem(HOMEPAGE_SETTINGS_STORAGE_KEY, JSON.stringify(savedSettings))
    mockHomepage()
    const mounted = render(<StrictMode><App /></StrictMode>)
    await act(async () => {})
    expect(JSON.parse(window.localStorage.getItem(HOMEPAGE_SETTINGS_STORAGE_KEY)!)).toEqual(savedSettings)
    expect(screen.getByLabelText('Watchlist page shell')).toHaveClass('dashboard-shell--zh', 'dashboard-shell--comfortable')
    fireEvent.click(screen.getByRole('button', { name: '打开设置' }))
    expect(screen.getByLabelText('显示大盘指数')).not.toBeChecked()
    fireEvent.change(screen.getByLabelText('密度'), { target: { value: 'compact' } })
    mounted.unmount()

    await act(async () => { render(<StrictMode><App /></StrictMode>) })
    expect(screen.getByLabelText('Watchlist page shell')).toHaveClass('dashboard-shell--zh', 'dashboard-shell--compact')
    expect(JSON.parse(window.localStorage.getItem(HOMEPAGE_SETTINGS_STORAGE_KEY)!)).toEqual({
      ...savedSettings, density: 'compact',
    })
  })
})
