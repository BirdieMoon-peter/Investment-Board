import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import { DEFAULT_HOMEPAGE_SETTINGS, HOMEPAGE_SETTINGS_STORAGE_KEY } from './homepageSettings'

const initial = { provider: 'openai', api_url: 'https://fixture.test/v1', model: 'fixture-model', temperature: 0.2, max_output_tokens: 1024, http_timeout_seconds: 60, source: 'environment', api_key_configured: true, configuration_error: null, mutation_token: 'fixture-private-token' }
const response = (body: unknown) => ({ ok: true, status: 200, json: async () => body })

afterEach(() => { vi.unstubAllGlobals(); window.localStorage.clear(); window.sessionStorage.clear() })

describe('Homepage AI settings integration', () => {
  it('loads only when settings is opened, preserves language edits, and never puts AI credentials in browser storage', async () => {
    const settings = { ...DEFAULT_HOMEPAGE_SETTINGS, autoRefreshEnabled: false, autoSyncEnabled: false }
    window.localStorage.setItem(HOMEPAGE_SETTINGS_STORAGE_KEY, JSON.stringify(settings))
    const fetch = vi.fn((url: string, options?: RequestInit) => {
      if (url === '/api/watchlist/items') return Promise.resolve(response([]))
      if (url === '/api/homepage/overview') return Promise.resolve(response({ indexes: [], macro: [], updated_at: null, warnings: [] }))
      if (url === '/api/ai/settings') {
        if (options?.method === 'PUT') return Promise.resolve(response({ ...initial, source: 'web' }))
        return Promise.resolve(response(initial))
      }
      throw new Error('Unexpected request')
    })
    vi.stubGlobal('fetch', fetch)
    await act(async () => { render(<App />) })
    expect(fetch.mock.calls.some(([url]) => url === '/api/ai/settings')).toBe(false)
    fireEvent.click(screen.getByRole('button', { name: 'Open settings' }))
    await screen.findByLabelText('Model')
    fireEvent.change(screen.getByLabelText('API key action'), { target: { value: 'replace' } })
    fireEvent.change(screen.getByLabelText('Replacement API key'), { target: { value: 'fixture-private-key' } })
    fireEvent.change(screen.getByLabelText('Model'), { target: { value: 'unsaved-model' } })
    fireEvent.change(screen.getByLabelText('Language'), { target: { value: 'zh' } })
    expect(screen.getByLabelText('模型名称')).toHaveValue('unsaved-model')
    expect(screen.getByLabelText('新 API 密钥')).toHaveValue('fixture-private-key')
    expect(fetch.mock.calls.filter(([url]) => url === '/api/ai/settings')).toHaveLength(1)
    fireEvent.click(screen.getByRole('button', { name: '保存 AI 配置' }))
    await screen.findByText('AI 配置已保存，后续 AI 请求将使用此配置。')
    const write = fetch.mock.calls.find(([url, options]) => url === '/api/ai/settings' && options?.method === 'PUT')
    expect(JSON.parse(write![1]!.body as string)).toMatchObject({ model: 'unsaved-model', api_key: 'fixture-private-key', key_action: 'replace' })
    expect(write![1]!.headers).toMatchObject({ 'X-AI-Settings-Token': 'fixture-private-token' })
    expect(JSON.stringify(window.localStorage)).not.toMatch(/fixture-private|unsaved-model|fixture-model/)
    expect(JSON.stringify(window.sessionStorage)).not.toMatch(/fixture-private|unsaved-model|fixture-model/)
    expect(JSON.parse(window.localStorage.getItem(HOMEPAGE_SETTINGS_STORAGE_KEY)!)).toMatchObject({ ...settings, language: 'zh' })
    fireEvent.click(screen.getByRole('button', { name: '关闭设置' }))
    expect(screen.queryByLabelText('模型名称')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: '打开设置' }))
    await screen.findByLabelText('模型名称')
    await waitFor(() => expect(fetch.mock.calls.filter(([url, options]) => url === '/api/ai/settings' && options?.method === 'GET')).toHaveLength(2))
  })
})
