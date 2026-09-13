import { afterEach, describe, expect, it, vi } from 'vitest'
import { fetchAiSettings, resetAiSettings, saveAiSettings, testAiSettings } from './aiSettings'
import type { AiSettingsDraft, AiSettingsView } from '../types/aiSettings'

const values = { provider: 'kimi', api_url: 'https://example.test/v1', model: 'custom-model', temperature: 0.2, max_output_tokens: 4096, http_timeout_seconds: 90 }
const view: AiSettingsView = { ...values, source: 'environment', api_key_configured: true, configuration_error: null, mutation_token: 'fixture-token' }
const draft: AiSettingsDraft = { ...values, key_action: 'keep' }
const response = (body: unknown, status = 200) => ({ ok: status < 400, status, json: async () => body })

afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks() })

describe('AI settings client', () => {
  it('reads without cache and forwards cancellation without browser persistence', async () => {
    const fetch = vi.fn().mockResolvedValue(response(view)); vi.stubGlobal('fetch', fetch)
    const storage = vi.spyOn(Storage.prototype, 'setItem')
    const signal = new AbortController().signal
    expect(await fetchAiSettings(signal)).toEqual(view)
    expect(fetch).toHaveBeenCalledWith('/api/ai/settings', expect.objectContaining({ method: 'GET', cache: 'no-store', signal }))
    expect(storage).not.toHaveBeenCalled()
  })
  it.each(['keep', 'clear'] as const)('omits credentials on %s and puts the token only in its header', async (key_action) => {
    const fetch = vi.fn().mockResolvedValue(response(view)); vi.stubGlobal('fetch', fetch)
    await saveAiSettings({ ...draft, key_action, api_key: 'must-not-send' }, 'fixture-token')
    expect(fetch).toHaveBeenCalledWith('/api/ai/settings', expect.objectContaining({ method: 'PUT', cache: 'no-store', headers: { 'Content-Type': 'application/json', 'X-AI-Settings-Token': 'fixture-token' }, body: JSON.stringify({ ...draft, key_action }) }))
  })
  it('sends a replacement key and tests the unsaved draft using the same protected contract', async () => {
    const fetch = vi.fn().mockResolvedValue(response({ ok: true, elapsed_ms: 12 })); vi.stubGlobal('fetch', fetch)
    const signal = new AbortController().signal
    const replacement = { ...draft, model: 'unsaved', key_action: 'replace' as const, api_key: 'fixture-key' }
    expect(await testAiSettings(replacement, 'fixture-token', signal)).toEqual({ ok: true, elapsed_ms: 12 })
    expect(fetch).toHaveBeenCalledWith('/api/ai/settings/test', expect.objectContaining({ method: 'POST', cache: 'no-store', signal, body: JSON.stringify(replacement), headers: expect.objectContaining({ 'X-AI-Settings-Token': 'fixture-token' }) }))
  })
  it('deletes only the settings override with the token and no request body', async () => {
    const fetch = vi.fn().mockResolvedValue(response(view)); vi.stubGlobal('fetch', fetch)
    await resetAiSettings('fixture-token')
    expect(fetch).toHaveBeenCalledWith('/api/ai/settings', expect.objectContaining({ method: 'DELETE', cache: 'no-store', headers: expect.objectContaining({ 'X-AI-Settings-Token': 'fixture-token' }) }))
    expect(fetch.mock.calls[0][1].body).toBeUndefined()
  })
  it.each([
    [422, 'untrusted secret', 'invalid'], [403, 'anything', 'access'], [409, 'anything', 'destination'], [503, 'anything', 'storage'],
    [502, 'AI provider authentication failed (401); check credentials or sign in again', 'authentication'],
    [502, 'AI provider access denied (403); check account and model permissions', 'permission'],
    [502, 'AI provider model or endpoint was not found (404); check configuration', 'notFound'],
    [502, 'AI provider rate limit reached (429); retry later or check quota', 'rateLimit'],
    [502, 'AI provider is temporarily unavailable (503); retry later', 'unavailable'],
    [502, 'AI provider has no available authenticated account (503); sign in to the provider again', 'account'],
    [502, 'AI provider request timed out; retry later', 'timeout'],
    [502, 'AI provider is unreachable; check that the service is running and the connection is available', 'unreachable'],
    [502, 'AI provider API key is not configured', 'noKey'],
    [502, 'AI provider returned empty text content', 'content'],
    [502, 'AI provider returned invalid JSON', 'content'],
    [502, 'unexpected response fixture-secret', 'request'], [500, 'fixture-secret', 'request'],
  ])('maps status %i to %s without exposing arbitrary details', async (status, detail, code) => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({ detail }, status)))
    await expect(testAiSettings(draft, 'fixture-token')).rejects.toMatchObject({ code })
    await expect(fetchAiSettings()).rejects.not.toThrow('fixture-secret')
  })
  it('maps network and unreadable errors to controlled messages', async () => {
    const fetch = vi.fn().mockRejectedValueOnce(new Error('https://secret-url.test/key')).mockResolvedValueOnce({ ok: false, status: 500, json: async () => { throw new Error('raw') } })
    vi.stubGlobal('fetch', fetch)
    await expect(fetchAiSettings()).rejects.toMatchObject({ code: 'network' })
    await expect(fetchAiSettings()).rejects.toMatchObject({ code: 'request' })
  })
})
