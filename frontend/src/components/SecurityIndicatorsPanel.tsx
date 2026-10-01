import {useCallback} from 'react'
import {Button} from '@fluentui/react-components'
import {fetchSecurityIndicators} from '../api/indicators'
import {useI18n} from '../i18n'
import {IndicatorResults} from './IndicatorResults'
import {useSavedIndicators} from './useSavedIndicators'
export function SecurityIndicatorsPanel({securityId, revision}: {securityId:number; revision:unknown}) {
  const {t} = useI18n(), load = useCallback((signal:AbortSignal) => fetchSecurityIndicators(securityId,signal),[securityId])
  const state = useSavedIndicators(securityId, revision, load)
  const groups = [
    ['price', (k:string) => /^(price_|ma_|max_drawdown|annualized_volatility|volume_)/.test(k)],
    ['financial', (k:string) => /^(revenue_|parent_|roe|debt_)/.test(k)],
    ['fund', (k:string) => /^(fund_|total_return|benchmark_|tracking_)/.test(k)],
  ] as const
  return <section className="stock-detail-section" aria-label={t('indicators.security')}><h2>{t('indicators.security')}</h2>
    <p className="stock-detail-subtle">{t('indicators.priceLimits')}</p>
    {state.loading && <p role="status">{t('indicators.loading')}</p>}
    {state.error && <div role="alert">{t('indicators.error')} <Button onClick={state.retry}>{t('dataCenter.retry')}</Button></div>}
    {state.data && <><p>{t('indicators.eligibility')}: {t(`dataCenter.${state.data.instrument_type}`)}</p>{groups.map(([name,test]) => <section key={name}><h3>{t(`indicators.${name}`)}</h3><IndicatorResults metrics={state.data!.metrics.filter(m => test(m.key))}/></section>)}
      <details><summary>{t('indicators.context')}</summary><dl className="indicator-provenance"><div><dt>{t('dataCenter.benchmark')}</dt><dd>{String(state.data.data_context.benchmark_code ?? t('indicators.unavailable'))}</dd></div><div><dt>{t('indicators.window')}</dt><dd>{String(state.data.data_context.price_observation_limit ?? t('indicators.unavailable'))} {t('indicators.observations')} · {String(state.data.data_context.financial_observation_limit ?? t('indicators.unavailable'))} {t('indicators.reports')}</dd></div></dl></details></>}
  </section>
}
