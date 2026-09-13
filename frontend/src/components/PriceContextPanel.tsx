import { useI18n } from '../i18n'
import type { StockDetailPriceBar } from '../types/watchlist'

interface PriceContextPanelProps {
  priceContext: StockDetailPriceBar[]
}

export function PriceContextPanel({ priceContext }: PriceContextPanelProps) {
  const { t, formatDateTime } = useI18n()

  return (
    <section className="stock-detail-section" aria-label={t('detail.priceContextSection')}>
      <h2>{t('detail.priceContext')}</h2>
      {priceContext.length === 0 ? (
        <p>{t('detail.noPriceContext')}</p>
      ) : (
        <div className="stock-detail-table-wrap">
          <table className="stock-detail-table" aria-label={t('detail.recentPriceContext')}>
            <thead>
              <tr>
                <th scope="col">{t('detail.snapshotTime')}</th>
                <th scope="col">{t('detail.lastPrice')}</th>
                <th scope="col">{t('detail.changeAmount')}</th>
                <th scope="col">{t('detail.changePercent')}</th>
              </tr>
            </thead>
            <tbody>
              {priceContext.map((snapshot, index) => (
                <tr key={`${snapshot.snapshot_time}-${index}`}>
                  <td>{formatDateTime(snapshot.snapshot_time)}</td>
                  <td>{snapshot.last_price}</td>
                  <td>{snapshot.change_amount}</td>
                  <td>{snapshot.change_percent}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
