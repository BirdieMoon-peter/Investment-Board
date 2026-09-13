import { useState } from 'react'
import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { WatchlistWorkspace, type WatchlistView } from './WatchlistWorkspace'
import type { WatchlistItem } from '../types/watchlist'
const items: WatchlistItem[] = [
  {
    security_id: 1,
    name: 'Low',
    market: 'SH',
    code: '600001',
    industry: 'Bank',
    last_price: '9.2000',
    change_percent: '2.1',
    snapshot_time: null,
  },
  {
    security_id: 2,
    name: 'High',
    market: 'SZ',
    code: '000001',
    industry: null,
    last_price: '100.1000',
    change_percent: '-3.0',
    snapshot_time: null,
  },
  {
    security_id: 3,
    name: 'Missing',
    market: 'SH',
    code: '600002',
    industry: null,
    last_price: null,
    change_percent: null,
    snapshot_time: null,
  },
]
function Harness({ onRemove = vi.fn(), onOpenDetail = vi.fn() }) {
  const [view, setView] = useState<WatchlistView>({
    query: '',
    market: 'all',
    sorting: [],
  })
  return (
    <WatchlistWorkspace
      items={items}
      view={view}
      onViewChange={setView}
      onSearch={vi.fn()}
      onRemove={onRemove}
      onOpenDetail={onOpenDetail}
    />
  )
}
function names() {
  return within(screen.getByRole('table'))
    .getAllByRole('row')
    .slice(1)
    .map(
      (row) =>
        within(row).getByRole('button', { name: /view details for/i })
          .textContent,
    )
}
describe('watchlist workspace', () => {
  it('sorts price and change numerically, with missing quotes last in both directions', () => {
    render(<Harness />)
    fireEvent.click(screen.getByRole('button', { name: 'Last price' }))
    expect(names()).toEqual(['Low', 'High', 'Missing'])
    expect(
      screen.getByRole('columnheader', { name: 'Last price' }),
    ).toHaveAttribute('aria-sort', 'ascending')
    fireEvent.click(screen.getByRole('button', { name: 'Last price' }))
    expect(names()).toEqual(['High', 'Low', 'Missing'])
    fireEvent.click(screen.getByRole('button', { name: 'Change percent' }))
    expect(names()).toEqual(['High', 'Low', 'Missing'])
    fireEvent.click(screen.getByRole('button', { name: 'Change percent' }))
    expect(names()).toEqual(['Low', 'High', 'Missing'])
  })
  it('sorts names in either direction and returns to the original order when cleared', () => {
    render(<Harness />)
    fireEvent.click(screen.getByRole('button', { name: 'Name' }))
    expect(names()).toEqual(['High', 'Low', 'Missing'])
    fireEvent.click(screen.getByRole('button', { name: 'Name' }))
    expect(names()).toEqual(['Missing', 'Low', 'High'])
    fireEvent.click(screen.getByRole('button', { name: 'Name' }))
    expect(names()).toEqual(['Low', 'High', 'Missing'])
  })
  it('filters loaded names/codes and market, and distinguishes filtered and total counts', () => {
    render(<Harness />)
    fireEvent.change(screen.getByLabelText('Filter watchlist'), {
      target: { value: '600' },
    })
    expect(names()).toEqual(['Low', 'Missing'])
    expect(screen.getByText('2 of 3 securities')).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Market filter'), {
      target: { value: 'SZ' },
    })
    expect(
      screen.getByText('No securities match these filters.'),
    ).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Clear filters' }))
    expect(names()).toEqual(['Low', 'High', 'Missing'])
  })
  it('requires an object-named removal confirmation, and cancellation never navigates or removes', async () => {
    const onRemove = vi.fn(),
      onOpenDetail = vi.fn()
    render(<Harness onRemove={onRemove} onOpenDetail={onOpenDetail} />)
    fireEvent.click(screen.getByRole('button', { name: 'Actions for Low' }))
    fireEvent.click(await screen.findByRole('menuitem', { name: 'Remove Low' }))
    const dialog = await screen.findByRole('dialog', { name: 'Remove Low?' })
    expect(onRemove).not.toHaveBeenCalled()
    fireEvent.click(within(dialog).getByRole('button', { name: 'Cancel' }))
    expect(onOpenDetail).not.toHaveBeenCalled()
    expect(onRemove).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'Actions for Low' }))
    fireEvent.click(await screen.findByRole('menuitem', { name: 'Remove Low' }))
    fireEvent.click(
      within(
        await screen.findByRole('dialog', { name: 'Remove Low?' }),
      ).getByRole('button', { name: 'Remove Low' }),
    )
    expect(onRemove).toHaveBeenCalledWith(1)
    expect(onOpenDetail).not.toHaveBeenCalled()
  })
})
