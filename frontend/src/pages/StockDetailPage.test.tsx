import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { generateHoldingAdvice, generateStockAdvice, fetchInvestmentAdviceHistory } from '../api/investmentAdvice'
import { fetchHoldings, removeHolding, upsertHolding, updateHolding } from '../api/holdings'
import { fetchStockDetail, syncStock } from '../api/stocks'
import { StockDetailPage } from './StockDetailPage'
import { I18nProvider } from '../i18n'
import type { InvestmentAdviceResponse } from '../types/investmentAdvice'
import type { StockDetailPageData, StockDetailPriceBar } from '../types/watchlist'

vi.mock('../api/stocks', () => ({
  fetchStockDetail: vi.fn(),
  syncStock: vi.fn(),
}))

vi.mock('../api/holdings', () => ({
  fetchHoldings: vi.fn(),
  upsertHolding: vi.fn(),
  updateHolding: vi.fn(),
  removeHolding: vi.fn(),
}))

vi.mock('../api/investmentAdvice', () => ({
  fetchInvestmentAdviceHistory: vi.fn(),
  generateStockAdvice: vi.fn(),
  generateHoldingAdvice: vi.fn(),
}))

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

const stalePriceContextBar: StockDetailPriceBar = {
  last_price: '9.1000',
  change_amount: '-0.1000',
  change_percent: '-1.0000',
  snapshot_time: '2026-03-09T15:00:00',
}

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
      last_price: '10.3000',
      change_amount: '0.3000',
      change_percent: '3.0000',
      snapshot_time: '2026-03-10T15:00:00',
    },
    stalePriceContextBar,
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

const paginatedDetailData: StockDetailPageData = {
  ...detailData,
  announcements: Array.from({ length: 12 }, (_, index) => ({
    title: `Announcement ${12 - index}`,
    source: 'SZSE',
    url: `https://example.com/announcements/${12 - index}`,
    summary: `Announcement summary ${12 - index}`,
    published_at: `2026-03-${String(20 - index).padStart(2, '0')}T09:00:00`,
  })),
  news: Array.from({ length: 12 }, (_, index) => ({
    title: `News ${12 - index}`,
    source: 'Market News',
    url: `https://example.com/news/${12 - index}`,
    summary: `News summary ${12 - index}`,
    published_at: `2026-03-${String(20 - index).padStart(2, '0')}T10:00:00`,
  })),
}

const fetchStockDetailMock = vi.mocked(fetchStockDetail)
const syncStockMock = vi.mocked(syncStock)
const fetchHoldingsMock = vi.mocked(fetchHoldings)
const upsertHoldingMock = vi.mocked(upsertHolding)
const updateHoldingMock = vi.mocked(updateHolding)
const removeHoldingMock = vi.mocked(removeHolding)
const fetchInvestmentAdviceHistoryMock = vi.mocked(fetchInvestmentAdviceHistory)
const generateStockAdviceMock = vi.mocked(generateStockAdvice)
const generateHoldingAdviceMock = vi.mocked(generateHoldingAdvice)

const holdingData = {
  holding_id: 1,
  security_id: 7,
  security: detailData.security,
  quantity: '80.0000',
  average_cost: '10.0000',
  notes: 'Base position',
  target_horizon: 'long_term' as const,
}

const adviceData: InvestmentAdviceResponse = {
  advice_id: 2,
  target_type: 'holding',
  target_id: 1,
  security_id: 7,
  holding_id: 1,
  market: 'SZ',
  code: '000001',
  name: 'Ping An Bank',
  recommendation: 'accumulate',
  confidence: 'medium',
  summary: 'Position can be added on pullbacks.',
  thesis_points: ['Valuation remains acceptable'],
  risk_points: ['Short-term volatility remains elevated'],
  position_notes: ['Average cost is below spot'],
  recent_catalysts: ['Broker target hike'],
  full_analysis: 'Detailed view.',
  warnings: [],
  generated_at: '2026-03-22T16:00:00',
  cached: true,
  disclaimer: 'Model-generated content, not financial advice.',
}

