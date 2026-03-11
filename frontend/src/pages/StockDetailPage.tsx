import { useEffect, useState } from 'react'

import { fetchStockDetail, syncStock } from '../api/stocks'
import { AnnouncementList } from '../components/AnnouncementList'
import { NewsList } from '../components/NewsList'
import { PriceContextPanel } from '../components/PriceContextPanel'
import { QuoteSummary } from '../components/QuoteSummary'
import { StatusMessage } from '../components/StatusMessage'
import { StockHeader } from '../components/StockHeader'
import type {
  StockDetailPageData,
  StockDetailPageViewState,
} from '../types/watchlist'

interface StockDetailPageProps {
  detail: StockDetailPageData | null
  viewState: StockDetailPageViewState
  onBack: () => void
}

export function StockDetailPage({ detail, viewState, onBack }: StockDetailPageProps) {
  const [currentDetail, setCurrentDetail] = useState(detail)
  const [isSyncing, setIsSyncing] = useState(false)
  const [syncMessage, setSyncMessage] = useState<string | null>(null)
  const [syncWarningMessage, setSyncWarningMessage] = useState<string | null>(null)
  const [syncError, setSyncError] = useState<string | null>(null)

  useEffect(() => {
    setCurrentDetail(detail)
  }, [detail])

  const securityName = currentDetail?.security.name ?? detail?.security.name ?? 'Unknown security'
  const securityId = currentDetail?.security.security_id ?? detail?.security.security_id ?? null

  async function handleSync() {
    if (securityId === null || isSyncing) {
      return
    }

    setIsSyncing(true)
    setSyncMessage('Syncing latest information…')
    setSyncWarningMessage(null)
    setSyncError(null)

    try {
      const result = await syncStock(securityId)
      const refreshedDetail = await fetchStockDetail(securityId)
      setCurrentDetail(refreshedDetail)
      const warningCount = result.warnings.length
      setSyncMessage(
        warningCount > 0
          ? `Information sync partially completed. Added ${result.announcements_upserted} announcements and ${result.news_items_upserted} news items with ${warningCount} warnings.`
          : `Information sync complete. Added ${result.announcements_upserted} announcements and ${result.news_items_upserted} news items.`,
      )
      setSyncWarningMessage(
        warningCount > 0 ? `Warnings: ${result.warnings.join('; ')}` : null,
      )
    } catch (error) {
      setSyncMessage(null)
      setSyncWarningMessage(null)
      setSyncError(
        error instanceof Error ? error.message : 'Unable to sync stock information right now.',
      )
    } finally {
      setIsSyncing(false)
    }
  }

  return (
    <section className="watchlist-shell" aria-label="Stock detail page shell">
      <header className="watchlist-shell__header">
        <p className="watchlist-shell__eyebrow">Investment Board</p>
        <h1>Stock detail</h1>
        <p className="watchlist-shell__description">
          Review the selected security before richer detail modules are connected.
        </p>
      </header>

      <button type="button" onClick={onBack}>
        Back to watchlist
      </button>

      {securityId !== null ? (
        <button type="button" onClick={() => void handleSync()} disabled={isSyncing}>
          {isSyncing ? 'Syncing latest information' : 'Sync latest information'}
        </button>
      ) : null}

      <StockHeader
        security={
          currentDetail?.security ??
          detail?.security ?? {
            security_id: -1,
            market: 'Unknown market',
            code: 'Unknown code',
            name: securityName,
            industry: null,
            status: 'unknown',
          }
        }
      />

      {viewState === 'loading' ? <StatusMessage message="Loading stock detail…" /> : null}
      {viewState === 'error' ? (
        <StatusMessage tone="error" message="Unable to load stock detail right now." />
      ) : null}
      {viewState === 'not-found' ? (
        <StatusMessage tone="error" message="The requested stock could not be found." />
      ) : null}
      {viewState === 'ready' && syncError ? <StatusMessage tone="error" message={syncError} /> : null}
      {viewState === 'ready' && syncMessage ? <StatusMessage message={syncMessage} /> : null}
      {viewState === 'ready' && syncWarningMessage ? (
        <StatusMessage tone="error" message={syncWarningMessage} />
      ) : null}

      {viewState === 'ready' && currentDetail ? (
        <>
          <QuoteSummary latestBar={currentDetail.price_context[0] ?? null} />
          <PriceContextPanel priceContext={currentDetail.price_context} />
          <AnnouncementList announcements={currentDetail.announcements} />
          <NewsList news={currentDetail.news} />
        </>
      ) : null}
    </section>
  )
}
