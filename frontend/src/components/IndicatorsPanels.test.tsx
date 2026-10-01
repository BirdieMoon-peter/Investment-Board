import {act,fireEvent,render,screen,waitFor} from '@testing-library/react'
import {beforeEach,describe,expect,it,vi} from 'vitest'
import {SecurityIndicatorsPanel} from './SecurityIndicatorsPanel'
import {HoldingsIndicatorsPanel} from './HoldingsIndicatorsPanel'
import {IndicatorResults} from './IndicatorResults'
import {I18nProvider} from '../i18n'
import {fetchSecurityIndicators,fetchHoldingsIndicators} from '../api/indicators'
import type {SecurityIndicators,IndicatorResult} from '../types/indicators'
vi.mock('../api/indicators',()=>({fetchSecurityIndicators:vi.fn(),fetchHoldingsIndicators:vi.fn()}))
const m:IndicatorResult={key:'ma_20',label:'均线',value:'100',status:'ready',formula:'sum(close) / count',formula_version:'1',window:'last_20_observations',unit:'CNY',as_of:'2026-10-01',sample_count:20,price_basis:'forward_adjusted',input_refs:[{source_key:'eastmoney'}],warnings:[]}
const payload=(value:string,id=1):SecurityIndicators=>({security_id:id,instrument_type:'stock',metrics:[{...m,value}],data_context:{calendar:{verified:false}}})
function deferred<T>() {let resolve!:(v:T)=>void, reject!:(e:Error)=>void;const promise=new Promise<T>((a,b)=>{resolve=a;reject=b});return {promise,resolve,reject}}
function panel(id=1,revision=0) {return <I18nProvider language="en"><SecurityIndicatorsPanel securityId={id} revision={revision}/></I18nProvider>}
beforeEach(()=>{vi.clearAllMocks();vi.mocked(fetchSecurityIndicators).mockResolvedValue(payload('100'));vi.mocked(fetchHoldingsIndicators).mockResolvedValue({positions:[],missing_price_security_ids:[],valuation_complete:true,denominator:'known_valued_positions_only',metrics:[],warnings:[]})})
describe('indicator presentation and saved read ownership',()=>{
  it('shows formula, observations, source and date with bilingual missing and zero',()=>{
    const {rerender}=render(<I18nProvider language="en"><IndicatorResults metrics={[{...m,key:'annualized_volatility',unit:'fraction',value:'0'}, {...m,key:'tracking_error',value:null,status:'unavailable',warnings:['benchmark_not_acquired']}]}/></I18nProvider>)
    expect(screen.getByText('0%')).toBeInTheDocument();expect(screen.getAllByText('Unavailable').length).toBeGreaterThan(0)
    expect(screen.getByText('Mapped benchmark has not been acquired')).toBeInTheDocument();expect(screen.getAllByText('20').length).toBe(2)
    expect(screen.getAllByText(/eastmoney/i).length).toBe(2)
    rerender(<I18nProvider language="zh"><IndicatorResults metrics={[{...m,value:null,status:'unavailable'}]}/></I18nProvider>)
    expect(screen.getAllByText('不可用').length).toBeGreaterThan(0);expect(screen.getByText('计算与证据')).toBeInTheDocument()
  })
  it.each(['success','failure'])('ignores an obsolete same-ID read %s',async outcome=>{
    const old=deferred<SecurityIndicators>();vi.mocked(fetchSecurityIndicators).mockReturnValueOnce(old.promise)
    const {rerender}=render(panel());await waitFor(()=>expect(fetchSecurityIndicators).toHaveBeenCalledTimes(1))
    vi.mocked(fetchSecurityIndicators).mockResolvedValue(payload('200'));rerender(panel(1,1));await screen.findByText('200 CNY')
    expect(vi.mocked(fetchSecurityIndicators).mock.calls[0][1]?.aborted).toBe(true)
    await act(async()=>{if(outcome==='success')old.resolve(payload('999'));else old.reject(new Error('old'))})
    expect(screen.getByText('200 CNY')).toBeInTheDocument();expect(screen.queryByRole('alert')).toBeNull()
  })
  it('ignores old security, retains matching failed snapshot and retries saved reads',async()=>{
    const old=deferred<SecurityIndicators>();vi.mocked(fetchSecurityIndicators).mockReturnValueOnce(old.promise)
    const {rerender}=render(panel());await waitFor(()=>expect(fetchSecurityIndicators).toHaveBeenCalledTimes(1))
    vi.mocked(fetchSecurityIndicators).mockResolvedValue(payload('200',2));rerender(panel(2));await screen.findByText('200 CNY')
    await act(async()=>old.resolve(payload('999')));expect(screen.queryByText('999 CNY')).toBeNull()
    vi.mocked(fetchSecurityIndicators).mockRejectedValueOnce(new Error('failed'));rerender(panel(2,1));await screen.findByRole('alert');expect(screen.getByText('200 CNY')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button',{name:'Retry'}));await waitFor(()=>expect(screen.queryByRole('alert')).toBeNull())
  })
  it('labels partial holdings denominator and missing positions by name',async()=>{
    vi.mocked(fetchHoldingsIndicators).mockResolvedValue({positions:[],missing_price_security_ids:[2],valuation_complete:false,denominator:'known_valued_positions_only',metrics:[{...m,key:'concentration_hhi',unit:'dimensionless',value:'0.5'}],warnings:[]})
    render(<I18nProvider language="en"><HoldingsIndicatorsPanel securityId={1} revision={0} names={{2:'Missing fund'}}/></I18nProvider>)
    await screen.findByText(/Missing fund/);expect(screen.getByText(/Partial valuation/)).toBeInTheDocument();expect(screen.getByText('0.5')).toBeInTheDocument();expect(screen.getByText(/Weights and concentration use known valued positions only/)).toBeInTheDocument()
  })
})
