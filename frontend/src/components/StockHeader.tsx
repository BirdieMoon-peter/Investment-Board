import { useI18n } from '../i18n'
import type { StockDetailPageSecurity, StockDetailPriceBar } from '../types/watchlist'

interface StockHeaderProps {
  security: StockDetailPageSecurity
  latestBar?: StockDetailPriceBar | null
}

// Add a sign without converting away source decimal precision.
export function signedQuote(value: string): string {
  return Number(value) > 0 && !value.startsWith('+') ? `+${value}` : value
}

export function StockHeader({ security, latestBar }: StockHeaderProps) {
  const { t, formatDateTime } = useI18n()
  return (
    <section className="detail-security-header" aria-label={t('detail.selectedSecuritySummary')}>
      <div>
        <h1>{security.name}</h1>
        <div className="detail-security-meta" aria-label={t('detail.stockIdentityAndStatus')}>
          <span className="workspace-numeric">{`${security.market}:${security.code}`}</span>
          {security.industry ? <span>{security.industry}</span> : null}
          <span>{t(`security.${security.status}`)}</span>
        </div>
      </div>
      {latestBar ? (
        <div className="detail-header-quote">
          <div className="detail-header-quote__values">
            <strong>{latestBar.last_price}</strong>
            <span className={Number(latestBar.change_percent) >= 0 ? 'quote-positive' : 'quote-negative'}>
              {signedQuote(latestBar.change_amount)} ({signedQuote(latestBar.change_percent)}%)
            </span>
          </div>
          <time dateTime={latestBar.snapshot_time}>{formatDateTime(latestBar.snapshot_time)}</time>
        </div>
      ) : null}
    </section>
  )
}
