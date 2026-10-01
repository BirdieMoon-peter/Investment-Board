import { signedQuote } from './StockHeader'
import { useI18n } from '../i18n'
import type { StockDetailPriceBar } from '../types/watchlist'

interface QuoteSummaryProps {
  indexContext?: boolean
  latestBar: StockDetailPriceBar | null
}

export function QuoteSummary({ latestBar, indexContext = false }: QuoteSummaryProps) {
  const { t, formatDateTime } = useI18n()

  return (
    <section className="stock-detail-section" aria-label={t('detail.quoteSummary')}>
      <h2>{t('detail.quoteSummary')}</h2>
      {latestBar ? (
        <dl className="stock-detail-grid">
          <div>
            <dt>{indexContext ? t('dataCenter.indexValue') : t('detail.lastPrice')}</dt>
            <dd>{latestBar.last_price}</dd>
          </div>
          <div>
            <dt>{indexContext ? t('dataCenter.indexChange') : t('detail.changeAmount')}</dt>
            <dd className={Number(latestBar.change_amount) >= 0 ? 'quote-positive' : 'quote-negative'}>{signedQuote(latestBar.change_amount)}</dd>
          </div>
          <div>
            <dt>{t('detail.changePercent')}</dt>
            <dd className={Number(latestBar.change_percent) >= 0 ? 'quote-positive' : 'quote-negative'}>{signedQuote(latestBar.change_percent)}%</dd>
          </div>
          <div>
            <dt>{t('detail.snapshotTime')}</dt>
            <dd>{formatDateTime(latestBar.snapshot_time)}</dd>
          </div>
        </dl>
      ) : (
        <p>{t('detail.noQuoteSummary')}</p>
      )}
    </section>
  )
}
