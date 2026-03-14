import type { StockDetailFinancialMetric } from '../types/watchlist'

interface FinancialMetricsPanelProps {
  financialMetrics: StockDetailFinancialMetric[]
}

export function FinancialMetricsPanel({ financialMetrics }: FinancialMetricsPanelProps) {
  return (
    <section className="stock-detail-section" aria-label="Financial metrics section">
      <h2>Financial metrics</h2>
      {financialMetrics.length === 0 ? (
        <p>No financial metrics are available yet.</p>
      ) : (
        <table className="stock-detail-table" aria-label="Financial metrics">
          <thead>
            <tr>
              <th scope="col">Report period</th>
              <th scope="col">Revenue</th>
              <th scope="col">Net profit</th>
              <th scope="col">EPS</th>
              <th scope="col">ROE</th>
              <th scope="col">Debt-to-asset ratio</th>
            </tr>
          </thead>
          <tbody>
            {financialMetrics.map((metric) => (
              <tr key={metric.report_period}>
                <td>{metric.report_period}</td>
                <td>{metric.revenue ?? '—'}</td>
                <td>{metric.net_profit ?? '—'}</td>
                <td>{metric.eps ?? '—'}</td>
                <td>{metric.roe ?? '—'}</td>
                <td>{metric.debt_to_asset_ratio ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}
