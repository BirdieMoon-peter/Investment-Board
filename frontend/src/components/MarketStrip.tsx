import { Skeleton, SkeletonItem } from '@fluentui/react-components'
import { useI18n } from '../i18n'
import type { HomepageMarketIndex } from '../types/homepage'
import { StatusMessage } from './StatusMessage'
export function MarketStrip({
  indexes,
  loading,
  error,
}: {
  indexes: HomepageMarketIndex[]
  loading: boolean
  error: string | null
}) {
  const { t, formatDateTime } = useI18n()
  const signed = (value: string | null, suffix = '') =>
    value === null
      ? t('common.notAvailable')
      : `${Number(value) > 0 ? '+' : ''}${value}${suffix}`
  return (
    <section className="market-strip" aria-label={t('homepage.marketIndexes')}>
      {error ? (
        <StatusMessage tone="error" message={error} />
      ) : loading ? (
        <Skeleton
          aria-label={t('homepage.overviewLoading')}
          className="market-strip-skeleton"
        >
          {[1, 2, 3, 4].map((id) => (
            <SkeletonItem key={id} size={48} />
          ))}
        </Skeleton>
      ) : indexes.length === 0 ? (
        <p className="workspace-muted">{t('homepage.noIndexData')}</p>
      ) : (
        indexes.map((item) => (
          <article className="market-strip-item" key={item.key}>
            <div>
              <span>{item.name}</span>
              <small>{item.market}</small>
            </div>
            <div>
              <strong className="workspace-numeric">
                {item.last_value ?? t('common.notAvailable')}
              </strong>
              <span
                className={`workspace-numeric change-${Number(item.change_percent) > 0 ? 'positive' : Number(item.change_percent) < 0 ? 'negative' : 'neutral'}`}
                title={signed(item.change_amount)}
              >
                {signed(item.change_percent, '%')}
              </span>
            </div>
            <time dateTime={item.snapshot_time ?? undefined}>
              {formatDateTime(item.snapshot_time)}
            </time>
          </article>
        ))
      )}
    </section>
  )
}
