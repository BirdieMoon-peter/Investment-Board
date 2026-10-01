import { useI18n } from '../i18n'
import type { ResearchEvidence } from '../types/research'
export function researchEvidenceAnchor(runId:number,evidenceId:string){return `research-${runId}-${evidenceId}`}
export function safeResearchUrl(value:string|null):string|null {if(!value)return null;try{const url=new URL(value);return ['http:','https:'].includes(url.protocol)?url.href:null}catch{return null}}
// Bounded, readable factual source objects. No source HTML or expressions are executed.
export function ResearchFacts({value,depth=0}:{value:unknown;depth?:number}) {
  const {t}=useI18n()
  if(value===null||value===undefined)return <span>{t('research.unknown')}</span>
  if(typeof value!=='object')return <span>{String(value)}</span>
  if(depth>=3)return <span>{t('research.nestedLimit')}</span>
  const entries=Array.isArray(value)?value.slice(0,12).map((v,i)=>[String(i+1),v] as const):Object.entries(value).slice(0,18)
  return <dl className="research-facts">{entries.map(([key,v])=><div key={key}><dt>{t(`research.field.${key}`)===`research.field.${key}`?key.replace(/_/g,' '):t(`research.field.${key}`)}</dt><dd><ResearchFacts value={v} depth={depth+1}/></dd></div>)}</dl>
}
export function ResearchEvidenceLedger({ledger,runId}:{ledger:ResearchEvidence[];runId:number}) {
  const {t}=useI18n()
  return <section className="research-ledger" aria-label={t('research.ledger')}><h3>{t('research.ledger')}</h3>
    <p className="stock-detail-subtle">{t('research.ledgerHint')}</p>
    {ledger.length===0?<p>{t('research.noEvidence')}</p>:ledger.map((e,i)=>{
      const url=safeResearchUrl(e.source_url)
      return <details key={e.evidence_id} id={researchEvidenceAnchor(runId,e.evidence_id)} className="research-evidence"><summary>{t('research.evidence')} {i+1} · {t(`research.kind.${e.kind}`)===`research.kind.${e.kind}`?e.kind.replace(/_/g,' '):t(`research.kind.${e.kind}`)} · {e.source_name??t('research.unknownSource')}{e.title_only?` · ${t('research.titleOnly')}`:''}{!e.provenance_known?` · ${t('research.unverifiedProvenance')}`:''}</summary>
        {url&&<a href={url} target="_blank" rel="noopener noreferrer">{t('research.originalSource')}</a>}
        <dl className="research-facts"><div><dt>{t('research.observed')}</dt><dd>{e.observed_at??t('research.unknown')}</dd></div><div><dt>{t('research.published')}</dt><dd>{e.published_at??t('research.unknown')}</dd></div><div><dt>{t('research.retrieved')}</dt><dd>{e.retrieved_at??t('research.unknown')}</dd></div><div><dt>{t('research.units')}</dt><dd>{e.unit??t('research.unknown')} · {e.price_basis}</dd></div></dl>
        {e.title_only&&<p className="research-warning">{t('research.titleOnlyHint')}</p>}
        {!e.provenance_known&&<p className="research-warning">{t('research.provenanceHint')}</p>}
        {e.dataset_source_key&&<p>{t('research.datasetSource')}: {e.dataset_source_key}</p>}
        {e.source_time_note&&<p className="stock-detail-subtle">{e.source_time_note}</p>}
        {e.field_units&&Object.keys(e.field_units).length>0&&<ResearchFacts value={e.field_units}/>}
        {[...(e.provenance_warnings??[]),...(e.context_disclosures??[])].map((w,j)=><p className="stock-detail-subtle" key={j}>{t(`research.code.${w}`)===`research.code.${w}`?w.replace(/_/g,' '):t(`research.code.${w}`)}</p>)}
        <ResearchFacts value={e.content}/>
      </details>
    })}
  </section>
}
