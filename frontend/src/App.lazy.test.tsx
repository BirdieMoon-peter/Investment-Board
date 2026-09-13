import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import { DEFAULT_HOMEPAGE_SETTINGS, HOMEPAGE_SETTINGS_STORAGE_KEY } from './homepageSettings'

const chunks = vi.hoisted(() => ({
  rejectDetail: undefined as undefined | ((error: Error) => void),
  rejectSettings: undefined as undefined | ((error: Error) => void),
}))
vi.mock('./pages/StockDetailPage', () => new Promise((_, reject) => { chunks.rejectDetail = reject }))
vi.mock('./components/SettingsDrawer', () => new Promise((_, reject) => { chunks.rejectSettings = reject }))

const stock = { security_id: 7, market: 'SZ', code: '000001', name: 'Example Bank', industry: null,
  last_price: '10.0000', change_percent: '0.0000', snapshot_time: null }
const fetch = vi.fn(async (url: string) => ({ ok: true, status: 200, json: async () => {
  if (url === '/api/watchlist/items') return [stock]
  if (url === '/api/homepage/overview') return { indexes: [], macro: [], updated_at: null, warnings: [] }
  if (url === '/api/ai/watchlist-labels?use_cache=true') return { items: [] }
  if (url === '/api/stocks/7') return { security: { ...stock, status: 'active' }, price_context: [], price_history: [], financial_metrics: [], company_profile: null, announcements: [], news: [] }
  throw new Error(`Unexpected API request: ${url}`)
} }))

beforeEach(() => {
  window.localStorage.setItem(HOMEPAGE_SETTINGS_STORAGE_KEY, JSON.stringify({
    ...DEFAULT_HOMEPAGE_SETTINGS, showMarketIndexes: false, showMacroPanel: false,
    showAiTags: false, showSpotlight: false, autoRefreshEnabled: false, autoSyncEnabled: false,
  }))
  fetch.mockClear()
  vi.stubGlobal('fetch', fetch)
  // React reports the intentionally rejected module even when its boundary recovers.
  vi.spyOn(console, 'error').mockImplementation(() => {})
  vi.spyOn(window, 'scrollTo').mockImplementation(() => {})
})
afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); window.localStorage.clear() })

describe('Workspace lazy-module failures', () => {
  it('captures and restores settings focus for pending and rejected imports on Close and Escape', async () => {
    render(<App />)
    await screen.findByRole('table')
    const trigger = screen.getByRole('button', { name: 'Open settings' })
    async function openSettings() {
      fireEvent.keyDown(document, { key: 'Tab' })
      act(() => trigger.focus())
      fireEvent.click(trigger)
      const drawer = await screen.findByRole('dialog', { name: 'Board settings' })
      await waitFor(() => expect(drawer).toContainElement(document.activeElement as HTMLElement))
    }
    async function closeSettings(usingEscape: boolean) {
      const close = screen.getByRole('button', { name: 'Close settings' })
      act(() => close.focus())
      if (usingEscape) fireEvent.keyDown(close, { key: 'Escape' })
      else fireEvent.click(close)
      await waitFor(() => expect(screen.queryByRole('dialog', { name: 'Board settings' })).not.toBeInTheDocument())
      await waitFor(() => expect(trigger).toHaveFocus())
    }

    await openSettings()
    expect(screen.getByRole('status')).toHaveTextContent('Loading settings…')
    await closeSettings(false)
    await openSettings()
    await closeSettings(true)
    await openSettings()
    await act(async () => { chunks.rejectSettings!(new Error('Settings chunk unavailable')) })
    expect(await screen.findByRole('alert')).toHaveTextContent('This part of the workspace could not load. Reload the page to try again.')
    expect(screen.getByRole('button', { name: 'Reload page' })).toBeEnabled()
    await closeSettings(false)
    await openSettings()
    await closeSettings(true)
    expect(screen.getByRole('table')).toBeVisible()
    expect(fetch.mock.calls.some(([url]) => /\/api\/ai\/(settings|history|stocks|holdings)/.test(url))).toBe(false)
  })

  it('returns to the preserved list after a detail import rejection without loading research data', async () => {
    render(<App />)
    await screen.findByRole('table')
    fireEvent.change(screen.getByLabelText('Filter watchlist'), { target: { value: 'Example' } })
    fireEvent.click(screen.getByRole('button', { name: 'View details for Example Bank' }))
    expect(await screen.findByRole('status')).toHaveTextContent('Loading stock detail…')
    fireEvent.click(screen.getByRole('button', { name: 'Back to watchlist' }))
    expect(await screen.findByRole('table')).toBeVisible()
    fireEvent.click(screen.getByRole('button', { name: 'View details for Example Bank' }))
    await act(async () => { chunks.rejectDetail!(new Error('Detail chunk unavailable')) })
    expect(await screen.findByRole('alert')).toHaveTextContent('This part of the workspace could not load.')
    fireEvent.click(screen.getByRole('button', { name: 'Back to watchlist' }))
    expect(await screen.findByRole('table')).toBeVisible()
    expect(screen.getByLabelText('Filter watchlist')).toHaveValue('Example')
    expect(fetch.mock.calls.some(([url]) => url.includes('/holdings') || /\/api\/ai\/(settings|history|stocks|holdings)/.test(url))).toBe(false)
  })
})
