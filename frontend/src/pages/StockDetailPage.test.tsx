import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { fetchStockDetail, syncStock } from '../api/stocks'
import { StockDetailPage } from './StockDetailPage'
import type { StockDetailPageData } from '../types/watchlist'

vi.mock('../api/stocks', () => ({
  fetchStockDetail: vi.fn(),
  syncStock: vi.fn(),
}))

const detailData: StockDetailPageData = {
  security: {
    security_id: 7,
    market: 'SZ',
    code: '000001',
    name: 'Ping An Bank',
    industry: 'Banking',
    status: 'active',
  },
  price_context: [
    {
      trade_date: '2026-03-10',
      open_price: '10.0000',
      high_price: '10.5000',
      low_price: '9.8000',
      close_price: '10.3000',
      volume: '1234567.0000',
    },
  ],
  price_history: [
    {
      trade_date: '2026-03-09',
      open_price: '9.9000',
      high_price: '10.2000',
      low_price: '9.7000',
      close_price: '10.1000',
      volume: '1111111.0000',
      amount: '2222222.0000',
    },
  ],
  financial_metrics: [
    {
      report_period: '2025-12-31',
      revenue: '100000000.00',
      net_profit: '25000000.00',
      eps: '1.23',
      roe: '12.5%',
      debt_to_asset_ratio: null,
    },
  ],
  company_profile: {
    full_name: 'Ping An Bank Co., Ltd.',
    english_name: 'Ping An Bank Co., Ltd.',
    registered_capital: '19405918198',
    establishment_date: '1987-12-22',
    website: 'https://bank.example.com',
    main_business: 'Commercial banking services',
    employees: 12345,
  },
  announcements: [
    {
      title: '2025 annual results released',
      source: 'SZSE',
      url: 'https://example.com/announcements/1',
      summary: 'Net profit increased year over year.',
      published_at: '2026-03-09T18:00:00',
    },
  ],
  news: [
    {
      title: 'Broker raises target price',
      source: 'Market News',
      url: 'https://example.com/news/1',
      summary: 'Analyst cited improving fundamentals.',
      published_at: '2026-03-10T08:30:00',
    },
  ],
}

const refreshedDetailData: StockDetailPageData = {
  ...detailData,
  announcements: [
    {
      title: 'Fresh filing available',
      source: 'SZSE',
      url: 'https://example.com/announcements/2',
      summary: 'A newly synced filing is now visible.',
      published_at: '2026-03-11T09:00:00',
    },
  ],
  news: [
    {
      title: 'Latest article after sync',
      source: 'Market News',
      url: 'https://example.com/news/2',
      summary: 'A newly synced article is now visible.',
      published_at: '2026-03-11T10:00:00',
    },
  ],
}

const fetchStockDetailMock = vi.mocked(fetchStockDetail)
const syncStockMock = vi.mocked(syncStock)

