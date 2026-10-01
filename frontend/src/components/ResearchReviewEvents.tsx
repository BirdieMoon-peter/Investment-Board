import { Button } from '@fluentui/react-components'
import { useI18n } from '../i18n'
import { ResearchFacts } from './ResearchEvidenceLedger'
import type { ResearchCheck, ResearchEvent } from '../types/research'
export function ResearchReviewEvents({events,check,busy,onResolve}:{events:ResearchEvent[];check:ResearchCheck|null;busy:boolean;onResolve:(event:ResearchEvent)=>void}) {
  const {t,formatDateTime}=useI18n()
  return <section className="research-events" aria-label={t('research.events')}><h3>{t('research.events')}</h3><p className="stock-detail-subtle">{t('research.checkHint')}</p>
    {check&&<div role="status"><p>{t(`research.check.${check.status}`)}{check.run_id!==null?` · ${t('research.savedReport')} #${check.run_id}`:''}</p>{check.conditions.map(c=><p key={c.index}>{t('research.condition')} {c.index+1} · {t(`research.condition.${c.status}`)}{c.metric_key?` · ${c.metric_key}`:''}{c.current_value!==undefined?` · ${t('research.current')}: ${c.current_value}`:''}</p>)}</div>}
    {events.length===0?<p>{t('research.noEvents')}</p>:Array.from(new Map(events.map(e=>[e.id,e])).values()).map(e=><article key={e.id} className="research-event">
      <h4>{t(`research.reason.${e.reason_code}`)}</h4><p className="stock-detail-subtle">{t('research.savedReport')} #{e.run_id} · {formatDateTime(e.created_at)} · {t(`research.event.${e.status}`)}</p>
      {e.reason_code==='data_changed'&&<p>{t('research.changeHint')}</p>}
      <details><summary>{t('research.changedFacts')}</summary>{e.details.changed_fields?.length?e.details.changed_fields.map((change,i)=><ResearchFacts key={i} value={change}/>):<p>{t('research.noFactDelta')}</p>}{e.details.conditions?.map(c=><p key={c.index}>{t('research.condition')} {c.index+1}: {t(`research.condition.${c.status}`)} · {c.metric_key??t('research.unknown')} · {t('research.previous')}: {c.previous_value??t('research.unknown')} · {t('research.current')}: {c.current_value??t('research.unknown')}</p>)}</details>
      {e.status==='open'&&<Button onClick={()=>onResolve(e)} disabled={busy}>{t('research.acknowledge')}</Button>}
      {e.resolved_at&&<p className="stock-detail-subtle">{t('research.acknowledgedAt')}: {formatDateTime(e.resolved_at)}</p>}
    </article>)}
  </section>
}
