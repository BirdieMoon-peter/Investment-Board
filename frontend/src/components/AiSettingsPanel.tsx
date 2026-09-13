import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
} from 'react'
import { Button, Input, Select } from '@fluentui/react-components'
import {
  AiSettingsError,
  fetchAiSettings,
  resetAiSettings,
  saveAiSettings,
  testAiSettings,
} from '../api/aiSettings'
import { useI18n } from '../i18n'
import type {
  AiKeyAction,
  AiProvider,
  AiSettingsDraft,
  AiSettingsView,
} from '../types/aiSettings'

const providers: AiProvider[] = [
  'anthropic',
  'openai',
  'openai_compatible',
  'dashscope_anthropic',
  'kimi',
]
const providerLabels: Record<AiProvider, string> = {
  anthropic: 'Anthropic',
  openai: 'OpenAI',
  openai_compatible: 'OpenAI-compatible',
  dashscope_anthropic: 'DashScope (Anthropic)',
  kimi: 'Kimi (Anthropic-compatible)',
}
interface FormValues {
  provider: string
  api_url: string
  model: string
  temperature: string
  max_output_tokens: string
  http_timeout_seconds: string
  key_action: AiKeyAction
  api_key: string
}
type Operation = 'loading' | 'saving' | 'testing' | 'resetting'
type Feedback = {
  key: string
  tone: 'success' | 'error'
  params?: Record<string, string | number>
}

