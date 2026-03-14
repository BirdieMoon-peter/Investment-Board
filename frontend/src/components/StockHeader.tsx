import type { StockDetailPageSecurity } from '../types/watchlist'

interface StockHeaderProps {
  security: StockDetailPageSecurity
}

export function StockHeader({ security }: StockHeaderProps) {
  return (
    <section className="stock-detail-section" aria-label="Selected security summary">
      <h2>{security.name}</h2>
      <div className="stock-detail-meta" aria-label="Stock identity and status">
        <span>{`${security.market}:${security.code}`}</span>
        <span>{security.status}</span>
      </div>
      {security.industry ? <p className="stock-detail-subtle">{security.industry}</p> : null}
    </section>
  )
}
