import { useI18n } from '../i18n'
import { useDataCenterFormat } from './dataCenterFormatting'
import { feePercentage } from '../api/dataCenter'
import type { IndicatorResult } from '../types/indicators'
export function formatIndicatorValue(value: string | null, unit: string, missing = 'Unavailable', points = 'points') {
  if (value === null) return missing
  if (unit === 'fraction') return feePercentage(value)
  if (unit === 'percentage_value') return `${value}%`
  if (unit === 'ratio') return `${value}×`
  if (unit === 'dimensionless') return value
  return `${value} ${unit === 'index_points' ? points : unit}`
}
export function IndicatorResults({ metrics }: { metrics: IndicatorResult[] }) {
  const {t, language} = useI18n()
  const {label} = useDataCenterFormat()
  const windowLabel = (value: string) => {
    const match = /^last_(\d+)_observations$/.exec(value)
    return match ? `${match[1]} ${t('indicators.observations')}` : t(`indicators.window.${value}`) === `indicators.window.${value}` ? value.replace(/_/g, ' ') : t(`indicators.window.${value}`)
  }
  return <div className="indicator-results">{metrics.map(m => <article key={m.key} className="indicator-result">
    <div className="indicator-result__heading"><h3>{language === 'zh' ? m.label : t(`indicators.key.${m.key}`) === `indicators.key.${m.key}` ? m.key.replace(/_/g, ' ') : t(`indicators.key.${m.key}`)}</h3>
      <strong>{formatIndicatorValue(m.value, m.unit, t('indicators.unavailable'), t('indicators.points'))}</strong></div>
    <p className="stock-detail-subtle">{t(`indicators.${m.status}`)} · {t('indicators.asOf')}: {m.as_of ?? t('indicators.unavailable')}</p>
    <details><summary>{t('indicators.calculation')}</summary><dl className="indicator-provenance">
      <div><dt>{t('indicators.formula')}</dt><dd>{m.formula}</dd></div>
      <div><dt>{t('indicators.version')}</dt><dd>{m.formula_version}</dd></div>
      <div><dt>{t('indicators.window')}</dt><dd>{windowLabel(m.window)}</dd></div>
      <div><dt>{t('indicators.samples')}</dt><dd>{m.sample_count}</dd></div>
      <div><dt>{t('indicators.basis')}</dt><dd>{label(m.price_basis)} · {label(m.unit)}</dd></div>
      <div><dt>{t('indicators.inputs')}</dt><dd>{m.input_refs.map((ref,i) => <dl className="indicator-input" key={i}>{Object.entries(ref).filter(([key]) => key !== 'row_ids').map(([key,value]) => <div key={key}><dt>{t(`indicators.input.${key}`) === `indicators.input.${key}` ? label(key) : t(`indicators.input.${key}`)}</dt><dd>{value === null ? t('indicators.unavailable') : Array.isArray(value) ? value.map(v => typeof v === 'string' ? label(v) : String(v)).join('; ') : typeof value === 'string' ? label(value) : String(value)}</dd></div>)}</dl>)}</dd></div>
    </dl></details>
    {m.warnings.length > 0 && <ul className="indicator-warnings">{m.warnings.map((w,i) => <li key={`${w}-${i}`}>{t(`indicators.warning.${w}`) === `indicators.warning.${w}` ? w.replace(/_/g, ' ') : t(`indicators.warning.${w}`)}</li>)}</ul>}
  </article>)}</div>
}
