import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import App from './App'

describe('App', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    window.localStorage.clear()
  })

  it('loads the watchlist on mount, refreshes after add, and refreshes after remove', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => [],
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          indexes: [],
          macro: [],
          updated_at: null,
          warnings: [],
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => [
          {
            security_id: 7,
            market: 'SZ',
            code: '000001',
            name: 'Ping An Bank',
            industry: 'Banking',
            status: 'active',
          },
        ],
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ security_id: 7 }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => [
          {
            security_id: 7,
            market: 'SZ',
            code: '000001',
            name: 'Ping An Bank',
            industry: 'Banking',
            last_price: '10.2000',
            change_percent: '2.0000',
            snapshot_time: '2026-03-10T10:00:00',
          },
        ],
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ items: [] }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ removed: true, security_id: 7 }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => [],
      })

    vi.stubGlobal('fetch', fetchMock)

    render(<App />)

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith('/api/watchlist/items')
    })

    fireEvent.click(screen.getByRole('button', { name: /search and add/i }))
    fireEvent.change(screen.getByLabelText(/search securities/i), {
      target: { value: 'Ping' },
    })
    fireEvent.click(screen.getByRole('button', { name: /^search$/i }))

    const addButton = await screen.findByRole('button', { name: /^add$/i })
    fireEvent.click(addButton)
    await screen.findByRole('button', { name: 'Already added' })
    fireEvent.click(screen.getByRole('button', { name: 'Close search' }))

    await screen.findByRole('table', { name: /watchlist holdings/i })
    expect(screen.getAllByText('Ping An Bank').length).toBeGreaterThanOrEqual(2)
    expect(screen.getAllByText('SZ:000001').length).toBeGreaterThanOrEqual(2)
    expect(screen.getAllByText('10.2000').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('+2.0000%').length).toBeGreaterThanOrEqual(1)

    fireEvent.click(
      screen.getByRole('button', { name: 'Actions for Ping An Bank' }),
    )
    fireEvent.click(
      await screen.findByRole('menuitem', { name: 'Remove Ping An Bank' }),
    )
    fireEvent.click(
      within(
        await screen.findByRole('dialog', { name: 'Remove Ping An Bank?' }),
      ).getByRole('button', { name: 'Remove Ping An Bank' }),
    )

    await waitFor(() => {
      expect(screen.getByText(/your watchlist is empty/i)).toBeInTheDocument()
    })

    expect(fetchMock).toHaveBeenNthCalledWith(1, '/api/watchlist/items')
    expect(fetchMock).toHaveBeenNthCalledWith(2, '/api/homepage/overview')
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      '/api/watchlist/securities/search?query=Ping',
    )
    expect(fetchMock).toHaveBeenNthCalledWith(4, '/api/watchlist/items', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ security_id: 7 }),
    })
    expect(fetchMock).toHaveBeenNthCalledWith(5, '/api/watchlist/items')
    expect(fetchMock).toHaveBeenNthCalledWith(
      6,
      '/api/ai/watchlist-labels?use_cache=true',
    )
    expect(fetchMock).toHaveBeenNthCalledWith(7, '/api/watchlist/items/7', {
      method: 'DELETE',
    })
    expect(fetchMock).toHaveBeenNthCalledWith(8, '/api/watchlist/items')
  })

  it('navigates from the watchlist table to the stock detail shell and back', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => [
          {
            security_id: 7,
            market: 'SZ',
            code: '000001',
            name: 'Ping An Bank',
            industry: 'Banking',
            last_price: '10.2000',
            change_percent: '2.0000',
            snapshot_time: '2026-03-10T10:00:00',
          },
        ],
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          indexes: [],
          macro: [],
          updated_at: null,
          warnings: [],
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ items: [] }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          security: {
            security_id: 7,
            market: 'SZ',
            code: '000001',
            name: 'Ping An Bank',
            industry: 'Banking',
            status: 'active',
          },
          price_context: [],
          price_history: [],
          financial_metrics: [],
          company_profile: null,
          announcements: [],
          news: [],
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => [],
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ items: [] }),
      })

    vi.stubGlobal('fetch', fetchMock)

    render(<App />)

    await screen.findByRole('table', { name: /watchlist holdings/i })
    const scroll = vi.spyOn(window, 'scrollTo').mockImplementation(() => {})
    fireEvent.change(screen.getByLabelText('Filter watchlist'), {
      target: { value: 'Ping' },
    })
    fireEvent.change(screen.getByLabelText('Market filter'), {
      target: { value: 'SZ' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Last price' }))
    expect(screen.getAllByText('SZ:000001').length).toBeGreaterThanOrEqual(2)

    fireEvent.click(
      screen.getAllByRole('button', {
        name: /view details for ping an bank/i,
      })[0],
    )

    expect(
      await screen.findByRole('region', { name: 'Stock detail page shell' }),
    ).toBeInTheDocument()
    expect(
      await screen.findByRole('heading', { name: /ping an bank/i }),
    ).toBeInTheDocument()
    expect(
      await screen.findByText('No price context is available yet.'),
    ).toBeInTheDocument()
    fireEvent.click(screen.getByRole('tab', { name: 'Holdings & AI' }))
    expect(
      await screen.findByText('No holding is saved for this stock yet.'),
    ).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /back to watchlist/i }))

    expect(
      await screen.findByRole('table', { name: /watchlist holdings/i }),
    ).toBeInTheDocument()
    expect(fetchMock).toHaveBeenNthCalledWith(1, '/api/watchlist/items')
    expect(fetchMock).toHaveBeenNthCalledWith(2, '/api/homepage/overview')
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      '/api/ai/watchlist-labels?use_cache=true',
    )
    expect(screen.getByLabelText('Filter watchlist')).toHaveValue('Ping')
    expect(screen.getByLabelText('Market filter')).toHaveValue('SZ')
    expect(
      screen.getByRole('columnheader', { name: 'Last price' }),
    ).toHaveAttribute('aria-sort', 'ascending')
    expect(
      screen.getAllByRole('button', {
        name: /view details for ping an bank/i,
      })[0],
    ).toHaveFocus()
    expect(scroll).toHaveBeenCalledWith({ top: 0, behavior: 'instant' })
    scroll.mockRestore()
    expect(fetchMock).toHaveBeenNthCalledWith(4, '/api/stocks/7')
    expect(fetchMock).toHaveBeenNthCalledWith(5, '/api/holdings')
    expect(fetchMock).toHaveBeenNthCalledWith(6, '/api/ai/history')
    expect(fetchMock).toHaveBeenCalledTimes(6)
  })

  it('adds a custom stock after an empty search fallback and refreshes the watchlist', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => [],
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          indexes: [],
          macro: [],
          updated_at: null,
          warnings: [],
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => [],
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          security_id: 11,
          security: {
            security_id: 11,
            market: 'SZ',
            code: '002594',
            name: 'BYD',
            industry: 'Auto',
            status: 'active',
          },
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => [
          {
            security_id: 11,
            market: 'SZ',
            code: '002594',
            name: 'BYD',
            industry: 'Auto',
            last_price: null,
            change_percent: null,
            snapshot_time: null,
          },
        ],
      })

    vi.stubGlobal('fetch', fetchMock)

    render(<App />)

    await screen.findByText(/your watchlist is empty/i)

    fireEvent.click(screen.getByRole('button', { name: /search and add/i }))
    fireEvent.change(screen.getByLabelText(/search securities/i), {
      target: { value: '002594' },
    })
    fireEvent.click(screen.getByRole('button', { name: /^search$/i }))
    fireEvent.click(
      await screen.findByRole('button', { name: /add sz:002594/i }),
    )
    await screen.findByRole('button', { name: 'Already added' })
    fireEvent.click(screen.getByRole('button', { name: 'Close search' }))

    expect(
      await screen.findByRole('table', { name: /watchlist holdings/i }),
    ).toBeInTheDocument()
    expect(screen.getAllByText('BYD').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('SZ:002594').length).toBeGreaterThanOrEqual(1)
    expect(fetchMock).toHaveBeenNthCalledWith(1, '/api/watchlist/items')
    expect(fetchMock).toHaveBeenNthCalledWith(2, '/api/homepage/overview')
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      '/api/watchlist/securities/search?query=002594',
    )
    expect(fetchMock).toHaveBeenNthCalledWith(
      4,
      '/api/watchlist/items/custom',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ market: 'SZ', code: '002594' }),
      },
    )
    expect(fetchMock).toHaveBeenNthCalledWith(5, '/api/watchlist/items')
  })

  it('renders the watchlist empty state after an empty initial load', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => [],
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          indexes: [],
          macro: [],
          updated_at: null,
          warnings: [],
        }),
      })

    vi.stubGlobal('fetch', fetchMock)

    render(<App />)

    expect(await screen.findByRole('status')).toHaveTextContent(
      'Your watchlist is empty.',
    )
  })

  it('loads homepage overview and lets the user hide overview sections from settings', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => [],
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          indexes: [
            {
              key: 'shanghai_composite',
              name: '上证指数',
              market: 'SH',
              last_value: '3957.0500',
              change_amount: '-49.5000',
              change_percent: '-1.2400',
              snapshot_time: '2026-03-22T15:00:00',
            },
          ],
          macro: [
            {
              key: 'cpi',
              title: 'CPI',
              category: 'inflation',
              value: '1.3',
              unit: '%',
              change_text: '环比1%',
              published_at: '2026-03-01T00:00:00',
              importance: 'high',
              summary: '2026年02月份',
            },
          ],
          updated_at: '2026-03-22T15:00:00',
          warnings: [],
        }),
      })

    vi.stubGlobal('fetch', fetchMock)

    render(<App />)

    expect(await screen.findByText('上证指数')).toBeInTheDocument()
    expect(screen.getByText('CPI')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /open settings/i }))
    await screen.findByRole('tab', { name: 'Interface and refresh' })
    fireEvent.click(screen.getByLabelText(/show market indexes/i))
    fireEvent.click(screen.getByLabelText(/show macro panel/i))

    await waitFor(() => {
      expect(screen.queryByText('上证指数')).not.toBeInTheDocument()
      expect(screen.queryByText('CPI')).not.toBeInTheDocument()
    })
  })

  it('renders homepage overview warning state without blocking watchlist rendering', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => [
          {
            security_id: 7,
            market: 'SZ',
            code: '000001',
            name: 'Ping An Bank',
            industry: 'Banking',
            last_price: '10.2000',
            change_percent: '2.0000',
            snapshot_time: '2026-03-10T10:00:00',
          },
        ],
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          indexes: [],
          macro: [],
          updated_at: null,
          warnings: [{ section: 'indexes', message: 'upstream timeout' }],
        }),
      })

    vi.stubGlobal('fetch', fetchMock)

    render(<App />)

    expect(
      await screen.findByRole('table', { name: /watchlist holdings/i }),
    ).toBeInTheDocument()
    expect(await screen.findByText(/overview warnings:/i)).toBeInTheDocument()
  })

  it('renders a visible add failure message when the add request fails', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => [],
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          indexes: [],
          macro: [],
          updated_at: null,
          warnings: [],
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => [
          {
            security_id: 7,
            market: 'SZ',
            code: '000001',
            name: 'Ping An Bank',
            industry: 'Banking',
            status: 'active',
          },
        ],
      })
      .mockResolvedValueOnce({
        ok: false,
        json: async () => ({ detail: 'add failed' }),
      })

    vi.stubGlobal('fetch', fetchMock)

    render(<App />)

    await screen.findByText(/your watchlist is empty/i)

    fireEvent.click(screen.getByRole('button', { name: /search and add/i }))
    fireEvent.change(screen.getByLabelText(/search securities/i), {
      target: { value: 'Ping' },
    })
    fireEvent.click(screen.getByRole('button', { name: /^search$/i }))
    fireEvent.click(await screen.findByRole('button', { name: /^add$/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Unable to add that security to your watchlist right now.',
    )
    expect(fetchMock).toHaveBeenCalledTimes(4)
  })

  it('renders a visible remove failure message when the remove request fails', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => [
          {
            security_id: 7,
            market: 'SZ',
            code: '000001',
            name: 'Ping An Bank',
            industry: 'Banking',
            last_price: '10.2000',
            change_percent: '2.0000',
            snapshot_time: '2026-03-10T10:00:00',
          },
        ],
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          indexes: [],
          macro: [],
          updated_at: null,
          warnings: [],
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ items: [] }),
      })
      .mockResolvedValueOnce({
        ok: false,
        json: async () => ({ detail: 'remove failed' }),
      })

    vi.stubGlobal('fetch', fetchMock)

    render(<App />)

    await screen.findByRole('table', { name: /watchlist holdings/i })

    fireEvent.click(
      screen.getByRole('button', { name: 'Actions for Ping An Bank' }),
    )
    fireEvent.click(
      await screen.findByRole('menuitem', { name: 'Remove Ping An Bank' }),
    )
    fireEvent.click(
      within(
        await screen.findByRole('dialog', { name: 'Remove Ping An Bank?' }),
      ).getByRole('button', { name: 'Remove Ping An Bank' }),
    )

    expect(
      await screen.findByText(
        'Unable to remove that security from your watchlist right now.',
      ),
    ).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(
      screen.getByRole('table', { name: /watchlist holdings/i }),
    ).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledTimes(4)
  })
})

