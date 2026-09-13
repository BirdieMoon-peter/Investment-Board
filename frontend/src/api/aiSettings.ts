import type { AiConnectionResult, AiSettingsDraft, AiSettingsView } from '../types/aiSettings'

export type AiSettingsErrorCode = 'invalid' | 'access' | 'destination' | 'storage' | 'authentication' | 'permission' | 'notFound' | 'rateLimit' | 'unavailable' | 'account' | 'timeout' | 'unreachable' | 'noKey' | 'content' | 'request' | 'network'
export class AiSettingsError extends Error {
  constructor(public readonly code: AiSettingsErrorCode) { super(code) }
}

// Only known, controlled backend messages may select UI copy. Never display a
// response body, rejected input, service URL or arbitrary exception message.
const providerErrors: Record<string, AiSettingsErrorCode> = {
  'AI provider authentication failed (401); check credentials or sign in again': 'authentication',
  'AI provider access denied (403); check account and model permissions': 'permission',
  'AI provider model or endpoint was not found (404); check configuration': 'notFound',
  'AI provider rate limit reached (429); retry later or check quota': 'rateLimit',
  'AI provider is temporarily unavailable (503); retry later': 'unavailable',
  'AI provider has no available authenticated account (503); sign in to the provider again': 'account',
  'AI provider request timed out; retry later': 'timeout',
  'AI provider is unreachable; check that the service is running and the connection is available': 'unreachable',
  'AI provider API key is not configured': 'noKey',
  'AI provider configuration is invalid': 'invalid',
  'AI provider returned invalid JSON': 'content',
  'AI provider returned invalid content payload': 'content',
  'AI provider returned empty text content': 'content',
  'AI provider returned invalid choices payload': 'content',
  'AI provider returned invalid message payload': 'content',
}

async function request<T>(method: string, path: string, token?: string, draft?: AiSettingsDraft, signal?: AbortSignal): Promise<T> {
  // Enumerate the editable fields so tokens, redacted metadata and stale keys
  // cannot accidentally be serialized when a caller passes a larger object.
  const body = draft ? {
    provider: draft.provider, api_url: draft.api_url, model: draft.model,
    temperature: draft.temperature, max_output_tokens: draft.max_output_tokens,
    http_timeout_seconds: draft.http_timeout_seconds, key_action: draft.key_action,
    ...(draft.key_action === 'replace' && draft.api_key?.trim() ? { api_key: draft.api_key.trim() } : {}),
  } : undefined
  let response: Response
  try {
    response = await fetch(path, {
      method, cache: 'no-store', signal,
      headers: { 'Content-Type': 'application/json', ...(token ? { 'X-AI-Settings-Token': token } : {}) },
      ...(body ? { body: JSON.stringify(body) } : {}),
    })
  } catch (error) {
    if (signal?.aborted || (error instanceof DOMException && error.name === 'AbortError')) throw error
    throw new AiSettingsError('network')
  }
  if (!response.ok) {
    let detail: unknown
    try { detail = ((await response.json()) as { detail?: unknown })?.detail } catch { /* use controlled fallback */ }
    const byStatus: Record<number, AiSettingsErrorCode> = { 422: 'invalid', 403: 'access', 409: 'destination', 503: 'storage' }
    const providerCode = typeof detail === 'string' && Object.prototype.hasOwnProperty.call(providerErrors, detail) ? providerErrors[detail] : 'request'
    throw new AiSettingsError(byStatus[response.status] ?? (response.status === 502 ? providerCode : 'request'))
  }
  try { return await response.json() as T } catch { throw new AiSettingsError('request') }
}

export function fetchAiSettings(signal?: AbortSignal): Promise<AiSettingsView> {
  return request('GET', '/api/ai/settings', undefined, undefined, signal)
}
export function saveAiSettings(draft: AiSettingsDraft, token: string, signal?: AbortSignal): Promise<AiSettingsView> {
  return request('PUT', '/api/ai/settings', token, draft, signal)
}
export function resetAiSettings(token: string, signal?: AbortSignal): Promise<AiSettingsView> {
  return request('DELETE', '/api/ai/settings', token, undefined, signal)
}
export function testAiSettings(draft: AiSettingsDraft, token: string, signal?: AbortSignal): Promise<AiConnectionResult> {
  return request('POST', '/api/ai/settings/test', token, draft, signal)
}
