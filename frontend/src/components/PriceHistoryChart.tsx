import { useEffect, useMemo, useState } from 'react'

import { useI18n } from '../i18n'
import type { StockDetailPriceHistoryBar } from '../types/watchlist'
import { CandlestickChart } from './CandlestickChart'

const PAGE_SIZE = 10

interface PriceHistoryChartProps {
  priceHistory: StockDetailPriceHistoryBar[]
}

export function PriceHistoryChart({ priceHistory }: PriceHistoryChartProps) {
  const { t } = useI18n()
  const [page, setPage] = useState(1)

  useEffect(() => {
    setPage(1)
  }, [priceHistory])

  const totalPages = Math.ceil(priceHistory.length / PAGE_SIZE)
  const pagedHistory = useMemo(() => {
    const start = (page - 1) * PAGE_SIZE
    return priceHistory.slice(start, start + PAGE_SIZE)
  }, [page, priceHistory])

  return (
    <section className="stock-detail-section" aria-label={t('detail.priceHistorySection')}>
      <h2>{t('detail.priceHistory')}</h2>
      {priceHistory.length === 0 ? (
        <p>{t('detail.noPriceHistory')}</p>
      ) : (
        <>
          <CandlestickChart bars={priceHistory} />
          <div className="stock-detail-table-wrap">
            <table className="stock-detail-table" aria-label={t('detail.priceHistory')}>
              <thead>
                <tr>
                  <th scope="col">{t('detail.tradeDate')}</th>
                  <th scope="col">{t('detail.open')}</th>
                  <th scope="col">{t('detail.high')}</th>
                  <th scope="col">{t('detail.low')}</th>
                  <th scope="col">{t('detail.close')}</th>
                  <th scope="col">{t('detail.volume')}</th>
                  <th scope="col">{t('detail.amount')}</th>
                </tr>
              </thead>
              <tbody>
                {pagedHistory.map((bar) => (
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
          </div>
          {totalPages > 1 ? (
            <nav aria-label="Price history pagination">
              <button type="button" onClick={() => setPage((current) => current - 1)} disabled={page === 1}>
                {t('common.previous')}
              </button>
              <span>{t('common.pageOf', { page, total: totalPages })}</span>
              <button
                type="button"
                onClick={() => setPage((current) => current + 1)}
                disabled={page === totalPages}
              >
                {t('common.next')}
              </button>
            </nav>
          ) : null}
        </>
      )}
    </section>
  )
}
