vi.mock('./api/quant', () => ({fetchQuantSummary: vi.fn().mockResolvedValue({accounts:0,awaiting_future_data:0,active_accounts:0,latest_account_session:null,failed_runs:0,window:'latest_100_saved_objects',mode:'paper_only'})}))
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import {
  DEFAULT_HOMEPAGE_SETTINGS,
  HOMEPAGE_SETTINGS_STORAGE_KEY,
} from './homepageSettings'
import {
  catalogFixture,
  deferred,
  jsonResponse,
  securityFixture,
  watchlistFixture,
} from './test/dataCenterFixtures'
import type { StockDetailPageData } from './types/watchlist'
vi.mock('./components/CandlestickChart', () => ({
  CandlestickChart: () => <div>Chart</div>,
}))
function detail(id: number): StockDetailPageData {
  return {
    security: {
      security_id: id,
      name: `Security ${id}`,
      market: 'SH',
      code: '510300',
      industry: 'ETF',
      status: 'active',
    },
    price_context: [],
    price_history: [],
    financial_metrics: [],
    company_profile: null,
    announcements: [],
    news: [],
  }
}
function setup(
  extra?: (url: string, options?: RequestInit) => Promise<unknown> | undefined,
) {
  window.localStorage.setItem(
    HOMEPAGE_SETTINGS_STORAGE_KEY,
    JSON.stringify({
      ...DEFAULT_HOMEPAGE_SETTINGS,
      autoSyncEnabled: false,
      autoRefreshEnabled: false,
      showAiTags: false,
      showSpotlight: false,
    }),
  )
  const fetch = vi.fn().mockImplementation((url: string, options?: RequestInit) => {
    const result = extra?.(url, options)
    if (result) return result
    if (url === '/api/watchlist/items')
      return Promise.resolve(jsonResponse(watchlistFixture))
    if (url === '/api/homepage/overview')
      return Promise.resolve(
        jsonResponse({ indexes: [], macro: [], updated_at: null, warnings: [] }),
      )
    if (url.startsWith('/api/indicators/securities/')) return Promise.resolve(jsonResponse({security_id:Number(url.split('/').pop()),instrument_type:'stock',metrics:[],data_context:{}}))
    if (url === '/api/indicators/holdings') return Promise.resolve(jsonResponse({positions:[],missing_price_security_ids:[],valuation_complete:true,denominator:'known_valued_positions_only',metrics:[],warnings:[]}))
    if (url === '/api/holdings') return Promise.resolve(jsonResponse([]))
    if (url === '/api/ai/history') return Promise.resolve(jsonResponse({ items: [] }))
    if (url === '/api/data/sources')
      return Promise.resolve(jsonResponse({ sources: catalogFixture }))
    if (url.startsWith('/api/data/securities/'))
      return Promise.resolve(jsonResponse(securityFixture(Number(url.split('/')[4]))))
    if (url.startsWith('/api/stocks/'))
      return Promise.resolve(jsonResponse(detail(Number(url.split('/')[3]))))
    throw new Error(`Unexpected synthetic request ${url}`)
  })
  vi.stubGlobal('fetch', fetch)
  return fetch
}
beforeEach(() => {
  vi.spyOn(window, 'scrollTo').mockImplementation(() => {})
})
afterEach(() => {
  vi.unstubAllGlobals()
  window.localStorage.clear()
})
describe('app data center integration', () => {
  it('header opens lazy modal with saved GET only and restores focus after closing', async () => {
    const fetch = setup()
    render(<App />)
    await screen.findByRole('table', { name: 'Watchlist holdings' })
    const trigger = screen.getByRole('button', { name: 'Data center' })
    act(() => trigger.focus())
    fetch.mockClear()
    fireEvent.click(trigger)
    await screen.findByText('Registered contract · Unknown')
    expect(screen.getByRole('dialog', { name: 'Data center' })).toHaveAttribute(
      'aria-modal',
      'true',
    )
    expect(
      fetch.mock.calls.every(
        ([url, o]) => url.startsWith('/api/data/') && o.method === 'GET',
      ),
    ).toBe(true)
    fireEvent.click(screen.getByRole('button', { name: 'Close data center' }))
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    await waitFor(() => expect(trigger).toHaveFocus())
  })
  it('successful category refresh keeps holding draft and active research group', async () => {
    const fetch = setup((url, options) =>
      options?.method === 'POST' && url === '/api/data/securities/1/sync'
        ? Promise.resolve(
            jsonResponse({
              security_id: 1,
              category_outcomes: { news: { outcome: 'succeeded' } },
              warnings: [],
              data: securityFixture(),
            }),
          )
        : undefined,
    )
    render(<App />)
    await screen.findByRole('table', { name: 'Watchlist holdings' })
    fireEvent.click(
      screen.getAllByRole('button', { name: 'View details for Security 1' })[0],
    )
    await screen.findByRole('heading', { name: 'Security 1' })
    fireEvent.click(screen.getByRole('tab', { name: 'Holdings & AI' }))
    await screen.findByText('No holding is saved for this stock yet.')
    fireEvent.change(screen.getByLabelText('Quantity'), { target: { value: '123' } })
    fireEvent.click(screen.getByRole('button', { name: 'Inspect data in data center' }))
    await screen.findByRole('button', { name: 'Retry · News' })
    fireEvent.click(screen.getByRole('button', { name: 'Retry · News' }))
    await screen.findByText('News: Succeeded', { exact: false })
    await waitFor(() =>
      expect(fetch.mock.calls.filter(([url]) => url === '/api/stocks/1')).toHaveLength(2),
    )
    fireEvent.click(screen.getByRole('button', { name: 'Close data center' }))
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    expect(screen.getByRole('tab', { name: 'Holdings & AI' })).toHaveAttribute(
      'aria-selected',
      'true',
    )
    expect(screen.getByLabelText('Quantity')).toHaveValue('123')
    expect(fetch.mock.calls.filter(([url]) => url === '/api/holdings')).toHaveLength(1)
  })
  it('late old detail refresh cannot overwrite a newer security selection', async () => {
    const pending = deferred<unknown>()
    let reads = 0
    setup((url, options) => {
      if (url === '/api/stocks/1' && ++reads === 2) return pending.promise
      if (options?.method === 'POST' && url === '/api/data/securities/1/sync')
        return Promise.resolve(
          jsonResponse({
            security_id: 1,
            category_outcomes: { news: { outcome: 'succeeded' } },
            warnings: [],
            data: securityFixture(),
          }),
        )
      return undefined
    })
    render(<App />)
    await screen.findByRole('table', { name: 'Watchlist holdings' })
    fireEvent.click(
      screen.getAllByRole('button', { name: 'View details for Security 1' })[0],
    )
    await screen.findByRole('heading', { name: 'Security 1' })
    fireEvent.click(screen.getByRole('button', { name: 'Inspect data in data center' }))
    await screen.findByRole('button', { name: 'Retry · News' })
    fireEvent.click(screen.getByRole('button', { name: 'Retry · News' }))
    await screen.findByText('News: Succeeded', { exact: false })
    fireEvent.click(screen.getByRole('button', { name: 'Close data center' }))
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    fireEvent.click(screen.getByRole('button', { name: 'Back to watchlist' }))
    await screen.findByRole('table', { name: 'Watchlist holdings' })
    fireEvent.click(
      screen.getAllByRole('button', { name: 'View details for Security 2' })[0],
    )
    await screen.findByRole('heading', { name: 'Security 2' })
    await act(async () => pending.resolve(jsonResponse(detail(1))))
    expect(screen.queryByRole('heading', { name: 'Security 1' })).not.toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Security 2' })).toBeInTheDocument()
  })
  it('reports a failed detail refresh without erasing the current detail or draft', async () => {
    let reads = 0
    setup((url, options) => {
      if (url === '/api/stocks/1' && ++reads === 2)
        return Promise.reject(new Error('private provider failure'))
      if (options?.method === 'POST' && url === '/api/data/securities/1/sync')
        return Promise.resolve(
          jsonResponse({
            security_id: 1,
            category_outcomes: { news: { outcome: 'succeeded' } },
            warnings: [],
            data: securityFixture(),
          }),
        )
      return undefined
    })
    render(<App />)
    await screen.findByRole('table', { name: 'Watchlist holdings' })
    fireEvent.click(
      screen.getAllByRole('button', { name: 'View details for Security 1' })[0],
    )
    await screen.findByRole('heading', { name: 'Security 1' })
    fireEvent.click(screen.getByRole('button', { name: 'Inspect data in data center' }))
    await screen.findByRole('button', { name: 'Retry · News' })
    fireEvent.click(screen.getByRole('button', { name: 'Retry · News' }))
    await screen.findByText('News: Succeeded', { exact: false })
    fireEvent.click(screen.getByRole('button', { name: 'Close data center' }))
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    expect(
      await screen.findByText(
        'The detail view could not refresh. Reopen the security to load its saved data.',
      ),
    ).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Security 1' })).toBeInTheDocument()
    expect(screen.queryByText(/private provider failure/)).not.toBeInTheDocument()
  })
  it.each([
    ['stock', 'index'],
    ['index', 'stock'],
  ] as const)(
    'metadata %s → %s refreshes mounted detail health and price labels while preserving drafts',
    async (before, after) => {
      let health = securityFixture()
      health.metadata.instrument_type = before
      health.metadata.effective_instrument_type = before
      health.categories.price_history.unit = before === 'index' ? 'index_points' : 'CNY'
      const fetch = setup((url, options) => {
        if (url === '/api/data/securities/1/metadata' && options?.method === 'PUT') {
          health = structuredClone(health)
          health.metadata.instrument_type = after
          health.metadata.effective_instrument_type = after
          health.metadata.classification_origin = 'manual'
          health.categories.price_history.unit =
            after === 'index' ? 'index_points' : 'CNY'
          return Promise.resolve(jsonResponse(health))
        }
        if (url === '/api/data/securities/1') return Promise.resolve(jsonResponse(health))
        if (url === '/api/stocks/1') {
          const savedDetail = detail(1)
          savedDetail.price_context = [
            {
              last_price: '100.0000',
              change_amount: '1.0000',
              change_percent: '1.0000',
              snapshot_time: '2026-10-01T00:00:00Z',
            },
          ]
          return Promise.resolve(jsonResponse(savedDetail))
        }
        return undefined
      })
      render(<App />)
      await screen.findByRole('table', { name: 'Watchlist holdings' })
      fireEvent.click(
        screen.getAllByRole('button', { name: 'View details for Security 1' })[0],
      )
      await screen.findByRole('heading', { name: 'Security 1' })
      if (before === 'index')
        await screen.findByText(
          'Index prices use verified index points or an unknown unit. Corporate adjustment and component volume comparability are unverified. Legacy derived context is read-only; this does not migrate saved records.',
        )
      fireEvent.click(await screen.findByRole('tab', { name: 'Holdings & AI' }))
      await screen.findByText('No holding is saved for this stock yet.')
      fireEvent.change(screen.getByLabelText('Quantity'), { target: { value: '123' } })
      fireEvent.click(screen.getByRole('button', { name: 'Inspect data in data center' }))
      await screen.findByRole('button', { name: 'Edit manual metadata' })
      fireEvent.click(screen.getByRole('button', { name: 'Edit manual metadata' }))
      fireEvent.change(screen.getByLabelText('Instrument classification'), {
        target: { value: after },
      })
      fireEvent.click(screen.getByRole('button', { name: 'Save' }))
      await screen.findByText(
        `${after === 'index' ? 'Index' : 'Stock'} · Manual classification and benchmark overlay`,
      )
      fireEvent.click(screen.getByRole('button', { name: 'Close data center' }))
      await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
      expect(screen.getByRole('tab', { name: 'Holdings & AI' })).toHaveAttribute(
        'aria-selected',
        'true',
      )
      expect(screen.getByLabelText('Quantity')).toHaveValue('123')
      fireEvent.click(screen.getByRole('tab', { name: 'Market & fundamentals' }))
      await waitFor(() =>
        expect(
          fetch.mock.calls.filter(([url]) => url === '/api/data/securities/1'),
        ).toHaveLength(3),
      )
      const disclosure =
        'Index prices use verified index points or an unknown unit. Corporate adjustment and component volume comparability are unverified. Legacy derived context is read-only; this does not migrate saved records.'
      if (after === 'index') expect(screen.getByText(disclosure)).toBeInTheDocument()
      else expect(screen.queryByText(disclosure)).not.toBeInTheDocument()
      const quote = within(screen.getByRole('region', { name: 'Quote summary' }))
      expect(
        quote.getByText(
          after === 'index' ? 'Index level (points / unit unverified)' : 'Last price',
        ),
      ).toBeInTheDocument()
      expect(
        quote.queryByText(
          after === 'index' ? 'Last price' : 'Index level (points / unit unverified)',
        ),
      ).not.toBeInTheDocument()
      expect(fetch.mock.calls.filter(([url]) => url === '/api/holdings')).toHaveLength(1)
    },
  )
  it.each(['succeeded', 'failed'] as const)(
    'explicit same-security refresh %s owns completion while the first detail read is pending',
    async (outcome) => {
      const initial = deferred<unknown>()
      let reads = 0
      setup((url, options) => {
        if (url === '/api/stocks/1') {
          reads += 1
          if (reads === 1) return initial.promise
          return outcome === 'succeeded'
            ? Promise.resolve(jsonResponse(detail(1)))
            : Promise.reject(new Error('controlled synthetic read failure'))
        }
        if (url === '/api/data/securities/1/sync' && options?.method === 'POST')
          return Promise.resolve(
            jsonResponse({
              security_id: 1,
              category_outcomes: { news: { outcome: 'succeeded' } },
              warnings: [],
              data: securityFixture(),
            }),
          )
        return undefined
      })
      render(<App />)
      await screen.findByRole('table', { name: 'Watchlist holdings' })
      fireEvent.click(
        screen.getAllByRole('button', { name: 'View details for Security 1' })[0],
      )
      fireEvent.click(screen.getByRole('button', { name: 'Data center' }))
      await screen.findByText('Registered contract · Unknown')
      fireEvent.click(screen.getByRole('tab', { name: 'Security data' }))
      fireEvent.click(await screen.findByRole('button', { name: 'Retry · News' }))
      await screen.findByText('News: Succeeded', { exact: false })
      fireEvent.click(screen.getByRole('button', { name: 'Close data center' }))
      await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
      if (outcome === 'succeeded')
        await screen.findByRole('tab', { name: 'Market & fundamentals' })
      else await screen.findByText('Unable to load stock detail right now.')
      expect(screen.queryByText('Loading stock detail…')).not.toBeInTheDocument()
      const old = detail(1)
      old.security.name = 'Stale initial security'
      await act(async () => initial.resolve(jsonResponse(old)))
      expect(
        screen.queryByRole('heading', { name: 'Stale initial security' }),
      ).not.toBeInTheDocument()
      if (outcome === 'failed')
        expect(
          screen.getByText('Unable to load stock detail right now.'),
        ).toBeInTheDocument()
    },
  )
  it.each(['success', 'error'])(
    'new authoritative same-security detail survives a late legacy GET %s',
    async (outcome) => {
      const pending = deferred<unknown>()
      let reads = 0
      let signal: AbortSignal | undefined
      const pricedDetail = (price: string) => {
        const data = detail(1)
        data.price_context = [
          {
            last_price: price,
            change_amount: '1.0000',
            change_percent: '1.0000',
            snapshot_time: '2026-10-01T00:00:00Z',
          },
        ]
        return data
      }
      const fetch = setup((url, options) => {
        if (url === '/api/stocks/1/sync')
          return Promise.resolve(
            jsonResponse({
              security_id: 1,
              synced: true,
              announcements_upserted: 0,
              news_items_upserted: 0,
              price_bars_upserted: 0,
              financial_metrics_upserted: 0,
              company_profile_updated: false,
              warnings: [],
              synced_at: '2026-10-01T00:00:00Z',
            }),
          )
        if (url === '/api/stocks/1') {
          reads += 1
          if (reads === 2) {
            signal = options?.signal as AbortSignal
            return pending.promise
          }
          return Promise.resolve(
            jsonResponse(pricedDetail(reads === 1 ? '100.0000' : '200.0000')),
          )
        }
        if (url === '/api/data/securities/1/sync')
          return Promise.resolve(
            jsonResponse({
              security_id: 1,
              category_outcomes: { news: { outcome: 'empty' } },
              warnings: [],
              data: securityFixture(),
            }),
          )
        return undefined
      })
      render(<App />)
      await screen.findByRole('table', { name: 'Watchlist holdings' })
      fireEvent.click(
        screen.getAllByRole('button', { name: 'View details for Security 1' })[0],
      )
      fireEvent.click(await screen.findByRole('tab', { name: 'Holdings & AI' }))
      await screen.findByText('No holding is saved for this stock yet.')
      fireEvent.change(screen.getByLabelText('Quantity'), { target: { value: '123' } })
      await within(screen.getByRole('region', { name: 'Data provenance' })).findByText(
        /Unknown/,
      )
      fireEvent.click(screen.getByRole('button', { name: 'Sync latest information' }))
      await waitFor(() => expect(reads).toBe(2))
      await waitFor(() =>
        expect(
          fetch.mock.calls.filter(([url]) => url === '/api/data/securities/1'),
        ).toHaveLength(2),
      )
      fireEvent.click(screen.getByRole('button', { name: 'Inspect data in data center' }))
      fireEvent.click(await screen.findByRole('button', { name: 'Retry · News' }))
      await waitFor(() => expect(reads).toBe(3))
      fireEvent.click(await screen.findByRole('button', { name: 'Close data center' }))
      await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
      expect(screen.getByRole('tab', { name: 'Holdings & AI' })).toHaveAttribute(
        'aria-selected',
        'true',
      )
      expect(screen.getByLabelText('Quantity')).toHaveValue('123')
      fireEvent.click(screen.getByRole('tab', { name: 'Market & fundamentals' }))
      const quote = within(screen.getByRole('region', { name: 'Quote summary' }))
      await quote.findByText('200.0000')
      await act(async () => {
        if (outcome === 'error')
          pending.reject(new Error('obsolete legacy refresh error'))
        else pending.resolve(jsonResponse(pricedDetail('100.0000')))
      })
      expect(quote.getByText('200.0000')).toBeInTheDocument()
      expect(screen.queryByText('obsolete legacy refresh error')).not.toBeInTheDocument()
      expect(signal?.aborted).toBe(true)
      expect(screen.queryByText('Syncing latest information…')).not.toBeInTheDocument()
      expect(
        screen.getByRole('button', { name: 'Sync latest information' }),
      ).toBeEnabled()
      fireEvent.click(screen.getByRole('tab', { name: 'Holdings & AI' }))
      expect(screen.getByLabelText('Quantity')).toHaveValue('123')
    },
  )
  it.each(['sync', 'detail'])(
    'late legacy %s response cannot refresh a newer selection',
    async (phase) => {
      const pending = deferred<unknown>()
      let reads = 0
      let signal: AbortSignal | undefined
      const result = {
        security_id: 1,
        synced: true,
        announcements_upserted: 0,
        news_items_upserted: 0,
        price_bars_upserted: 0,
        financial_metrics_upserted: 0,
        company_profile_updated: false,
        warnings: [],
        synced_at: '2026-10-01T00:00:00Z',
      }
      const fetch = setup((url, options) => {
        if (url === '/api/stocks/1/sync') {
          signal = options?.signal as AbortSignal
          return phase === 'sync'
            ? pending.promise
            : Promise.resolve(jsonResponse(result))
        }
        if (url === '/api/stocks/1' && ++reads === 2 && phase === 'detail')
          return pending.promise
        return undefined
      })
      render(<App />)
      await screen.findByRole('table', { name: 'Watchlist holdings' })
      fireEvent.click(
        screen.getAllByRole('button', { name: 'View details for Security 1' })[0],
      )
      const status = within(
        await screen.findByRole('region', { name: 'Data provenance' }),
      )
      await status.findByText(/Unknown/)
      fireEvent.click(screen.getByRole('button', { name: 'Sync latest information' }))
      await waitFor(() => expect(signal).toBeDefined())
      if (phase === 'detail') await waitFor(() => expect(reads).toBe(2))
      fireEvent.click(screen.getByRole('button', { name: 'Back to watchlist' }))
      await screen.findByRole('table', { name: 'Watchlist holdings' })
      fireEvent.click(
        screen.getAllByRole('button', { name: 'View details for Security 2' })[0],
      )
      await screen.findByRole('heading', { name: 'Security 2' })
      await within(screen.getByRole('region', { name: 'Data provenance' })).findByText(
        /Unknown/,
      )
      expect(signal?.aborted).toBe(true)
      const healthReads = fetch.mock.calls.filter(([url]) =>
        url.startsWith('/api/data/securities/'),
      ).length
      await act(async () =>
        pending.resolve(jsonResponse(phase === 'sync' ? result : detail(1))),
      )
      expect(screen.getByRole('heading', { name: 'Security 2' })).toBeInTheDocument()
      expect(
        screen.queryByRole('heading', { name: 'Security 1' }),
      ).not.toBeInTheDocument()
      expect(
        fetch.mock.calls.filter(([url]) => url.startsWith('/api/data/securities/')),
      ).toHaveLength(healthReads)
    },
  )
  it.each([false, true])(
    'legacy sync refreshes saved health before its detail GET (GET failure: %s)',
    async (failDetail) => {
      let completed = false
      const savedDetail = detail(1)
      savedDetail.price_context = [
        {
          last_price: '100.0000',
          change_amount: '1.0000',
          change_percent: '1.0000',
          snapshot_time: '2026-09-01T00:00:00Z',
        },
      ]
      const fetch = setup((url) => {
        if (url === '/api/data/securities/1') {
          const health = securityFixture()
          health.categories.price_history.health = completed
            ? failDetail
              ? 'failed'
              : 'healthy'
            : 'unknown'
          return Promise.resolve(jsonResponse(health))
        }
        if (url === '/api/stocks/1/sync') {
          completed = true
          return Promise.resolve(
            jsonResponse({
              security_id: 1,
              synced: true,
              announcements_upserted: 0,
              news_items_upserted: 0,
              price_bars_upserted: 0,
              financial_metrics_upserted: 0,
              company_profile_updated: false,
              warnings: failDetail ? ['failed price fetch'] : [],
              synced_at: '2026-10-01T00:00:00Z',
            }),
          )
        }
        if (url === '/api/stocks/1')
          return Promise.resolve(
            completed && failDetail
              ? { ok: false, status: 503 }
              : jsonResponse(savedDetail),
          )
        return undefined
      })
      render(<App />)
      await screen.findByRole('table', { name: 'Watchlist holdings' })
      fireEvent.click(
        screen.getAllByRole('button', { name: 'View details for Security 1' })[0],
      )
      fireEvent.click(await screen.findByRole('tab', { name: 'Holdings & AI' }))
      await screen.findByText('No holding is saved for this stock yet.')
      fireEvent.change(screen.getByLabelText('Quantity'), { target: { value: '123' } })
      const status = within(screen.getByRole('region', { name: 'Data provenance' }))
      await status.findByText(/Unknown/)
      fireEvent.click(screen.getByRole('button', { name: 'Sync latest information' }))
      await status.findByText(
        failDetail ? /Failed attempt/ : /Within estimated freshness threshold/,
      )
      expect(
        fetch.mock.calls.filter(([url]) => url === '/api/data/securities/1'),
      ).toHaveLength(2)
      expect(screen.getByRole('tab', { name: 'Holdings & AI' })).toHaveAttribute(
        'aria-selected',
        'true',
      )
      expect(screen.getByLabelText('Quantity')).toHaveValue('123')
      fireEvent.click(screen.getByRole('tab', { name: 'Market & fundamentals' }))
      expect(
        within(screen.getByRole('region', { name: 'Quote summary' })).getByText(
          '100.0000',
        ),
      ).toBeInTheDocument()
      expect(
        fetch.mock.calls.filter(([, options]) => options?.method === 'POST'),
      ).toHaveLength(1)
    },
  )
  it('a completed failed acquisition updates mounted health without replacing retained prices or drafts', async () => {
    let health = securityFixture()
    const savedDetail = detail(1)
    savedDetail.price_context = [
      {
        last_price: '100.0000',
        change_amount: '1.0000',
        change_percent: '1.0000',
        snapshot_time: '2026-09-01T00:00:00Z',
      },
    ]
    const fetch = setup((url, options) => {
      if (url === '/api/stocks/1') return Promise.resolve(jsonResponse(savedDetail))
      if (url === '/api/data/securities/1') return Promise.resolve(jsonResponse(health))
      if (url === '/api/data/securities/1/sync' && options?.method === 'POST') {
        health = structuredClone(health)
        health.categories.price_history.health = 'failed'
        return Promise.resolve(
          jsonResponse({
            security_id: 1,
            category_outcomes: { price_history: { outcome: 'failed_fetch' } },
            warnings: [],
            data: health,
          }),
        )
      }
      return undefined
    })
    render(<App />)
    await screen.findByRole('table', { name: 'Watchlist holdings' })
    fireEvent.click(
      screen.getAllByRole('button', { name: 'View details for Security 1' })[0],
    )
    fireEvent.click(await screen.findByRole('tab', { name: 'Holdings & AI' }))
    await screen.findByText('No holding is saved for this stock yet.')
    fireEvent.change(screen.getByLabelText('Quantity'), { target: { value: '123' } })
    const status = within(screen.getByRole('region', { name: 'Data provenance' }))
    await status.findByText(/Unknown/)
    fireEvent.click(screen.getByRole('button', { name: 'Inspect data in data center' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Retry · Price history' }))
    await screen.findByText('Price history: Acquisition failed', { exact: false })
    fireEvent.click(screen.getByRole('button', { name: 'Close data center' }))
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    await status.findByText(/Failed attempt/)
    expect(
      status.queryByText(/Within estimated freshness threshold/),
    ).not.toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Holdings & AI' })).toHaveAttribute(
      'aria-selected',
      'true',
    )
    expect(screen.getByLabelText('Quantity')).toHaveValue('123')
    fireEvent.click(screen.getByRole('tab', { name: 'Market & fundamentals' }))
    expect(
      within(screen.getByRole('region', { name: 'Quote summary' })).getByText('100.0000'),
    ).toBeInTheDocument()
    expect(fetch.mock.calls.filter(([url]) => url === '/api/holdings')).toHaveLength(1)
    expect(
      fetch.mock.calls.filter(([, options]) => options?.method === 'POST'),
    ).toHaveLength(1)
    expect(
      fetch.mock.calls.filter(
        ([url, options]) => url.startsWith('/api/ai/') && options?.method === 'POST',
      ),
    ).toHaveLength(0)
  })
})
