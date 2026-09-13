import { useEffect, useRef } from 'react'
import {
  createChart,
  CandlestickSeries,
  HistogramSeries,
  type IChartApi,
  type ISeriesApi,
  type CandlestickData,
  type HistogramData,
  type Time,
  ColorType,
} from 'lightweight-charts'

import type { StockDetailPriceHistoryBar } from '../types/watchlist'

interface CandlestickSeriesData {
  time: Time
  open: number
  high: number
  low: number
  close: number
}

interface VolumeSeriesData {
  time: Time
  value: number
  color: string
}

export interface TransformedBars {
  candles: CandlestickSeriesData[]
  volumes: VolumeSeriesData[]
}

const GREEN = '#26a69a'
const RED = '#ef5350'

export function transformBars(bars: StockDetailPriceHistoryBar[]): TransformedBars {
  const sorted = [...bars].sort((a, b) => a.trade_date.localeCompare(b.trade_date))

  const candles: CandlestickSeriesData[] = []
  const volumes: VolumeSeriesData[] = []

  for (const bar of sorted) {
    const open = parseFloat(bar.open_price)
    const high = parseFloat(bar.high_price)
    const low = parseFloat(bar.low_price)
    const close = parseFloat(bar.close_price)
    const volume = parseFloat(bar.volume)

    if ([open, high, low, close].some(Number.isNaN)) continue

    const time = bar.trade_date as Time

    candles.push({ time, open, high, low, close })
    volumes.push({
      time,
      value: Number.isNaN(volume) ? 0 : volume,
      color: close >= open ? GREEN : RED,
    })
  }

  return { candles, volumes }
}

interface CandlestickChartProps {
  bars: StockDetailPriceHistoryBar[]
  height?: number
}

export function CandlestickChart({ bars, height = 400 }: CandlestickChartProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const candleSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null)

  // Mount / unmount chart
  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const chart = createChart(container, {
      height,
      layout: {
        background: { type: ColorType.Solid, color: '#ffffff' },
        textColor: '#333',
      },
      grid: {
        vertLines: { color: '#eee' },
        horzLines: { color: '#eee' },
      },
      timeScale: { borderColor: '#ccc' },
    })

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: GREEN,
      downColor: RED,
      borderDownColor: RED,
      borderUpColor: GREEN,
      wickDownColor: RED,
      wickUpColor: GREEN,
    })

    const volumeSeries = chart.addSeries(HistogramSeries, {
      priceFormat: { type: 'volume' },
      priceScaleId: 'volume',
    })

    chart.priceScale('volume').applyOptions({
      scaleMargins: { top: 0.8, bottom: 0 },
    })

    chartRef.current = chart
    candleSeriesRef.current = candleSeries
    volumeSeriesRef.current = volumeSeries

    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width } = entry.contentRect
        if (width > 0) chart.applyOptions({ width })
      }
    })
    observer.observe(container)

    return () => {
      observer.disconnect()
      chart.remove()
      chartRef.current = null
      candleSeriesRef.current = null
      volumeSeriesRef.current = null
    }
  }, [height])

  // Update data
  useEffect(() => {
    if (!candleSeriesRef.current || !volumeSeriesRef.current) return

    const { candles, volumes } = transformBars(bars)
    candleSeriesRef.current.setData(candles as CandlestickData<Time>[])
    volumeSeriesRef.current.setData(volumes as HistogramData<Time>[])
    chartRef.current?.timeScale().fitContent()
  }, [bars])

  return (
    <div
      ref={containerRef}
      data-testid="candlestick-chart"
      style={{ width: '100%' }}
    />
  )
}
