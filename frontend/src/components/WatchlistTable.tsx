import { useI18n } from '../i18n'
import type { HomepageAdviceLabel } from '../types/homepageAdvice'
import type { WatchlistItem } from '../types/watchlist'

interface WatchlistTableProps {
  items: WatchlistItem[]
  adviceLabels?: Record<number, HomepageAdviceLabel>
  showAiTags?: boolean
  onOpenDetail: (securityId: number) => void
  onRemove: (securityId: number) => void
}

export function WatchlistTable({ items, adviceLabels = {}, showAiTags = true, onOpenDetail, onRemove }: WatchlistTableProps) {
  const { t } = useI18n()

  function formatChangePercent(value: string | null) {
    return value === null ? t('common.pendingSync') : `${value}%`
  }

  function changeToneClass(value: string | null) {
    if (value === null) {
      return 'watchlist-table__change watchlist-table__change--neutral'
    }

    return Number(value) >= 0
      ? 'watchlist-table__change watchlist-table__change--positive'
      : 'watchlist-table__change watchlist-table__change--negative'
  }

  function formatLastPrice(value: string | null) {
    return value ?? t('common.pendingSync')
  }

  function adviceToneClass(recommendation: HomepageAdviceLabel['recommendation']) {
    if (recommendation === 'buy' || recommendation === 'accumulate') {
      return 'watchlist-table__ai-tag watchlist-table__ai-tag--positive'
    }
    if (recommendation === 'trim' || recommendation === 'sell') {
      return 'watchlist-table__ai-tag watchlist-table__ai-tag--negative'
    }
    return 'watchlist-table__ai-tag watchlist-table__ai-tag--neutral'
  }

  return (
    <div className="watchlist-table-wrap">
      <table className="watchlist-table" aria-label={t('watchlist.tableLabel')}>
        <thead>
          <tr>
            <th scope="col">{t('watchlist.marketCode')}</th>
            <th scope="col">{t('watchlist.name')}</th>
            <th scope="col">{t('watchlist.industry')}</th>
            <th scope="col">{t('watchlist.lastPrice')}</th>
            <th scope="col">{t('watchlist.changePercent')}</th>
            <th scope="col">{t('homepage.aiRecommendation')}</th>
            <th scope="col">{t('watchlist.actions')}</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.security_id}>
              <td>{`${item.market}:${item.code}`}</td>
              <td>{item.name}</td>
              <td>{item.industry ?? t('common.notAvailable')}</td>
              <td>{formatLastPrice(item.last_price)}</td>
              <td className={changeToneClass(item.change_percent)}>{formatChangePercent(item.change_percent)}</td>
              <td>
                {showAiTags ? (
                  adviceLabels[item.security_id]?.recommendation ? (
                    <div className="watchlist-table__ai-stack">
                      <span className={adviceToneClass(adviceLabels[item.security_id].recommendation)}>
                        {t(`detail.recommendation.${adviceLabels[item.security_id].recommendation}`)}
                      </span>
                      {adviceLabels[item.security_id].has_holding_context ? (
                        <small className="watchlist-table__ai-meta">{t('homepage.holdingAware')}</small>
                      ) : null}
                    </div>
                  ) : (
                    <span className="watchlist-table__ai-placeholder">{t('homepage.aiPending')}</span>
                  )
                ) : (
                  <span className="watchlist-table__ai-placeholder">{t('common.notAvailable')}</span>
                )}
              </td>
              <td>
                <div className="watchlist-table__actions">
                  <button type="button" onClick={() => onOpenDetail(item.security_id)}>
                    {t('homepage.viewDetailsFor', { name: item.name })}
                  </button>
                  <button type="button" className="button button--ghost" onClick={() => onRemove(item.security_id)}>
                    {t('watchlist.remove', { name: item.name })}
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
