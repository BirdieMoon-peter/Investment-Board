import { useEffect, useState } from 'react'
import { Button, useRestoreFocusTarget } from '@fluentui/react-components'
import { fetchSecurityData } from '../api/dataCenter'
import type { SecurityData } from '../types/dataCenter'
import { useDataCenterFormat } from './dataCenterFormatting'
export function SecurityDataStatus({
  securityId,
  revision = 0,
  onOpen,
  onData,
}: {
  securityId: number
  revision?: number
  onOpen: (origin: HTMLElement) => void
  onData?: (data: SecurityData) => void
}) {
  const { t, date, label } = useDataCenterFormat(),
    restore = useRestoreFocusTarget()
  const [data, setData] = useState<SecurityData | null>(null),
    [error, setError] = useState(false),
    [loading, setLoading] = useState(true),
    [retry, setRetry] = useState(0)
  useEffect(() => {
    const c = new AbortController()
    setData(null)
    setError(false)
    setLoading(true)
    fetchSecurityData(securityId, c.signal)
      .then((d) => {
        if (!c.signal.aborted) {
          setData(d)
          onData?.(d)
        }
      })
      .catch(() => {
        if (!c.signal.aborted) setError(true)
      })
      .finally(() => {
        if (!c.signal.aborted) setLoading(false)
      })
    return () => c.abort()
  }, [securityId, revision, retry, onData])
  const price = data?.categories.price_history
  return (
    <section className="security-data-status" aria-label={t('dataCenter.status')}>
      <div>
        <h2>{t('dataCenter.status')}</h2>
        {loading ? (
          <p role="status">{t('dataCenter.loading')}</p>
        ) : error ? (
          <p role="alert">{t('dataCenter.error')}</p>
        ) : price ? (
          <p>
            {label(price.health)} · {price.source_key ?? t('dataCenter.unknown')} ·{' '}
            {t('dataCenter.fetched')}:{' '}
            {price.fetched_at ? date(price.fetched_at) : t('dataCenter.missing')} ·{' '}
            {label(price.unit ?? 'unknown')}
          </p>
        ) : null}
      </div>
      <div className="data-center-actions">
        {error ? (
          <Button onClick={() => setRetry((v) => v + 1)}>{t('dataCenter.retry')}</Button>
        ) : null}
        <Button {...restore} onClick={(event) => onOpen(event.currentTarget)}>
          {t('dataCenter.open')}
        </Button>
      </div>
    </section>
  )
}
