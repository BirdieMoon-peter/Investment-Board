import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react'

import { fetchHomepageOverview } from './api/homepage'
import { fetchHomepageAdviceLabels } from './api/homepageAdvice'
import { fetchStockDetail } from './api/stocks'
import {
  addCustomWatchlistItem,
  addWatchlistItem,
  fetchWatchlistWithMetadata,
  removeWatchlistItem,
  syncWatchlist,
} from './api/watchlist'
import {
  type HomepageSettings,
  loadHomepageSettings,
  saveHomepageSettings,
} from './homepageSettings'
import { I18nProvider, useI18n } from './i18n'
import { AppThemeProvider } from './theme'
import { Button, Skeleton, SkeletonItem } from '@fluentui/react-components'
import { WorkspaceHeader } from './components/WorkspaceHeader'
import { MarketStrip } from './components/MarketStrip'
import { WorkspaceAside } from './components/WorkspaceAside'
import { SecuritySearchDialog } from './components/SecuritySearchDialog'
import { SettingsLoadFallback } from './components/SettingsLoadFallback'
import { WorkspaceLoadBoundary } from './components/WorkspaceLoadBoundary'
import { StatusMessage } from './components/StatusMessage'
import {
  WatchlistWorkspace,
  type WatchlistView,
} from './components/WatchlistWorkspace'
import type { HomepageAdviceLabel } from './types/homepageAdvice'
import type { HomepageMacroItem, HomepageMarketIndex } from './types/homepage'
import type {
  StockDetailPageData,
  StockDetailPageViewState,
  WatchlistItem,
} from './types/watchlist'

const StockDetailPage = lazy(() => import('./pages/StockDetailPage').then((module) => ({ default: module.StockDetailPage })))
const SettingsDrawer = lazy(() => import('./components/SettingsDrawer').then((module) => ({ default: module.SettingsDrawer })))

function ScreenLoadFailure({ onDismiss, dismissLabel }: { onDismiss: () => void; dismissLabel: string }) {
  const { t } = useI18n()
  return <div className="workspace-load-failure">
    <StatusMessage tone="error" message={t('workspace.loadFailed')} />
    <div className="workspace-load-failure__actions">
      <Button onClick={onDismiss}>{dismissLabel}</Button>
      <Button appearance="primary" onClick={() => window.location.reload()}>{t('workspace.reloadPage')}</Button>
    </div>
  </div>
}

