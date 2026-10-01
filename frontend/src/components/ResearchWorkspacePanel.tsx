import { useState } from 'react'
import { Button, Checkbox, Dialog, DialogActions, DialogBody, DialogContent, DialogSurface, DialogTitle, Field, Select } from '@fluentui/react-components'
import { useI18n } from '../i18n'
import { StatusMessage } from './StatusMessage'
import { ResearchQuestionEditor } from './ResearchQuestionEditor'
import { ResearchRunView } from './ResearchRunView'
import { ResearchReviewEvents } from './ResearchReviewEvents'
import { useResearchWorkspace } from './useResearchWorkspace'
import type { ResearchProject } from '../types/research'
export function ResearchWorkspacePanel({securityId}:{securityId:number}) {
  const {t,formatDateTime}=useI18n();const w=useResearchWorkspace(securityId)
  const [critique,setCritique]=useState(false),[pending,setPending]=useState<ResearchProject|null|undefined>(undefined),[discardLatest,setDiscardLatest]=useState(false)
  function choose(p:ResearchProject|null){if(w.dirty){setPending(p);return}void w.select(p)}
  return <section className="stock-detail-section research-workspace" aria-label={t('research.workspace')}>
    <div className="dashboard-panel__header"><h2>{t('research.workspace')}</h2></div><p className="stock-detail-subtle">{t('research.scope')}</p>
    {w.loading&&<StatusMessage message={t('research.loading')}/>}
    {w.error&&<div><StatusMessage tone="error" message={t(`research.error.${w.error}`)}/><Button disabled={w.busy||w.loading} onClick={()=>void w.retry()}>{t('research.retry')}</Button></div>}
    <div className="research-workspace-grid"><aside className="research-questions">
      <Field label={t('research.recentQuestions')}><Select value={w.project?.id??''} disabled={w.busy} onChange={(_,d)=>choose(w.projects.find(p=>String(p.id)===d.value)??null)}><option value="">{t('research.newQuestion')}</option>{w.projects.map(p=><option key={p.id} value={p.id}>{p.question} · v{p.version} · {t(`research.${p.status}`)}</option>)}</Select></Field>
      <p className="stock-detail-subtle">{t('research.recentHint')}</p>
      <ResearchQuestionEditor project={w.project} draft={w.draft} onChange={w.edit} onSave={()=>void w.mutate('save')} busy={w.busy} dirty={w.dirty}/>
      {w.latest&&<section className="research-conflict"><h3>{t('research.latestServer')}</h3><p>{t('research.version')} {w.latest.version} · {t(`research.${w.latest.status}`)}</p><p>{w.latest.question}</p><p>{w.latest.hypothesis}</p><p>{w.latest.horizon}</p><Button onClick={()=>setDiscardLatest(true)}>{t('research.reloadLatest')}</Button></section>}
      {w.project?.status==='active'&&<div className="research-actions"><Checkbox checked={critique} disabled={w.busy} label={t('research.critique')} onChange={(_,d)=>setCritique(d.checked===true)}/><p className="stock-detail-subtle">{t('research.settingsHint')}</p><Button appearance="primary" disabled={w.busy||w.dirty} onClick={()=>void w.mutate('generate',critique)}>{t('research.generate')}</Button><Button disabled={w.busy} onClick={()=>void w.mutate('check')}>{t('research.recheck')}</Button><Button disabled={w.busy||w.dirty} onClick={()=>void w.mutate('archive')}>{t('research.archive')}</Button></div>}
      {w.project?.status==='archived'&&<p>{t('research.archivedHint')}</p>}
    </aside><div className="research-results">
      {w.project&&<Field label={t('research.recentReports')}><Select value={w.run?.id??''} disabled={w.busy} onChange={(_,d)=>w.setRun(w.runs.find(r=>String(r.id)===d.value)??null)}><option value="">{t('research.selectReport')}</option>{w.runs.map(r=><option key={r.id} value={r.id}>#{r.id} · {t(`research.${r.status}`)} · {formatDateTime(r.created_at)} · v{r.project_version}</option>)}</Select></Field>}
      {w.run?<ResearchRunView run={w.run}/>:<p className="dashboard-empty">{t('research.noReport')}</p>}
      {w.project&&<ResearchReviewEvents events={w.events} check={w.check} busy={w.busy} onResolve={e=>void w.mutate('resolve',false,e)}/>}
    </div></div>
    <Dialog open={pending!==undefined||discardLatest} onOpenChange={(_,d)=>{if(!d.open){setPending(undefined);setDiscardLatest(false)}}}><DialogSurface><DialogBody><DialogTitle>{t('research.discardTitle')}</DialogTitle><DialogContent>{t('research.discardHint')}</DialogContent><DialogActions><Button onClick={()=>{setPending(undefined);setDiscardLatest(false)}}>{t('research.keepEditing')}</Button><Button appearance="primary" onClick={()=>{if(discardLatest)w.reloadLatest();else if(pending!==undefined)void w.select(pending);setPending(undefined);setDiscardLatest(false)}}>{t('research.discard')}</Button></DialogActions></DialogBody></DialogSurface></Dialog>
  </section>
}
