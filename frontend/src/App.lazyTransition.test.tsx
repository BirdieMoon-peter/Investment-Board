import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import App from './App'
import { DEFAULT_HOMEPAGE_SETTINGS, HOMEPAGE_SETTINGS_STORAGE_KEY } from './homepageSettings'

const settingsChunk = vi.hoisted(() => ({ release: undefined as undefined | (() => void) }))
vi.mock('./components/SettingsDrawer', async () => {
  await new Promise<void>((resolve) => { settingsChunk.release = resolve })
  return vi.importActual('./components/SettingsDrawer')
})

afterEach(() => { vi.unstubAllGlobals(); window.localStorage.clear() })

it('moves focus into the loaded settings drawer without restoring over its controls', async () => {
  window.localStorage.setItem(HOMEPAGE_SETTINGS_STORAGE_KEY, JSON.stringify({
    ...DEFAULT_HOMEPAGE_SETTINGS, autoRefreshEnabled: false, autoSyncEnabled: false,
  }))
  const fetch = vi.fn(async (url: string) => ({ ok: true, status: 200, json: async () => {
    if (url === '/api/watchlist/items') return []
    if (url === '/api/homepage/overview') return { indexes: [], macro: [], updated_at: null, warnings: [] }
    throw new Error(`Unexpected request: ${url}`)
  } }))
  vi.stubGlobal('fetch', fetch)
  render(<App />)
  const trigger = screen.getByRole('button', { name: 'Open settings' })
  fireEvent.keyDown(document, { key: 'Tab' })
  act(() => trigger.focus())
  fireEvent.click(trigger)
  expect(await screen.findByRole('status')).toHaveTextContent('Loading settings…')
  const pendingClose = screen.getByRole('button', { name: 'Close settings' })
  await waitFor(() => expect(pendingClose).toHaveFocus())
  await waitFor(() => expect(settingsChunk.release).toBeTypeOf('function'))
  await act(async () => { settingsChunk.release!() })
  await screen.findByRole('tab', { name: 'Interface and refresh' })
  const loadedClose = screen.getByRole('button', { name: 'Close settings' })
  expect(loadedClose).not.toBe(pendingClose)
  expect(screen.getAllByRole('dialog', { name: 'Board settings' })).toHaveLength(1)
  await waitFor(() => expect(loadedClose).toHaveFocus())
  const language = screen.getByRole('combobox', { name: 'Language' })
  act(() => language.focus())
  await act(async () => { await new Promise((resolve) => window.setTimeout(resolve, 0)) })
  expect(language).toHaveFocus()
  fireEvent.keyDown(language, { key: 'Escape' })
  await waitFor(() => expect(screen.queryByRole('dialog', { name: 'Board settings' })).not.toBeInTheDocument())
  await waitFor(() => expect(trigger).toHaveFocus())
  expect(fetch.mock.calls.some(([url]) => url.includes('/ai/'))).toBe(false)
})
