import { useI18n } from '../i18n'
import type { StockDetailPageSecurity } from '../types/watchlist'

interface StockHeaderProps {
  security: StockDetailPageSecurity
}

export function StockHeader({ security }: StockHeaderProps) {
  const { t } = useI18n()

  return (
    <section className="stock-detail-section" aria-label={t('detail.selectedSecuritySummary')}>
      <h2>{security.name}</h2>
      <div className="stock-detail-meta" aria-label={t('detail.stockIdentityAndStatus')}>
        <span>{`${security.market}:${security.code}`}</span>
        <span>{t(`security.${security.status}`)}</span>
      </div>
      {security.industry ? <p className="stock-detail-subtle">{security.industry}</p> : null}
    </section>
  )
}
