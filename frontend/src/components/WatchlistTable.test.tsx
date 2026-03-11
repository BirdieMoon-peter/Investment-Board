import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { WatchlistTable } from './WatchlistTable'

describe('WatchlistTable', () => {
  it('renders a fallback when quote data is missing and removes an item when requested', () => {
    const onRemove = vi.fn()

    render(
      <WatchlistTable
        items={[
          {
            security_id: 1,
            code: '000001',
            name: 'Ping An Bank',
            industry: 'Banking',
            last_price: null,
            change_percent: null,
            snapshot_time: null,
          },
        ]}
        onRemove={onRemove}
      />,
    )

    expect(screen.getByRole('table', { name: /watchlist holdings/i })).toBeInTheDocument()
    expect(screen.getByText('Ping An Bank')).toBeInTheDocument()
    expect(screen.getByText('000001')).toBeInTheDocument()
    expect(screen.getAllByText('Pending sync')).toHaveLength(2)

    fireEvent.click(screen.getByRole('button', { name: /remove ping an bank/i }))

    expect(onRemove).toHaveBeenCalledWith(1)
  })
})