const freshStockAdviceData: InvestmentAdviceResponse = {
  ...adviceData,
  target_type: 'stock',
  target_id: 7,
  holding_id: null,
  cached: false,
  generated_at: '2026-03-24T18:00:00',
  summary: 'Fresh stock advice generated from the live provider.',
}

describe('StockDetailPage', () => {
  beforeEach(() => {
    fetchStockDetailMock.mockReset()
    syncStockMock.mockReset()
    fetchHoldingsMock.mockReset()
    upsertHoldingMock.mockReset()
    updateHoldingMock.mockReset()
    removeHoldingMock.mockReset()
    fetchInvestmentAdviceHistoryMock.mockReset()
    generateStockAdviceMock.mockReset()
    generateHoldingAdviceMock.mockReset()

    fetchHoldingsMock.mockResolvedValue([])
    fetchInvestmentAdviceHistoryMock.mockResolvedValue({ items: [] })
  })

  async function renderReadyDetailPage(data: StockDetailPageData = detailData) {
    render(
      <StockDetailPage
        detail={data}
        viewState="ready"
        onBack={vi.fn()}
      />,
    )

    await waitFor(() => {
      expect(fetchHoldingsMock).toHaveBeenCalled()
      expect(fetchInvestmentAdviceHistoryMock).toHaveBeenCalled()
    })
  }

  it('opens the market group by default and keeps other groups mounted but inaccessible', async () => {
    await renderReadyDetailPage()
    expect(screen.getByRole('tab', { name: 'Market & fundamentals' })).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByRole('tabpanel', { name: 'Market & fundamentals' })).toBeVisible()
    expect(screen.getAllByRole('tabpanel', { hidden: true })).toHaveLength(3)
    expect(screen.queryByRole('button', { name: 'Save holding' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Broker raises target price' })).not.toBeInTheDocument()
  })

  it('keeps holding drafts and selected history across groups without generating advice', async () => {
    fetchHoldingsMock.mockResolvedValue([holdingData])
    fetchInvestmentAdviceHistoryMock.mockResolvedValue({ items: [freshStockAdviceData, adviceData] })
    await renderReadyDetailPage()
    fireEvent.click(screen.getByRole('tab', { name: 'Holdings & AI' }))
    await screen.findByDisplayValue('80.0000')
    fireEvent.change(screen.getByLabelText('Notes'), { target: { value: 'Unsaved research note' } })
    const history = screen.getByRole('list', { name: 'Advice history' })
    fireEvent.click(within(history).getAllByRole('button')[1])
    expect(screen.getByText(adviceData.summary)).toBeVisible()
    fireEvent.click(screen.getByRole('tab', { name: 'News & announcements' }))
    expect(screen.queryByRole('textbox', { name: 'Notes' })).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('tab', { name: 'Market & fundamentals' }))
    fireEvent.click(screen.getByRole('tab', { name: 'Holdings & AI' }))
    expect(screen.getByLabelText('Notes')).toHaveValue('Unsaved research note')
    expect(screen.getByText(adviceData.summary)).toBeVisible()
    expect(fetchHoldingsMock).toHaveBeenCalledTimes(1)
    expect(fetchInvestmentAdviceHistoryMock).toHaveBeenCalledTimes(1)
    expect(generateStockAdviceMock).not.toHaveBeenCalled()
    expect(generateHoldingAdviceMock).not.toHaveBeenCalled()
  })

  it('keeps wide table regions keyboard reachable without exposing collapsed prices', async () => {
    await renderReadyDetailPage()
    expect(screen.getByRole('region', { name: 'Recent price context' })).toHaveAttribute('tabindex', '0')
    expect(screen.getByRole('region', { name: 'Financial metrics' })).toHaveAttribute('tabindex', '0')
    expect(screen.queryByRole('region', { name: 'Price history' })).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Raw price data' }))
    expect(screen.getByRole('region', { name: 'Price history' })).toHaveAttribute('tabindex', '0')
  })

  it('shares the active group between the mobile selector and desktop tabs', async () => {
    await renderReadyDetailPage()
    fireEvent.change(screen.getByRole('combobox', { name: 'Research group' }), { target: { value: 'news' } })
    expect(screen.getByRole('tab', { name: 'News & announcements' })).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByRole('tabpanel', { name: 'News & announcements' })).toBeVisible()
    fireEvent.click(screen.getByRole('tab', { name: 'Holdings & AI' }))
    expect(screen.getByRole('combobox', { name: 'Research group' })).toHaveValue('holdings')
  })

  function openHoldingsGroup() {
    fireEvent.click(screen.getByRole('tab', { name: /Holdings & AI|持仓与 AI/ }))
  }

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

  it('renders populated detail sections for a loaded stock', async () => {
    await renderReadyDetailPage()

    expect(screen.getByRole('region', { name: /selected security summary/i })).toHaveTextContent(
      'SZ',
    )
    expect(screen.getByRole('region', { name: /selected security summary/i })).toHaveTextContent(
      'active',
    )
    expect(screen.getByRole('region', { name: /quote summary/i })).toHaveTextContent('10.3000')
    expect(screen.getByRole('region', { name: /quote summary/i })).toHaveTextContent('0.3000')
    expect(screen.getByRole('region', { name: /quote summary/i })).toHaveTextContent('3.0000%')
    fireEvent.click(screen.getByRole('button', { name: 'Raw price data' }))
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
    fireEvent.click(screen.getByRole('tab', { name: 'News & announcements' }))
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

  it('prefers the newest price context row in quote summary', async () => {
    await renderReadyDetailPage()

    const quoteSummary = screen.getByRole('region', { name: /quote summary/i })

    expect(quoteSummary).toHaveTextContent('10.3000')
    expect(quoteSummary).toHaveTextContent('0.3000')
    expect(quoteSummary).toHaveTextContent('3.0000%')
    expect(quoteSummary).not.toHaveTextContent('9.1000')
    expect(quoteSummary).not.toHaveTextContent('-0.1000')
    expect(quoteSummary).not.toHaveTextContent('-1.0000%')
  })

  it('renders a stronger stock identity header with market, code, industry, and status', async () => {
    await renderReadyDetailPage()

    const securitySummary = screen.getByRole('region', { name: /selected security summary/i })

    expect(screen.getByText('SZ:000001')).toBeInTheDocument()
    expect(securitySummary).toHaveTextContent('Banking')
    expect(securitySummary).toHaveTextContent('active')
  })

  it('paginates announcements and news with 10 newest items per page', async () => {
    await renderReadyDetailPage(paginatedDetailData)
    fireEvent.click(screen.getByRole('tab', { name: 'News & announcements' }))

    expect(screen.getByRole('navigation', { name: 'Announcements pagination' })).toBeInTheDocument()
    expect(screen.getByRole('navigation', { name: 'News pagination' })).toBeInTheDocument()
    expect(screen.getAllByText('Page 1 of 2')).toHaveLength(2)

    expect(screen.getByRole('link', { name: 'Announcement 12' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Announcement 3' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Announcement 2' })).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'News 12' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'News 3' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'News 2' })).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('navigation', { name: 'Announcements pagination' }).querySelector('button:last-of-type')!)
    fireEvent.click(screen.getByRole('navigation', { name: 'News pagination' }).querySelector('button:last-of-type')!)

    expect(screen.getAllByText('Page 2 of 2')).toHaveLength(2)
    expect(screen.getByRole('link', { name: 'Announcement 2' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Announcement 1' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Announcement 12' })).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'News 2' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'News 1' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'News 12' })).not.toBeInTheDocument()
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
    expect(screen.getByText('Syncing latest information…')).toBeInTheDocument()

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
    fireEvent.click(screen.getByRole('tab', { name: 'News & announcements' }))
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

  it('shows backend AI error details when stock advice generation fails', async () => {
    generateStockAdviceMock.mockRejectedValue(new Error('AI provider request failed: The read operation timed out'))

    render(
      <StockDetailPage
        detail={detailData}
        viewState="ready"
        onBack={vi.fn()}
      />,
    )
    openHoldingsGroup()

    fireEvent.click(screen.getByRole('button', { name: 'Generate fresh stock advice' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'AI provider request failed: The read operation timed out',
    )
  })

  it('requests fresh stock advice when the user asks for a live refresh', async () => {
    fetchInvestmentAdviceHistoryMock
      .mockResolvedValueOnce({ items: [] })
      .mockResolvedValueOnce({ items: [freshStockAdviceData] })
    generateStockAdviceMock.mockResolvedValue(freshStockAdviceData)

    render(
      <StockDetailPage
        detail={detailData}
        viewState="ready"
        onBack={vi.fn()}
      />,
    )
    openHoldingsGroup()

    fireEvent.click(screen.getByRole('button', { name: 'Generate fresh stock advice' }))

    await waitFor(() => {
      expect(generateStockAdviceMock).toHaveBeenCalledWith(7, false)
    })
    expect(await screen.findByText('AI advice generated.')).toBeInTheDocument()
    expect(screen.getByText('Fresh')).toBeInTheDocument()
    expect(screen.getByText('Fresh stock advice generated from the live provider.')).toBeInTheDocument()
  })

  it('loads holdings and renders cached AI advice for the current stock', async () => {
    fetchHoldingsMock.mockResolvedValue([holdingData])
    fetchInvestmentAdviceHistoryMock.mockResolvedValue({ items: [adviceData] })

    render(
      <StockDetailPage
        detail={detailData}
        viewState="ready"
        onBack={vi.fn()}
      />,
    )
    openHoldingsGroup()

    expect(await screen.findByText('80.0000')).toBeInTheDocument()
    await waitFor(() => {
      expect(screen.getByDisplayValue('80.0000')).toBeInTheDocument()
    })
    expect(screen.getByText('Position can be added on pullbacks.')).toBeInTheDocument()
    expect(screen.getByText('Detailed view.')).toBeInTheDocument()
    expect(screen.getByText('Cached')).toBeInTheDocument()
    expect(screen.getByText('Average cost is below spot')).toBeInTheDocument()
  })

  it('shows loaded holdings when advice history fails and confines the error to the advice panel', async () => {
    fetchHoldingsMock.mockResolvedValue([holdingData])
    fetchInvestmentAdviceHistoryMock.mockRejectedValue(new Error('Advice history unavailable'))

    await renderReadyDetailPage()
    expect(screen.getByRole('region', { name: 'Quote summary' })).toHaveTextContent('10.3000')
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    openHoldingsGroup()

    expect(await screen.findByDisplayValue('80.0000')).toBeInTheDocument()
    const holdingPanel = within(screen.getByRole('region', { name: 'Holdings section' }))
    const advicePanel = within(screen.getByRole('region', { name: 'AI advice section' }))
    expect(holdingPanel.queryByRole('alert')).not.toBeInTheDocument()
    expect(advicePanel.getByRole('alert')).toHaveTextContent('Advice history unavailable')
    expect(screen.getByRole('button', { name: 'Update holding' })).toBeEnabled()
  })

  it('shows cached advice when holdings fail and confines the error to the holdings panel', async () => {
    fetchHoldingsMock.mockRejectedValue(new Error('Holdings unavailable'))
    fetchInvestmentAdviceHistoryMock.mockResolvedValue({ items: [adviceData] })

    await renderReadyDetailPage()
    openHoldingsGroup()

    expect(await screen.findByText('Position can be added on pullbacks.')).toBeInTheDocument()
    const holdingPanel = within(screen.getByRole('region', { name: 'Holdings section' }))
    const advicePanel = within(screen.getByRole('region', { name: 'AI advice section' }))
    expect(holdingPanel.getByRole('alert')).toHaveTextContent('Holdings unavailable')
    expect(advicePanel.queryByRole('alert')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Load cached holding advice' })).toBeDisabled()
  })

  it('shows holdings without waiting for a pending advice history request', async () => {
    fetchHoldingsMock.mockResolvedValue([holdingData])
    fetchInvestmentAdviceHistoryMock.mockReturnValue(new Promise(() => {}))

    await renderReadyDetailPage()
    openHoldingsGroup()

    expect(await screen.findByDisplayValue('80.0000')).toBeInTheDocument()
    expect(screen.queryByText('Loading holdings…')).not.toBeInTheDocument()
    expect(screen.getByText('Loading advice history…')).toBeInTheDocument()
  })

  it('shows cached advice without waiting for a pending holdings request', async () => {
    fetchHoldingsMock.mockReturnValue(new Promise(() => {}))
    fetchInvestmentAdviceHistoryMock.mockResolvedValue({ items: [adviceData] })

    await renderReadyDetailPage()
    openHoldingsGroup()

    expect(await screen.findByText('Position can be added on pullbacks.')).toBeInTheDocument()
    expect(screen.getByText('Loading holdings…')).toBeInTheDocument()
    expect(screen.queryByText('Loading advice history…')).not.toBeInTheDocument()
  })

  it('saves a new holding and refreshes the holding summary', async () => {
    fetchHoldingsMock
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([holdingData])
    upsertHoldingMock.mockResolvedValue(holdingData)

    render(
      <StockDetailPage
        detail={detailData}
        viewState="ready"
        onBack={vi.fn()}
      />,
    )
    openHoldingsGroup()

    fireEvent.change(screen.getByLabelText('Quantity'), {
      target: { value: '80.0000' },
    })
    fireEvent.change(screen.getByLabelText('Average cost'), {
      target: { value: '10.0000' },
    })
    fireEvent.change(screen.getByLabelText('Notes'), {
      target: { value: 'Base position' },
    })
    fireEvent.change(screen.getByLabelText('Target horizon'), {
      target: { value: 'long_term' },
    })

    fireEvent.click(screen.getByRole('button', { name: 'Save holding' }))

    await waitFor(() => {
      expect(upsertHoldingMock).toHaveBeenCalledWith({
        security_id: 7,
        quantity: '80.0000',
        average_cost: '10.0000',
        notes: 'Base position',
        target_horizon: 'long_term',
      })
    })
    expect(await screen.findByText('Holding saved.')).toBeInTheDocument()
    expect(screen.getByText('80.0000')).toBeInTheDocument()
  })

  it.each([
    ['en', false, 'quantity', '-1'],
    ['zh', true, 'quantity', '0'],
    ['zh', false, 'quantity', 'Infinity'],
    ['en', true, 'quantity', 'not-a-number'],
    ['en', false, 'averageCost', '-0.1'],
    ['zh', true, 'averageCost', '0'],
    ['zh', false, 'averageCost', 'NaN'],
    ['en', true, 'averageCost', '0x10'],
  ] as const)('validates %s holding inputs before saving (existing=%s, %s=%s)', async (language, existing, field, invalidValue) => {
    fetchHoldingsMock.mockResolvedValue(existing ? [holdingData] : [])
    render(<I18nProvider language={language}><StockDetailPage detail={detailData} viewState="ready" onBack={vi.fn()} /></I18nProvider>)
    openHoldingsGroup()
    await waitFor(() => { expect(screen.queryByText(/Loading holdings|正在加载持仓/)).not.toBeInTheDocument() })
    fireEvent.change(screen.getByLabelText(language === 'en' ? 'Quantity' : '持仓数量'), {
      target: { value: field === 'quantity' ? invalidValue : '1.25' },
    })
    fireEvent.change(screen.getByLabelText(language === 'en' ? 'Average cost' : '持仓成本'), {
      target: { value: field === 'averageCost' ? invalidValue : '2.5000' },
    })
    fireEvent.click(screen.getByRole('button', { name: language === 'en'
      ? existing ? 'Update holding' : 'Save holding'
      : existing ? '更新持仓' : '保存持仓' }))
    const expected = language === 'en'
      ? field === 'quantity' ? 'Quantity must be a finite number greater than 0.' : 'Average cost must be a finite number greater than 0.'
      : field === 'quantity' ? '持仓数量必须是大于 0 的有限数值。' : '平均成本必须是大于 0 的有限数值。'
    expect(await screen.findByRole('alert')).toHaveTextContent(expected)
    expect(upsertHoldingMock).not.toHaveBeenCalled()
    expect(updateHoldingMock).not.toHaveBeenCalled()
  })

  it('preserves positive decimal strings when saving a holding', async () => {
    upsertHoldingMock.mockResolvedValue(holdingData)
    await renderReadyDetailPage()
    openHoldingsGroup()
    fireEvent.change(screen.getByLabelText('Quantity'), { target: { value: '0.2500' } })
    fireEvent.change(screen.getByLabelText('Average cost'), { target: { value: '2.5000' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save holding' }))
    await waitFor(() => { expect(upsertHoldingMock).toHaveBeenCalledWith(expect.objectContaining({
      quantity: '0.2500', average_cost: '2.5000',
    })) })
  })

  it.each(['stock', 'holding'] as const)('replays matching cached %s advice from history without generating', async (target) => {
    fetchHoldingsMock.mockResolvedValue([holdingData])
    const matching = target === 'holding' ? adviceData : freshStockAdviceData
    const otherStock = { ...freshStockAdviceData, security_id: 99, target_id: 99, summary: 'Other stock' }
    const formerHolding = { ...adviceData, holding_id: 42, target_id: 42, summary: 'Former holding' }
    fetchInvestmentAdviceHistoryMock.mockResolvedValueOnce({ items: [] })
      .mockResolvedValueOnce({ items: [otherStock, formerHolding, matching] })
    await renderReadyDetailPage()
    openHoldingsGroup()
    await screen.findByDisplayValue('80.0000')
    fireEvent.click(screen.getByRole('button', { name: `Load cached ${target} advice` }))
    expect(await screen.findByText('Loaded cached AI advice.')).toBeInTheDocument()
    expect(screen.getByText(matching.summary)).toBeInTheDocument()
    expect(screen.getByText('Cached')).toBeInTheDocument()
    expect(screen.queryByText('Other stock')).not.toBeInTheDocument()
    expect(screen.queryByText('Former holding')).not.toBeInTheDocument()
    expect(fetchInvestmentAdviceHistoryMock).toHaveBeenCalledTimes(2)
    expect(generateStockAdviceMock).not.toHaveBeenCalled()
    expect(generateHoldingAdviceMock).not.toHaveBeenCalled()
  })

  it.each(['stock', 'holding'] as const)('reports missing cached %s advice without generating or replaying unrelated history', async (target) => {
    fetchHoldingsMock.mockResolvedValue([holdingData])
    fetchInvestmentAdviceHistoryMock.mockResolvedValueOnce({ items: [] }).mockResolvedValueOnce({ items: [
      { ...freshStockAdviceData, security_id: 99, target_id: 99 },
      { ...adviceData, holding_id: 42, target_id: 42 },
    ] })
    await renderReadyDetailPage()
    openHoldingsGroup()
    await screen.findByDisplayValue('80.0000')
    fireEvent.click(screen.getByRole('button', { name: `Load cached ${target} advice` }))
    expect(await screen.findByText('No cached advice is available for this selection.')).toBeInTheDocument()
    expect(screen.queryByText('Position can be added on pullbacks.')).not.toBeInTheDocument()
    expect(generateStockAdviceMock).not.toHaveBeenCalled()
    expect(generateHoldingAdviceMock).not.toHaveBeenCalled()
  })

  it('reports missing cached advice in Chinese without generating', async () => {
    render(<I18nProvider language="zh"><StockDetailPage detail={detailData} viewState="ready" onBack={vi.fn()} /></I18nProvider>)
    openHoldingsGroup()
    await waitFor(() => { expect(screen.queryByText('正在加载建议历史…')).not.toBeInTheDocument() })
    fireEvent.click(screen.getByRole('button', { name: '加载缓存股票建议' }))
    expect(await screen.findByText('当前选择暂无缓存建议。')).toBeInTheDocument()
    expect(generateStockAdviceMock).not.toHaveBeenCalled()
    expect(generateHoldingAdviceMock).not.toHaveBeenCalled()
  })

  it.each([
    ['cached', 'empty'], ['cached', 'other target'], ['cached', 'error'],
    ['fresh', 'empty'], ['fresh', 'other target'], ['fresh', 'error'],
  ] as const)('keeps explicit %s advice when the initial history request later returns %s', async (mode, initialOutcome) => {
    let resolveInitial!: (value: Awaited<ReturnType<typeof fetchInvestmentAdviceHistory>>) => void
    let rejectInitial!: (reason: Error) => void
    const initialHistory = new Promise<Awaited<ReturnType<typeof fetchInvestmentAdviceHistory>>>((resolve, reject) => {
      resolveInitial = resolve
      rejectInitial = reject
    })
    fetchInvestmentAdviceHistoryMock.mockReturnValueOnce(initialHistory)
      .mockResolvedValue({ items: [freshStockAdviceData] })
    generateStockAdviceMock.mockResolvedValue(freshStockAdviceData)
    await renderReadyDetailPage()
    openHoldingsGroup()

    fireEvent.click(screen.getByRole('button', { name: mode === 'cached'
      ? 'Load cached stock advice' : 'Generate fresh stock advice' }))
    const successMessage = mode === 'cached' ? 'Loaded cached AI advice.' : 'AI advice generated.'
    expect(await screen.findByText(successMessage)).toBeInTheDocument()
    expect(screen.getByText(freshStockAdviceData.summary)).toBeInTheDocument()

    await act(async () => {
      if (initialOutcome === 'error') rejectInitial(new Error('Obsolete initial history failure'))
      else resolveInitial({ items: initialOutcome === 'empty' ? [] : [adviceData] })
    })

    expect(screen.getByText(freshStockAdviceData.summary)).toBeInTheDocument()
    expect(screen.getByText(successMessage)).toBeInTheDocument()
    expect(screen.queryByText(adviceData.summary)).not.toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(screen.queryByText('Loading advice history…')).not.toBeInTheDocument()
  })

  it('generates holding advice and refreshes advice history', async () => {
    fetchHoldingsMock.mockResolvedValue([holdingData])
    fetchInvestmentAdviceHistoryMock
      .mockResolvedValueOnce({ items: [] })
      .mockResolvedValueOnce({ items: [adviceData] })
    generateHoldingAdviceMock.mockResolvedValue(adviceData)

    render(
      <StockDetailPage
        detail={detailData}
        viewState="ready"
        onBack={vi.fn()}
      />,
    )
    openHoldingsGroup()

    expect(await screen.findByText('80.0000')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Generate fresh holding advice' }))

    await waitFor(() => {
      expect(generateHoldingAdviceMock).toHaveBeenCalledWith(1, false)
    })
    expect(await screen.findByText('Loaded cached AI advice.')).toBeInTheDocument()
    expect(screen.getByText('Position can be added on pullbacks.')).toBeInTheDocument()
    expect(screen.getByText('Valuation remains acceptable')).toBeInTheDocument()
  })
})