function toForm(settings: AiSettingsView): FormValues {
  return {
    provider: settings.provider,
    api_url: settings.api_url,
    model: settings.model,
    temperature: String(settings.temperature),
    max_output_tokens: String(settings.max_output_tokens),
    http_timeout_seconds: String(settings.http_timeout_seconds),
    key_action: 'keep',
    api_key: '',
  }
}
function isSupported(provider: string): provider is AiProvider {
  return providers.includes(provider as AiProvider)
}
function safeUrl(value: string): boolean {
  try {
    if (/[\s\\?#\u0000-\u001f]/.test(value)) return false
    const url = new URL(value)
    const local =
      url.hostname === 'localhost' ||
      url.hostname === '[::1]' ||
      /^127(?:\.\d{1,3}){3}$/.test(url.hostname)
    return (
      !!url.hostname &&
      !url.username &&
      !url.password &&
      url.port !== '0' &&
      (url.protocol === 'https:' || (url.protocol === 'http:' && local))
    )
  } catch {
    return false
  }
}
function validLoaded(value: AiSettingsView): boolean {
  return (
    !!value &&
    typeof value.provider === 'string' &&
    typeof value.api_url === 'string' &&
    typeof value.model === 'string' &&
    typeof value.mutation_token === 'string' &&
    !!value.mutation_token &&
    ['web', 'environment', 'default'].includes(value.source) &&
    [
      value.temperature,
      value.max_output_tokens,
      value.http_timeout_seconds,
    ].every((number) => typeof number === 'number' && Number.isFinite(number))
  )
}

export interface AiPanelState {
  dirty: boolean
  busy: boolean
}
export function AiSettingsPanel({
  onStateChange,
}: { onStateChange?: (state: AiPanelState) => void } = {}) {
  const { t } = useI18n()
  const [loaded, setLoaded] = useState<AiSettingsView | null>(null)
  const [form, setForm] = useState<FormValues | null>(null)
  const [operation, setOperation] = useState<Operation | null>('loading')
  const [feedback, setFeedback] = useState<Feedback | null>(null)
  const [confirmReset, setConfirmReset] = useState(false)
  const active = useRef<AbortController | null>(null)

  const acceptSettings = useCallback((value: AiSettingsView) => {
    if (!validLoaded(value)) throw new AiSettingsError('request')
    setLoaded(value)
    setForm(toForm(value))
    setConfirmReset(false)
  }, [])
  const errorFeedback = (error: unknown): Feedback => ({
    key: `aiSettings.error.${error instanceof AiSettingsError ? error.code : 'request'}`,
    tone: 'error',
  })
  const load = useCallback(async () => {
    if (active.current) return
    const controller = new AbortController()
    active.current = controller
    setOperation('loading')
    setFeedback(null)
    try {
      const response = await fetchAiSettings(controller.signal)
      if (active.current === controller && !controller.signal.aborted)
        acceptSettings(response)
    } catch (error) {
      if (active.current === controller && !controller.signal.aborted)
        setFeedback(errorFeedback(error))
    } finally {
      if (active.current === controller) {
        active.current = null
        setOperation(null)
      }
    }
  }, [acceptSettings])
  useEffect(() => {
    void load()
    return () => {
      active.current?.abort()
      active.current = null
    }
  }, [load])

  const savedForm = loaded ? toForm(loaded) : null
  const hasUnsavedChanges = !!(
    form &&
    savedForm &&
    (Object.keys(form) as (keyof FormValues)[]).some(
      (key) => form[key] !== savedForm[key],
    )
  )
  useLayoutEffect(() => {
    onStateChange?.({
      dirty: hasUnsavedChanges,
      busy: operation !== null && operation !== 'loading',
    })
  }, [hasUnsavedChanges, operation, onStateChange])
  // The backend owns canonical destination checks before any stored-key use.
  const hasServiceEdits = !!(
    form &&
    loaded &&
    (form.provider !== loaded.provider ||
      form.api_url.trim() !== loaded.api_url.trim())
  )
  const edit = (patch: Partial<FormValues>) => {
    if (active.current) return
    setForm((current) => (current ? { ...current, ...patch } : current))
    setFeedback(null)
    setConfirmReset(false)
  }
  const payload = (): AiSettingsDraft | null => {
    if (!form) return null
    const temperature = Number(form.temperature),
      maxTokens = Number(form.max_output_tokens),
      timeout = Number(form.http_timeout_seconds)
    let error: string | null = null
    if (
      !isSupported(form.provider) ||
      !safeUrl(form.api_url.trim()) ||
      !form.model.trim() ||
      !form.temperature.trim() ||
      !form.max_output_tokens.trim() ||
      !form.http_timeout_seconds.trim() ||
      !Number.isFinite(temperature) ||
      temperature < 0 ||
      temperature > 2 ||
      !Number.isInteger(maxTokens) ||
      maxTokens < 1 ||
      maxTokens > 131072 ||
      !Number.isFinite(timeout) ||
      timeout < 1 ||
      timeout > 600
    )
      error = 'aiSettings.error.invalid'
    else if (
      form.key_action === 'replace' &&
      (!form.api_key.trim() || /[^\x20-\x7e]/.test(form.api_key))
    )
      error = 'aiSettings.keyRequired'
    else if (form.key_action === 'keep' && loaded?.configuration_error)
      error = 'aiSettings.repair'
    if (error) {
      setFeedback({ key: error, tone: 'error' })
      return null
    }
    return {
      provider: form.provider,
      api_url: form.api_url.trim(),
      model: form.model.trim(),
      temperature,
      max_output_tokens: maxTokens,
      http_timeout_seconds: timeout,
      key_action: form.key_action,
      ...(form.key_action === 'replace'
        ? { api_key: form.api_key.trim() }
        : {}),
    }
  }
  const run = async (action: Exclude<Operation, 'loading'>) => {
    if (active.current || !loaded) return
    const draft = action === 'resetting' ? null : payload()
    if (action !== 'resetting' && !draft) return
    const controller = new AbortController()
    active.current = controller
    setOperation(action)
    setFeedback(null)
    try {
      if (action === 'testing') {
        const result = await testAiSettings(
          draft!,
          loaded.mutation_token,
          controller.signal,
        )
        if (active.current === controller && !controller.signal.aborted) {
          if (
            result.ok !== true ||
            !Number.isFinite(result.elapsed_ms) ||
            result.elapsed_ms < 0
          )
            throw new AiSettingsError('request')
          setFeedback({
            key: 'aiSettings.testSuccess',
            tone: 'success',
            params: { time: Math.round(result.elapsed_ms) },
          })
        }
      } else {
        const result =
          action === 'saving'
            ? await saveAiSettings(
                draft!,
                loaded.mutation_token,
                controller.signal,
              )
            : await resetAiSettings(loaded.mutation_token, controller.signal)
        if (active.current === controller && !controller.signal.aborted) {
          acceptSettings(result)
          setFeedback({
            key:
              action === 'saving' ? 'aiSettings.saved' : 'aiSettings.restored',
            tone: 'success',
          })
        }
      }
    } catch (error) {
      if (active.current === controller && !controller.signal.aborted)
        setFeedback(errorFeedback(error))
    } finally {
      if (active.current === controller) {
        active.current = null
        setOperation(null)
      }
    }
  }

  return (
    <section
      className="ai-settings"
      aria-labelledby="ai-settings-title"
      aria-busy={operation !== null}
    >
      <div className="ai-settings__heading">
        <div>
          <h3 id="ai-settings-title">{t('aiSettings.title')}</h3>
          <p>{t('aiSettings.description')}</p>
        </div>
        {loaded ? (
          <span className="ai-settings__source">
            {t(`aiSettings.source.${loaded.source}`)}
          </span>
        ) : null}
      </div>
      {hasUnsavedChanges ? (
        <p className="ai-settings__notice">{t('aiSettings.unsaved')}</p>
      ) : null}
      {operation === 'loading' ? (
        <p role="status">{t('aiSettings.loading')}</p>
      ) : null}
      {!form && !operation ? (
        <Button
          type="button"
          appearance="secondary"
          onClick={() => void load()}
        >
          {t('aiSettings.retry')}
        </Button>
      ) : null}
      {form && loaded ? (
        <form
          onSubmit={(event) => {
            event.preventDefault()
            void run('saving')
          }}
          noValidate
          autoComplete="off"
        >
          <fieldset
            disabled={operation !== null}
            className="ai-settings__fieldset"
          >
            <legend className="ai-settings__legend">
              {t('aiSettings.configuration')}
            </legend>
            <div className="ai-settings__grid">
              <label>
                {t('aiSettings.provider')}
                <Select
                  disabled={operation !== null}
                  value={form.provider}
                  onChange={(event) =>
                    edit({
                      provider: event.target.value,
                      api_url: '',
                      model: '',
                    })
                  }
                >
                  {!isSupported(form.provider) ? (
                    <option value={form.provider}>
                      {t('aiSettings.unsupportedProvider')}
                    </option>
                  ) : null}
                  {providers.map((provider) => (
                    <option key={provider} value={provider}>
                      {providerLabels[provider]}
                    </option>
                  ))}
                </Select>
              </label>
              <label>
                {t('aiSettings.url')}
                <Input
                  disabled={operation !== null}
                  type="text"
                  inputMode="url"
                  spellCheck={false}
                  value={form.api_url}
                  placeholder="https://api.example.com/v1"
                  onChange={(event) => edit({ api_url: event.target.value })}
                />
              </label>
              <label>
                {t('aiSettings.model')}
                <Input
                  disabled={operation !== null}
                  type="text"
                  spellCheck={false}
                  value={form.model}
                  onChange={(event) => edit({ model: event.target.value })}
                />
              </label>
            </div>
            <p className="ai-settings__hint">{t('aiSettings.urlHint')}</p>
            <div className="ai-settings__key-box">
              <p className="ai-settings__key-state">
                {t(
                  loaded.api_key_configured
                    ? 'aiSettings.keyConfigured'
                    : 'aiSettings.keyMissing',
                )}
              </p>
              <div className="ai-settings__grid ai-settings__grid--key">
                <label>
                  {t('aiSettings.keyAction')}
                  <Select
                    disabled={operation !== null}
                    value={form.key_action}
                    onChange={(event) =>
                      edit({
                        key_action: event.target.value as AiKeyAction,
                        api_key: '',
                      })
                    }
                  >
                    <option value="keep">{t('aiSettings.keepKey')}</option>
                    <option value="replace">
                      {t('aiSettings.replaceKey')}
                    </option>
                    <option value="clear">{t('aiSettings.clearKey')}</option>
                  </Select>
                </label>
                <label>
                  {t('aiSettings.replacementKey')}
                  <Input
                    type="password"
                    disabled={
                      operation !== null || form.key_action !== 'replace'
                    }
                    autoComplete="new-password"
                    spellCheck={false}
                    value={form.api_key}
                    placeholder={t('aiSettings.keyPlaceholder')}
                    onChange={(event) => edit({ api_key: event.target.value })}
                  />
                </label>
              </div>
              <p className="ai-settings__hint">{t('aiSettings.keyHint')}</p>
              {form.key_action === 'clear' ? (
                <p className="ai-settings__notice">
                  {t('aiSettings.clearHint')}
                </p>
              ) : null}
            </div>
            {hasServiceEdits ? (
              <p className="ai-settings__notice">
                {t('aiSettings.destinationChanged')}
              </p>
            ) : null}
            {loaded.configuration_error ? (
              <p className="ai-settings__notice">
                {t('aiSettings.repair')} {t('aiSettings.urlRepair')}
              </p>
            ) : null}
            <details className="ai-settings__advanced">
              <summary>{t('aiSettings.advanced')}</summary>
              <div className="ai-settings__grid">
                <label>
                  {t('aiSettings.temperature')}
                  <Input
                    disabled={operation !== null}
                    type="number"
                    min="0"
                    max="2"
                    step="any"
                    value={form.temperature}
                    onChange={(event) =>
                      edit({ temperature: event.target.value })
                    }
                  />
                </label>
                <label>
                  {t('aiSettings.maxTokens')}
                  <Input
                    disabled={operation !== null}
                    type="number"
                    min="1"
                    max="131072"
                    step="1"
                    value={form.max_output_tokens}
                    onChange={(event) =>
                      edit({ max_output_tokens: event.target.value })
                    }
                  />
                </label>
                <label>
                  {t('aiSettings.timeout')}
                  <Input
                    disabled={operation !== null}
                    type="number"
                    min="1"
                    max="600"
                    step="any"
                    value={form.http_timeout_seconds}
                    onChange={(event) =>
                      edit({ http_timeout_seconds: event.target.value })
                    }
                  />
                </label>
              </div>
              <p className="ai-settings__hint">{t('aiSettings.limits')}</p>
            </details>
            <p className="ai-settings__hint">{t('aiSettings.testHint')}</p>
            <div className="ai-settings__actions">
              <Button type="submit" appearance="primary">
                {t('aiSettings.save')}
              </Button>
              <Button
                type="button"
                appearance="secondary"
                onClick={() => void run('testing')}
              >
                {t('aiSettings.test')}
              </Button>
              <Button
                type="button"
                appearance="secondary"
                onClick={() => {
                  if (!active.current) setConfirmReset(true)
                }}
              >
                {t('aiSettings.reset')}
              </Button>
            </div>
            {confirmReset ? (
              <div className="ai-settings__confirmation">
                <p>{t('aiSettings.resetConfirm')}</p>
                <div className="ai-settings__actions">
                  <Button
                    type="button"
                    appearance="secondary"
                    onClick={() => void run('resetting')}
                  >
                    {t('aiSettings.confirmReset')}
                  </Button>
                  <Button
                    type="button"
                    appearance="secondary"
                    onClick={() => setConfirmReset(false)}
                  >
                    {t('aiSettings.cancel')}
                  </Button>
                </div>
              </div>
            ) : null}
          </fieldset>
        </form>
      ) : null}
      {operation && operation !== 'loading' ? (
        <p role="status" className="ai-settings__feedback">
          {t(`aiSettings.${operation}`)}
        </p>
      ) : null}
      {feedback ? (
        <p
          role={feedback.tone === 'error' ? 'alert' : 'status'}
          className={`ai-settings__feedback ai-settings__feedback--${feedback.tone}`}
        >
          {t(feedback.key, feedback.params)}
        </p>
      ) : null}
    </section>
  )
}
