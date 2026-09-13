import { StrictMode } from 'react'
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AiSettingsPanel } from './AiSettingsPanel'
import { I18nProvider } from '../i18n'
import { AiSettingsError, fetchAiSettings, resetAiSettings, saveAiSettings, testAiSettings } from '../api/aiSettings'
import type { AiSettingsView } from '../types/aiSettings'

vi.mock('../api/aiSettings', async (importOriginal) => {
  const original = await importOriginal<typeof import('../api/aiSettings')>()
  return { ...original, fetchAiSettings: vi.fn(), saveAiSettings: vi.fn(), resetAiSettings: vi.fn(), testAiSettings: vi.fn() }
})
const initial: AiSettingsView = { provider: 'openai_compatible', api_url: 'https://example.test/v1', model: 'initial-model', temperature: 0.2, max_output_tokens: 4096, http_timeout_seconds: 90, source: 'environment', api_key_configured: true, configuration_error: null, mutation_token: 'fixture-token' }
const basePayload = { provider: initial.provider, api_url: initial.api_url, model: initial.model, temperature: initial.temperature, max_output_tokens: initial.max_output_tokens, http_timeout_seconds: initial.http_timeout_seconds, key_action: 'keep' }
function deferred<T>() { let resolve!: (value: T) => void; let reject!: (reason: unknown) => void; const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no }); return { promise, resolve, reject } }
const tree = (language: 'en' | 'zh' = 'en') => <I18nProvider language={language}><AiSettingsPanel /></I18nProvider>
async function ready() { await screen.findByLabelText('Model') }
function change(label: string, value: string) { fireEvent.change(screen.getByLabelText(label), { target: { value } }) }
function click(name: string) { fireEvent.click(screen.getByRole('button', { name })) }
function keyAction(value: string) { change('API key action', value) }
beforeEach(() => {
  vi.mocked(fetchAiSettings).mockReset().mockResolvedValue({ ...initial })
  vi.mocked(saveAiSettings).mockReset().mockResolvedValue({ ...initial, source: 'web' })
  vi.mocked(resetAiSettings).mockReset().mockResolvedValue({ ...initial })
  vi.mocked(testAiSettings).mockReset().mockResolvedValue({ ok: true, elapsed_ms: 12 })
})
afterEach(() => vi.restoreAllMocks())

