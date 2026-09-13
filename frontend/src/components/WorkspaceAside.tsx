import { Button, Skeleton, SkeletonItem } from '@fluentui/react-components'
import { ArrowUpRight } from '@phosphor-icons/react'
import { useI18n } from '../i18n'
import type { HomepageMacroItem } from '../types/homepage'
import type { WatchlistItem } from '../types/watchlist'
import { StatusMessage } from './StatusMessage'
interface Props {
  showSpotlight: boolean
  showMacro: boolean
  spotlight: WatchlistItem | null
  spotlightLoading?: boolean
  macro: HomepageMacroItem[]
  loading: boolean
  error: string | null
  onOpenDetail: (id: number, originId: string) => void
}
export function WorkspaceAside({
  showSpotlight,
  showMacro,
  spotlight,
  spotlightLoading = false,
  macro,
  loading,
  error,
  onOpenDetail,
}: Props) {
  const { t, formatDateTime } = useI18n()
  return (
    <aside className="workspace-aside">
      {showSpotlight ? (
        <section
          className="workspace-surface"
          aria-label={t('homepage.spotlight')}
        >
          <div className="workspace-section-heading">
            <h2>{t('homepage.boardFocus')}</h2>
            <span className="workspace-muted">{t('homepage.leadMover')}</span>
          </div>
          {spotlightLoading ? (
            <Skeleton className="workspace-spotlight workspace-spotlight--loading"
              aria-label={`${t('homepage.spotlight')} ${t('common.loading')}`}>
              <div className="security-code"><SkeletonItem size={12} style={{ width: '35%' }} /></div>
              <h3><SkeletonItem size={20} style={{ width: '60%' }} /></h3>
              <div className="workspace-muted"><SkeletonItem size={12} style={{ width: '40%' }} /></div>
              <dl>
                {[1, 2].map((id) => <div key={id}>
                  <dt><SkeletonItem size={8} style={{ width: '55%' }} /></dt>
                  <dd><SkeletonItem size={16} style={{ width: '70%' }} /></dd>
                </div>)}
              </dl>
              <SkeletonItem size={32} />
            </Skeleton>
          ) : spotlight ? (
            <div className="workspace-spotlight">
              <span className="security-code">
                {spotlight.market}:{spotlight.code}
              </span>
              <h3>{spotlight.name}</h3>
              <span className="workspace-muted">
                {spotlight.industry ?? t('homepage.industryPending')}
              </span>
              <dl>
                <div>
                  <dt>{t('homepage.lastPrice')}</dt>
                  <dd className="workspace-numeric">
                    {spotlight.last_price ?? t('common.pendingSync')}
                  </dd>
                </div>
                <div>
                  <dt>{t('homepage.change')}</dt>
                  <dd
                    className={`workspace-numeric change-${Number(spotlight.change_percent) > 0 ? 'positive' : Number(spotlight.change_percent) < 0 ? 'negative' : 'neutral'}`}
                  >
                    {spotlight.change_percent === null
                      ? t('common.pendingSync')
                      : `${Number(spotlight.change_percent) > 0 ? '+' : ''}${spotlight.change_percent}%`}
                  </dd>
                </div>
              </dl>
              <Button
                id={`watchlist-spotlight-${spotlight.security_id}`}
                appearance="secondary"
                icon={<ArrowUpRight />}
                onClick={(event) =>
                  onOpenDetail(spotlight.security_id, event.currentTarget.id)
                }
              >
                {t('homepage.viewDetailsFor', { name: spotlight.name })}
              </Button>
            </div>
          ) : (
            <p className="workspace-empty">{t('homepage.addSecurityPrompt')}</p>
          )}
        </section>
      ) : null}
      {showMacro ? (
        <section className="workspace-surface">
          <div className="workspace-section-heading">
            <h2>{t('homepage.macroPulse')}</h2>
          </div>
          {error ? (
            <StatusMessage tone="error" message={error} />
          ) : loading ? (
            <Skeleton className="workspace-macro workspace-macro--loading" aria-label={t('homepage.overviewLoading')}>
              {/* The overview provides CPI, PPI, manufacturing PMI and M2. */}
              {Array.from({ length: macro.length || 4 }, (_, index) => <article key={index}>
                <div className="workspace-muted"><SkeletonItem size={8} style={{ width: '35%' }} /></div>
                <h3><SkeletonItem size={12} style={{ width: '45%' }} /></h3>
                <div className="workspace-macro-value">
                  <SkeletonItem size={20} style={{ width: '30%' }} />
                  <SkeletonItem size={8} style={{ width: '40%' }} />
                </div>
                <p><SkeletonItem size={8} style={{ width: '65%' }} /></p>
                <div className="workspace-macro-time"><SkeletonItem size={8} style={{ width: '55%' }} /></div>
              </article>)}
            </Skeleton>
          ) : macro.length === 0 ? (
            <p className="workspace-empty">{t('homepage.noMacroData')}</p>
          ) : (
            <div className="workspace-macro">
              {macro.map((item) => (
                <article key={item.key}>
                  <span className="workspace-muted">{item.category}</span>
                  <h3>{item.title}</h3>
                  <div className="workspace-macro-value">
                    <strong className="workspace-numeric">
                      {item.value ?? t('common.notAvailable')}
                      {item.unit ?? ''}
                    </strong>
                    <span>{item.change_text ?? t('common.notAvailable')}</span>
                  </div>
                  {item.summary ? <p>{item.summary}</p> : null}
                  <time dateTime={item.published_at ?? undefined}>
                    {formatDateTime(item.published_at)}
                  </time>
                </article>
              ))}
            </div>
          )}
        </section>
      ) : null}
    </aside>
  )
}
