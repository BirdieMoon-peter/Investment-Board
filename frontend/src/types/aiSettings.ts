export type AiProvider = 'anthropic' | 'openai' | 'openai_compatible' | 'dashscope_anthropic' | 'kimi'
export type AiKeyAction = 'keep' | 'replace' | 'clear'

export interface AiSettingsValues {
  provider: string
  api_url: string
  model: string
  temperature: number
  max_output_tokens: number
  http_timeout_seconds: number
}

export interface AiSettingsView extends AiSettingsValues {
  source: 'web' | 'environment' | 'default'
  api_key_configured: boolean
  configuration_error: string | null
  mutation_token: string
}

export interface AiSettingsDraft extends AiSettingsValues {
  key_action: AiKeyAction
  api_key?: string | null
}

export interface AiConnectionResult {
  ok: true
  elapsed_ms: number
}