function AppBody({
  settings,
  onSettingsChange,
}: {
  settings: HomepageSettings
  onSettingsChange: (settings: HomepageSettings) => void
}) {
  const { t, formatDateTime, language } = useI18n()
  const [watchlistItems, setWatchlistItems] = useState<WatchlistItem[]>([])
  const [currentPage, setCurrentPage] = useState<'watchlist' | 'detail'>(
    'watchlist',
  )
  const [selectedDetail, setSelectedDetail] =
    useState<StockDetailPageData | null>(null)
  const [detailViewState, setDetailViewState] =
    useState<StockDetailPageViewState>('ready')
  const [isLoadingWatchlist, setIsLoadingWatchlist] = useState(true)
  const [watchlistError, setWatchlistError] = useState<string | null>(null)
  const [watchlistInfo, setWatchlistInfo] = useState<string>(
    t('homepage.loadingWatchlist'),
  )
  const [lastRefreshAt, setLastRefreshAt] = useState<string | null>(null)
  const [isWatchlistCached, setIsWatchlistCached] = useState(false)
  const [lastSyncAt, setLastSyncAt] = useState<string | null>(null)
  const [autoSyncError, setAutoSyncError] = useState<string | null>(null)
  const [isAutoRefreshing, setIsAutoRefreshing] = useState(false)
  const [isAutoSyncing, setIsAutoSyncing] = useState(false)
  const autoRefreshInFlightRef = useRef(false)
  const autoSyncInFlightRef = useRef(false)
  const [hasLoadedWatchlist, setHasLoadedWatchlist] = useState(false)
  const [isLoadingOverview, setIsLoadingOverview] = useState(true)
  const [overviewError, setOverviewError] = useState<string | null>(null)
  const [overviewIndexes, setOverviewIndexes] = useState<HomepageMarketIndex[]>(
    [],
  )
  const [overviewMacro, setOverviewMacro] = useState<HomepageMacroItem[]>([])
  const [overviewWarnings, setOverviewWarnings] = useState<string[]>([])
  const [overviewUpdatedAt, setOverviewUpdatedAt] = useState<string | null>(
    null,
  )
  const [homepageAdviceLabels, setHomepageAdviceLabels] = useState<
    Record<number, HomepageAdviceLabel>
  >({})
  const [homepageAdviceError, setHomepageAdviceError] = useState<string | null>(
    null,
  )
  const [isSettingsOpen, setIsSettingsOpen] = useState(false)
  const [isSearchOpen, setIsSearchOpen] = useState(false)
  const [watchlistView, setWatchlistView] = useState<WatchlistView>({
    query: '',
    market: 'all',
    sorting: [],
  })
  const returnPosition = useRef<{ scrollY: number; originId: string } | null>(
    null,
  )
  const shouldRestore = useRef(false)
  useEffect(() => {
    if (
      currentPage !== 'watchlist' ||
      !shouldRestore.current ||
      !returnPosition.current
    )
      return
    shouldRestore.current = false
    const origin = document.getElementById(returnPosition.current.originId)
    if (origin && !origin.closest('[hidden], [aria-hidden="true"]')) {
      origin.focus({ preventScroll: true })
    }
    if (!origin || document.activeElement !== origin) {
      document
        .getElementById('watchlist-search-trigger')
        ?.focus({ preventScroll: true })
    }
    window.scrollTo({
      top: returnPosition.current.scrollY,
      behavior: 'instant',
    })
  }, [currentPage])
  const interactionReadyAtRef = useRef(Date.now() + 1000)

  useEffect(() => {
    setWatchlistInfo((currentValue) => {
      if (!currentValue) {
        return watchlistItems.length === 0 ? t('homepage.emptyWatchlist') : ''
      }
      if (currentValue === t('homepage.emptyWatchlist')) {
        return watchlistItems.length === 0 ? t('homepage.emptyWatchlist') : ''
      }
      return currentValue.includes('Loading') || currentValue.includes('加载')
        ? t('homepage.loadingWatchlist')
        : currentValue
    })
  }, [t, watchlistItems.length])

  const dashboardStats = useMemo(() => {
    const trackedCount = watchlistItems.length
    const syncedCount = watchlistItems.filter(
      (item) => item.last_price !== null,
    ).length
    const pendingSyncCount = trackedCount - syncedCount
    const movers = watchlistItems.filter((item) => item.change_percent !== null)
    const leadMover = movers.reduce<WatchlistItem | null>(
      (currentLead, item) => {
        if (item.change_percent === null) {
          return currentLead
        }

        if (currentLead?.change_percent === null || currentLead === null) {
          return item
        }

        return Number(item.change_percent) > Number(currentLead.change_percent)
          ? item
          : currentLead
      },
      null,
    )

    return {
      trackedCount,
      syncedCount,
      pendingSyncCount,
      leadMover,
    }
  }, [watchlistItems])

  const spotlightItem = useMemo(() => {
    if (watchlistItems.length === 0) {
      return null
    }

    return dashboardStats.leadMover ?? watchlistItems[0]
  }, [dashboardStats.leadMover, watchlistItems])

  const updateSettings = useCallback(
    (nextPatch: Partial<HomepageSettings>) => {
      onSettingsChange({ ...settings, ...nextPatch })
    },
    [onSettingsChange, settings],
  )

  const refreshHomepageAdviceLabelsInBackground = useCallback(async () => {
    try {
      const response = await fetchHomepageAdviceLabels()
      setHomepageAdviceLabels(
        Object.fromEntries(
          response.items.map((item) => [item.security_id, item]),
        ),
      )
      setHomepageAdviceError(null)
    } catch {
      setHomepageAdviceError(t('homepage.aiLabelsUnavailable'))
    }
  }, [t])

  const loadOverview = useCallback(async () => {
    setIsLoadingOverview(true)
    setOverviewError(null)

    try {
      const overview = await fetchHomepageOverview()
      setOverviewIndexes(overview.indexes)
      setOverviewMacro(overview.macro)
      setOverviewUpdatedAt(overview.updated_at)
      setOverviewWarnings(
        overview.warnings.map(
          (warning) => `${warning.section}: ${warning.message}`,
        ),
      )
    } catch {
      setOverviewIndexes([])
      setOverviewMacro([])
      setOverviewUpdatedAt(null)
      setOverviewWarnings([])
      setOverviewError(t('homepage.overviewUnavailable'))
    } finally {
      setIsLoadingOverview(false)
    }
  }, [t])

  const refreshOverviewInBackground = useCallback(async () => {
    try {
      const overview = await fetchHomepageOverview()
      setOverviewIndexes(overview.indexes)
      setOverviewMacro(overview.macro)
      setOverviewUpdatedAt(overview.updated_at)
      setOverviewWarnings(
        overview.warnings.map(
          (warning) => `${warning.section}: ${warning.message}`,
        ),
      )
      setOverviewError(null)
    } catch {
      setOverviewError(t('homepage.overviewUnavailable'))
    }
  }, [t])

  const loadWatchlist = useCallback(async () => {
    setIsLoadingWatchlist(true)
    setWatchlistError(null)
    setWatchlistInfo(t('homepage.loadingWatchlist'))

    try {
      const result = await fetchWatchlistWithMetadata()
      const nextItems = result.items
      if (!Array.isArray(nextItems)) {
        throw new Error('invalid-watchlist-response')
      }
      setWatchlistItems(nextItems)
      setLastRefreshAt(result.fetchedAt)
      setIsWatchlistCached(result.source === 'cache')
      setWatchlistInfo(
        nextItems.length === 0 ? t('homepage.emptyWatchlist') : '',
      )
      setHasLoadedWatchlist(true)
      if (nextItems.length > 0) {
        await refreshHomepageAdviceLabelsInBackground()
      } else {
        setHomepageAdviceLabels({})
        setHomepageAdviceError(null)
      }
    } catch {
      setWatchlistItems([])
      setWatchlistError(t('homepage.loadError'))
      setWatchlistInfo('')
    } finally {
      setIsLoadingWatchlist(false)
    }
  }, [t, refreshHomepageAdviceLabelsInBackground])

  const refreshWatchlistInBackground = useCallback(async () => {
    if (currentPage !== 'watchlist' || autoRefreshInFlightRef.current) {
      return
    }

    autoRefreshInFlightRef.current = true
    setIsAutoRefreshing(true)
    try {
      const result = await fetchWatchlistWithMetadata()
      const nextItems = result.items
      if (!Array.isArray(nextItems)) {
        throw new Error('invalid-watchlist-response')
      }
      setWatchlistItems(nextItems)
      setLastRefreshAt(result.fetchedAt)
      setIsWatchlistCached(result.source === 'cache')
      setWatchlistError(null)
      setWatchlistInfo(
        nextItems.length === 0 ? t('homepage.emptyWatchlist') : '',
      )
      await refreshOverviewInBackground()
      if (nextItems.length > 0) {
        await refreshHomepageAdviceLabelsInBackground()
      } else {
        setHomepageAdviceLabels({})
        setHomepageAdviceError(null)
      }
    } catch {
      setWatchlistError(t('homepage.loadError'))
    } finally {
      autoRefreshInFlightRef.current = false
      setIsAutoRefreshing(false)
    }
  }, [
    currentPage,
    refreshOverviewInBackground,
    refreshHomepageAdviceLabelsInBackground,
    t,
  ])

  const syncHomepageBoard = useCallback(async () => {
    if (
      currentPage !== 'watchlist' ||
      watchlistItems.length === 0 ||
      autoSyncInFlightRef.current
    ) {
      return
    }

    autoSyncInFlightRef.current = true
    setIsAutoSyncing(true)
    setAutoSyncError(null)
    try {
      const result = await syncWatchlist()
      setLastSyncAt(result.synced_at)
      if (result.warnings.length > 0) {
        setAutoSyncError(
          `${t('homepage.autoSyncWarningPrefix')} ${result.warnings.join('; ')}`,
        )
      }
      await refreshWatchlistInBackground()
    } catch {
      setAutoSyncError(t('homepage.autoSyncError'))
    } finally {
      autoSyncInFlightRef.current = false
      setIsAutoSyncing(false)
    }
  }, [currentPage, refreshWatchlistInBackground, t, watchlistItems.length])

  useEffect(() => {
    void loadWatchlist()
    void loadOverview()
  }, [loadOverview, loadWatchlist])

  useEffect(() => {
    if (currentPage !== 'watchlist') {
      return
    }

    const refreshInterval =
      settings.homepageMode === 'live' && settings.autoRefreshEnabled
        ? window.setInterval(() => {
            void refreshWatchlistInBackground()
          }, settings.autoRefreshIntervalMs)
        : null

    const syncInterval =
      settings.homepageMode === 'live' && settings.autoSyncEnabled
        ? window.setInterval(() => {
            void syncHomepageBoard()
          }, settings.autoSyncIntervalMs)
        : null

    const handleVisibilityOrFocus = () => {
      if (Date.now() < interactionReadyAtRef.current || !hasLoadedWatchlist) {
        return
      }
      if (document.visibilityState !== 'visible') {
        return
      }
      if (settings.autoRefreshEnabled) {
        void refreshWatchlistInBackground()
      }
      if (settings.homepageMode === 'focused' && settings.autoSyncEnabled) {
        void syncHomepageBoard()
      }
    }

    document.addEventListener('visibilitychange', handleVisibilityOrFocus)
    window.addEventListener('focus', handleVisibilityOrFocus)

    return () => {
      if (refreshInterval !== null) {
        window.clearInterval(refreshInterval)
      }
      if (syncInterval !== null) {
        window.clearInterval(syncInterval)
      }
      document.removeEventListener('visibilitychange', handleVisibilityOrFocus)
      window.removeEventListener('focus', handleVisibilityOrFocus)
    }
  }, [
    currentPage,
    refreshWatchlistInBackground,
    hasLoadedWatchlist,
    settings.autoRefreshEnabled,
    settings.autoRefreshIntervalMs,
    settings.autoSyncEnabled,
    settings.autoSyncIntervalMs,
    settings.homepageMode,
    syncHomepageBoard,
  ])

  async function handleAdd(securityId: number) {
    try {
      await addWatchlistItem(securityId)
      await loadWatchlist()
    } catch {
      throw new Error(t('homepage.addError'))
    }
  }

  async function handleAddCustom(market: string, code: string) {
    try {
      await addCustomWatchlistItem(market, code)
      await loadWatchlist()
    } catch {
      throw new Error(t('homepage.addCustomError'))
    }
  }

  async function handleRemove(securityId: number) {
    try {
      await removeWatchlistItem(securityId)
      await loadWatchlist()
    } catch {
      throw new Error(t('homepage.removeError'))
    }
  }

  async function handleOpenDetail(
    securityId: number,
    originId = `watchlist-security-${securityId}`,
  ) {
    returnPosition.current = { scrollY: window.scrollY, originId }
    setCurrentPage('detail')
    setDetailViewState('loading')

    try {
      const detail = await fetchStockDetail(securityId)
      setSelectedDetail(detail)
      setDetailViewState('ready')
    } catch (error) {
      setSelectedDetail(null)
      setDetailViewState(
        error instanceof Error && error.message === 'not-found'
          ? 'not-found'
          : 'error',
      )
    }
  }

  function handleBackToWatchlist() {
    shouldRestore.current = true
    setCurrentPage('watchlist')
  }

  const homepageStatusMessage = watchlistError
    ? { tone: 'error' as const, message: watchlistError }
    : homepageAdviceError
      ? { tone: 'error' as const, message: homepageAdviceError }
      : autoSyncError
        ? { tone: 'warning' as const, message: autoSyncError }
        : watchlistInfo && watchlistInfo !== t('homepage.loadingWatchlist')
          ? { tone: 'info' as const, message: watchlistInfo }
          : null

  return (
    <div
      className={`professional-workspace professional-workspace--${settings.density}`}
    >
      <WorkspaceHeader
        onSettings={() => setIsSettingsOpen(true)}
        onSync={
          currentPage === 'watchlist'
            ? () => void syncHomepageBoard()
            : undefined
        }
        syncing={isAutoSyncing}
        syncDisabled={watchlistItems.length === 0}
      />
      <main className="workspace-content">
        {currentPage === 'detail' ? (
          <WorkspaceLoadBoundary fallback={<ScreenLoadFailure onDismiss={handleBackToWatchlist} dismissLabel={t('detail.backToWatchlist')} />}>
          <Suspense fallback={<div role="status" className="detail-loading" aria-label={t('detail.loading')}>
            <Button onClick={handleBackToWatchlist}>{t('detail.backToWatchlist')}</Button>
            <span>{t('detail.loading')}</span>
            <Skeleton aria-hidden="true"><SkeletonItem style={{ height: 360 }} /></Skeleton>
          </div>}>
          <StockDetailPage
            detail={selectedDetail}
            viewState={detailViewState}
            onBack={handleBackToWatchlist}
          />
          </Suspense>
          </WorkspaceLoadBoundary>
        ) : (
          <section
            className={`dashboard-shell dashboard-shell--${settings.density} dashboard-shell--${language}`}
            aria-label="Watchlist page shell"
          >
            {settings.showMarketIndexes ? (
              <MarketStrip
                indexes={overviewIndexes}
                loading={isLoadingOverview}
                error={overviewError}
              />
            ) : null}
            {settings.showHero ? (
              <div className="workspace-summary">
                <div>
                  <h2>{t('homepage.title')}</h2>
                  <span className="workspace-muted">
                    {t('homepage.description')}
                  </span>
                </div>
                <div className="workspace-summary-mover">
                  <span>{t('homepage.leadMover')}</span>
                  <strong>
                    {dashboardStats.leadMover
                      ? `${dashboardStats.leadMover.name} ${Number(dashboardStats.leadMover.change_percent) > 0 ? '+' : ''}${dashboardStats.leadMover.change_percent}%`
                      : t('homepage.waitingForSyncedPrices')}
                  </strong>
                </div>
              </div>
            ) : null}
            <header
              className="workspace-status-summary"
              aria-label="Homepage status"
            >
              <span className="dashboard-header-compact__item dashboard-header-compact__stat">
                <span className="dashboard-header-compact__label">
                  {t('homepage.trackedSecurities')}:
                </span>{' '}
                <strong>{dashboardStats.trackedCount}</strong>
              </span>
              <span className="dashboard-header-compact__separator" />
              <span className="dashboard-header-compact__item dashboard-header-compact__stat">
                <span className="dashboard-header-compact__label">
                  {t('homepage.syncedQuotes')}:
                </span>{' '}
                <strong>{dashboardStats.syncedCount}</strong>
              </span>
              <span className="dashboard-header-compact__separator" />
              <span className="dashboard-header-compact__item dashboard-header-compact__stat">
                <span className="dashboard-header-compact__label">
                  {t('homepage.pendingSync')}:
                </span>{' '}
                <strong>{dashboardStats.pendingSyncCount}</strong>
              </span>
              <span className="dashboard-header-compact__separator" />
              <span className="dashboard-header-compact__item">
                <span className="dashboard-header-compact__label">
                  {t('homepage.autoRefresh')}:
                </span>{' '}
                {settings.autoRefreshEnabled
                  ? isAutoRefreshing
                    ? t('homepage.refreshing')
                    : t('homepage.standby')
                  : t('homepage.disabled')}
                  <span className="dashboard-header-compact__meta workspace-refresh-time">
                    {t(
                      isWatchlistCached
                        ? 'homepage.cachedWatchlist'
                        : 'homepage.lastRefresh',
                      {
                        time: formatDateTime(lastRefreshAt),
                      },
                    )}
                  </span>
              </span>
              <span className="dashboard-header-compact__separator" />
              <span className="dashboard-header-compact__item">
                <span className="dashboard-header-compact__label">
                  {t('homepage.autoSync')}:
                </span>{' '}
                {settings.autoSyncEnabled
                  ? isAutoSyncing
                    ? t('homepage.syncing')
                    : t('homepage.standby')
                  : t('homepage.disabled')}
                {lastSyncAt && (
                  <span className="dashboard-header-compact__meta">
                    {t('homepage.lastSync', {
                      time: formatDateTime(lastSyncAt),
                    })}
                  </span>
                )}
              </span>
              <span className="dashboard-header-compact__separator" />
              <span className="dashboard-header-compact__item">
                <span className="dashboard-header-compact__label">
                  {t('homepage.boardMode')}:
                </span>{' '}
                {settings.homepageMode === 'live'
                  ? t('homepage.live')
                  : t('homepage.focused')}
              </span>
            </header>

            <div
              className={`workspace-columns${settings.showSpotlight || settings.showMacroPanel ? '' : ' workspace-columns--full'}`}
            >
              <div className="workspace-surface workspace-watchlist">
                {homepageStatusMessage ? (
                  <StatusMessage
                    tone={homepageStatusMessage.tone}
                    message={homepageStatusMessage.message}
                  />
                ) : null}
                <WatchlistWorkspace
                  items={watchlistItems}
                  loading={isLoadingWatchlist && !hasLoadedWatchlist}
                  view={watchlistView}
                  onViewChange={setWatchlistView}
                  onSearch={() => setIsSearchOpen(true)}
                  onOpenDetail={handleOpenDetail}
                  onRemove={handleRemove}
                  adviceLabels={homepageAdviceLabels}
                  showAiTags={settings.showAiTags}
                />
                {isLoadingWatchlist && !hasLoadedWatchlist ? (
                  <Skeleton
                    aria-label={t('homepage.loadingWatchlist')}
                    className="watchlist-skeleton"
                  >
                    <div className="watchlist-skeleton-header"><SkeletonItem size={12} style={{ width: '70%' }} /></div>
                    {[1, 2, 3, 4, 5].map((id) => (
                      <div className="watchlist-skeleton-row" key={id}>
                        <div><SkeletonItem size={16} /><SkeletonItem size={8} style={{ width: '60%' }} /></div>
                        <SkeletonItem size={16} />
                        <SkeletonItem size={16} />
                      </div>
                    ))}
                  </Skeleton>
                ) : null}
              </div>
              {settings.showSpotlight || settings.showMacroPanel ? (
                <WorkspaceAside
                  showSpotlight={settings.showSpotlight}
                  showMacro={settings.showMacroPanel}
                  spotlight={spotlightItem}
                  spotlightLoading={isLoadingWatchlist && !hasLoadedWatchlist}
                  macro={overviewMacro}
                  loading={isLoadingOverview}
                  error={overviewError}
                  onOpenDetail={handleOpenDetail}
                />
              ) : null}
            </div>
            {overviewWarnings.length ? (
              <p className="workspace-muted">
                {t('homepage.overviewWarningPrefix')}{' '}
                {overviewWarnings.join('; ')}
              </p>
            ) : null}
            {overviewUpdatedAt ? (
              <p className="workspace-source-time">
                {t('homepage.overviewUpdatedAt', {
                  time: formatDateTime(overviewUpdatedAt),
                })}
              </p>
            ) : null}
          </section>
        )}
        <footer className="workspace-footer">
          {t('workspace.disclaimer')}
        </footer>
      </main>
      {isSearchOpen ? (
        <SecuritySearchDialog
          onClose={() => setIsSearchOpen(false)}
          onAdd={handleAdd}
          onAddCustom={handleAddCustom}
          addedSecurityIds={watchlistItems.map((item) => item.security_id)}
        />
      ) : null}
      {isSettingsOpen ? (
        <WorkspaceLoadBoundary fallback={<SettingsLoadFallback failed onClose={() => setIsSettingsOpen(false)} />}>
        <Suspense fallback={<SettingsLoadFallback onClose={() => setIsSettingsOpen(false)} />}>
        <SettingsDrawer
          settings={settings}
          onSettingsChange={updateSettings}
          onClose={() => setIsSettingsOpen(false)}
        />
        </Suspense>
        </WorkspaceLoadBoundary>
      ) : null}
    </div>
  )
}

export default function App() {
  const [settings, setSettings] =
    useState<HomepageSettings>(loadHomepageSettings)

  useEffect(() => {
    saveHomepageSettings(settings)
  }, [settings])

  return (
    <AppThemeProvider>
      <I18nProvider language={settings.language}>
        <AppBody settings={settings} onSettingsChange={setSettings} />
      </I18nProvider>
    </AppThemeProvider>
  )
}
