import { useI18n } from '../i18n'
import type { StockDetailFinancialMetric } from '../types/watchlist'

interface FinancialMetricsPanelProps {
  financialMetrics: StockDetailFinancialMetric[]
}

export function FinancialMetricsPanel({ financialMetrics }: FinancialMetricsPanelProps) {
  const { t } = useI18n()

  return (
    <section className="stock-detail-section" aria-label={t('detail.financialMetricsSection')}>
      <h2>{t('detail.financialMetrics')}</h2>
      {financialMetrics.length === 0 ? (
        <p>{t('detail.noFinancialMetrics')}</p>
      ) : (
        <div className="stock-detail-table-wrap" tabIndex={0} role="region" aria-label={t('detail.financialMetrics')}>
          <table className="stock-detail-table" aria-label={t('detail.financialMetrics')}>
            <thead>
              <tr>
                <th scope="col">{t('detail.reportPeriod')}</th>
                <th scope="col">{t('detail.revenue')}</th>
                <th scope="col">{t('detail.netProfit')}</th>
                <th scope="col">{t('detail.eps')}</th>
                <th scope="col">{t('detail.roe')}</th>
                <th scope="col">{t('detail.debtToAssetRatio')}</th>
              </tr>
            </thead>
            <tbody>
              {financialMetrics.map((metric) => (
                <tr key={metric.report_period}>
                  <td>{metric.report_period}</td>
                  <td>{metric.revenue ?? t('common.notAvailable')}</td>
                  <td>{metric.net_profit ?? t('common.notAvailable')}</td>
                  <td>{metric.eps ?? t('common.notAvailable')}</td>
                  <td>{metric.roe ?? t('common.notAvailable')}</td>
                  <td>{metric.debt_to_asset_ratio ?? t('common.notAvailable')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
