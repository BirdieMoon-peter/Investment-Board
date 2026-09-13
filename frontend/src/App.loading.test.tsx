import { act, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import App from './App'
import { DEFAULT_HOMEPAGE_SETTINGS, HOMEPAGE_SETTINGS_STORAGE_KEY } from './homepageSettings'

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((done) => { resolve = done })
  return { promise, resolve }
}
const response = (data: unknown) => ({ ok: true, status: 200, json: async () => data })

afterEach(() => { vi.unstubAllGlobals(); window.localStorage.clear() })

it('keeps loading in the count slot and removes row skeletons as soon as watchlist data arrives', async () => {
  window.localStorage.setItem(HOMEPAGE_SETTINGS_STORAGE_KEY, JSON.stringify({
    ...DEFAULT_HOMEPAGE_SETTINGS, autoRefreshEnabled: false, autoSyncEnabled: false,
  }))
  const watchlist = deferred<ReturnType<typeof response>>()
  const labels = deferred<ReturnType<typeof response>>()
  const fetch = vi.fn((url: string) => {
    if (url === '/api/watchlist/items') return watchlist.promise
    if (url === '/api/ai/watchlist-labels?use_cache=true') return labels.promise
    if (url === '/api/homepage/overview') return Promise.resolve(response({ indexes: [], macro: [], updated_at: null, warnings: [] }))
    throw new Error(`Unexpected request: ${url}`)
  })
  vi.stubGlobal('fetch', fetch)
  const { container } = render(<App />)
  const countSlot = await screen.findByRole('status', { name: 'Loading watchlist…' })
  expect(countSlot).toHaveTextContent('Loading…')
  expect(countSlot.closest('.workspace-section-heading')).not.toBeNull()
  expect(container.querySelector('.workspace-watchlist > .status-message')).toBeNull()
  expect(screen.getByRole('progressbar', { name: 'Loading watchlist…' })).toBeInTheDocument()
  const refreshSlot = screen.getByText('Last refresh Not available')
  expect(screen.getByRole('button', { name: 'Search and add' })).toBeEnabled()
  expect(screen.getByRole('progressbar', { name: 'Spotlight Loading…' })).toBeInTheDocument()
  expect(screen.queryByText('Add a security to start building your homepage board.')).not.toBeInTheDocument()

  await act(async () => { watchlist.resolve(response([{
    security_id: 7, market: 'SZ', code: '000001', name: 'Example Bank', industry: null,
    last_price: '10.0000', change_percent: '0.0000', snapshot_time: null,
  }])) })
  await screen.findByRole('table', { name: 'Watchlist holdings' })
  expect(countSlot).toHaveTextContent('1 of 1 securities')
  expect(screen.queryByRole('progressbar', { name: 'Spotlight Loading…' })).not.toBeInTheDocument()
  expect(screen.queryByRole('progressbar', { name: 'Loading watchlist…' })).not.toBeInTheDocument()
  expect(container.querySelector('.workspace-watchlist > .status-message')).toBeNull()
  expect(refreshSlot).toHaveTextContent(/Last refresh \d/)
  await waitFor(() => expect(fetch).toHaveBeenCalledWith('/api/ai/watchlist-labels?use_cache=true'))

  await act(async () => { labels.resolve(response({ items: [] })) })
  expect(screen.getByRole('table', { name: 'Watchlist holdings' })).toBeInTheDocument()
  expect(countSlot).toHaveTextContent('1 of 1 securities')
  expect(fetch).toHaveBeenCalledTimes(3)
})
