import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { WatchlistTable } from './WatchlistTable'

describe('WatchlistTable', () => {
  it('renders market and code together in the watchlist table', () => {
    render(
      <WatchlistTable
        items={[
          {
            security_id: 1,
            market: 'SZ',
            code: '000001',
            name: 'Ping An Bank',
            industry: 'Banking',
            last_price: null,
            change_percent: null,
            snapshot_time: null,
          },
        ]}
        onOpenDetail={vi.fn()}
        onRemove={vi.fn()}
      />,
    )

    expect(screen.getByText('SZ:000001')).toBeInTheDocument()
  })

  it('renders a fallback when quote data is missing and removes an item when requested', async () => {
    const onRemove = vi.fn()

    render(
      <WatchlistTable
        items={[
          {
            security_id: 1,
            market: 'SZ',
            code: '000001',
            name: 'Ping An Bank',
            industry: 'Banking',
            last_price: null,
            change_percent: null,
            snapshot_time: null,
          },
        ]}
        onOpenDetail={vi.fn()}
        onRemove={onRemove}
      />,
    )

    expect(
      screen.getByRole('table', { name: /watchlist holdings/i }),
    ).toBeInTheDocument()
    expect(screen.getByText('Ping An Bank')).toBeInTheDocument()
    expect(screen.getByText('SZ:000001')).toBeInTheDocument()
    expect(screen.getAllByText('Pending sync')).toHaveLength(2)

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

    expect(onRemove).toHaveBeenCalledWith(1)
  })
})
