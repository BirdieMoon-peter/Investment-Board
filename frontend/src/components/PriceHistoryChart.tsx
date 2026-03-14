import type { StockDetailPriceHistoryBar } from '../types/watchlist'

interface PriceHistoryChartProps {
  priceHistory: StockDetailPriceHistoryBar[]
}

export function PriceHistoryChart({ priceHistory }: PriceHistoryChartProps) {
  return (
    <section className="stock-detail-section" aria-label="Price history section">
      <h2>Price history</h2>
      {priceHistory.length === 0 ? (
        <p>No price history is available yet.</p>
      ) : (
        <table className="stock-detail-table" aria-label="Price history">
          <thead>
            <tr>
              <th scope="col">Trade date</th>
              <th scope="col">Open</th>
              <th scope="col">High</th>
              <th scope="col">Low</th>
              <th scope="col">Close</th>
              <th scope="col">Volume</th>
              <th scope="col">Amount</th>
            </tr>
          </thead>
          <tbody>
            {priceHistory.map((bar) => (
              <tr key={bar.trade_date}>
                <td>{bar.trade_date}</td>
                <td>{bar.open_price}</td>
                <td>{bar.high_price}</td>
                <td>{bar.low_price}</td>
                <td>{bar.close_price}</td>
                <td>{bar.volume}</td>
                <td>{bar.amount}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}
