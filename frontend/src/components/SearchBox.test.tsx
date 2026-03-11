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

    render(<SearchBox onAdd={onAdd} />)

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

  it('renders the empty-result state when a search returns no matches', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [],
    })

    vi.stubGlobal('fetch', fetchMock)

    render(<SearchBox onAdd={vi.fn()} />)

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

    render(<SearchBox onAdd={vi.fn()} />)

    fireEvent.change(screen.getByLabelText(/search securities/i), {
      target: { value: 'Ping' },
    })
    fireEvent.click(screen.getByRole('button', { name: /search/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Search failed. Please try again.')
  })
})
