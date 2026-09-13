import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import type { StockDetailPriceHistoryBar } from '../types/watchlist'
import { CandlestickChart, transformBars } from './CandlestickChart'

// Mock lightweight-charts so tests don't need a real canvas
vi.mock('lightweight-charts', () => {
  const mockSeries = {
    setData: vi.fn(),
  }
  const mockTimeScale = {
    fitContent: vi.fn(),
  }
  const mockPriceScale = {
    applyOptions: vi.fn(),
  }
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

const makeBars = (
  overrides: Partial<StockDetailPriceHistoryBar>[] = [],
): StockDetailPriceHistoryBar[] =>
  overrides.map((o) => ({
    trade_date: '2026-01-01',
    open_price: '10.00',
    high_price: '11.00',
    low_price: '9.00',
    close_price: '10.50',
    volume: '100000',
    amount: '1050000.00',
    ...o,
  }))

describe('transformBars', () => {
  it('sorts bars ascending by trade_date', () => {
    const bars = makeBars([
      { trade_date: '2026-01-03' },
      { trade_date: '2026-01-01' },
      { trade_date: '2026-01-02' },
    ])

    const { candles } = transformBars(bars)

    expect(candles.map((c) => c.time)).toEqual([
      '2026-01-01',
      '2026-01-02',
      '2026-01-03',
    ])
  })

  it('parses string prices to numbers', () => {
    const bars = makeBars([
      { open_price: '12.34', high_price: '15.67', low_price: '11.11', close_price: '14.00' },
    ])

    const { candles } = transformBars(bars)

    expect(candles[0]).toEqual(
      expect.objectContaining({ open: 12.34, high: 15.67, low: 11.11, close: 14 }),
    )
  })

  it('assigns green color when close >= open, red otherwise', () => {
    const bars = makeBars([
      { trade_date: '2026-01-01', open_price: '10.00', close_price: '12.00' },
      { trade_date: '2026-01-02', open_price: '12.00', close_price: '10.00' },
      { trade_date: '2026-01-03', open_price: '10.00', close_price: '10.00' },
    ])

    const { volumes } = transformBars(bars)

    expect(volumes[0].color).toBe('#26a69a') // green — close > open
    expect(volumes[1].color).toBe('#ef5350') // red — close < open
    expect(volumes[2].color).toBe('#26a69a') // green — close == open
  })

  it('filters out bars with NaN price values', () => {
    const bars = makeBars([
      { trade_date: '2026-01-01', open_price: 'bad' },
      { trade_date: '2026-01-02' },
    ])

    const { candles } = transformBars(bars)

    expect(candles).toHaveLength(1)
    expect(candles[0].time).toBe('2026-01-02')
  })

  it('returns empty arrays for empty input', () => {
    const { candles, volumes } = transformBars([])

    expect(candles).toEqual([])
    expect(volumes).toEqual([])
  })
})

describe('CandlestickChart', () => {
  it('renders a chart container', () => {
    const bars = makeBars([{ trade_date: '2026-01-01' }])

    render(<CandlestickChart bars={bars} />)

    expect(screen.getByTestId('candlestick-chart')).toBeInTheDocument()
  })

  it('renders a chart container with empty bars', () => {
    render(<CandlestickChart bars={[]} />)

    expect(screen.getByTestId('candlestick-chart')).toBeInTheDocument()
  })
})
