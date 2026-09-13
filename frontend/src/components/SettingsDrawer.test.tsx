import { useState } from 'react'
import { act, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { SettingsDrawer } from './SettingsDrawer'
import { DEFAULT_HOMEPAGE_SETTINGS } from '../homepageSettings'
const initial = {
  provider: 'openai',
  api_url: 'https://fixture.test/v1',
  model: 'fixture-model',
  temperature: 0.2,
  max_output_tokens: 1024,
  http_timeout_seconds: 60,
  source: 'environment',
  api_key_configured: true,
  configuration_error: null,
  mutation_token: 'fixture-token',
}
const response = (data: unknown) => ({
  ok: true,
  status: 200,
  json: async () => data,
})
function Harness() {
  const [open, setOpen] = useState(true)
  return open ? (
    <SettingsDrawer
      settings={DEFAULT_HOMEPAGE_SETTINGS}
      onSettingsChange={vi.fn()}
      onClose={() => setOpen(false)}
    />
  ) : (
    <p>Closed</p>
  )
}
afterEach(() => {
  vi.unstubAllGlobals()
})
describe('settings drawer', () => {
  it('lazily mounts AI, preserves a draft across tabs and protects close until discard', async () => {
    const fetch = vi.fn().mockResolvedValue(response(initial))
    vi.stubGlobal('fetch', fetch)
    render(<Harness />)
    expect(fetch).not.toHaveBeenCalled()
    fireEvent.click(
      screen.getByRole('tab', { name: 'AI service configuration' }),
    )
    fireEvent.change(await screen.findByLabelText('Model'), {
      target: { value: 'draft-model' },
    })
    fireEvent.change(screen.getByLabelText('API key action'), {
      target: { value: 'replace' },
    })
    fireEvent.change(screen.getByLabelText('Replacement API key'), {
      target: { value: 'fixture-secret' },
    })
    fireEvent.click(screen.getByRole('tab', { name: 'Interface and refresh' }))
    fireEvent.click(
      screen.getByRole('tab', { name: 'AI service configuration' }),
    )
    expect(screen.getByLabelText('Model')).toHaveValue('draft-model')
    expect(screen.getByLabelText('Replacement API key')).toHaveValue(
      'fixture-secret',
    )
    expect(fetch).toHaveBeenCalledTimes(1)
    act(() => screen.getByRole('button', { name: 'Close settings' }).focus())
    fireEvent.click(screen.getByRole('button', { name: 'Close settings' }))
    const confirmation = await screen.findByRole('dialog', {
      name: 'Discard unsaved AI changes?',
    })
    fireEvent.click(
      await within(confirmation).findByRole('button', {
        name: 'Continue editing',
      }),
    )
    expect(
      screen.queryByRole('dialog', {
        name: 'Discard unsaved AI changes?',
        hidden: true,
      }),
    ).not.toBeInTheDocument()
    expect(
      await screen.findByRole('button', { name: 'Close settings' }),
    ).toBeEnabled()
    expect(screen.getByLabelText('Model')).toHaveValue('draft-model')
    fireEvent.keyDown(screen.getByLabelText('Model'), { key: 'Escape' })
    fireEvent.click(
      within(
        await screen.findByRole('dialog', {
          name: 'Discard unsaved AI changes?',
        }),
      ).getByRole('button', { name: 'Discard changes' }),
    )
    expect(screen.getByText('Closed')).toBeInTheDocument()
    expect(
      screen.queryByLabelText('Replacement API key'),
    ).not.toBeInTheDocument()
  })
  it.each([
    'Save AI settings',
    'Test connection',
    'Restore environment configuration',
  ])('prevents every dismissal while %s is pending', async (action) => {
    let resolve!: (value: unknown) => void
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(response(initial))
      .mockReturnValueOnce(
        new Promise((done) => {
          resolve = done
        }),
      )
    vi.stubGlobal('fetch', fetch)
    render(<Harness />)
    fireEvent.click(
      screen.getByRole('tab', { name: 'AI service configuration' }),
    )
    await screen.findByLabelText('Model')
    fireEvent.click(screen.getByRole('button', { name: action }))
    if (action === 'Restore environment configuration')
      fireEvent.click(screen.getByRole('button', { name: 'Confirm restore' }))
    expect(
      screen.getByRole('button', { name: 'Close settings' }),
    ).toBeDisabled()
    fireEvent.keyDown(screen.getByLabelText('Model'), { key: 'Escape' })
    expect(screen.queryByText('Closed')).not.toBeInTheDocument()
    await act(async () =>
      resolve(
        response(
          action === 'Test connection' ? { ok: true, elapsed_ms: 12 } : initial,
        ),
      ),
    )
    fireEvent.click(screen.getByRole('button', { name: 'Close settings' }))
    expect(screen.getByText('Closed')).toBeInTheDocument()
  })
})
