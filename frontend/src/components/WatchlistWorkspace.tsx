import { useMemo } from 'react'
import {
  Button,
  Field,
  Input,
  Select,
  useRestoreFocusTarget,
} from '@fluentui/react-components'
import { MagnifyingGlass, Plus } from '@phosphor-icons/react'
import {
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  useReactTable,
  type SortingState,
  type ColumnDef,
} from '@tanstack/react-table'
import { useI18n } from '../i18n'
import type { WatchlistItem } from '../types/watchlist'
import type { HomepageAdviceLabel } from '../types/homepageAdvice'
import { WatchlistTable } from './WatchlistTable'
export interface WatchlistView {
  query: string
  market: 'all' | 'SH' | 'SZ'
  sorting: SortingState
}
interface Props {
  items: WatchlistItem[]
  view: WatchlistView
  onViewChange: (view: WatchlistView) => void
  onSearch: () => void
  onOpenDetail: (id: number) => void
  onRemove: (id: number) => void | Promise<void>
  adviceLabels?: Record<number, HomepageAdviceLabel>
  showAiTags?: boolean
  loading?: boolean
}
const numericValue = (value: string | null) =>
  value === null || value.trim() === '' || !Number.isFinite(Number(value))
    ? undefined
    : Number(value)
export function WatchlistWorkspace({
  items,
  view,
  onViewChange,
  onSearch,
  loading = false,
  ...props
}: Props) {
  const restoreFocusTarget = useRestoreFocusTarget()
  const { t, language } = useI18n()
  const columns = useMemo<ColumnDef<WatchlistItem>[]>(
    () => [
      {
        id: 'name',
        accessorKey: 'name',
        sortingFn: (a, b) =>
          a.original.name.localeCompare(
            b.original.name,
            language === 'zh' ? 'zh-CN' : 'en',
          ),
        sortDescFirst: false,
      },
      {
        id: 'last_price',
        accessorFn: (item) => numericValue(item.last_price),
        sortUndefined: 'last',
        sortDescFirst: false,
      },
      {
        id: 'change_percent',
        accessorFn: (item) => numericValue(item.change_percent),
        sortUndefined: 'last',
        sortDescFirst: false,
      },
    ],
    [language],
  )
  const filteredItems = useMemo(
    () =>
      items.filter((item) => {
        const query = view.query.trim().toLocaleLowerCase()
        return (
          (view.market === 'all' || item.market === view.market) &&
          (!query ||
            `${item.name} ${item.code}`.toLocaleLowerCase().includes(query))
        )
      }),
    [items, view.query, view.market],
  )
  const table = useReactTable({
    data: filteredItems,
    columns,
    state: { sorting: view.sorting },
    onSortingChange: (updater) =>
      onViewChange({
        ...view,
        sorting:
          typeof updater === 'function' ? updater(view.sorting) : updater,
      }),
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getSortedRowModel: getSortedRowModel(),
    enableMultiSort: false,
  })
  const sortedItems = table.getRowModel().rows.map((row) => row.original)
  return (
    <section
      className="watchlist-workspace"
      aria-labelledby="watchlist-heading"
    >
      <div className="workspace-section-heading">
        <div>
          <h2 id="watchlist-heading">{t('homepage.watchlist')}</h2>
          <span className="workspace-muted watchlist-count" role={loading ? 'status' : undefined}
            aria-label={loading ? t('homepage.loadingWatchlist') : undefined}>
            {loading ? t('common.loading') : t('workspace.count', {
              filtered: filteredItems.length,
              total: items.length,
            })}
          </span>
        </div>
        <Button
          id="watchlist-search-trigger"
          {...restoreFocusTarget}
          appearance="primary"
          icon={<Plus />}
          onClick={onSearch}
        >
          {t('homepage.searchAndAdd')}
        </Button>
      </div>
      <div className="watchlist-filters">
        <Field label={t('workspace.filter')}>
          <Input
            type="search"
            contentBefore={<MagnifyingGlass />}
            value={view.query}
            onChange={(_, data) => onViewChange({ ...view, query: data.value })}
            placeholder={t('search.placeholder')}
          />
        </Field>
        <Field label={t('workspace.market')}>
          <Select
            value={view.market}
            onChange={(_, data) =>
              onViewChange({
                ...view,
                market: data.value as WatchlistView['market'],
              })
            }
          >
            <option value="all">{t('workspace.allMarkets')}</option>
            <option value="SH">SH</option>
            <option value="SZ">SZ</option>
          </Select>
        </Field>
        {view.query || view.market !== 'all' ? (
          <Button
            appearance="subtle"
            onClick={() => onViewChange({ ...view, query: '', market: 'all' })}
          >
            {t('workspace.clearFilters')}
          </Button>
        ) : null}
      </div>
      {filteredItems.length ? (
        <WatchlistTable
          items={sortedItems}
          {...props}
          sorting={view.sorting}
          onSort={(id) => table.getColumn(id)?.toggleSorting()}
        />
      ) : items.length ? (
        <p className="workspace-empty" role="status">
          {t('workspace.noMatches')}
        </p>
      ) : null}
    </section>
  )
}
