import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { PriceHistoryChart } from './PriceHistoryChart'

vi.mock('lightweight-charts', () => {
  const mockSeries = { setData: vi.fn() }
  const mockTimeScale = { fitContent: vi.fn() }
  const mockPriceScale = { applyOptions: vi.fn() }
  const mockChart = {
    addSeries: vi.fn(() => mockSeries),
    priceScale: vi.fn(() => mockPriceScale),
    timeScale: vi.fn(() => mockTimeScale),
    applyOptions: vi.fn(),
    remove: vi.fn(),
  }
  return {
    createChart: vi.fn(() => mockChart),
    CandlestickSeries: 'CandlestickSeries',
    HistogramSeries: 'HistogramSeries',
    ColorType: { Solid: 'Solid' },
  }
})

describe('PriceHistoryChart', () => {
  it('renders an empty state when no price history is available', () => {
    render(<PriceHistoryChart priceHistory={[]} />)

    expect(
      screen.getByRole('heading', { name: 'Price history', level: 2 }),
    ).toBeInTheDocument()
    expect(screen.getByText('No price history is available yet.')).toBeInTheDocument()
    expect(screen.queryByRole('table', { name: 'Price history' })).not.toBeInTheDocument()
    expect(screen.queryByTestId('candlestick-chart')).not.toBeInTheDocument()
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
    expect(screen.getByTestId('candlestick-chart')).toBeInTheDocument()
  })

  it('shows 10 newest rows per page and paginates older rows', () => {
    render(
      <PriceHistoryChart
        priceHistory={Array.from({ length: 12 }, (_, index) => ({
          trade_date: `2026-03-${String(20 - index).padStart(2, '0')}`,
          open_price: `${index}.0000`,
          high_price: `${index}.1000`,
          low_price: `${index}.2000`,
          close_price: `${index}.3000`,
          volume: `${index}.4000`,
          amount: `${index}.5000`,
        }))}
      />,
    )

    expect(screen.getByText('Page 1 of 2')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Previous' })).toBeDisabled()
    expect(screen.getByRole('cell', { name: '2026-03-20' })).toBeInTheDocument()
    expect(screen.getByRole('cell', { name: '2026-03-11' })).toBeInTheDocument()
    expect(screen.queryByRole('cell', { name: '2026-03-10' })).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Next' }))

    expect(screen.getByText('Page 2 of 2')).toBeInTheDocument()
    expect(screen.getByRole('cell', { name: '2026-03-10' })).toBeInTheDocument()
    expect(screen.getByRole('cell', { name: '2026-03-09' })).toBeInTheDocument()
    expect(screen.queryByRole('cell', { name: '2026-03-20' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Next' })).toBeDisabled()
  })
})