describe('AI settings panel', () => {
  it('loads current values and provider alias with masked empty replacement input and source', async () => {
    render(tree()); await ready()
    expect(screen.getByLabelText('Provider / protocol')).toHaveValue('openai_compatible')
    expect(screen.getByLabelText('Model')).toHaveValue('initial-model')
    expect(screen.getByLabelText('Replacement API key')).toHaveAttribute('type', 'password')
    expect(screen.getByLabelText('Replacement API key')).toHaveValue('')
    expect(screen.getByText('API key configured')).toBeInTheDocument()
    expect(screen.getByText('Environment configuration')).toBeInTheDocument()
    expect(screen.getByText(/only a short fixed message/i)).toBeInTheDocument()
  })
  it('allows defaults without a key to be saved and retains no secret in browser storage', async () => {
    vi.mocked(fetchAiSettings).mockResolvedValue({ ...initial, source: 'default', api_key_configured: false })
    const storage = vi.spyOn(Storage.prototype, 'setItem')
    render(tree()); await ready(); click('Save AI settings')
    await screen.findByText('AI settings saved. Subsequent AI requests use this configuration.')
    expect(saveAiSettings).toHaveBeenCalledWith(basePayload, 'fixture-token', expect.any(AbortSignal))
    expect(storage).not.toHaveBeenCalled()
  })
  it('saves replacement then clears typed key and invalidates saved success on an edit', async () => {
    const storage = vi.spyOn(Storage.prototype, 'setItem')
    render(tree()); await ready(); keyAction('replace'); change('Replacement API key', 'fixture-secret'); click('Save AI settings')
    await screen.findByText('AI settings saved. Subsequent AI requests use this configuration.')
    expect(saveAiSettings).toHaveBeenCalledWith({ ...basePayload, key_action: 'replace', api_key: 'fixture-secret' }, 'fixture-token', expect.any(AbortSignal))
    expect(screen.getByLabelText('Replacement API key')).toHaveValue('')
    expect(screen.getByLabelText('API key action')).toHaveValue('keep')
    change('Model', 'new-model')
    expect(screen.queryByText('AI settings saved. Subsequent AI requests use this configuration.')).not.toBeInTheDocument()
    expect(storage).not.toHaveBeenCalled()
  })
  it('requires a nonempty replacement key and permits explicit clear', async () => {
    render(tree()); await ready(); keyAction('replace'); click('Save AI settings')
    expect(await screen.findByText('Enter a new API key, or choose to keep or clear it.')).toBeInTheDocument()
    expect(saveAiSettings).not.toHaveBeenCalled()
    keyAction('clear'); click('Save AI settings')
    await waitFor(() => expect(saveAiSettings).toHaveBeenCalledWith({ ...basePayload, key_action: 'clear' }, 'fixture-token', expect.any(AbortSignal)))
  })
  it('clears incompatible service fields and recovers from a destination conflict by saving without a key', async () => {
    vi.mocked(saveAiSettings).mockRejectedValueOnce(new AiSettingsError('destination'))
    render(tree()); await ready(); change('Provider / protocol', 'anthropic')
    expect(screen.getByLabelText('Service URL')).toHaveValue('')
    expect(screen.getByLabelText('Model')).toHaveValue('')
    change('Service URL', 'https://other.test'); change('Model', 'claude-custom'); click('Save AI settings')
    expect(await screen.findByRole('alert')).toHaveTextContent('The current key cannot be reused for this service.')
    expect(saveAiSettings).toHaveBeenCalledWith(expect.objectContaining({ key_action: 'keep' }), 'fixture-token', expect.any(AbortSignal))
    keyAction('clear'); click('Save AI settings')
    await waitFor(() => expect(saveAiSettings).toHaveBeenCalledWith(expect.objectContaining({ provider: 'anthropic', api_url: 'https://other.test', model: 'claude-custom', key_action: 'clear' }), 'fixture-token', expect.any(AbortSignal)))
  })
  it('handles an authoritative URL-only destination conflict and permits replacement', async () => {
    vi.mocked(saveAiSettings).mockRejectedValueOnce(new AiSettingsError('destination'))
    render(tree()); await ready(); change('Service URL', 'https://new.test/v1'); click('Save AI settings')
    expect(await screen.findByRole('alert')).toHaveTextContent('The current key cannot be reused for this service.')
    keyAction('replace'); change('Replacement API key', 'new-fixture'); click('Save AI settings')
    await waitFor(() => expect(saveAiSettings).toHaveBeenCalledWith(expect.objectContaining({ api_url: 'https://new.test/v1', key_action: 'replace', api_key: 'new-fixture' }), 'fixture-token', expect.any(AbortSignal)))
  })
  it('permits retaining the key for equivalent resolved endpoints and same-protocol aliases', async () => {
    render(tree()); await ready(); change('Provider / protocol', 'openai')
    change('Service URL', 'https://example.test/v1/chat/completions'); change('Model', 'custom-model'); click('Save AI settings')
    await waitFor(() => expect(saveAiSettings).toHaveBeenCalledWith(expect.objectContaining({ provider: 'openai', key_action: 'keep' }), 'fixture-token', expect.any(AbortSignal)))
  })
  it.each([
    ['openai', 'https://example.test/v1/.'],
    ['openai_compatible', 'https://example.test/v1/child/..'],
    ['openai', 'https://example.test/v1/chat/./completions'],
    ['kimi', 'https://example.test/v1/messages/.'],
  ])('retains the key for the equivalent %s dot-segment destination %s', async (provider, api_url) => {
    vi.mocked(fetchAiSettings).mockResolvedValue({ ...initial, provider })
    render(tree()); await ready(); change('Service URL', api_url); click('Save AI settings')
    await waitFor(() => expect(saveAiSettings).toHaveBeenCalledWith(expect.objectContaining({ provider, api_url, key_action: 'keep' }), 'fixture-token', expect.any(AbortSignal)))
  })
  it('preserves encoded dot segments and shows an authoritative test conflict without saving', async () => {
    vi.mocked(testAiSettings).mockRejectedValueOnce(new AiSettingsError('destination'))
    render(tree()); await ready(); change('Service URL', 'https://example.test/%2e%2e/v1')
    expect(screen.getByText('The service address or provider was edited. A different destination requires a new key or clearing the current key. Equivalent addresses can keep it; the server checks before saving or testing.')).toBeInTheDocument()
    click('Test connection')
    expect(await screen.findByRole('alert')).toHaveTextContent('The current key cannot be reused for this service.')
    expect(testAiSettings).toHaveBeenCalledWith(expect.objectContaining({ api_url: 'https://example.test/%2e%2e/v1', key_action: 'keep' }), 'fixture-token', expect.any(AbortSignal))
    expect(saveAiSettings).not.toHaveBeenCalled()
    expect(screen.getByLabelText('Service URL')).toHaveValue('https://example.test/%2e%2e/v1')
  })
  it.each(['anthropic', 'dashscope_anthropic', 'kimi'])('retains an Anthropic key for the %s alias at the same resolved endpoint', async (provider) => {
    vi.mocked(fetchAiSettings).mockResolvedValue({ ...initial, provider: 'anthropic' })
    render(tree()); await ready(); change('Provider / protocol', provider)
    change('Service URL', 'https://example.test/v1/messages'); change('Model', 'anthropic-model'); click('Save AI settings')
    await waitFor(() => expect(saveAiSettings).toHaveBeenCalledWith(expect.objectContaining({ provider, key_action: 'keep' }), 'fixture-token', expect.any(AbortSignal)))
    expect(screen.getByRole('option', { name: 'Kimi (Anthropic-compatible)' })).toBeInTheDocument()
  })
  it('handles a protocol conflict when moving from OpenAI to Kimi on the same host', async () => {
    vi.mocked(saveAiSettings).mockRejectedValueOnce(new AiSettingsError('destination'))
    render(tree()); await ready(); change('Provider / protocol', 'kimi')
    change('Service URL', initial.api_url); change('Model', initial.model); click('Save AI settings')
    expect(await screen.findByRole('alert')).toHaveTextContent('The current key cannot be reused for this service.')
    expect(saveAiSettings).toHaveBeenCalledWith(expect.objectContaining({ provider: 'kimi', key_action: 'keep' }), 'fixture-token', expect.any(AbortSignal))
  })
  it('marks edited values as unsaved and clears the hint when saved or restored', async () => {
    render(tree()); await ready()
    expect(screen.queryByText('Unsaved changes. Save to apply this draft to subsequent AI requests.')).not.toBeInTheDocument()
    change('Model', 'edited-model')
    expect(screen.getByText('Unsaved changes. Save to apply this draft to subsequent AI requests.')).toBeInTheDocument()
    click('Test connection')
    await screen.findByText('Connection successful (12 ms). This test did not change the saved configuration.')
    expect(screen.getByText('Unsaved changes. Save to apply this draft to subsequent AI requests.')).toBeInTheDocument()
    click('Save AI settings')
    await screen.findByText('AI settings saved. Subsequent AI requests use this configuration.')
    expect(screen.queryByText('Unsaved changes. Save to apply this draft to subsequent AI requests.')).not.toBeInTheDocument()
    change('Model', 'another-model'); click('Restore environment configuration'); click('Confirm restore')
    await screen.findByText('Web override removed. Environment or default configuration is now active.')
    expect(screen.queryByText('Unsaved changes. Save to apply this draft to subsequent AI requests.')).not.toBeInTheDocument()
  })
  it('marks key actions as unsaved and translates the hint without losing the draft', async () => {
    const ui = render(tree()); await ready(); keyAction('clear')
    expect(screen.getByText('Unsaved changes. Save to apply this draft to subsequent AI requests.')).toBeInTheDocument()
    keyAction('keep')
    expect(screen.queryByText('Unsaved changes. Save to apply this draft to subsequent AI requests.')).not.toBeInTheDocument()
    keyAction('replace'); change('Replacement API key', 'fixture-secret'); ui.rerender(tree('zh'))
    expect(screen.getByText('有未保存的更改。保存后，后续 AI 请求才会使用当前草稿。')).toBeInTheDocument()
    expect(screen.getByLabelText('新 API 密钥')).toHaveValue('fixture-secret')
    expect(fetchAiSettings).toHaveBeenCalledTimes(1)
  })
  it('tests the unsaved draft without persistence and clears result when edited', async () => {
    render(tree()); await ready(); change('Model', 'unsaved-model'); click('Test connection')
    await screen.findByText(/Connection successful/)
    expect(testAiSettings).toHaveBeenCalledWith({ ...basePayload, model: 'unsaved-model' }, 'fixture-token', expect.any(AbortSignal))
    expect(saveAiSettings).not.toHaveBeenCalled()
    expect(screen.getByText('Environment configuration')).toBeInTheDocument()
    change('Model', 'later'); expect(screen.queryByText(/Connection successful/)).not.toBeInTheDocument()
  })
  it('keeps failed save edits and replacement key for retry with translated errors', async () => {
    vi.mocked(saveAiSettings).mockRejectedValueOnce(new AiSettingsError('storage'))
    render(tree()); await ready(); keyAction('replace'); change('Replacement API key', 'fixture-secret'); click('Save AI settings')
    await screen.findByText('The local settings file could not be read or written. Check folder permissions and retry, or restore environment configuration.')
    expect(screen.getByLabelText('Replacement API key')).toHaveValue('fixture-secret')
    click('Save AI settings'); await screen.findByText(/AI settings saved/)
    expect(saveAiSettings).toHaveBeenCalledTimes(2)
  })
  it('requires inline reset confirmation, permits cancellation, then reloads returned fallback', async () => {
    render(tree()); await ready(); change('Model', 'unsaved-model'); click('Restore environment configuration')
    expect(resetAiSettings).not.toHaveBeenCalled()
    expect(screen.getByText(/Only the web AI override/)).toBeInTheDocument()
    click('Cancel'); expect(screen.queryByRole('button', { name: 'Confirm restore' })).not.toBeInTheDocument()
    expect(screen.getByLabelText('Model')).toHaveValue('unsaved-model')
    click('Restore environment configuration'); click('Confirm restore')
    await screen.findByText('Web override removed. Environment or default configuration is now active.')
    expect(resetAiSettings).toHaveBeenCalledWith('fixture-token', expect.any(AbortSignal))
    expect(screen.getByLabelText('Model')).toHaveValue('initial-model')
  })
  it('retries load failures and reloads after reopening', async () => {
    vi.mocked(fetchAiSettings).mockRejectedValueOnce(new AiSettingsError('network'))
    const first = render(tree()); await screen.findByRole('button', { name: 'Retry loading' }); click('Retry loading'); await ready()
    change('Model', 'discarded'); first.unmount()
    vi.mocked(fetchAiSettings).mockResolvedValue({ ...initial, model: 'fresh' })
    render(tree()); await ready(); expect(screen.getByLabelText('Model')).toHaveValue('fresh')
    expect(fetchAiSettings).toHaveBeenCalledTimes(3)
  })
  it('offers clear/replace/reset recovery for corrupt configuration without exposing raw errors', async () => {
    vi.mocked(fetchAiSettings).mockResolvedValue({ ...initial, configuration_error: 'corrupt fixture-secret', api_key_configured: false })
    render(tree()); await ready()
    expect(screen.getByText(/Saved settings need repair/)).toBeInTheDocument()
    expect(screen.queryByText(/fixture-secret/)).not.toBeInTheDocument()
    click('Save AI settings'); expect(saveAiSettings).not.toHaveBeenCalled()
    keyAction('clear'); click('Save AI settings'); await waitFor(() => expect(saveAiSettings).toHaveBeenCalled())
  })
  it('shows safe URL recovery guidance and offers an unsupported legacy provider fallback', async () => {
    vi.mocked(fetchAiSettings).mockResolvedValue({ ...initial, provider: 'legacy', configuration_error: 'The saved environment API address contains hidden or invalid URL parts; re-enter a clean API address before saving' })
    render(tree()); await ready()
    expect(screen.getByLabelText('Provider / protocol')).toHaveValue('legacy')
    expect(screen.getByRole('option', { name: /Unsupported saved provider/ })).toBeInTheDocument()
    expect(screen.getByText(/Re-enter a safe service URL/)).toBeInTheDocument()
    change('Provider / protocol', 'openai'); expect(screen.getByLabelText('Service URL')).toHaveValue('')
  })
  it.each([
    ['Temperature', '-1'], ['Temperature', '2.1'], ['Temperature', ''],
    ['Maximum output tokens', '1.5'], ['Maximum output tokens', '131073'],
    ['Request timeout (seconds)', '0'], ['Request timeout (seconds)', '601'],
    ['Service URL', 'https://user:secret@example.test'], ['Service URL', 'https://example.test/?key=secret'], ['Service URL', 'http://public.test'], ['Model', ''],
  ])('rejects invalid %s locally', async (label, value) => {
    render(tree()); await ready(); change(label, value); click('Save AI settings')
    expect(saveAiSettings).not.toHaveBeenCalled()
    expect(await screen.findByRole('alert')).toBeInTheDocument()
  })
  it('guards overlapping operations and ignores late load replies after StrictMode cleanup', async () => {
    const stale = deferred<AiSettingsView>(); const current = deferred<AiSettingsView>(); const pending = deferred<{ ok: true; elapsed_ms: number }>()
    vi.mocked(fetchAiSettings).mockReturnValueOnce(stale.promise).mockReturnValueOnce(current.promise)
    vi.mocked(testAiSettings).mockReturnValue(pending.promise)
    render(<StrictMode>{tree()}</StrictMode>)
    await act(async () => current.resolve(initial)); await ready(); change('Model', 'draft')
    await act(async () => stale.resolve({ ...initial, model: 'stale' }))
    expect(screen.getByLabelText('Model')).toHaveValue('draft')
    click('Test connection'); click('Save AI settings'); click('Restore environment configuration')
    expect(screen.getByLabelText('Model')).toBeDisabled()
    expect(testAiSettings).toHaveBeenCalledTimes(1); expect(saveAiSettings).not.toHaveBeenCalled(); expect(resetAiSettings).not.toHaveBeenCalled()
    await act(async () => pending.resolve({ ok: true, elapsed_ms: 12 }))
    await screen.findByText(/Connection successful/)
  })
  it('aborts on unmount and ignores old mutation replies after reopening', async () => {
    const pending = deferred<AiSettingsView>(); vi.mocked(saveAiSettings).mockReturnValue(pending.promise)
    const first = render(tree()); await ready(); click('Save AI settings')
    const signal = vi.mocked(saveAiSettings).mock.calls[0][2]!
    first.unmount(); expect(signal.aborted).toBe(true)
    render(tree()); await ready()
    await act(async () => pending.resolve({ ...initial, model: 'stale' }))
    expect(screen.getByLabelText('Model')).toHaveValue('initial-model')
    expect(screen.queryByText(/AI settings saved/)).not.toBeInTheDocument()
  })
  it('preserves unsaved values on language change and translates a pending result in the new language', async () => {
    const pending = deferred<{ ok: true; elapsed_ms: number }>(); vi.mocked(testAiSettings).mockReturnValue(pending.promise)
    const ui = render(tree()); await ready(); change('Model', 'draft'); click('Test connection')
    ui.rerender(tree('zh'))
    expect(fetchAiSettings).toHaveBeenCalledTimes(1)
    expect(screen.getByLabelText('模型名称')).toHaveValue('draft')
    await act(async () => pending.resolve({ ok: true, elapsed_ms: 12 }))
    expect(await screen.findByText(/连接成功/)).toBeInTheDocument()
    change('模型名称', '修改'); expect(screen.queryByText(/连接成功/)).not.toBeInTheDocument()
  })
  it('translates controlled test errors and never displays arbitrary rejected text', async () => {
    vi.mocked(testAiSettings).mockRejectedValueOnce(new AiSettingsError('authentication')).mockRejectedValueOnce(new Error('fixture-secret'))
    const ui = render(tree()); await ready(); click('Test connection'); await screen.findByText('Authentication failed (401). Replace the key or sign in to your provider again.')
    ui.rerender(tree('zh')); expect(await screen.findByText(/认证失败（401）/)).toBeInTheDocument()
    ui.rerender(tree()); click('Test connection'); await screen.findByText('The request failed. Check the service and retry.')
    expect(screen.queryByText(/fixture-secret/)).not.toBeInTheDocument()
  })
})
