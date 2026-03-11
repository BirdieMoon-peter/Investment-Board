import type { StockDetailPriceBar } from '../types/watchlist'

interface PriceContextPanelProps {
  priceContext: StockDetailPriceBar[]
}

export function PriceContextPanel({ priceContext }: PriceContextPanelProps) {
  return (
    <section className="stock-detail-section" aria-label="Price context section">
      <h2>Price context</h2>
      {priceContext.length === 0 ? (
        <p>No price context is available yet.</p>
      ) : (
        <table className="stock-detail-table" aria-label="Recent price context">
          <thead>
            <tr>
              <th scope="col">Trade date</th>
              <th scope="col">Open</th>
              <th scope="col">High</th>
              <th scope="col">Low</th>
              <th scope="col">Close</th>
              <th scope="col">Volume</th>
            </tr>
          </thead>
          <tbody>
            {priceContext.map((bar) => (
              <tr key={bar.trade_date}>
                <td>{bar.trade_date}</td>
                <td>{bar.open_price}</td>
                <td>{bar.high_price}</td>
                <td>{bar.low_price}</td>
                <td>{bar.close_price}</td>
                <td>{bar.volume}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}
