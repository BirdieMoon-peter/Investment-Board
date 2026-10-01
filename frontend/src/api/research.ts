import type { ResearchProject, ResearchRun, ResearchEvent, ResearchCheck, ResearchDraft, ResearchOutput } from '../types/research'
export class ResearchError extends Error {
  constructor(public readonly code: 'payload' | 'network' | 'request' | 'conflict' | 'invalid') { super(code) }
}
const fail = (): never => { throw new ResearchError('payload') }
function obj(v: unknown): Record<string, unknown> { if (!v || typeof v !== 'object' || Array.isArray(v)) return fail(); return v as Record<string, unknown> }
function str(v: unknown, max = 10000, empty = false) { if (typeof v !== 'string' || v.length > max || (!empty && !v.length)) fail() }
function nullable(v: unknown, max = 10000) { if (v !== null) str(v, max, true) }
function int(v: unknown, min = 1) { if (!Number.isSafeInteger(v) || (v as number) < min) fail() }
function bool(v: unknown) { if (typeof v !== 'boolean') fail() }
function choice(v: unknown, values: string[]) { if (!values.includes(v as string)) fail() }
function list(v: unknown, max: number, check: (v: unknown) => unknown): unknown[] { if (!Array.isArray(v) || v.length > max) return fail(); v.forEach(item => check(item)); return v }
const texts = (v: unknown, max = 30) => list(v, max, v => str(v, 4000))
export function finiteResearchDecimal(v: unknown): boolean { return typeof v === 'string' && v.length <= 100 && /^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/.test(v) }
function decimal(v: unknown) { if (!finiteResearchDecimal(v)) fail() }
// Bound arbitrary saved source objects without converting their exact numeric strings.
function bounded(v: unknown, depth = 0): void {
  if (depth > 8) fail()
  if (v === null || typeof v === 'boolean') return
  if (typeof v === 'string') { str(v, 16000, true); return }
  if (typeof v === 'number') { if (!Number.isFinite(v)) fail(); return }
  if (Array.isArray(v)) { if (v.length > 200) fail(); v.forEach(x => bounded(x, depth + 1)); return }
  const o = obj(v); if (Object.keys(o).length > 100) fail(); Object.values(o).forEach(x => bounded(x, depth + 1))
}
function unique(items: unknown[], key: string) { const ids = items.map(v => obj(v)[key]); if (new Set(ids).size !== ids.length) fail() }
export function validateResearchProject(v: unknown, securityId: number, projectId?: number): ResearchProject {
  const o = obj(v); int(o.id); int(o.security_id); int(o.version)
  if (o.security_id !== securityId || (projectId !== undefined && o.id !== projectId)) fail()
  str(o.question, 2000); nullable(o.hypothesis, 4000); nullable(o.horizon, 200)
  choice(o.status, ['active', 'archived']); str(o.created_at); str(o.updated_at)
  return v as ResearchProject
}
function metrics(v: unknown) {
  const items = list(v, 100, v => { const m = obj(v)
    ;['key', 'label', 'formula', 'formula_version', 'window', 'unit', 'price_basis'].forEach(k => str(m[k]))
    choice(m.status, ['ready', 'unavailable']); if (m.status === 'ready') decimal(m.value); else if (m.value !== null) fail()
    nullable(m.as_of); int(m.sample_count, 0); list(m.input_refs, 100, bounded); texts(m.warnings, 100)
  }); unique(items, 'key')
}
function snapshot(v: unknown, securityId: number, projectId: number, version: number) {
  const s = obj(v), p = obj(s.project), security = obj(s.security)
  if (p.id !== projectId || p.version !== version || security.id !== securityId) fail()
  str(p.question, 2000); nullable(p.hypothesis, 4000); nullable(p.horizon, 200)
  ;['market','code','name'].forEach(k => str(security[k])); str(s.snapshot_version); str(s.as_of_snapshot)
  const ledger = list(s.ledger, 150, v => { const e = obj(v)
    str(e.evidence_id, 100); str(e.kind); obj(e.content); bounded(e.content)
    ;['source_name','source_url','observed_at','published_at','retrieved_at'].forEach(k => nullable(e[k]))
    nullable(e.unit); str(e.price_basis); bool(e.provenance_known); bool(e.title_only)
    if (e.dataset_source_key !== undefined) nullable(e.dataset_source_key)
    if (e.field_units !== undefined) Object.values(obj(e.field_units)).forEach(v => str(v))
    if (e.source_time_note !== undefined) str(e.source_time_note)
    if (e.health !== undefined) str(e.health)
    if (e.provenance_warnings !== undefined) texts(e.provenance_warnings,100)
    if (e.context_disclosures !== undefined) texts(e.context_disclosures,100)
  }); unique(ledger, 'evidence_id'); metrics(s.metrics); obj(s.metadata); bounded(s.metadata); obj(s.context); bounded(s.context); texts(s.data_gaps,100)
}
function output(v: unknown, saved: Record<string,unknown>) {
  const o = obj(v), r = obj(o.research); str(r.executive_summary,4000)
  const evidenceIds = new Set((saved.ledger as {evidence_id:string}[]).map(e=>e.evidence_id)), metricKeys = new Set((saved.metrics as {key:string}[]).map(m=>m.key))
  const claims = list(r.claims,30,v=>{const c=obj(v); choice(c.kind,['fact','inference','hypothesis']); str(c.statement,4000)
    for (const k of ['evidence_ids','counter_evidence_ids']) list(c[k],30,v=>{str(v,100); if(!evidenceIds.has(v as string))fail()})
    list(c.metric_refs,30,v=>{const m=obj(v);str(m.metric_key,100);if(!metricKeys.has(m.metric_key as string))fail();nullable(m.reported_value,100)})
  }); texts(r.risks);texts(r.data_gaps);texts(r.next_checks)
  list(r.invalidation_conditions,20,v=>{const c=obj(v);str(c.description,4000);nullable(c.metric_key,100);nullable(c.operator,20);nullable(c.threshold,100)})
  const diagnostics=list(o.diagnostics,30,v=>{const d=obj(v);int(d.claim_index,0);if((d.claim_index as number)>=claims.length)fail();choice(d.reference_check,['passed']);choice(d.numeric_check,['matched','mismatch','not_reported']);choice(d.semantic_support,['not_assessed']);texts(d.codes)})
  unique(diagnostics,'claim_index');if(diagnostics.length!==claims.length)fail()
  const review=obj(o.model_review);choice(review.status,['not_requested','available','unavailable']);str(review.label)
  if(review.status==='available'){const items=list(review.claims,30,v=>{const c=obj(v);int(c.claim_index,0);if((c.claim_index as number)>=claims.length)fail();choice(c.support,['supported','unsupported','uncertain']);str(c.explanation,4000)})
    // Backend critique schema allows repeated indices. Ambiguous optional review
    // must not hide a valid immutable primary report or choose arbitrary support.
    const indices=items.map(item=>obj(item).claim_index)
    if(new Set(indices).size!==indices.length)return {...o,model_review:{status:'unavailable',label:'model_review_not_verification',error_code:'ambiguous_review'}} as ResearchOutput
  }
  return v as ResearchOutput
}
export function validateResearchRun(v: unknown, securityId: number, projectId: number, runId?: number): ResearchRun {
  const o=obj(v);int(o.id);int(o.project_id);int(o.project_version)
  if(o.project_id!==projectId||(runId!==undefined&&o.id!==runId))fail()
  choice(o.status,['completed','failed']);snapshot(o.input_snapshot,securityId,projectId,o.project_version as number)
  str(o.input_fingerprint,100);str(o.model_name);str(o.prompt_version);str(o.created_at);nullable(o.error_code,100)
  if(o.status==='completed'){const validated=output(o.output,obj(o.input_snapshot));if(o.error_code!==null)fail();return {...o,output:validated} as unknown as ResearchRun}
  else {if(o.output!==null)fail();str(o.error_code,100)}
  return v as ResearchRun
}
function condition(v:unknown) {const c=obj(v);int(c.index,0);if((c.index as number)>=20)fail();choice(c.status,['triggered','not_triggered','uncheckable']);nullable(c.metric_key,100);if(c.previous_value!==undefined&&c.previous_value!==null)decimal(c.previous_value);if(c.current_value!==undefined)decimal(c.current_value);if(c.as_of!==undefined)nullable(c.as_of)}
export function validateResearchEvent(v:unknown, projectId:number, eventId?:number):ResearchEvent {
  const e=obj(v);int(e.id);int(e.run_id);if(e.project_id!==projectId||(eventId!==undefined&&e.id!==eventId))fail()
  choice(e.reason_code,['data_changed','condition_triggered','data_unavailable']);choice(e.status,['open','resolved']);str(e.input_fingerprint,100);str(e.created_at);nullable(e.resolved_at)
  const details=obj(e.details);bounded(details);if(details.conditions!==undefined)list(details.conditions,20,condition)
  if(details.changed_fields!==undefined)list(details.changed_fields,30,obj)
  return v as ResearchEvent
}
export function validateResearchCheck(v:unknown, projectId:number):ResearchCheck {
  const c=obj(v);bool(c.changed);choice(c.status,['no_completed_run','unchanged','needs_review']);if(c.run_id!==null)int(c.run_id)
  const events=list(c.events,3,v=>{const e=validateResearchEvent(v,projectId);if(e.run_id!==c.run_id)fail()});unique(events,'id')
  list(c.conditions,20,condition)
  if(c.status==='no_completed_run'&&(c.run_id!==null||c.changed||events.length||(c.conditions as unknown[]).length))fail()
  if(c.status==='unchanged'&&(c.run_id===null||c.changed||events.length))fail()
  if(c.status==='needs_review'&&(c.run_id===null||!events.length))fail()
  return v as ResearchCheck
}
async function request<T>(path:string,validate:(v:unknown)=>T,signal?:AbortSignal,method='GET',body?:unknown):Promise<T>{
  let response:Response
  try {response=await fetch(`/api/research/${path}`,{method,cache:'no-store',signal,...(body===undefined?{}:{headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})})}
  catch(error){if(signal?.aborted||(error instanceof DOMException&&error.name==='AbortError'))throw error;throw new ResearchError('network')}
  if(!response.ok)throw new ResearchError(response.status===409?'conflict':'request')
  let v:unknown;try{v=await response.json()}catch{throw new ResearchError('payload')}
  if(signal?.aborted)throw new DOMException('Aborted','AbortError')
  return validate(v)
}
function id(v:number){if(!Number.isSafeInteger(v)||v<=0)throw new ResearchError('invalid')}
export function fetchResearchProjects(securityId:number,signal?:AbortSignal){id(securityId);return request(`projects?security_id=${securityId}&limit=20`,v=>{const items=list(v,20,v=>validateResearchProject(v,securityId));unique(items,'id');return items as ResearchProject[]},signal)}
export function fetchResearchProject(securityId:number,projectId:number,signal?:AbortSignal){id(securityId);id(projectId);return request(`projects/${projectId}`,v=>validateResearchProject(v,securityId,projectId),signal)}
export function createResearchProject(securityId:number,draft:ResearchDraft,signal?:AbortSignal){id(securityId);return request('projects',v=>validateResearchProject(v,securityId),signal,'POST',{security_id:securityId,...draft,hypothesis:draft.hypothesis||null,horizon:draft.horizon||null})}
export function updateResearchProject(project:ResearchProject,changes:Partial<ResearchDraft>,signal?:AbortSignal){return request(`projects/${project.id}`,v=>validateResearchProject(v,project.security_id,project.id),signal,'PUT',{expected_version:project.version,...changes})}
export function archiveResearchProject(project:ResearchProject,signal?:AbortSignal){return request(`projects/${project.id}/archive`,v=>validateResearchProject(v,project.security_id,project.id),signal,'POST',{expected_version:project.version})}
export function fetchResearchRuns(securityId:number,projectId:number,signal?:AbortSignal){id(projectId);return request(`projects/${projectId}/runs?limit=20`,v=>{const items=list(v,20,obj).map(item=>validateResearchRun(item,securityId,projectId));unique(items,'id');return items},signal)}
export function fetchResearchRun(securityId:number,projectId:number,runId:number,signal?:AbortSignal){id(runId);return request(`projects/${projectId}/runs/${runId}`,v=>validateResearchRun(v,securityId,projectId,runId),signal)}
export function generateResearchRun(securityId:number,projectId:number,critique:boolean,signal?:AbortSignal){return request(`projects/${projectId}/runs`,v=>validateResearchRun(v,securityId,projectId),signal,'POST',{critique})}
export function fetchResearchEvents(projectId:number,signal?:AbortSignal){id(projectId);return request(`projects/${projectId}/events?limit=20`,v=>{const items=list(v,20,v=>validateResearchEvent(v,projectId));unique(items,'id');return items as ResearchEvent[]},signal)}
export function checkResearchProject(projectId:number,signal?:AbortSignal){return request(`projects/${projectId}/check`,v=>validateResearchCheck(v,projectId),signal,'POST')}
export function resolveResearchEvent(projectId:number,eventId:number,signal?:AbortSignal){return request(`events/${eventId}/resolve`,v=>validateResearchEvent(v,projectId,eventId),signal,'POST')}
