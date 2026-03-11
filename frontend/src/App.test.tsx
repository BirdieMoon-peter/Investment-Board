import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import App from './App'

describe('App', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
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

    fireEvent.change(screen.getByLabelText(/search securities/i), {
      target: { value: 'Ping' },
    })
    fireEvent.click(screen.getByRole('button', { name: /search/i }))

    const addButton = await screen.findByRole('button', { name: /add/i })
    fireEvent.click(addButton)

    await screen.findByRole('table', { name: /watchlist holdings/i })
    expect(screen.getAllByText('Ping An Bank')).toHaveLength(2)
    expect(screen.getByText('10.2000')).toBeInTheDocument()
    expect(screen.getByText('2.0000%')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /remove ping an bank/i }))

    await waitFor(() => {
      expect(screen.getByText(/your watchlist is empty/i)).toBeInTheDocument()
    })

    expect(fetchMock).toHaveBeenNthCalledWith(1, '/api/watchlist/items')
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      '/api/watchlist/securities/search?query=Ping',
    )
    expect(fetchMock).toHaveBeenNthCalledWith(3, '/api/watchlist/items', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ security_id: 7 }),
    })
    expect(fetchMock).toHaveBeenNthCalledWith(4, '/api/watchlist/items')
    expect(fetchMock).toHaveBeenNthCalledWith(5, '/api/watchlist/items/7', {
      method: 'DELETE',
    })
    expect(fetchMock).toHaveBeenNthCalledWith(6, '/api/watchlist/items')
  })

  it('navigates from the watchlist table to the stock detail shell and back', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => [
          {
            security_id: 7,
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
          announcements: [],
          news: [],
        }),
      })

    vi.stubGlobal('fetch', fetchMock)

    render(<App />)

    await screen.findByRole('table', { name: /watchlist holdings/i })

    fireEvent.click(screen.getByRole('button', { name: /view details for ping an bank/i }))

    expect(screen.getByRole('heading', { name: /stock detail/i })).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: /ping an bank/i })).toBeInTheDocument()
    expect(await screen.findByText('No price context is available yet.')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /back to watchlist/i }))

    expect(await screen.findByRole('table', { name: /watchlist holdings/i })).toBeInTheDocument()
    expect(fetchMock).toHaveBeenNthCalledWith(1, '/api/watchlist/items')
    expect(fetchMock).toHaveBeenNthCalledWith(2, '/api/stocks/7')
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('renders the watchlist empty state after an empty initial load', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [],
    })

    vi.stubGlobal('fetch', fetchMock)

    render(<App />)

    expect(await screen.findByRole('status')).toHaveTextContent('Your watchlist is empty.')
  })

  it('renders the watchlist load error state when the initial request fails', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      json: async () => ({ detail: 'boom' }),
    })

    vi.stubGlobal('fetch', fetchMock)

    render(<App />)

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Unable to load your watchlist right now.',
    )
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

    fireEvent.change(screen.getByLabelText(/search securities/i), {
      target: { value: 'Ping' },
    })
    fireEvent.click(screen.getByRole('button', { name: /search/i }))
    fireEvent.click(await screen.findByRole('button', { name: /add/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Unable to add that security to your watchlist right now.',
    )
    expect(fetchMock).toHaveBeenCalledTimes(3)
  })

  it('renders a visible remove failure message when the remove request fails', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => [
          {
            security_id: 7,
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
        ok: false,
        json: async () => ({ detail: 'remove failed' }),
      })

    vi.stubGlobal('fetch', fetchMock)

    render(<App />)

    await screen.findByRole('table', { name: /watchlist holdings/i })

    fireEvent.click(screen.getByRole('button', { name: /remove ping an bank/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Unable to remove that security from your watchlist right now.',
    )
    expect(screen.getByRole('table', { name: /watchlist holdings/i })).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })
})
