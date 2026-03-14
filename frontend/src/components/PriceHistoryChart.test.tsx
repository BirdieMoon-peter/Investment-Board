import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { PriceHistoryChart } from './PriceHistoryChart'

describe('PriceHistoryChart', () => {
  it('renders an empty state when no price history is available', () => {
    render(<PriceHistoryChart priceHistory={[]} />)

    expect(
      screen.getByRole('heading', { name: 'Price history', level: 2 }),
    ).toBeInTheDocument()
    expect(screen.getByText('No price history is available yet.')).toBeInTheDocument()
    expect(screen.queryByRole('table', { name: 'Price history' })).not.toBeInTheDocument()
  })

  it('renders a price history table with preserved string values', () => {
    render(
      <PriceHistoryChart
        priceHistory={[
          {
            trade_date: '2026-03-12',
            open_price: '12.3400',
            high_price: '12.5600',
            low_price: '12.1100',
            close_price: '12.5000',
            volume: '123456789',
            amount: '987654321.00',
          },
        ]}
      />,
    )

    expect(screen.getByRole('table', { name: 'Price history' })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'Trade date' })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'Open' })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'High' })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'Low' })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'Close' })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'Volume' })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'Amount' })).toBeInTheDocument()
    expect(screen.getByRole('cell', { name: '2026-03-12' })).toBeInTheDocument()
    expect(screen.getByRole('cell', { name: '12.3400' })).toBeInTheDocument()
    expect(screen.getByRole('cell', { name: '12.5600' })).toBeInTheDocument()
    expect(screen.getByRole('cell', { name: '12.1100' })).toBeInTheDocument()
    expect(screen.getByRole('cell', { name: '12.5000' })).toBeInTheDocument()
    expect(screen.getByRole('cell', { name: '123456789' })).toBeInTheDocument()
    expect(screen.getByRole('cell', { name: '987654321.00' })).toBeInTheDocument()
  })
})
