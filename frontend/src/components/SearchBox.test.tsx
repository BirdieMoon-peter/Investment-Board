import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { SearchBox } from './SearchBox'

describe('SearchBox', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('searches for securities, renders an Add button, and calls onAdd when clicked', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [
        {
          security_id: 1,
          market: 'SZ',
          code: '000001',
          name: 'Ping An Bank',
          industry: 'Banking',
          status: 'active',
        },
      ],
    })

    const onAdd = vi.fn()

    vi.stubGlobal('fetch', fetchMock)

    render(<SearchBox onAdd={onAdd} onAddCustom={vi.fn()} />)

    fireEvent.change(screen.getByLabelText(/search securities/i), {
      target: { value: 'Ping' },
    })
    fireEvent.click(screen.getByRole('button', { name: /search/i }))

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith('/api/watchlist/securities/search?query=Ping')
    })

    expect(await screen.findByText('Ping An Bank')).toBeInTheDocument()
    expect(screen.getByText('SZ:000001')).toBeInTheDocument()

    const addButton = screen.getByRole('button', { name: /add/i })
    expect(addButton).toBeInTheDocument()

    fireEvent.click(addButton)

    expect(onAdd).toHaveBeenCalledWith(1)
  })

  it('offers a market selector with a safe default for a custom code fallback', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [],
    })

    const onAddCustom = vi.fn()

    vi.stubGlobal('fetch', fetchMock)

    render(<SearchBox onAdd={vi.fn()} onAddCustom={onAddCustom} />)

    fireEvent.change(screen.getByLabelText(/search securities/i), {
      target: { value: '600519' },
    })
    fireEvent.click(screen.getByRole('button', { name: /search/i }))

    expect(await screen.findByLabelText(/market for custom stock/i)).toHaveValue('SH')
    expect(screen.getByRole('button', { name: /add sh:600519/i })).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText(/market for custom stock/i), {
      target: { value: 'SZ' },
    })
    fireEvent.click(screen.getByRole('button', { name: /add sz:600519/i }))

    expect(onAddCustom).toHaveBeenCalledWith('SZ', '600519')
  })

  it('does not offer custom add for a freeform non-code query', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [],
    })

    vi.stubGlobal('fetch', fetchMock)

    render(<SearchBox onAdd={vi.fn()} onAddCustom={vi.fn()} />)

    fireEvent.change(screen.getByLabelText(/search securities/i), {
      target: { value: 'Ping An' },
    })
    fireEvent.click(screen.getByRole('button', { name: /search/i }))

    expect(await screen.findByText(/no securities matched your search/i)).toBeInTheDocument()
    expect(screen.queryByLabelText(/market for custom stock/i)).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /add /i })).not.toBeInTheDocument()
  })

  it('offers custom add when search returns no matches and adds by market and code', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [],
    })

    const onAddCustom = vi.fn()

    vi.stubGlobal('fetch', fetchMock)

    render(<SearchBox onAdd={vi.fn()} onAddCustom={onAddCustom} />)

    fireEvent.change(screen.getByLabelText(/search securities/i), {
      target: { value: '002594' },
    })
    fireEvent.click(screen.getByRole('button', { name: /search/i }))

    expect(await screen.findByRole('button', { name: /add sz:002594/i })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /add sz:002594/i }))

    expect(onAddCustom).toHaveBeenCalledWith('SZ', '002594')
  })

  it('renders the empty-result state when a search returns no matches', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [],
    })

    vi.stubGlobal('fetch', fetchMock)

    render(<SearchBox onAdd={vi.fn()} onAddCustom={vi.fn()} />)

    fireEvent.change(screen.getByLabelText(/search securities/i), {
      target: { value: 'Missing' },
    })
    fireEvent.click(screen.getByRole('button', { name: /search/i }))

    expect(await screen.findByText(/no securities matched your search/i)).toBeInTheDocument()
  })

  it('renders the search error state when the request fails', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      json: async () => ({ detail: 'boom' }),
    })

    vi.stubGlobal('fetch', fetchMock)

    render(<SearchBox onAdd={vi.fn()} onAddCustom={vi.fn()} />)

    fireEvent.change(screen.getByLabelText(/search securities/i), {
      target: { value: 'Ping' },
    })
    fireEvent.click(screen.getByRole('button', { name: /search/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Search failed. Please try again.')
  })
})
