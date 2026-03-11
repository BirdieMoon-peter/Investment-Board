import { useCallback, useEffect, useState } from 'react'

import { fetchStockDetail } from './api/stocks'
import {
  addWatchlistItem,
  fetchWatchlist,
  removeWatchlistItem,
} from './api/watchlist'
import { SearchBox } from './components/SearchBox'
import { StatusMessage } from './components/StatusMessage'
import { WatchlistTable } from './components/WatchlistTable'
import { StockDetailPage } from './pages/StockDetailPage'
import type {
  StockDetailPageData,
  StockDetailPageViewState,
  WatchlistItem,
} from './types/watchlist'

export default function App() {
  const [watchlistItems, setWatchlistItems] = useState<WatchlistItem[]>([])
  const [currentPage, setCurrentPage] = useState<'watchlist' | 'detail'>('watchlist')
  const [selectedDetail, setSelectedDetail] = useState<StockDetailPageData | null>(null)
  const [detailViewState, setDetailViewState] = useState<StockDetailPageViewState>('ready')
  const [isLoadingWatchlist, setIsLoadingWatchlist] = useState(true)
  const [watchlistError, setWatchlistError] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [watchlistInfo, setWatchlistInfo] = useState('Loading watchlist…')

  const loadWatchlist = useCallback(async () => {
    setIsLoadingWatchlist(true)
    setWatchlistError(null)
    setWatchlistInfo('Loading watchlist…')

    try {
      const nextItems = await fetchWatchlist()
      setWatchlistItems(nextItems)
      setWatchlistInfo(nextItems.length === 0 ? 'Your watchlist is empty.' : '')
    } catch {
      setWatchlistItems([])
      setWatchlistError('Unable to load your watchlist right now.')
      setWatchlistInfo('')
    } finally {
      setIsLoadingWatchlist(false)
    }
  }, [])

  useEffect(() => {
    void loadWatchlist()
  }, [loadWatchlist])

  async function handleAdd(securityId: number) {
    setActionError(null)

    try {
      await addWatchlistItem(securityId)
      await loadWatchlist()
    } catch {
      setActionError('Unable to add that security to your watchlist right now.')
    }
  }

  async function handleRemove(securityId: number) {
    setActionError(null)

    try {
      await removeWatchlistItem(securityId)
      await loadWatchlist()
    } catch {
      setActionError('Unable to remove that security from your watchlist right now.')
    }
  }

  async function handleOpenDetail(securityId: number) {
    setCurrentPage('detail')
    setDetailViewState('loading')

    try {
      const detail = await fetchStockDetail(securityId)
      setSelectedDetail(detail)
      setDetailViewState('ready')
    } catch (error) {
      setSelectedDetail(null)
      setDetailViewState(error instanceof Error && error.message === 'not-found' ? 'not-found' : 'error')
    }
  }

  function handleBackToWatchlist() {
    setCurrentPage('watchlist')
  }

  return (
    <main className="app-shell">
      {currentPage === 'detail' ? (
        <StockDetailPage
          detail={selectedDetail}
          viewState={detailViewState}
          onBack={handleBackToWatchlist}
        />
      ) : (
        <section className="watchlist-shell" aria-label="Watchlist page shell">
          <header className="watchlist-shell__header">
            <p className="watchlist-shell__eyebrow">Investment Board</p>
            <h1>Watchlist</h1>
            <p className="watchlist-shell__description">
              Track securities you want to monitor from a single workspace.
            </p>
          </header>

          <SearchBox onAdd={(securityId) => void handleAdd(securityId)} />

          {watchlistError ? <StatusMessage tone="error" message={watchlistError} /> : null}
          {!watchlistError && actionError ? <StatusMessage tone="error" message={actionError} /> : null}
          {!watchlistError && (isLoadingWatchlist || watchlistInfo) ? (
            <StatusMessage message={watchlistInfo} />
          ) : null}
          {!watchlistError && !isLoadingWatchlist && watchlistItems.length > 0 ? (
            <WatchlistTable
              items={watchlistItems}
              onOpenDetail={handleOpenDetail}
              onRemove={(securityId) => void handleRemove(securityId)}
            />
          ) : null}
        </section>
      )}
    </main>
  )
}
