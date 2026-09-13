import { StrictMode } from 'react'
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { AppThemeProvider, THEME_PREFERENCE_STORAGE_KEY, useAppTheme } from './theme'

function ThemeControls() {
  const { preference, resolvedTheme, setPreference } = useAppTheme()
  return (
    <>
      <output aria-label="Preference">{preference}</output>
      <output aria-label="Resolved theme">{resolvedTheme}</output>
      <button onClick={() => setPreference('light')}>Light</button>
      <button onClick={() => setPreference('dark')}>Dark</button>
      <button onClick={() => setPreference('system')}>System</button>
    </>
  )
}

function installSystemTheme(dark: boolean) {
  const listeners = new Set<() => void>()
  const media = {
    matches: dark,
    media: '(prefers-color-scheme: dark)',
    addEventListener: vi.fn((_event: string, listener: () => void) => listeners.add(listener)),
    removeEventListener: vi.fn((_event: string, listener: () => void) => listeners.delete(listener)),
  }
  vi.stubGlobal('matchMedia', vi.fn(() => media))
  return {
    media,
    listeners,
    change(matches: boolean) {
      act(() => {
        media.matches = matches
        listeners.forEach((listener) => listener())
      })
    },
  }
}

describe('App theme', () => {
  beforeEach(() => {
    window.localStorage.clear()
    document.documentElement.removeAttribute('data-theme')
    document.documentElement.style.removeProperty('color-scheme')
    document.documentElement.style.removeProperty('--bg-app')
  })

  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it('defaults to system and reacts to operating system theme changes', () => {
    const system = installSystemTheme(false)
    render(<AppThemeProvider><ThemeControls /></AppThemeProvider>)

    expect(screen.getByLabelText('Preference')).toHaveTextContent('system')
    expect(screen.getByLabelText('Resolved theme')).toHaveTextContent('light')
    expect(document.documentElement).toHaveAttribute('data-theme', 'light')
    expect(document.documentElement.style.colorScheme).toBe('light')

    system.change(true)
    expect(screen.getByLabelText('Resolved theme')).toHaveTextContent('dark')
    expect(document.documentElement).toHaveAttribute('data-theme', 'dark')
    expect(document.documentElement.style.colorScheme).toBe('dark')
  })

  it('uses the dark system theme on the first render', () => {
    installSystemTheme(true)
    render(<AppThemeProvider><ThemeControls /></AppThemeProvider>)
    expect(screen.getByLabelText('Resolved theme')).toHaveTextContent('dark')
  })

  it('keeps an explicit selection when the system changes and resumes following when selected', () => {
    const system = installSystemTheme(false)
    render(<AppThemeProvider><ThemeControls /></AppThemeProvider>)
    fireEvent.click(screen.getByRole('button', { name: 'Dark' }))
    system.change(true)
    system.change(false)
    expect(screen.getByLabelText('Preference')).toHaveTextContent('dark')
    expect(screen.getByLabelText('Resolved theme')).toHaveTextContent('dark')
    fireEvent.click(screen.getByRole('button', { name: 'System' }))
    expect(screen.getByLabelText('Resolved theme')).toHaveTextContent('light')
  })

  it.each(['light', 'dark'])('persists only the %s preference and restores it across remounts', (preference) => {
    installSystemTheme(false)
    window.localStorage.setItem('investment-board-homepage-settings', '{"language":"zh"}')
    const first = render(<AppThemeProvider><ThemeControls /></AppThemeProvider>)
    fireEvent.click(screen.getByRole('button', { name: preference === 'light' ? 'Light' : 'Dark' }))
    expect(window.localStorage.getItem(THEME_PREFERENCE_STORAGE_KEY)).toBe(preference)
    expect(window.localStorage.getItem('investment-board-homepage-settings')).toBe('{"language":"zh"}')
    expect(window.localStorage.length).toBe(2)
    first.unmount()
    render(<AppThemeProvider><ThemeControls /></AppThemeProvider>)
    expect(screen.getByLabelText('Preference')).toHaveTextContent(preference)
    expect(screen.getByLabelText('Resolved theme')).toHaveTextContent(preference)
  })

  it.each(['invalid', '{broken', '{"theme":"dark","api_key":"fixture"}', 'null'])('ignores malformed theme storage: %s', (value) => {
    installSystemTheme(false)
    window.localStorage.setItem(THEME_PREFERENCE_STORAGE_KEY, value)
    render(<AppThemeProvider><ThemeControls /></AppThemeProvider>)
    expect(screen.getByLabelText('Preference')).toHaveTextContent('system')
    expect(screen.getByLabelText('Resolved theme')).toHaveTextContent('light')
  })

  it('remains usable when storage reads and writes are denied', () => {
    installSystemTheme(false)
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => { throw new Error('denied') })
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('denied') })
    render(<AppThemeProvider><ThemeControls /></AppThemeProvider>)
    fireEvent.click(screen.getByRole('button', { name: 'Dark' }))
    expect(screen.getByLabelText('Resolved theme')).toHaveTextContent('dark')
    expect(document.documentElement).toHaveAttribute('data-theme', 'dark')
  })

  it('cleans up listeners and restores document appearance after a StrictMode unmount', () => {
    const system = installSystemTheme(false)
    document.documentElement.setAttribute('data-theme', 'previous')
    document.documentElement.style.colorScheme = 'light dark'
    document.documentElement.style.setProperty('--bg-app', 'previous-surface')
    const view = render(<StrictMode><AppThemeProvider><ThemeControls /></AppThemeProvider></StrictMode>)
    expect(system.listeners.size).toBe(1)
    fireEvent.click(screen.getByRole('button', { name: 'Dark' }))
    view.unmount()
    expect(system.listeners.size).toBe(0)
    expect(document.documentElement).toHaveAttribute('data-theme', 'previous')
    expect(document.documentElement.style.colorScheme).toBe('light dark')
    expect(document.documentElement.style.getPropertyValue('--bg-app')).toBe('previous-surface')
  })

  it('provides official Fluent context and semantic variables in both themes', () => {
    installSystemTheme(false)
    render(<AppThemeProvider><ThemeControls /></AppThemeProvider>)
    const provider = screen.getByLabelText('Preference').closest('.fui-FluentProvider') as HTMLElement
    expect(provider).not.toBeNull()
    expect(provider.style.getPropertyValue('--bg-app')).not.toBe('')
    expect(provider.style.getPropertyValue('--text-primary')).not.toBe('')
    const lightSurface = provider.style.getPropertyValue('--bg-app')
    const lightText = provider.style.getPropertyValue('--text-primary')
    fireEvent.click(screen.getByRole('button', { name: 'Dark' }))
    expect(provider.style.getPropertyValue('--bg-app')).not.toBe(lightSurface)
    expect(provider.style.getPropertyValue('--text-primary')).not.toBe(lightText)
  })

  it('has a safe fallback for components tested outside the app provider', () => {
    render(<ThemeControls />)
    expect(screen.getByLabelText('Preference')).toHaveTextContent('system')
    expect(screen.getByLabelText('Resolved theme')).toHaveTextContent('light')
    expect(() => fireEvent.click(screen.getByRole('button', { name: 'Dark' }))).not.toThrow()
  })

  it('supports environments without matchMedia', () => {
    vi.stubGlobal('matchMedia', undefined)
    render(<AppThemeProvider><ThemeControls /></AppThemeProvider>)
    expect(screen.getByLabelText('Resolved theme')).toHaveTextContent('light')
    fireEvent.click(screen.getByRole('button', { name: 'Dark' }))
    expect(screen.getByLabelText('Resolved theme')).toHaveTextContent('dark')
  })
})
