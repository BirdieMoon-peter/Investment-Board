import {act,fireEvent,render,screen,waitFor,within} from '@testing-library/react'
import {beforeEach,describe,expect,it,vi} from 'vitest'
import {ResearchWorkspacePanel} from './ResearchWorkspacePanel'
import {ResearchRunView} from './ResearchRunView'
import {DetailWorkspaceTabs,type DetailGroup} from './DetailWorkspaceTabs'
import {I18nProvider} from '../i18n'
import {useState} from 'react'
import * as api from '../api/research'
import {researchProject as p,researchRun as r,researchEvent as e} from '../test/researchFixtures'
import type {ResearchProject,ResearchRun} from '../types/research'
vi.mock('../api/research',async()=>{const actual=await vi.importActual<typeof import('../api/research')>('../api/research');return {...actual,...Object.fromEntries(['fetchResearchProjects','fetchResearchProject','createResearchProject','updateResearchProject','archiveResearchProject','fetchResearchRuns','fetchResearchEvents','generateResearchRun','checkResearchProject','resolveResearchEvent'].map(k=>[k,vi.fn()]))}})
const mock=(fn:typeof api.fetchResearchProjects)=>vi.mocked(fn)
function deferred<T>(){let resolve!:(v:T)=>void,reject!:(e:Error)=>void;const promise=new Promise<T>((a,b)=>{resolve=a;reject=b});return {promise,resolve,reject}}
function panel(id=1){return <I18nProvider language="en"><ResearchWorkspacePanel securityId={id}/></I18nProvider>}
async function select(id=1){await waitFor(()=>expect(screen.getByRole('combobox',{name:'Recent saved questions'}).querySelector(`option[value="${id}"]`)).toBeTruthy());fireEvent.change(screen.getByRole('combobox',{name:'Recent saved questions'}),{target:{value:String(id)}});await waitFor(()=>expect(api.fetchResearchRuns).toHaveBeenCalled())}
beforeEach(()=>{
  vi.clearAllMocks();mock(api.fetchResearchProjects).mockResolvedValue([p]);vi.mocked(api.fetchResearchRuns).mockResolvedValue([r]);vi.mocked(api.fetchResearchEvents).mockResolvedValue([])
  vi.mocked(api.fetchResearchProject).mockResolvedValue({...p,version:2,question:'Latest server question?'})
  vi.mocked(api.createResearchProject).mockResolvedValue(p);vi.mocked(api.updateResearchProject).mockResolvedValue({...p,version:2});vi.mocked(api.archiveResearchProject).mockResolvedValue({...p,status:'archived',version:2})
  vi.mocked(api.generateResearchRun).mockResolvedValue(r);vi.mocked(api.checkResearchProject).mockResolvedValue({run_id:1,changed:true,status:'needs_review',events:[e],conditions:[{index:0,metric_key:'ma_20',status:'uncheckable'}]})
  vi.mocked(api.resolveResearchEvent).mockResolvedValue({...e,status:'resolved',resolved_at:'2026-10-01T01:00:00Z'})
})
describe('evidence research workflow',()=>{
  it('keeps typed new draft during catalog hydration, saves, and generates only on explicit click',async()=>{
    const pending=deferred<ResearchProject[]>();mock(api.fetchResearchProjects).mockReturnValueOnce(pending.promise)
    render(panel());fireEvent.change(screen.getByRole('textbox',{name:'Research question'}),{target:{value:'Typed while loading?'}})
    await act(async()=>pending.resolve([p]));expect(screen.getByRole('textbox',{name:'Research question'})).toHaveValue('Typed while loading?')
    expect(api.generateResearchRun).not.toHaveBeenCalled();fireEvent.click(screen.getByRole('button',{name:'Save question'}))
    await screen.findByRole('button',{name:'Generate research report'});await waitFor(()=>expect(screen.getByRole('button',{name:'Generate research report'})).toBeEnabled())
    expect(api.createResearchProject).toHaveBeenCalledWith(1,{question:'Typed while loading?',hypothesis:'',horizon:''},expect.any(AbortSignal))
    expect(api.generateResearchRun).not.toHaveBeenCalled();fireEvent.click(screen.getByRole('button',{name:'Generate research report'}));await waitFor(()=>expect(api.generateResearchRun).toHaveBeenCalledWith(1,1,false,expect.any(AbortSignal)))
  })
  it('preserves dirty question and compares a 409 latest version until explicit discard',async()=>{
    vi.mocked(api.updateResearchProject).mockRejectedValue(new api.ResearchError('conflict'))
    render(panel());await select();fireEvent.change(screen.getByRole('textbox',{name:'Research question'}),{target:{value:'My unsaved question?'}})
    expect(screen.getByRole('button',{name:'Generate research report'})).toBeDisabled();fireEvent.click(screen.getByRole('button',{name:'Save question'}))
    await screen.findByText('Latest server question?');expect(screen.getByRole('textbox',{name:'Research question'})).toHaveValue('My unsaved question?')
    expect(api.updateResearchProject).toHaveBeenCalledWith(p,{question:'My unsaved question?'},expect.any(AbortSignal))
    fireEvent.click(screen.getByRole('button',{name:'Discard draft and load latest version'}));fireEvent.click(screen.getByRole('button',{name:'Keep editing'}));await waitFor(()=>expect(screen.getByRole('textbox',{name:'Research question'})).toHaveValue('My unsaved question?'))
    fireEvent.click(screen.getByRole('button',{name:'Discard draft and load latest version'}));fireEvent.click(screen.getByRole('button',{name:'Discard draft'}));await waitFor(()=>expect(screen.getByRole('textbox',{name:'Research question'})).toHaveValue('Latest server question?'))
  })
  it('guards dirty selection, keeps draft across task groups, and never implicitly generates',async()=>{
    function Groups(){const [active,setActive]=useState<DetailGroup>('research');return <I18nProvider language="en"><DetailWorkspaceTabs active={active} onChange={setActive} market={<p>Market</p>} news={<p>News</p>} holdings={<p>Holdings</p>} research={<ResearchWorkspacePanel securityId={1}/>}/></I18nProvider>}
    render(<Groups/>);await select();fireEvent.change(screen.getByRole('textbox',{name:'Research question'}),{target:{value:'Keep this draft'}})
    fireEvent.click(screen.getByRole('tab',{name:'News & announcements'}));fireEvent.click(screen.getByRole('tab',{name:'Evidence research'}));expect(screen.getByRole('textbox',{name:'Research question'})).toHaveValue('Keep this draft')
    fireEvent.change(screen.getByRole('combobox',{name:'Recent saved questions'}),{target:{value:''}});await screen.findByRole('dialog');fireEvent.click(screen.getByRole('button',{name:'Keep editing'}));await waitFor(()=>expect(screen.getByRole('textbox',{name:'Research question'})).toHaveValue('Keep this draft'));expect(api.generateResearchRun).not.toHaveBeenCalled()
  })
  it('archives without deleting readable history or enabling generation/check',async()=>{
    render(panel());await select();await screen.findByText('Frozen old question?');fireEvent.click(screen.getByRole('button',{name:'Archive question'}));await screen.findByText('Archived questions and their reports remain readable. Generation and rechecks are disabled.')
    expect(screen.queryByRole('button',{name:'Generate research report'})).toBeNull();expect(screen.queryByRole('button',{name:'Recheck saved viewpoint'})).toBeNull();expect(screen.getByText('Frozen old question?')).toBeInTheDocument()
  })
  it('shows a failed saved generation and retains input context',async()=>{
    const failed:ResearchRun={...r,id:2,status:'failed',output:null,error_code:'not_configured'};vi.mocked(api.generateResearchRun).mockResolvedValue(failed);vi.mocked(api.fetchResearchRuns).mockResolvedValue([failed,r])
    render(panel());await select();await waitFor(()=>expect(screen.getByRole('button',{name:'Generate research report'})).toBeEnabled());fireEvent.click(screen.getByRole('button',{name:'Generate research report'}))
    await screen.findByText(/Report generation failed/);expect(screen.getByText('Frozen old question?')).toBeInTheDocument();expect(screen.queryByText('A saved synthetic report')).toBeNull()
  })
  it('rechecks locally, deduplicates events, acknowledges without editing the saved report',async()=>{
    render(panel());await select();await screen.findByText('Frozen old question?')
    // Refresh reflects the same stored event; repeated checks must not duplicate it.
    vi.mocked(api.fetchResearchEvents).mockResolvedValue([e])
    fireEvent.click(screen.getByRole('button',{name:'Recheck saved viewpoint'}));await screen.findByRole('button',{name:'Acknowledge review event'});await waitFor(()=>expect(screen.getByRole('button',{name:'Recheck saved viewpoint'})).toBeEnabled())
    fireEvent.click(screen.getByRole('button',{name:'Recheck saved viewpoint'}));await waitFor(()=>expect(api.checkResearchProject).toHaveBeenCalledTimes(2));expect(screen.getAllByText('Saved input facts changed')).toHaveLength(1)
    expect(screen.getByText('100.01')).toBeInTheDocument();expect(screen.getByText('101.02')).toBeInTheDocument();expect(screen.getByText(/does not establish that the thesis is disproved/)).toBeInTheDocument()
    await waitFor(()=>expect(screen.getByRole('button',{name:'Acknowledge review event'})).toBeEnabled());vi.mocked(api.fetchResearchEvents).mockResolvedValue([{...e,status:'resolved',resolved_at:'2026-10-01T01:00:00Z'}]);fireEvent.click(screen.getByRole('button',{name:'Acknowledge review event'}));await screen.findByText(/Acknowledged at/)
    expect(screen.getByText('Frozen old question?')).toBeInTheDocument();expect(api.generateResearchRun).not.toHaveBeenCalled();expect(api.updateResearchProject).not.toHaveBeenCalled()
  })
  it.each(['success','failure'])('excludes obsolete project read %s and its finally',async outcome=>{
    const old=deferred<ResearchRun[]>();vi.mocked(api.fetchResearchRuns).mockReturnValueOnce(old.promise);mock(api.fetchResearchProjects).mockResolvedValue([p,{...p,id:2,question:'Second question?'}])
    const next:ResearchRun={...r,id:2,project_id:2,input_snapshot:{...r.input_snapshot,project:{...r.input_snapshot.project,id:2,question:'Second frozen question?'}}};vi.mocked(api.fetchResearchRuns).mockResolvedValue(next?[next]:[])
    const {rerender}=render(panel());await select(1);fireEvent.change(screen.getByRole('combobox',{name:'Recent saved questions'}),{target:{value:'2'}});await screen.findByText('Second frozen question?')
    await act(async()=>{if(outcome==='success')old.resolve([r]);else old.reject(new Error('obsolete'))});expect(screen.queryByText('Frozen old question?')).toBeNull();expect(screen.queryByRole('alert')).toBeNull();expect(screen.queryByText('Loading saved research…')).toBeNull();rerender(panel())
  })
  it('clears mutation ownership on security change, excluding late success and enabling a new draft',async()=>{
    const old=deferred<ResearchRun>();vi.mocked(api.generateResearchRun).mockReturnValueOnce(old.promise)
    const {rerender}=render(panel());await select();await screen.findByText('Frozen old question?');fireEvent.click(screen.getByRole('button',{name:'Generate research report'}))
    mock(api.fetchResearchProjects).mockResolvedValue([]);rerender(panel(2));await waitFor(()=>expect(screen.getByRole('textbox',{name:'Research question'})).toBeEnabled());fireEvent.change(screen.getByRole('textbox',{name:'Research question'}),{target:{value:'New security question?'}})
    await act(async()=>old.resolve({...r,id:3}));expect(screen.queryByText('Frozen old question?')).toBeNull();expect(screen.getByRole('textbox',{name:'Research question'})).toHaveValue('New security question?');expect(screen.getByRole('button',{name:'Save question'})).toBeEnabled()
  })
  it('retains owned report on refresh failure with visible saved-read retry',async()=>{
    render(panel());await select();await screen.findByText('Frozen old question?');vi.mocked(api.fetchResearchRuns).mockRejectedValueOnce(new api.ResearchError('network'))
    fireEvent.click(screen.getByRole('button',{name:'Recheck saved viewpoint'}));await screen.findByRole('alert');expect(screen.getByText('Frozen old question?')).toBeInTheDocument();await waitFor(()=>expect(screen.getByRole('button',{name:'Retry saved reads'})).toBeEnabled());fireEvent.click(screen.getByRole('button',{name:'Retry saved reads'}));await waitFor(()=>expect(screen.queryByRole('alert')).toBeNull())
  })
  it('shows saved primary output with unassessed semantics when optional critique has ambiguous duplicate indices',()=>{
    const saved=api.validateResearchRun({...r,output:{...r.output!,model_review:{...r.output!.model_review,claims:[r.output!.model_review.claims![0],{...r.output!.model_review.claims![0],support:'unsupported'}]}}},1,1)
    render(<I18nProvider language="en"><ResearchRunView run={saved}/></I18nProvider>)
    expect(screen.getByText('A saved synthetic report')).toBeInTheDocument()
    expect(screen.getByText(/Optional review is unavailable; the primary report remains readable/)).toBeInTheDocument()
    expect(screen.getAllByText(/Model semantic review: Unassessed/)).toHaveLength(2)
    expect(screen.queryByText(/Model is uncertain/)).toBeNull();expect(screen.queryByText(/Model considers unsupported/)).toBeNull()
  })
  it('renders frozen inputs, separate checks, title-only limits, unknown units, and safe links',()=>{
    const safe={...r,input_snapshot:{...r.input_snapshot,ledger:[r.input_snapshot.ledger[0],{...r.input_snapshot.ledger[0],evidence_id:'e_safe',source_url:'https://example.com/document',title_only:false}]}}
    render(<I18nProvider language="en"><ResearchRunView run={safe}/></I18nProvider>)
    expect(screen.getByText('Frozen old question?')).toBeInTheDocument();expect(screen.getAllByText(/9007199254740993.123456789 CNY/)).toHaveLength(2)
    expect(screen.getAllByText(/References exist in this snapshot/)).toHaveLength(2);expect(screen.getByText(/Reported values match saved metrics/)).toBeInTheDocument();expect(screen.getByText(/Model is uncertain/)).toBeInTheDocument();expect(screen.getByText(/Model semantic review: Unassessed/)).toBeInTheDocument()
    expect(screen.getAllByText(/A title is not verified numeric evidence/).length).toBe(1);expect(screen.getAllByText(/Row attribution or units are unknown or mixed/)).toHaveLength(2)
    const links=screen.getAllByRole('link',{name:'Open original source'});expect(links).toHaveLength(1);expect(links[0]).toHaveAttribute('href','https://example.com/document');expect(links[0]).toHaveAttribute('rel','noopener noreferrer')
    expect(within(screen.getByRole('article',{name:'Saved report'})).queryByText('Saved question?')).toBeNull()
  })
})
