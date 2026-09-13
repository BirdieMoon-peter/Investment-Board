import { act, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { createChart } from 'lightweight-charts'
import type { StockDetailPriceHistoryBar } from '../types/watchlist'
import { CandlestickChart, transformBars } from './CandlestickChart'

const themeState = vi.hoisted(() => ({ resolvedTheme: 'light' }))
vi.mock('../theme', () => ({ useAppTheme: () => themeState }))
afterEach(() => { themeState.resolvedTheme = 'light'; vi.unstubAllGlobals() })

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
  it('updates theme options without recreating the chart, resetting its range or changing data', () => {
    const bars = makeBars([{ trade_date: '2026-01-01' }])
    const { rerender } = render(<CandlestickChart bars={bars} />)
    const chart = vi.mocked(vi.mocked(createChart).mock.results.slice(-1)[0].value, true)
    const creates = vi.mocked(createChart).mock.calls.length
    chart.applyOptions.mockClear()
    chart.timeScale().fitContent.mockClear()
    chart.addSeries.mock.results.forEach((result: { value: { setData: ReturnType<typeof vi.fn> } }) => vi.mocked(result.value!.setData).mockClear())
    themeState.resolvedTheme = 'dark'
    rerender(<CandlestickChart bars={bars} />)
    expect(createChart).toHaveBeenCalledTimes(creates)
    expect(chart.applyOptions).toHaveBeenCalledWith(expect.objectContaining({
      layout: { background: { type: 'Solid', color: '#1f1f1f' }, textColor: '#ffffff' },
      grid: { vertLines: { color: '#525252' }, horzLines: { color: '#525252' } },
      timeScale: { borderColor: '#666666' }, rightPriceScale: { borderColor: '#666666' },
    }))
    expect(chart.timeScale().fitContent).not.toHaveBeenCalled()
    chart.addSeries.mock.results.forEach((result: { value: { setData: ReturnType<typeof vi.fn> } }) => expect(result.value!.setData).not.toHaveBeenCalled())
  })

  it('ignores hidden zero widths, resizes when shown and disconnects on unmount', () => {
    let resize!: ResizeObserverCallback
    const disconnect = vi.fn()
    vi.stubGlobal('ResizeObserver', class {
      constructor(callback: ResizeObserverCallback) { resize = callback }
      observe = vi.fn()
      disconnect = disconnect
    })
    const { unmount } = render(<CandlestickChart bars={makeBars([{ trade_date: '2026-01-01' }])} />)
    const chart = vi.mocked(vi.mocked(createChart).mock.results.slice(-1)[0].value, true)
    chart.applyOptions.mockClear()
    chart.timeScale().fitContent.mockClear()
    act(() => resize([{ contentRect: { width: 0 } }] as ResizeObserverEntry[], {} as ResizeObserver))
    expect(chart.applyOptions).not.toHaveBeenCalled()
    act(() => resize([{ contentRect: { width: 640 } }] as ResizeObserverEntry[], {} as ResizeObserver))
    expect(chart.applyOptions).toHaveBeenCalledWith({ width: 640 })
    expect(chart.timeScale().fitContent).not.toHaveBeenCalled()
    unmount()
    expect(disconnect).toHaveBeenCalledOnce()
  })

})
