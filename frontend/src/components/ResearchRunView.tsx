import { useI18n } from '../i18n'
import { IndicatorResults, formatIndicatorValue } from './IndicatorResults'
import { ResearchEvidenceLedger, researchEvidenceAnchor } from './ResearchEvidenceLedger'
import type { ResearchRun } from '../types/research'
export function ResearchRunView({run}:{run:ResearchRun}) {
  const {t,formatDateTime}=useI18n();const s=run.input_snapshot,o=run.output
  const evidenceLabel=(id:string)=>`${t('research.evidence')} ${s.ledger.findIndex(e=>e.evidence_id===id)+1}`
  return <article className="research-report" aria-label={t('research.savedReport')}>
    <h3>{t('research.savedReport')} #{run.id}</h3>
    <p className="stock-detail-subtle">{t(`research.${run.status}`)} · {formatDateTime(run.created_at)} · {run.model_name} · {t('research.prompt')} {run.prompt_version} · {t('research.version')} {run.project_version}</p>
    <section className="research-saved-question"><h4>{t('research.frozenQuestion')}</h4><p>{s.project.question}</p>{s.project.hypothesis&&<p>{t('research.hypothesis')}: {s.project.hypothesis}</p>}{s.project.horizon&&<p>{t('research.horizon')}: {s.project.horizon}</p>}<p className="stock-detail-subtle">{t('research.snapshotDate')}: {s.as_of_snapshot}</p></section>
    {run.status==='failed'&&<p role="alert" className="research-warning">{t('research.generationFailed')} {t(`research.failure.${run.error_code}`)===`research.failure.${run.error_code}`?t('research.failure.invalid_output'):t(`research.failure.${run.error_code}`)}</p>}
    {o&&<><h4>{t('research.summary')}</h4><p className="research-summary">{o.research.executive_summary}</p>
      <section aria-label={t('research.claims')}><h4>{t('research.claims')}</h4>{o.research.claims.map((claim,i)=>{
        const diagnostic=o.diagnostics.find(d=>d.claim_index===i), review=o.model_review.claims?.find(c=>c.claim_index===i)
        return <article className="research-claim" key={i}><h5>{i+1}. {t(`research.${claim.kind}`)}</h5><p>{claim.statement}</p>
          {(['evidence_ids','counter_evidence_ids'] as const).map(key=>claim[key].length>0&&<p key={key}>{t(key==='evidence_ids'?'research.support':'research.counterEvidence')}: {claim[key].map(id=><a key={id} className="research-reference" href={`#${researchEvidenceAnchor(run.id,id)}`}>{evidenceLabel(id)}</a>)}</p>)}
          {claim.metric_refs.map((ref,j)=>{const m=s.metrics.find(m=>m.key===ref.metric_key);return <p key={j}>{m?.label??ref.metric_key}: {ref.reported_value??t('research.notReported')} · {t('research.savedValue')}: {m?formatIndicatorValue(m.value,m.unit,t('research.unknown'),t('indicators.points')):t('research.unknown')}</p>})}
          <div className="research-diagnostics"><p>{t('research.referenceCheck')}: {t(diagnostic?'research.referencesExist':'research.notAssessed')}</p><p>{t('research.numericCheck')}: {t(`research.numeric.${diagnostic?.numeric_check??'not_reported'}`)}</p><p>{t('research.semanticCheck')}: {t(review?`research.model.${review.support}`:'research.notAssessed')}</p></div>
          {diagnostic?.codes.map((code,j)=><p className="research-warning" key={j}>{t(`research.code.${code}`)===`research.code.${code}`?code.replace(/_/g,' '):t(`research.code.${code}`)}</p>)}
          {review&&<p>{t('research.modelReview')}: {review.explanation}</p>}
        </article>
      })}</section>
      <p className="stock-detail-subtle">{t('research.modelReviewHint')} {t(`research.review.${o.model_review.status}`)}</p>
      <div className="research-report-sections">{(['risks','data_gaps','next_checks'] as const).map(k=><section key={k}><h4>{t(`research.${k}`)}</h4>{o.research[k].length?<ul>{o.research[k].map((text,i)=><li key={i}>{text}</li>)}</ul>:<p>{t('research.none')}</p>}</section>)}</div>
      <h4>{t('research.conditions')}</h4>{o.research.invalidation_conditions.length?<ol>{o.research.invalidation_conditions.map((c,i)=><li key={i}>{c.description}{c.metric_key&&<span className="stock-detail-subtle"> · {c.metric_key} {c.operator??t('research.unknown')} {c.threshold??t('research.unknown')}</span>}</li>)}</ol>:<p>{t('research.none')}</p>}
    </>}
    <details><summary>{t('research.savedInputs')}</summary><IndicatorResults metrics={s.metrics}/>{s.data_gaps.map((gap,i)=><p key={i}>{gap}</p>)}</details>
    <ResearchEvidenceLedger ledger={s.ledger} runId={run.id}/>
    <details className="research-trace"><summary>{t('research.trace')}</summary><p>{t('research.fingerprint')}: {run.input_fingerprint}</p>{s.ledger.map((e,i)=><p key={e.evidence_id}>{t('research.evidence')} {i+1}: {e.evidence_id}</p>)}</details>
  </article>
}
