import { useCallback, useEffect, useRef, useState } from 'react'
import * as api from '../api/research'
import type { ResearchCheck, ResearchDraft, ResearchEvent, ResearchProject, ResearchRun } from '../types/research'
export const emptyResearchDraft: ResearchDraft = {question:'',hypothesis:'',horizon:''}
export const projectDraft = (p:ResearchProject):ResearchDraft => ({question:p.question,hypothesis:p.hypothesis??'',horizon:p.horizon??''})
export function useResearchWorkspace(securityId:number) {
  const [projects,setProjects]=useState<ResearchProject[]>([]), [project,setProject]=useState<ResearchProject|null>(null)
  const [draft,setDraft]=useState<ResearchDraft>(emptyResearchDraft), [runs,setRuns]=useState<ResearchRun[]>([]), [run,setRun]=useState<ResearchRun|null>(null)
  const [events,setEvents]=useState<ResearchEvent[]>([]), [check,setCheck]=useState<ResearchCheck|null>(null)
  const [busy,setBusy]=useState(false), [loading,setLoading]=useState(false), [error,setError]=useState<string|null>(null)
  const [latest,setLatest]=useState<ResearchProject|null>(null)
  const owner=useRef(0), controller=useRef<AbortController|null>(null), locked=useRef(false), mounted=useRef(true)
  const scope=useRef(securityId); if(scope.current!==securityId){scope.current=securityId;owner.current++;controller.current?.abort()}
  const begin=useCallback(()=>{controller.current?.abort();const c=new AbortController();controller.current=c;const token=++owner.current;return {signal:c.signal,owns:()=>mounted.current&&owner.current===token&&!c.signal.aborted}},[])
  const reportError=(e:unknown)=>setError(e instanceof api.ResearchError?e.code:'request')
  const reset=(p:ResearchProject|null)=>{setProject(p);setDraft(p?projectDraft(p):emptyResearchDraft);setLatest(null);setRuns([]);setRun(null);setEvents([]);setCheck(null);setError(null)}
  async function history(p:ResearchProject,request:ReturnType<typeof begin>,preferred?:ResearchRun){
    const results=await Promise.allSettled([api.fetchResearchRuns(securityId,p.id,request.signal),api.fetchResearchEvents(p.id,request.signal)])
    if(!request.owns())return
    const [r,e]=results
    if(r.status==='fulfilled'){setRuns(r.value);setRun(current=>preferred??r.value.find(v=>v.id===current?.id)??r.value[0]??null)}
    if(e.status==='fulfilled')setEvents(e.value)
    const failed=results.find(v=>v.status==='rejected');if(failed?.status==='rejected')reportError(failed.reason)
  }
  async function select(p:ResearchProject|null){const request=begin();locked.current=false;setBusy(false);reset(p);setLoading(!!p)
    if(!p)return
    try{await history(p,request)}catch(e){if(request.owns())reportError(e)}finally{if(request.owns())setLoading(false)}
  }
  async function loadProjects(){const request=begin();setLoading(true);setError(null)
    try{const ps=await api.fetchResearchProjects(securityId,request.signal);if(!request.owns())return;setProjects(ps)
      // Initial hydration never replaces a draft entered while the read was pending.
    }catch(e){if(request.owns())reportError(e)}finally{if(request.owns())setLoading(false)}
  }
  useEffect(()=>{mounted.current=true;locked.current=false;setBusy(false);reset(null);setProjects([]);void loadProjects();return()=>{mounted.current=false;owner.current++;controller.current?.abort()}},[securityId]) // security owns all saved views
  const dirty=project?JSON.stringify(draft)!==JSON.stringify(projectDraft(project)):Object.values(draft).some(Boolean)
  async function mutate(action:'save'|'archive'|'generate'|'check'|'resolve',critique=false,event?:ResearchEvent){
    if(locked.current||(action!=='save'&&!project))return
    if(action!=='save'&&project?.status!=='active'&&action!=='resolve')return
    if(action==='generate'&&dirty)return
    if(action==='resolve'&&(!event||event.project_id!==project?.id||!events.some(e=>e.id===event.id&&e.run_id===event.run_id)))return
    locked.current=true;const request=begin();setBusy(true);setLoading(false);setError(null);setLatest(null)
    const p=project
    try{
      let saved=p, generated:ResearchRun|undefined
      if(action==='save'){
        const clean={question:draft.question.trim(),hypothesis:draft.hypothesis.trim(),horizon:draft.horizon.trim()}
        if(!clean.question||clean.question.length>2000||clean.hypothesis.length>4000||clean.horizon.length>200)throw new api.ResearchError('invalid')
        const changes:Partial<ResearchDraft>={};if(p){const before=projectDraft(p);for(const field of ['question','hypothesis','horizon'] as const)if(clean[field]!==before[field])changes[field]=clean[field]}
        saved=p?await api.updateResearchProject(p,changes,request.signal):await api.createResearchProject(securityId,clean,request.signal)
        if(!request.owns())return;setProject(saved);setDraft(projectDraft(saved));setLatest(null)
      }else if(action==='archive'){
        saved=await api.archiveResearchProject(p!,request.signal);if(!request.owns())return;setProject(saved)
      }else if(action==='generate'){
        generated=await api.generateResearchRun(securityId,p!.id,critique,request.signal);if(!request.owns())return
        setRun(generated);setRuns(current=>[generated!,...current.filter(r=>r.id!==generated!.id)].slice(0,20))
      }else if(action==='check'){
        const result=await api.checkResearchProject(p!.id,request.signal);if(!request.owns())return;setCheck(result)
        setEvents(current=>Array.from(new Map([...current,...result.events].map(e=>[e.id,e])).values()).slice(0,20))
      }else if(event){
        const resolved=await api.resolveResearchEvent(p!.id,event.id,request.signal);if(!request.owns())return
        if(resolved.run_id!==event.run_id)throw new api.ResearchError('payload')
        setEvents(current=>current.map(e=>e.id===resolved.id?resolved:e))
      }
      if(!request.owns())return
      if(saved) {
        const ps=await api.fetchResearchProjects(securityId,request.signal);if(!request.owns())return;setProjects(ps)
        await history(saved,request,generated)
      }
    }catch(e){if(!request.owns())return;reportError(e)
      if(e instanceof api.ResearchError&&e.code==='conflict'&&p){try{const fresh=await api.fetchResearchProject(securityId,p.id,request.signal);if(request.owns())setLatest(fresh)}catch{/* original conflict remains visible */}}
    }finally{if(request.owns()){locked.current=false;setBusy(false)}}
  }
  async function retry(){if(locked.current)return;if(!project){await loadProjects();return}const request=begin();setLoading(true);setError(null);try{await history(project,request)}finally{if(request.owns())setLoading(false)}}
  function edit(next:ResearchDraft){if(locked.current)return; // Saved-list hydration never replaces this draft.
    setDraft(next)
  }
  function reloadLatest(){if(latest){setProject(latest);setDraft(projectDraft(latest));setLatest(null);setError(null)}}
  return {projects,project,draft,edit,dirty,runs,run,setRun,events,check,busy,loading,error,latest,select,mutate,retry,reloadLatest}
}
