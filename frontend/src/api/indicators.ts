import type { HoldingsIndicators, SecurityIndicators } from '../types/indicators'
export class IndicatorsError extends Error {
  constructor(public readonly code: 'payload' | 'network' | 'request' | 'invalid') { super(code) }
}
function fail(): never { throw new IndicatorsError('payload') }
function object(v: unknown): Record<string, unknown> {
  if (!v || typeof v !== 'object' || Array.isArray(v)) return fail()
  return v as Record<string, unknown>
}
function text(v: unknown) { if (typeof v !== 'string' || !v.length) fail() }
function integer(v: unknown, minimum = 0) { if (!Number.isSafeInteger(v) || (v as number) < minimum) fail() }
function decimal(v: unknown) {
  if (typeof v !== 'string' || !/^[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?$/.test(v)) fail()
}
function list(v: unknown, check: (v: unknown) => void): unknown[] {
  if (!Array.isArray(v)) return fail()
  v.forEach(check); return v
}
function nullable(v: unknown) { if (v !== null) text(v) }
function metrics(v: unknown) {
  const keys = new Set()
  list(v, v => {
    const o = object(v)
    ;['key', 'label', 'formula', 'formula_version', 'window', 'unit', 'price_basis'].forEach(k => text(o[k]))
    if (keys.has(o.key)) fail(); keys.add(o.key)
    if (o.status === 'ready') decimal(o.value)
    else if (o.status !== 'unavailable' || o.value !== null) fail()
    nullable(o.as_of); integer(o.sample_count)
    list(o.input_refs, object); list(o.warnings, text)
  })
}
export function validateSecurityIndicators(v: unknown, securityId: number): SecurityIndicators {
  const o = object(v); integer(o.security_id, 1)
  if (o.security_id !== securityId) fail()
  text(o.instrument_type); metrics(o.metrics); object(o.data_context)
  return v as SecurityIndicators
}
export function validateHoldingsIndicators(v: unknown): HoldingsIndicators {
  const o = object(v), holdingIds = new Set(), securityIds = new Set<number>()
  const unavailableIds = new Set<number>()
  list(o.positions, v => {
    const p = object(v); integer(p.holding_id, 1); integer(p.security_id, 1)
    if (holdingIds.has(p.holding_id) || securityIds.has(p.security_id as number)) fail()
    holdingIds.add(p.holding_id); securityIds.add(p.security_id as number)
    decimal(p.quantity); decimal(p.average_cost); nullable(p.valuation_at); metrics(p.metrics); list(p.warnings, text)
    const marketValue = (p.metrics as {key: string; status: string}[]).find(m => m.key === 'market_value')
    if (!marketValue) fail()
    if (marketValue.status === 'unavailable') unavailableIds.add(p.security_id as number)
    if ((marketValue.status === 'ready') !== (p.valuation_at !== null)) fail()
  })
  const missing = list(o.missing_price_security_ids, v => integer(v, 1)) as number[]
  if (new Set(missing).size !== missing.length || missing.length !== unavailableIds.size || missing.some(id => !unavailableIds.has(id))) fail()
  if (typeof o.valuation_complete !== 'boolean' || o.valuation_complete !== (missing.length === 0) || o.denominator !== 'known_valued_positions_only') fail()
  metrics(o.metrics); list(o.warnings, text)
  return v as HoldingsIndicators
}
async function request<T>(path: string, validate: (v: unknown) => T, signal?: AbortSignal): Promise<T> {
  let response: Response
  try { response = await fetch(`/api/indicators/${path}`, {method: 'GET', cache: 'no-store', signal}) }
  catch (error) { if (signal?.aborted || (error instanceof DOMException && error.name === 'AbortError')) throw error; throw new IndicatorsError('network') }
  if (!response.ok) throw new IndicatorsError('request')
  let v: unknown
  try { v = await response.json() } catch { throw new IndicatorsError('payload') }
  return validate(v)
}
export function fetchSecurityIndicators(id: number, signal?: AbortSignal) {
  if (!Number.isSafeInteger(id) || id <= 0) throw new IndicatorsError('invalid')
  return request(`securities/${id}`, v => validateSecurityIndicators(v, id), signal)
}
export function fetchHoldingsIndicators(signal?: AbortSignal) { return request('holdings', validateHoldingsIndicators, signal) }
