import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { SearchBox } from './SearchBox'

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('SearchBox', () => {
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
      expect(fetchMock).toHaveBeenCalledWith(
        '/api/watchlist/securities/search?query=Ping',
      )
    })

    expect(await screen.findByText('Ping An Bank')).toBeInTheDocument()
    expect(screen.getByText('SZ:000001')).toBeInTheDocument()

    const addButton = screen.getByRole('button', { name: /add/i })
    expect(addButton).toBeInTheDocument()

    fireEvent.click(addButton)

    expect(onAdd).toHaveBeenCalledWith(1)
  })

  it('shows externally discovered A-share results through the normal Add flow', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [
        {
          security_id: 99,
          market: 'SZ',
          code: '002594',
          name: 'BYD',
          industry: 'Auto',
          status: 'active',
        },
      ],
    })

    const onAdd = vi.fn()
    vi.stubGlobal('fetch', fetchMock)

    render(<SearchBox onAdd={onAdd} onAddCustom={vi.fn()} />)

    fireEvent.change(screen.getByLabelText(/search securities/i), {
      target: { value: '002594' },
    })
    fireEvent.click(screen.getByRole('button', { name: /search/i }))

    expect(await screen.findByText('BYD')).toBeInTheDocument()
    expect(screen.getByText('SZ:002594')).toBeInTheDocument()
    expect(
      screen.queryByLabelText(/market for custom stock/i),
    ).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /^add$/i }))
    expect(onAdd).toHaveBeenCalledWith(99)
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

    expect(
      await screen.findByLabelText(/market for custom stock/i),
    ).toHaveValue('SH')
    expect(
      screen.getByRole('button', { name: /add sh:600519/i }),
    ).toBeInTheDocument()

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

    expect(
      await screen.findByText(/no securities matched your search/i),
    ).toBeInTheDocument()
    expect(
      screen.queryByLabelText(/market for custom stock/i),
    ).not.toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: /add /i }),
    ).not.toBeInTheDocument()
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

    expect(
      await screen.findByRole('button', { name: /add sz:002594/i }),
    ).toBeInTheDocument()

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

    expect(
      await screen.findByText(/no securities matched your search/i),
    ).toBeInTheDocument()
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

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Search failed. Please try again.',
    )
  })
})

it('discards a pending search after the query changes and does not search while typing', async () => {
  let resolve!: (value: unknown) => void
  const fetchMock = vi.fn().mockReturnValue(
    new Promise((value) => {
      resolve = value
    }),
  )
  vi.stubGlobal('fetch', fetchMock)
  render(<SearchBox onAdd={vi.fn()} onAddCustom={vi.fn()} />)
  fireEvent.change(screen.getByLabelText(/search securities/i), {
    target: { value: 'Old' },
  })
  expect(fetchMock).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button', { name: /^search$/i }))
  fireEvent.change(screen.getByLabelText(/search securities/i), {
    target: { value: 'New' },
  })
  resolve({
    ok: true,
    json: async () => [
      { security_id: 1, name: 'Old result', market: 'SH', code: '600000' },
    ],
  })
  await waitFor(() =>
    expect(screen.queryByText(/searching/i)).not.toBeInTheDocument(),
  )
  expect(screen.queryByText('Old result')).not.toBeInTheDocument()
  expect(fetchMock).toHaveBeenCalledTimes(1)
})
it('keeps add failures in the search and prevents duplicate additions', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [
        { security_id: 1, name: 'Tracked', market: 'SH', code: '600001' },
        { security_id: 2, name: 'Available', market: 'SZ', code: '000002' },
      ],
    }),
  )
  const onAdd = vi.fn().mockRejectedValue(new Error('private upstream failure'))
  render(
    <SearchBox onAdd={onAdd} onAddCustom={vi.fn()} addedSecurityIds={[1]} />,
  )
  fireEvent.change(screen.getByLabelText(/search securities/i), {
    target: { value: 'a' },
  })
  fireEvent.click(screen.getByRole('button', { name: /^search$/i }))
  expect(
    await screen.findByRole('button', { name: 'Already added' }),
  ).toBeDisabled()
  fireEvent.click(screen.getByRole('button', { name: /^add$/i }))
  expect(await screen.findByRole('alert')).toHaveTextContent(
    'Unable to add that security to your watchlist right now.',
  )
  expect(screen.getByText('Available')).toBeInTheDocument()
})

it('keeps a newer successful result when an older submitted request fails later', async () => {
  let rejectOld!: (error: Error) => void
  const fetchMock = vi
    .fn()
    .mockReturnValueOnce(
      new Promise((_, reject) => {
        rejectOld = reject
      }),
    )
    .mockResolvedValueOnce({
      ok: true,
      json: async () => [
        { security_id: 2, name: 'New result', market: 'SZ', code: '000002' },
      ],
    })
  vi.stubGlobal('fetch', fetchMock)
  render(<SearchBox onAdd={vi.fn()} onAddCustom={vi.fn()} />)
  fireEvent.change(screen.getByLabelText('Search securities'), {
    target: { value: 'Old' },
  })
  fireEvent.click(screen.getByRole('button', { name: 'Search' }))
  fireEvent.change(screen.getByLabelText('Search securities'), {
    target: { value: 'New' },
  })
  fireEvent.click(screen.getByRole('button', { name: 'Search' }))
  await screen.findByText('New result')
  await act(async () => rejectOld(new Error('old failure')))
  expect(screen.getByText('New result')).toBeInTheDocument()
  expect(screen.queryByRole('alert')).not.toBeInTheDocument()
})
it('does not reuse an obsolete search after closing and reopening', async () => {
  let resolveOld!: (value: unknown) => void
  vi.stubGlobal(
    'fetch',
    vi.fn().mockReturnValue(
      new Promise((resolve) => {
        resolveOld = resolve
      }),
    ),
  )
  const old = render(<SearchBox onAdd={vi.fn()} onAddCustom={vi.fn()} />)
  fireEvent.change(screen.getByLabelText('Search securities'), {
    target: { value: 'Old' },
  })
  fireEvent.click(screen.getByRole('button', { name: 'Search' }))
  old.unmount()
  render(<SearchBox onAdd={vi.fn()} onAddCustom={vi.fn()} />)
  await act(async () =>
    resolveOld({
      ok: true,
      json: async () => [
        { security_id: 1, name: 'Old result', market: 'SH', code: '600001' },
      ],
    }),
  )
  expect(screen.getByLabelText('Search securities')).toHaveValue('')
  expect(screen.queryByText('Old result')).not.toBeInTheDocument()
})