it.each([false, true])(
  'restores a filtered-out spotlight origin or a list fallback after detail (origin hidden: %s)',
  async (hideOrigin) => {
    const security = {
      security_id: 7,
      market: 'SZ',
      code: '000001',
      name: 'Ping An Bank',
      industry: 'Banking',
      status: 'active',
    }
    const items = [
      {
        ...security,
        last_price: '10.2000',
        change_percent: '5.0000',
        snapshot_time: null,
      },
      {
        ...security,
        security_id: 8,
        name: 'Other Bank',
        code: '000002',
        last_price: '9.0000',
        change_percent: '-1.0000',
      },
    ]
    const fetch = vi.fn((url: string) =>
      Promise.resolve({
        ok: true,
        status: 200,
        json: async () => {
          if (url === '/api/watchlist/items') return items
          if (url === '/api/homepage/overview')
            return { indexes: [], macro: [], updated_at: null, warnings: [] }
          if (url === '/api/stocks/7')
            return {
              security,
              price_context: [],
              price_history: [],
              financial_metrics: [],
              company_profile: null,
              announcements: [],
              news: [],
            }
          if (url === '/api/holdings') return []
          return { items: [] }
        },
      }),
    )
    vi.stubGlobal('fetch', fetch)
    const scroll = vi.spyOn(window, 'scrollTo').mockImplementation(() => {})
    try {
      render(<App />)
      await screen.findByRole('table')
      fireEvent.change(screen.getByLabelText('Filter watchlist'), {
        target: { value: 'Other' },
      })
      expect(
        within(screen.getByRole('table')).queryByText('Ping An Bank'),
      ).not.toBeInTheDocument()
      fireEvent.click(
        screen.getByRole('button', { name: 'View details for Ping An Bank' }),
      )
      await screen.findByRole('heading', { name: 'Ping An Bank' })
      if (hideOrigin) {
        fireEvent.click(screen.getByRole('button', { name: 'Open settings' }))
        await screen.findByRole('tab', { name: 'Interface and refresh' })
        fireEvent.click(screen.getByLabelText('Show spotlight section'))
        fireEvent.click(screen.getByRole('button', { name: 'Close settings' }))
      }
      fireEvent.click(
        await screen.findByRole('button', { name: 'Back to watchlist' }),
      )
      await screen.findByRole('table')
      expect(screen.getByLabelText('Filter watchlist')).toHaveValue('Other')
      expect(
        screen.getByRole('button', {
          name: hideOrigin ? 'Search and add' : 'View details for Ping An Bank',
        }),
      ).toHaveFocus()
      expect(scroll).toHaveBeenCalledWith({ top: 0, behavior: 'instant' })
    } finally {
      scroll.mockRestore()
      window.localStorage.clear()
      vi.unstubAllGlobals()
    }
  },
)
