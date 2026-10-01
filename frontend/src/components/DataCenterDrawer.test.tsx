import { useState } from 'react'
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { DataCenterDrawer } from './DataCenterDrawer'
import { I18nProvider } from '../i18n'
import {
  catalogFixture,
  deferred,
  jsonResponse,
  securityFixture,
  watchlistFixture,
  attemptFixture,
} from '../test/dataCenterFixtures'
import type { SecurityData } from '../types/dataCenter'
const synced = vi.fn()
function Harness({
  language = 'en',
  initial = 1,
}: {
  language?: 'en' | 'zh'
  initial?: number | null
}) {
  const [open, setOpen] = useState(true)
  return (
    <I18nProvider language={language}>
      {open ? (
        <DataCenterDrawer
          items={watchlistFixture}
          initialSecurityId={initial}
          onClose={() => setOpen(false)}
          onSynced={synced}
        />
      ) : (
        <p>Closed</p>
      )}
    </I18nProvider>
  )
}
function mockRead(data = securityFixture()) {
  const fetch = vi
    .fn()
    .mockImplementation((url: string) =>
      Promise.resolve(
        jsonResponse(url === '/api/data/sources' ? { sources: catalogFixture } : data),
      ),
    )
  vi.stubGlobal('fetch', fetch)
  return fetch
}
afterEach(() => {
  vi.unstubAllGlobals()
  synced.mockReset()
})
describe('source-first data center', () => {
  it('opens with saved GET only and keeps registered sources distinct from health', async () => {
    const fetch = mockRead()
    render(<Harness initial={null} />)
    expect(await screen.findByText('Registered contract · Unknown')).toBeInTheDocument()
    expect(fetch.mock.calls.every(([, options]) => options.method === 'GET')).toBe(true)
    expect(fetch.mock.calls.every(([url]) => url.startsWith('/api/data/'))).toBe(true)
    expect(screen.getByRole('switch')).toBeChecked()
    fireEvent.change(screen.getByLabelText('Vendor'), { target: { value: 'tencent' } })
    await screen.findByRole('heading', { name: 'tencent' })
    expect(screen.queryByRole('switch')).not.toBeInTheDocument()
    expect(
      screen.getByText(
        'Untracked homepage / lookup · Daily · Forward adjusted (source confirmed)',
      ),
    ).toBeInTheDocument()
    fireEvent.click(screen.getByText('Endpoint and field details'))
    expect(screen.getByText('close_price', { exact: false })).toBeInTheDocument()
  })
  it('shows independent vendor failures and last success even after disabling', async () => {
    const failed = {
      ...catalogFixture[0],
      runtime: {
        state: 'failed',
        recent_attempts: [attemptFixture],
        latest_attempt: attemptFixture,
        last_succeeded_attempt: {
          ...attemptFixture,
          id: 2,
          status: 'succeeded',
          state: 'succeeded',
          finished_at: '2026-09-01T00:00:00Z',
        },
      },
    }
    const fetch = vi
      .fn()
      .mockImplementation((url: string, options: { method: string }) =>
        Promise.resolve(
          jsonResponse(
            url === '/api/data/sources'
              ? { sources: [failed, ...catalogFixture.slice(1)] }
              : options.method === 'PUT'
                ? { ...failed, enabled: false }
                : securityFixture(),
          ),
        ),
      )
    vi.stubGlobal('fetch', fetch)
    render(<Harness initial={null} />)
    await screen.findByText('Registered contract · Failed attempt')
    fireEvent.click(screen.getByRole('switch'))
    await waitFor(() => expect(screen.getByRole('switch')).not.toBeChecked())
    expect(screen.getByText('Registered contract · Failed attempt')).toBeInTheDocument()
    expect(screen.getByText('fetch_error', { exact: false })).toBeInTheDocument()
    expect(
      JSON.parse(fetch.mock.calls.find(([, o]) => o.method === 'PUT')![1].body),
    ).toEqual({ enabled: false })
  })
  it('retries just the chosen category with explicit price source and presents partial evidence without faking health', async () => {
    const data = securityFixture()
    data.categories.price_history.fetched_at = '2026-09-01T00:00:00Z'
    data.categories.price_history.source_key = 'sina'
    const next = structuredClone(data)
    next.categories.price_history.health = 'partial'
    const fetch = mockRead(data)
    fetch.mockImplementation((url: string, options: { method: string }) =>
      Promise.resolve(
        jsonResponse(
          options.method === 'POST'
            ? {
                security_id: 1,
                category_outcomes: {
                  price_history: { outcome: 'partial', received: 3, written: 2 },
                },
                warnings: ['One row rejected'],
                data: next,
              }
            : url === '/api/data/sources'
              ? { sources: catalogFixture }
              : data,
        ),
      ),
    )
    render(<Harness />)
    await screen.findByRole('heading', { name: 'Security 1' })
    fireEvent.change(screen.getByLabelText('Price history source'), {
      target: { value: 'sina' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Retry · Price history' }))
    await screen.findByText('One row rejected')
    expect(
      JSON.parse(fetch.mock.calls.find(([, o]) => o.method === 'POST')![1].body),
    ).toEqual({ categories: ['price_history'], price_source: 'sina' })
    expect(synced).toHaveBeenCalledWith(1)
    expect(screen.getByText('Partial / warnings')).toBeInTheDocument()
    expect(
      screen.getByText('Price history: Partial / warnings', { exact: false }),
    ).toBeInTheDocument()
  })
  it('failed retry retains saved acquisition timestamp, shows safe error and remains retryable', async () => {
    const data = securityFixture()
    data.categories.price_history.fetched_at = '2026-09-01T00:00:00Z'
    data.categories.price_history.unit = 'CNY'
    const fetch = mockRead(data)
    fetch.mockImplementation((url: string, options: { method: string }) =>
      options.method === 'POST'
        ? Promise.resolve({
            ok: false,
            status: 503,
            json: async () => ({ detail: 'secret' }),
          })
        : Promise.resolve(
            jsonResponse(
              url === '/api/data/sources' ? { sources: catalogFixture } : data,
            ),
          ),
    )
    render(<Harness />)
    await screen.findByText('CNY / — (not supplied or unverified)')
    fireEvent.click(screen.getByRole('button', { name: 'Retry · Price history' }))
    await screen.findByRole('alert')
    expect(screen.queryByText(/secret/)).not.toBeInTheDocument()
    expect(screen.getByText('09/01/2026, 08:00:00')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Retry · Price history' })).toBeEnabled()
    expect(synced).not.toHaveBeenCalled()
  })
  it('blocks all close and duplicate mutation routes while busy', async () => {
    const pending = deferred<unknown>()
    const fetch = mockRead()
    fetch.mockImplementation((url: string, o: { method: string }) =>
      o.method === 'POST'
        ? pending.promise
        : Promise.resolve(
            jsonResponse(
              url === '/api/data/sources'
                ? { sources: catalogFixture }
                : securityFixture(),
            ),
          ),
    )
    render(<Harness />)
    await screen.findByRole('heading', { name: 'Security 1' })
    fireEvent.click(screen.getByRole('button', { name: 'Retry · News' }))
    expect(screen.getByRole('button', { name: 'Close data center' })).toBeDisabled()
    expect(screen.getByLabelText('Watchlist security')).toBeDisabled()
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(screen.queryByText('Closed')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Retry · News' }))
    expect(fetch.mock.calls.filter(([, o]) => o.method === 'POST')).toHaveLength(1)
    await act(async () =>
      pending.resolve(
        jsonResponse({
          security_id: 1,
          category_outcomes: { news: { outcome: 'failed_fetch' } },
          warnings: [],
          data: securityFixture(),
        }),
      ),
    )
    expect(synced).toHaveBeenCalledWith(1)
    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Close data center' })).toBeEnabled(),
    )
  })
  it('protects metadata draft on close and selection, validates qualified benchmark, labels exact fees/NAV missing honestly', async () => {
    mockRead()
    render(<Harness />)
    await screen.findByText('0.5%')
    expect(screen.getByText('0.1%')).toBeInTheDocument()
    expect(screen.getByText('No connected benchmark')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Edit manual metadata' }))
    fireEvent.change(screen.getByLabelText('Market-qualified benchmark code'), {
      target: { value: '000300' },
    })
    expect(screen.getByRole('button', { name: 'Save' })).toBeDisabled()
    fireEvent.change(screen.getByLabelText('Market-qualified benchmark code'), {
      target: { value: 'SH:000300' },
    })
    expect(screen.getByRole('button', { name: 'Save' })).toBeEnabled()
    fireEvent.click(screen.getByRole('button', { name: 'Close data center' }))
    await screen.findByRole('dialog', { name: 'Discard unsaved metadata?' })
    fireEvent.click(screen.getByRole('button', { name: 'Continue editing' }))
    expect(screen.getByLabelText('Market-qualified benchmark code')).toHaveValue(
      'SH:000300',
    )
    fireEvent.change(screen.getByLabelText('Watchlist security'), {
      target: { value: '2' },
    })
    await screen.findByRole('dialog', { name: 'Discard unsaved metadata?' })
    fireEvent.click(screen.getByRole('button', { name: 'Discard changes' }))
    await waitFor(() =>
      expect(screen.getByLabelText('Watchlist security')).toHaveValue('2'),
    )
  })
  it('saves manual overlay with separate provider fee fields and cancellation', async () => {
    const data = securityFixture(),
      saved = structuredClone(data)
    saved.metadata.classification_origin = 'manual'
    saved.metadata.benchmark_code = 'SH:000300'
    const fetch = mockRead(data)
    fetch.mockImplementation((url: string, o: { method: string }) =>
      Promise.resolve(
        jsonResponse(
          o.method === 'PUT'
            ? saved
            : url === '/api/data/sources'
              ? { sources: catalogFixture }
              : data,
        ),
      ),
    )
    render(<Harness />)
    await screen.findByText('0.5%')
    fireEvent.click(screen.getByRole('button', { name: 'Edit manual metadata' }))
    fireEvent.change(screen.getByLabelText('Market-qualified benchmark code'), {
      target: { value: 'SH:000300' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    await screen.findByText('SH:000300')
    expect(
      screen.getByText('ETF · Manual classification and benchmark overlay'),
    ).toBeInTheDocument()
    expect(screen.getByText('0.5%')).toBeInTheDocument()
    expect(synced).toHaveBeenCalledWith(1)
    fireEvent.click(screen.getByRole('button', { name: 'Edit manual metadata' }))
    fireEvent.change(screen.getByLabelText('Benchmark name'), {
      target: { value: 'Unsaved' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    fireEvent.click(screen.getByRole('button', { name: 'Close data center' }))
    expect(await screen.findByText('Closed')).toBeInTheDocument()
  })
  it('aborts stale security read and ignores late response after a newer selection', async () => {
    const pending = deferred<unknown>()
    const signals: AbortSignal[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((url: string, o: { signal: AbortSignal }) => {
        if (url === '/api/data/sources')
          return Promise.resolve(jsonResponse({ sources: catalogFixture }))
        if (url.endsWith('/1')) {
          signals.push(o.signal)
          return pending.promise
        }
        return Promise.resolve(jsonResponse(securityFixture(2)))
      }),
    )
    render(<Harness />)
    fireEvent.change(screen.getByLabelText('Watchlist security'), {
      target: { value: '2' },
    })
    await screen.findByRole('heading', { name: 'Security 2' })
    expect(signals[0].aborted).toBe(true)
    await act(async () => pending.resolve(jsonResponse(securityFixture(1))))
    expect(screen.queryByRole('heading', { name: 'Security 1' })).not.toBeInTheDocument()
  })
  it('aborts pending mutation on unmount and cannot refresh parent from its late result', async () => {
    const pending = deferred<unknown>()
    let signal: AbortSignal | undefined
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockImplementation((url: string, o: { method: string; signal: AbortSignal }) => {
          if (o.method === 'POST') {
            signal = o.signal
            return pending.promise
          }
          return Promise.resolve(
            jsonResponse(
              url === '/api/data/sources'
                ? { sources: catalogFixture }
                : securityFixture(),
            ),
          )
        }),
    )
    const view = render(<Harness />)
    await screen.findByRole('heading', { name: 'Security 1' })
    fireEvent.click(screen.getByRole('button', { name: 'Retry · News' }))
    view.unmount()
    expect(signal?.aborted).toBe(true)
    await act(async () =>
      pending.resolve(
        jsonResponse({
          security_id: 1,
          category_outcomes: { news: { outcome: 'succeeded' } },
          warnings: [],
          data: securityFixture(),
        }),
      ),
    )
    expect(synced).not.toHaveBeenCalled()
  })
  it('renders bilingual unknown and index provenance, distinct NAV kinds and dates', async () => {
    const data = securityFixture()
    data.metadata.effective_instrument_type = 'index'
    data.categories.price_history.unit = 'index_points'
    data.categories.price_history.context_disclosures = [
      'Retained legacy context is unverified',
    ]
    data.nav_observations = [
      {
        nav_date: '2026-09-30',
        nav_kind: 'unit_nav',
        value: '1.123400',
        source_key: 'eastmoney_fund_nav',
        fetched_at: '2026-10-01T00:00:00Z',
        published_at: null,
      },
      {
        nav_date: '2026-09-30',
        nav_kind: 'cumulative_nav',
        value: '2.345600',
        source_key: 'eastmoney_fund_nav',
        fetched_at: '2026-10-01T00:00:00Z',
        published_at: null,
      },
    ]
    mockRead(data)
    render(<Harness language="zh" />)
    await screen.findByText('单位净值')
    expect(screen.getByText('累计净值')).toBeInTheDocument()
    expect(screen.getByText('1.123400')).toBeInTheDocument()
    expect(screen.getByText('2.345600')).toBeInTheDocument()
    expect(screen.getByText('Retained legacy context is unverified')).toBeInTheDocument()
    expect(screen.getByText('指数点 / —（未提供或未经验证）')).toBeInTheDocument()
    expect(screen.getByText(/旧版派生上下文只读展示/)).toBeInTheDocument()
  })
  it('supports empty watchlist and source load retry without acquiring externally', async () => {
    const fetch = vi
      .fn()
      .mockResolvedValueOnce({ ok: false, status: 503 })
      .mockResolvedValue(jsonResponse({ sources: catalogFixture }))
    vi.stubGlobal('fetch', fetch)
    render(<DataCenterDrawer items={[]} onClose={vi.fn()} onSynced={synced} />)
    await screen.findByRole('alert')
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
    await screen.findByText('Registered contract · Unknown')
    fireEvent.click(screen.getByRole('tab', { name: 'Security data' }))
    expect(
      screen.getByText('Add a security to your watchlist to inspect saved datasets.'),
    ).toBeInTheDocument()
    expect(
      fetch.mock.calls.every(
        ([url, o]) => url === '/api/data/sources' && o.method === 'GET',
      ),
    ).toBe(true)
  })
  it('benchmark editing starts from effective unknown rather than a retained historical ETF', async () => {
    const data = securityFixture()
    data.metadata.instrument_type = 'etf'
    data.metadata.effective_instrument_type = 'unknown'
    data.metadata.classification_origin = 'fund_profile_unresolved'
    const fetch = mockRead(data)
    render(<Harness />)
    await screen.findByRole('heading', { name: 'Security 1' })
    fireEvent.click(screen.getByRole('button', { name: 'Edit manual metadata' }))
    expect(screen.getByLabelText('Instrument classification')).toHaveValue('unknown')
    fireEvent.change(screen.getByLabelText('Market-qualified benchmark code'), {
      target: { value: 'SH:000300' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    await waitFor(() =>
      expect(fetch.mock.calls.some(([, o]) => o.method === 'PUT')).toBe(true),
    )
    expect(
      JSON.parse(fetch.mock.calls.find(([, o]) => o.method === 'PUT')![1].body)
        .instrument_type,
    ).toBe('unknown')
  })
  it.each([
    'announcements',
    'news',
    'price_history',
    'quote_snapshot',
    'financial_metrics',
    'company_profile',
    'fund_nav',
    'fund_profile',
  ])('retry %s never requests unrelated categories', async (category) => {
    const fetch = mockRead()
    fetch.mockImplementation((url: string, o: { method: string }) =>
      Promise.resolve(
        jsonResponse(
          o.method === 'POST'
            ? {
                security_id: 1,
                category_outcomes: { [category]: { outcome: 'empty' } },
                warnings: [],
                data: securityFixture(),
              }
            : url === '/api/data/sources'
              ? { sources: catalogFixture }
              : securityFixture(),
        ),
      ),
    )
    render(<Harness />)
    await screen.findByRole('heading', { name: 'Security 1' })
    const names: Record<string, string> = {
      announcements: 'Announcements',
      news: 'News',
      price_history: 'Price history',
      quote_snapshot: 'Quote snapshot',
      financial_metrics: 'Financial metrics',
      company_profile: 'Company profile',
      fund_nav: 'Fund NAV',
      fund_profile: 'Fund profile',
    }
    fireEvent.click(screen.getByRole('button', { name: `Retry · ${names[category]}` }))
    await waitFor(() =>
      expect(fetch.mock.calls.some(([, o]) => o.method === 'POST')).toBe(true),
    )
    expect(
      JSON.parse(fetch.mock.calls.find(([, o]) => o.method === 'POST')![1].body),
    ).toEqual({ categories: [category] })
    await screen.findByText(`${names[category]}: Empty result`, { exact: false })
    expect(synced).toHaveBeenCalledWith(1)
  })
  it('disabling a selected price provider resets retry choice and keeps its history visible', async () => {
    const fetch = mockRead()
    fetch.mockImplementation((url: string, o: { method: string }) =>
      Promise.resolve(
        jsonResponse(
          o.method === 'PUT'
            ? { ...catalogFixture[1], enabled: false }
            : url === '/api/data/sources'
              ? { sources: catalogFixture }
              : securityFixture(),
        ),
      ),
    )
    render(<Harness />)
    await screen.findByRole('heading', { name: 'Security 1' })
    fireEvent.change(screen.getByLabelText('Price history source'), {
      target: { value: 'sina' },
    })
    fireEvent.click(screen.getByRole('tab', { name: 'Sources' }))
    fireEvent.change(screen.getByLabelText('Vendor'), { target: { value: 'sina' } })
    fireEvent.click(screen.getByRole('switch'))
    await waitFor(() => expect(screen.getByRole('switch')).not.toBeChecked())
    fireEvent.click(screen.getByRole('tab', { name: 'Security data' }))
    expect(screen.getByLabelText('Price history source')).toHaveValue('')
    expect(screen.getByRole('option', { name: 'sina · Unknown' })).toBeDisabled()
  })
  it('a catalog reload cannot overwrite a later confirmed disable or re-enable its price choice', async () => {
    const pending = deferred<unknown>()
    let reads = 0
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((url: string, options: RequestInit) => {
        if (url === '/api/data/sources') {
          reads += 1
          return reads === 1
            ? Promise.resolve(jsonResponse({ sources: catalogFixture }))
            : pending.promise
        }
        if (options.method === 'PUT')
          return Promise.resolve(jsonResponse({ ...catalogFixture[0], enabled: false }))
        if (options.method === 'POST')
          return Promise.resolve(
            jsonResponse({
              security_id: 1,
              category_outcomes: { news: { outcome: 'empty' } },
              warnings: [],
              data: securityFixture(),
            }),
          )
        return Promise.resolve(jsonResponse(securityFixture()))
      }),
    )
    render(<Harness />)
    fireEvent.click(await screen.findByRole('button', { name: 'Retry · News' }))
    await waitFor(() => expect(reads).toBe(2))
    fireEvent.change(screen.getByLabelText('Price history source'), {
      target: { value: 'eastmoney' },
    })
    fireEvent.click(screen.getByRole('tab', { name: 'Sources' }))
    fireEvent.click(screen.getByRole('switch'))
    await waitFor(() => expect(screen.getByRole('switch')).not.toBeChecked())
    await act(async () => pending.resolve(jsonResponse({ sources: catalogFixture })))
    expect(screen.getByRole('switch')).not.toBeChecked()
    fireEvent.click(screen.getByRole('tab', { name: 'Security data' }))
    expect(screen.getByLabelText('Price history source')).toHaveValue('')
    expect(
      screen
        .getByLabelText('Price history source')
        .querySelector('option[value="eastmoney"]'),
    ).toBeDisabled()
  })
  it('aborted metadata save cannot notify the detail owner from its late response', async () => {
    const pending = deferred<unknown>()
    let signal: AbortSignal | undefined
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockImplementation((url: string, o: { method: string; signal: AbortSignal }) => {
          if (o.method === 'PUT') {
            signal = o.signal
            return pending.promise
          }
          return Promise.resolve(
            jsonResponse(
              url === '/api/data/sources'
                ? { sources: catalogFixture }
                : securityFixture(),
            ),
          )
        }),
    )
    const view = render(<Harness />)
    await screen.findByRole('button', { name: 'Edit manual metadata' })
    fireEvent.click(screen.getByRole('button', { name: 'Edit manual metadata' }))
    fireEvent.change(screen.getByLabelText('Instrument classification'), {
      target: { value: 'index' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    view.unmount()
    expect(signal?.aborted).toBe(true)
    await act(async () => pending.resolve(jsonResponse(securityFixture())))
    expect(synced).not.toHaveBeenCalled()
  })
  it.each([
    'empty',
    'disabled',
    'unavailable',
    'failed_fetch',
    'failed_persist',
  ] as const)(
    'completed %s outcome invalidates saved health without claiming success',
    async (outcome) => {
      const data = securityFixture()
      data.categories.price_history.health = 'unknown'
      const fetch = mockRead(data)
      fetch.mockImplementation((url: string, o: { method: string }) =>
        Promise.resolve(
          jsonResponse(
            o.method === 'POST'
              ? {
                  security_id: 1,
                  category_outcomes: { price_history: { outcome } },
                  warnings: [],
                  data,
                }
              : url === '/api/data/sources'
                ? { sources: catalogFixture }
                : data,
          ),
        ),
      )
      render(<Harness />)
      fireEvent.click(
        await screen.findByRole('button', { name: 'Retry · Price history' }),
      )
      await waitFor(() => expect(synced).toHaveBeenCalledWith(1))
      expect(synced).toHaveBeenCalledTimes(1)
      expect(
        screen.queryByText('Within estimated freshness threshold'),
      ).not.toBeInTheDocument()
      expect(fetch.mock.calls.filter(([, o]) => o.method === 'POST')).toHaveLength(1)
    },
  )
})
