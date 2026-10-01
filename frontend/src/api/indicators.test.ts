import {afterEach, describe, expect, it, vi} from 'vitest'
import {fetchSecurityIndicators,fetchHoldingsIndicators,validateSecurityIndicators,validateHoldingsIndicators} from './indicators'
export const metric = {key:'price_return_20',label:'收益',value:'1e-10000',status:'ready',formula:'P_last / P_first - 1',formula_version:'1',window:'last_21_observations',unit:'fraction',as_of:'2026-10-01',sample_count:21,price_basis:'forward_adjusted',input_refs:[{source_key:'eastmoney_kline'}],warnings:['calendar_unverified']}
const security = {security_id:1,instrument_type:'stock',metrics:[metric],data_context:{calendar:{verified:false}}}
const position = {holding_id:1,security_id:1,quantity:'10',average_cost:'2.01',valuation_at:null,metrics:[{...metric,key:'market_value',status:'unavailable',value:null}],warnings:['missing']}
const holdings = {positions:[position],missing_price_security_ids:[1],valuation_complete:false,denominator:'known_valued_positions_only',metrics:[],warnings:[]}
afterEach(() => vi.unstubAllGlobals())
describe('saved indicators contract', () => {
  it('preserves exact scientific values and explicitly unavailable nulls', () => {
    expect(validateSecurityIndicators(security,1).metrics[0].value).toBe('1e-10000')
    expect(validateHoldingsIndicators(holdings).positions[0].metrics[0].value).toBeNull()
  })
  it.each([NaN,Infinity,2,'NaN','Infinity','1.2.3',''])('rejects invalid decimal %s', value => expect(() => validateSecurityIndicators({...security,metrics:[{...metric,value}]},1)).toThrow('payload'))
  it.each(['formula','formula_version','window','unit','as_of','sample_count','price_basis','input_refs','warnings'])('requires %s', key => {
    const broken:Record<string,unknown> = {...metric};delete broken[key]
    expect(() => validateSecurityIndicators({...security,metrics:[broken]},1)).toThrow('payload')
  })
  it('rejects identity, duplicate metrics and invalid ready/unavailable pairings', () => {
    expect(() => validateSecurityIndicators(security,2)).toThrow('payload')
    for (const m of [{...metric,status:'unavailable'}, {...metric,value:null},{...metric,sample_count:-1}]) expect(() => validateSecurityIndicators({...security,metrics:[m]},1)).toThrow('payload')
    expect(() => validateSecurityIndicators({...security,metrics:[metric,metric]},1)).toThrow('payload')
  })
  it('rejects incomplete ownership and false completeness of valuations', () => {
    for (const change of [{valuation_complete:true},{denominator:'all_positions'}, {missing_price_security_ids:[]},{missing_price_security_ids:[2]},{positions:[position,position]}]) expect(() => validateHoldingsIndicators({...holdings,...change})).toThrow('payload')
  })
  it('uses saved-only GET and forwards cancellation', async () => {
    const fetch = vi.fn().mockResolvedValue({ok:true,json:async()=>security});vi.stubGlobal('fetch',fetch)
    const c = new AbortController();await fetchSecurityIndicators(1,c.signal)
    expect(fetch).toHaveBeenCalledWith('/api/indicators/securities/1',{method:'GET',cache:'no-store',signal:c.signal})
    fetch.mockResolvedValue({ok:true,json:async()=>holdings});await fetchHoldingsIndicators(c.signal)
    expect(fetch).toHaveBeenLastCalledWith('/api/indicators/holdings',{method:'GET',cache:'no-store',signal:c.signal})
  })
  it('reports HTTP, payload and network failures', async () => {
    const fetch=vi.fn().mockResolvedValue({ok:false});vi.stubGlobal('fetch',fetch)
    await expect(fetchSecurityIndicators(1)).rejects.toThrow('request')
    fetch.mockResolvedValue({ok:true,json:async()=>({...security,security_id:2})});await expect(fetchSecurityIndicators(1)).rejects.toThrow('payload')
    fetch.mockRejectedValue(new Error('offline'));await expect(fetchSecurityIndicators(1)).rejects.toThrow('network')
  })
})
