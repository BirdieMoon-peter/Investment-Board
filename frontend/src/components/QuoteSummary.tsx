import type { StockDetailPriceBar } from '../types/watchlist'

interface QuoteSummaryProps {
  latestBar: StockDetailPriceBar | null
}

export function QuoteSummary({ latestBar }: QuoteSummaryProps) {
  if (!latestBar) {
    return <p>No quote summary is available yet.</p>
  }

  return (
    <section className="stock-detail-section" aria-label="Quote summary">
      <h2>Quote summary</h2>
      <dl className="stock-detail-grid">
        <div>
          <dt>Close</dt>
          <dd>{latestBar.close_price}</dd>
        </div>
        <div>
          <dt>Open</dt>
          <dd>{latestBar.open_price}</dd>
        </div>
        <div>
          <dt>High</dt>
          <dd>{latestBar.high_price}</dd>
        </div>
        <div>
          <dt>Low</dt>
          <dd>{latestBar.low_price}</dd>
        </div>
        <div>
          <dt>Volume</dt>
          <dd>{latestBar.volume}</dd>
        </div>
        <div>
          <dt>Trade date</dt>
          <dd>{latestBar.trade_date}</dd>
        </div>
      </dl>
    </section>
  )
}