describe('StockDetailPage', () => {
  beforeEach(() => {
    fetchStockDetailMock.mockReset()
    syncStockMock.mockReset()
  })

  it('renders the loading state', () => {
    render(
      <StockDetailPage
        detail={detailData}
        viewState="loading"
        onBack={vi.fn()}
      />,
    )

    expect(screen.getByRole('heading', { name: /ping an bank/i })).toBeInTheDocument()
    expect(screen.getByRole('status')).toHaveTextContent('Loading stock detail…')
  })

  it('renders the error state', () => {
    render(
      <StockDetailPage
        detail={detailData}
        viewState="error"
        onBack={vi.fn()}
      />,
    )

    expect(screen.getByRole('alert')).toHaveTextContent(
      'Unable to load stock detail right now.',
    )
  })

  it('renders the not found state', () => {
    render(
      <StockDetailPage
        detail={null}
        viewState="not-found"
        onBack={vi.fn()}
      />,
    )

    expect(screen.getByRole('alert')).toHaveTextContent(
      'The requested stock could not be found.',
    )
  })

  it('renders populated detail sections for a loaded stock', () => {
    render(
      <StockDetailPage
        detail={detailData}
        viewState="ready"
        onBack={vi.fn()}
      />,
    )

    expect(screen.getByRole('region', { name: /selected security summary/i })).toHaveTextContent(
      'SZ',
    )
    expect(screen.getByRole('region', { name: /selected security summary/i })).toHaveTextContent(
      'active',
    )
    expect(screen.getByRole('region', { name: /quote summary/i })).toHaveTextContent('10.3000')
    expect(screen.getByRole('region', { name: /quote summary/i })).toHaveTextContent('1234567.0000')
    expect(screen.getByRole('table', { name: /price history/i })).toHaveTextContent('2026-03-09')
    expect(screen.getByRole('table', { name: /price history/i })).toHaveTextContent('2222222.0000')
    expect(screen.getByRole('table', { name: /financial metrics/i })).toHaveTextContent('2025-12-31')
    expect(screen.getByRole('table', { name: /financial metrics/i })).toHaveTextContent('100000000.00')
    expect(screen.getByRole('list', { name: /company profile/i })).toHaveTextContent(
      'Ping An Bank Co., Ltd.',
    )
    expect(screen.getByRole('link', { name: 'https://bank.example.com' })).toHaveAttribute(
      'href',
      'https://bank.example.com',
    )
    expect(screen.getByText('12345')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /2025 annual results released/i })).toHaveAttribute(
      'href',
      'https://example.com/announcements/1',
    )
    expect(screen.getByText('Net profit increased year over year.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /broker raises target price/i })).toHaveAttribute(
      'href',
      'https://example.com/news/1',
    )
    expect(screen.getByText('Analyst cited improving fundamentals.')).toBeInTheDocument()
    expect(screen.queryByText('No price context is available yet.')).not.toBeInTheDocument()
    expect(screen.queryByText('No price history is available yet.')).not.toBeInTheDocument()
    expect(screen.queryByText('No financial metrics are available yet.')).not.toBeInTheDocument()
    expect(screen.queryByText('No company profile is available yet.')).not.toBeInTheDocument()
    expect(screen.queryByText('No announcements are available yet.')).not.toBeInTheDocument()
    expect(screen.queryByText('No news is available yet.')).not.toBeInTheDocument()
  })

  it('renders a stronger stock identity header with market, code, industry, and status', () => {
    render(
      <StockDetailPage
        detail={detailData}
        viewState="ready"
        onBack={vi.fn()}
      />,
    )

    const securitySummary = screen.getByRole('region', { name: /selected security summary/i })

    expect(screen.getByText('SZ:000001')).toBeInTheDocument()
    expect(securitySummary).toHaveTextContent('Banking')
    expect(securitySummary).toHaveTextContent('active')
  })

  it('shows sync controls and refreshes detail after a successful sync', async () => {
    syncStockMock.mockResolvedValue({
      security_id: 7,
      synced: true,
      announcements_upserted: 2,
      news_items_upserted: 3,
      price_bars_upserted: 5,
      financial_metrics_upserted: 4,
      company_profile_updated: true,
      warnings: ['announcement source B failed', 'news source A timeout'],
      synced_at: '2026-03-11T14:00:00',
    })
    fetchStockDetailMock.mockResolvedValue(refreshedDetailData)

    render(
      <StockDetailPage
        detail={detailData}
        viewState="ready"
        onBack={vi.fn()}
      />,
    )

    const syncButton = screen.getByRole('button', { name: /sync latest information/i })
    expect(syncButton).toBeInTheDocument()

    fireEvent.click(syncButton)

    expect(screen.getByRole('button', { name: /syncing latest information/i })).toBeDisabled()
    expect(screen.getByRole('status')).toHaveTextContent('Syncing latest information…')

    await waitFor(() => {
      expect(syncStockMock).toHaveBeenCalledWith(7)
    })
    await waitFor(() => {
      expect(fetchStockDetailMock).toHaveBeenCalledWith(7)
    })

    expect(await screen.findByRole('status')).toHaveTextContent(
      'Information sync partially completed. Announcements: 2, news items: 3, price bars: 5, financial metric sets: 4, company profile: updated.',
    )
    expect(screen.getByRole('alert')).toHaveTextContent('Warnings: announcement source B failed; news source A timeout')
    expect(await screen.findByRole('link', { name: /fresh filing available/i })).toHaveAttribute(
      'href',
      'https://example.com/announcements/2',
    )
    expect(await screen.findByRole('link', { name: /latest article after sync/i })).toHaveAttribute(
      'href',
      'https://example.com/news/2',
    )
  })

  it('shows an error message when sync fails and keeps existing detail visible', async () => {
    syncStockMock.mockRejectedValue(new Error('Unable to sync stock information right now.'))

    render(
      <StockDetailPage
        detail={detailData}
        viewState="ready"
        onBack={vi.fn()}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: /sync latest information/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Unable to sync stock information right now.',
    )
    expect(screen.getByRole('region', { name: /quote summary/i })).toHaveTextContent('10.3000')
    expect(fetchStockDetailMock).not.toHaveBeenCalled()
  })
})
