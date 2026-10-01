import {Button} from '@fluentui/react-components'
import {fetchHoldingsIndicators} from '../api/indicators'
import {useI18n} from '../i18n'
import {IndicatorResults} from './IndicatorResults'
import {useSavedIndicators} from './useSavedIndicators'
export function HoldingsIndicatorsPanel({securityId, revision, names = {}}: {securityId:number; revision:unknown; names?:Record<number,string>}) {
  const {t} = useI18n(), state = useSavedIndicators(securityId,revision,fetchHoldingsIndicators)
  return <section className="stock-detail-section" aria-label={t('indicators.holdings')}><h2>{t('indicators.holdings')}</h2><p>{t('indicators.denominator')}</p><p className="stock-detail-subtle">{t('indicators.positionLimits')}</p>
    {state.loading && <p role="status">{t('indicators.loading')}</p>}
    {state.error && <div role="alert">{t('indicators.error')} <Button onClick={state.retry}>{t('dataCenter.retry')}</Button></div>}
    {state.data && <><p>{t(state.data.valuation_complete ? 'indicators.complete' : 'indicators.partial')}</p>
      {state.data.missing_price_security_ids.length > 0 && <p>{t('indicators.missingPositions')}: {state.data.missing_price_security_ids.map(id => names[id] ?? `#${id}`).join(', ')}</p>}
      <IndicatorResults metrics={state.data.metrics}/>
      {state.data.positions.map(p => <section key={p.holding_id}><h3>{names[p.security_id] ?? `#${p.security_id}`} · {t('indicators.position')} #{p.holding_id}</h3><p>{t('detail.holdingQuantity')}: {p.quantity} · {t('detail.holdingAverageCost')}: {p.average_cost}</p><IndicatorResults metrics={p.metrics}/></section>)}
      {state.data.positions.length === 0 && <p>{t('indicators.noPositions')}</p>}
      {state.data.warnings.length > 0 && <p className="stock-detail-subtle">{state.data.warnings.map(w => t(`indicators.warning.${w}`) === `indicators.warning.${w}` ? w.replace(/_/g,' ') : t(`indicators.warning.${w}`)).join('; ')}</p>}
    </>}
  </section>
}
