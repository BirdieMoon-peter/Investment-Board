import {afterEach,describe,expect,it,vi} from 'vitest'
import * as api from './research'
import {researchProject as project,researchRun as run,researchEvent as event} from '../test/researchFixtures'
afterEach(()=>vi.unstubAllGlobals())
const response=(body:unknown,status=200)=>({ok:status>=200&&status<300,status,json:async()=>body})
describe('saved research client',()=>{
  it('preserves exact amounts, null source units and optional provenance',()=>{
    const saved=api.validateResearchRun(run,1,1)
    expect(saved.input_snapshot.metrics[0].value).toBe('9007199254740993.123456789')
    expect(saved.input_snapshot.ledger[0].unit).toBeNull();expect(saved.input_snapshot.ledger[0].dataset_source_key).toBe('vendor_context')
  })
  it.each(['1e10000','1e-10000','+.5','-0','1.'])('accepts finite exact decimal syntax %s without lossy conversion',v=>{expect(api.finiteResearchDecimal(v)).toBe(true);expect(api.validateResearchRun({...run,input_snapshot:{...run.input_snapshot,metrics:[{...run.input_snapshot.metrics[0],value:v}]}},1,1)).toBeTruthy()})
  it.each(['NaN','Infinity','-Infinity','1.2.3',2,null])('rejects invalid metric amount %s',value=>expect(()=>api.validateResearchRun({...run,input_snapshot:{...run.input_snapshot,metrics:[{...run.input_snapshot.metrics[0],value}]}},1,1)).toThrow('payload'))
  it('rejects foreign ownership at project, run and frozen snapshot levels',()=>{
    expect(()=>api.validateResearchProject(project,2)).toThrow('payload')
    expect(()=>api.validateResearchProject(project,1,2)).toThrow('payload')
    expect(()=>api.validateResearchRun(run,1,2)).toThrow('payload')
    expect(()=>api.validateResearchRun(run,2,1)).toThrow('payload')
    expect(()=>api.validateResearchRun({...run,project_version:2},1,1)).toThrow('payload')
    expect(()=>api.validateResearchEvent(event,2)).toThrow('payload')
  })
  it('rejects malformed completed output, duplicate diagnostics, foreign references and oversized source data',()=>{
    const output=run.output!
    for(const changed of [null,{...output,diagnostics:[output.diagnostics[0],output.diagnostics[0]]},{...output,research:{...output.research,claims:[{...output.research.claims[0],evidence_ids:['foreign']}]}}])expect(()=>api.validateResearchRun({...run,output:changed},1,1)).toThrow('payload')
    expect(()=>api.validateResearchRun({...run,input_snapshot:{...run.input_snapshot,ledger:Array(151).fill(run.input_snapshot.ledger[0])}},1,1)).toThrow('payload')
  })
  it('retains the valid primary report when saved optional critique contains duplicate claim indices',async()=>{
    const duplicated={...run,output:{...run.output!,model_review:{...run.output!.model_review,claims:[run.output!.model_review.claims![0],{...run.output!.model_review.claims![0],support:'unsupported'}]}}}
    const saved=api.validateResearchRun(duplicated,1,1)
    expect(saved.output?.research.executive_summary).toBe('A saved synthetic report')
    expect(saved.output?.model_review.status).toBe('unavailable');expect(saved.output?.model_review.claims).toBeUndefined()
    expect(duplicated.output.model_review.claims).toHaveLength(2)
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue(response([duplicated])))
    const history=await api.fetchResearchRuns(1,1)
    expect(history[0].output?.research.executive_summary).toBe('A saved synthetic report')
    expect(history[0].output?.model_review.status).toBe('unavailable');expect(history[0].output?.model_review.claims).toBeUndefined()
  })
  it('accepts a failed 201 as a failed saved run, without assuming generation succeeded',async()=>{
    const failed={...run,status:'failed',output:null,error_code:'not_configured'}
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue(response(failed,201)))
    expect((await api.generateResearchRun(1,1,false)).status).toBe('failed')
    expect(()=>api.validateResearchRun({...failed,output:run.output},1,1)).toThrow('payload')
  })
  it('reads bounded saved history and forwards AbortSignal',async()=>{
    const fetch=vi.fn().mockResolvedValue(response([project]));vi.stubGlobal('fetch',fetch)
    const c=new AbortController();await api.fetchResearchProjects(1,c.signal)
    expect(fetch).toHaveBeenLastCalledWith('/api/research/projects?security_id=1&limit=20',{method:'GET',cache:'no-store',signal:c.signal})
    fetch.mockResolvedValue(response([run]));await api.fetchResearchRuns(1,1,c.signal)
    expect(fetch.mock.calls.every(call=>call[1].method==='GET')).toBe(true)
  })
  it('sends only changed fields and expected version on update, with explicit critique generation',async()=>{
    const fetch=vi.fn().mockResolvedValue(response(project));vi.stubGlobal('fetch',fetch)
    await api.updateResearchProject(project,{question:'Changed?'})
    expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual({expected_version:1,question:'Changed?'})
    fetch.mockResolvedValue(response(run));await api.generateResearchRun(1,1,true)
    expect(JSON.parse(fetch.mock.calls[1][1].body)).toEqual({critique:true})
  })
  it('maps version conflict and arbitrary HTTP errors to controlled codes without exposing response text',async()=>{
    const fetch=vi.fn().mockResolvedValue(response({detail:'SECRET'},409));vi.stubGlobal('fetch',fetch)
    await expect(api.updateResearchProject(project,{question:'Draft?'})).rejects.toThrow('conflict')
    fetch.mockResolvedValue(response({detail:'SECRET'},500));await expect(api.fetchResearchProjects(1)).rejects.toThrow('request')
    fetch.mockRejectedValue(new Error('SECRET'));await expect(api.fetchResearchProjects(1)).rejects.toThrow('network')
  })
  it('preserves abort rejection and excludes a late successful aborted read',async()=>{
    const c=new AbortController();const fetch=vi.fn().mockImplementation(async()=>{c.abort();return response([project])});vi.stubGlobal('fetch',fetch)
    await expect(api.fetchResearchProjects(1,c.signal)).rejects.toMatchObject({name:'AbortError'})
  })
  it('validates check event ownership and condition statuses',()=>{
    expect(api.validateResearchCheck({run_id:1,changed:true,events:[event],conditions:[{index:0,metric_key:'ma_20',status:'uncheckable'}],status:'needs_review'},1).status).toBe('needs_review')
    expect(()=>api.validateResearchCheck({run_id:2,changed:true,events:[event],conditions:[],status:'needs_review'},1)).toThrow('payload')
    expect(()=>api.validateResearchCheck({run_id:null,changed:true,events:[],conditions:[],status:'no_completed_run'},1)).toThrow('payload')
    expect(()=>api.validateResearchCheck({run_id:1,changed:false,events:[],conditions:[{index:0,metric_key:null,status:'certain'}],status:'unchanged'},1)).toThrow('payload')
  })
})
