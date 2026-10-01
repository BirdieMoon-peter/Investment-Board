import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  DataCenterError,
  feePercentage,
  fetchDataSources,
  fetchSecurityData,
  saveDataSource,
  saveSecurityMetadata,
  syncSecurityData,
} from './dataCenter'
import { catalogFixture, jsonResponse, securityFixture } from '../test/dataCenterFixtures'
afterEach(() => vi.unstubAllGlobals())
describe('data center contract clients', () => {
  it('reads saved sources with AbortSignal and no mutation', async () => {
    const fetch = vi.fn().mockResolvedValue(jsonResponse({ sources: catalogFixture }))
    vi.stubGlobal('fetch', fetch)
    const signal = new AbortController().signal
    expect(await fetchDataSources(signal)).toHaveLength(5)
    expect(fetch).toHaveBeenCalledWith(
      '/api/data/sources',
      expect.objectContaining({ method: 'GET', signal, cache: 'no-store' }),
    )
  })
  it('posts exactly one category and explicit price source', async () => {
    const data = securityFixture()
    const fetch = vi.fn().mockResolvedValue(
      jsonResponse({
        security_id: 1,
        category_outcomes: {
          price_history: { outcome: 'partial', received: 2, written: 1 },
        },
        warnings: [],
        data,
      }),
    )
    vi.stubGlobal('fetch', fetch)
    await syncSecurityData(1, 'price_history', 'sina')
    expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual({
      categories: ['price_history'],
      price_source: 'sina',
    })
    expect(() => syncSecurityData(1, 'news', 'sina')).toThrow(DataCenterError)
  })
  it('sends only allowed metadata and enabled fields', async () => {
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(catalogFixture[0]))
      .mockResolvedValueOnce(jsonResponse(securityFixture()))
    vi.stubGlobal('fetch', fetch)
    await saveDataSource('eastmoney', false)
    await saveSecurityMetadata(1, {
      instrument_type: 'etf',
      benchmark_code: 'SH:000300',
      benchmark_name: 'CSI300',
      manager: 'must not send',
    } as never)
    expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual({ enabled: false })
    expect(JSON.parse(fetch.mock.calls[1][1].body)).toEqual({
      instrument_type: 'etf',
      benchmark_code: 'SH:000300',
      benchmark_name: 'CSI300',
    })
  })
  it.each([
    {},
    { sources: [{ vendor_key: 'sina' }] },
    { sources: [{ ...catalogFixture[0], enabled: 'yes' }] },
  ])('rejects invalid catalog payload %j', async (payload) => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(payload)))
    await expect(fetchDataSources()).rejects.toMatchObject({ code: 'payload' })
  })
  it('rejects wrong-security response and invalid decimal/nav enums', async () => {
    const data = securityFixture(2)
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(data)))
    await expect(fetchSecurityData(1)).rejects.toMatchObject({ code: 'payload' })
    data.security.id = 1
    data.metadata.management_fee = 'NaN'
    await expect(fetchSecurityData(1)).rejects.toMatchObject({ code: 'payload' })
  })
  it('uses controlled HTTP/network/JSON errors without leaking response details', async () => {
    const fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
      json: async () => ({ detail: 'secret credential' }),
    })
    vi.stubGlobal('fetch', fetch)
    await expect(fetchDataSources()).rejects.toMatchObject({ message: 'unavailable' })
    fetch.mockRejectedValueOnce(new Error('secret'))
    await expect(fetchSecurityData(1)).rejects.toMatchObject({ message: 'network' })
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => {
        throw new Error('secret')
      },
    })
    await expect(fetchDataSources()).rejects.toMatchObject({ code: 'payload' })
  })
  it('preserves cancellation', async () => {
    const c = new AbortController()
    c.abort()
    const error = new DOMException('aborted', 'AbortError')
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(error))
    await expect(fetchDataSources(c.signal)).rejects.toBe(error)
  })
  it.each([
    ['0.005', '0.5%'],
    ['0.001', '0.1%'],
    ['0', '0%'],
    ['1E-8', '0.000001%'],
    ['0.000000000000000000000001', '0.0000000000000000000001%'],
    ['1E-325', '0.' + '0'.repeat(322) + '1%'],
    [null, '—'],
  ])('formats exact fee fraction %s once', (value, expected) => {
    expect(feePercentage(value)).toBe(expected)
  })
  it('preserves decimal strings above binary-number range and below binary-number precision', async () => {
    const data = securityFixture()
    data.metadata.management_fee = '1E-325'
    data.metadata.fund_assets = '1E+400'
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(data)))
    const result = await fetchSecurityData(1)
    expect(result.metadata.management_fee).toBe('1E-325')
    expect(result.metadata.fund_assets).toBe('1E+400')
  })
  it('rejects a source update response for a different vendor', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(catalogFixture[1])))
    await expect(saveDataSource('eastmoney', false)).rejects.toMatchObject({
      code: 'payload',
    })
  })
  it.each([{}, { news: { outcome: 'succeeded' } }])(
    'rejects missing or unrelated outcome for the requested category',
    async (category_outcomes) => {
      vi.stubGlobal(
        'fetch',
        vi
          .fn()
          .mockResolvedValue(
            jsonResponse({
              security_id: 1,
              category_outcomes,
              warnings: [],
              data: securityFixture(),
            }),
          ),
      )
      await expect(syncSecurityData(1, 'price_history')).rejects.toMatchObject({
        code: 'payload',
      })
    },
  )
})
