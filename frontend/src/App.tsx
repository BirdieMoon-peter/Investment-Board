import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

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
import { SearchBox } from './components/SearchBox'
import { StatusMessage } from './components/StatusMessage'
import { WatchlistTable } from './components/WatchlistTable'
import { StockDetailPage } from './pages/StockDetailPage'
import type { HomepageAdviceLabel } from './types/homepageAdvice'
import type { HomepageMacroItem, HomepageMarketIndex } from './types/homepage'
import type {
  StockDetailPageData,
  StockDetailPageViewState,
  WatchlistItem,
} from './types/watchlist'

function getChangeTone(value: string | null): 'positive' | 'negative' | 'neutral' {
  if (!value) {
    return 'neutral'
  }

  const numeric = Number(value)
  if (Number.isNaN(numeric) || numeric === 0) {
    return 'neutral'
  }

  return numeric > 0 ? 'positive' : 'negative'
}

function formatSignedValue(value: string | null, suffix = ''): string {
  if (!value) {
    return '—'
  }

  const numeric = Number(value)
  if (Number.isNaN(numeric)) {
    return `${value}${suffix}`
  }

  const sign = numeric > 0 ? '+' : ''
  return `${sign}${value}${suffix}`
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
  const [currentPage, setCurrentPage] = useState<'watchlist' | 'detail'>('watchlist')
  const [selectedDetail, setSelectedDetail] = useState<StockDetailPageData | null>(null)
  const [detailViewState, setDetailViewState] = useState<StockDetailPageViewState>('ready')
  const [isLoadingWatchlist, setIsLoadingWatchlist] = useState(true)
  const [watchlistError, setWatchlistError] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [watchlistInfo, setWatchlistInfo] = useState<string>(t('homepage.loadingWatchlist'))
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
  const [overviewIndexes, setOverviewIndexes] = useState<HomepageMarketIndex[]>([])
  const [overviewMacro, setOverviewMacro] = useState<HomepageMacroItem[]>([])
  const [overviewWarnings, setOverviewWarnings] = useState<string[]>([])
  const [overviewUpdatedAt, setOverviewUpdatedAt] = useState<string | null>(null)
  const [homepageAdviceLabels, setHomepageAdviceLabels] = useState<Record<number, HomepageAdviceLabel>>({})
  const [homepageAdviceError, setHomepageAdviceError] = useState<string | null>(null)
  const [isLoadingHomepageAdvice, setIsLoadingHomepageAdvice] = useState(false)
  const [isSettingsOpen, setIsSettingsOpen] = useState(false)
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
    const syncedCount = watchlistItems.filter((item) => item.last_price !== null).length
    const pendingSyncCount = trackedCount - syncedCount
    const movers = watchlistItems.filter((item) => item.change_percent !== null)
    const leadMover = movers.reduce<WatchlistItem | null>((currentLead, item) => {
      if (item.change_percent === null) {
        return currentLead
      }

      if (currentLead?.change_percent === null || currentLead === null) {
        return item
      }

      return Number(item.change_percent) > Number(currentLead.change_percent) ? item : currentLead
    }, null)

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

  const loadHomepageAdviceLabels = useCallback(async () => {
    setIsLoadingHomepageAdvice(true)
    setHomepageAdviceError(null)

    try {
      const response = await fetchHomepageAdviceLabels()
      setHomepageAdviceLabels(
        Object.fromEntries(response.items.map((item) => [item.security_id, item]))
      )
    } catch {
      setHomepageAdviceLabels({})
      setHomepageAdviceError(t('homepage.aiLabelsUnavailable'))
    } finally {
      setIsLoadingHomepageAdvice(false)
    }
  }, [t])

  const refreshHomepageAdviceLabelsInBackground = useCallback(async () => {
    try {
      const response = await fetchHomepageAdviceLabels()
      setHomepageAdviceLabels(
        Object.fromEntries(response.items.map((item) => [item.security_id, item]))
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
        overview.warnings.map((warning) => `${warning.section}: ${warning.message}`),
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
        overview.warnings.map((warning) => `${warning.section}: ${warning.message}`),
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
      setWatchlistInfo(nextItems.length === 0 ? t('homepage.emptyWatchlist') : '')
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
      setWatchlistInfo(nextItems.length === 0 ? t('homepage.emptyWatchlist') : '')
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
  }, [currentPage, refreshOverviewInBackground, refreshHomepageAdviceLabelsInBackground, t])

  const syncHomepageBoard = useCallback(async () => {
    if (currentPage !== 'watchlist' || watchlistItems.length === 0 || autoSyncInFlightRef.current) {
      return
    }

    autoSyncInFlightRef.current = true
    setIsAutoSyncing(true)
    setAutoSyncError(null)
    try {
      const result = await syncWatchlist()
      setLastSyncAt(result.synced_at)
      if (result.warnings.length > 0) {
        setAutoSyncError(`${t('homepage.autoSyncWarningPrefix')} ${result.warnings.join('; ')}`)
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
    setActionError(null)

    try {
      await addWatchlistItem(securityId)
      await loadWatchlist()
    } catch {
      setActionError(t('homepage.addError'))
    }
  }

  async function handleAddCustom(market: string, code: string) {
    setActionError(null)

    try {
      await addCustomWatchlistItem(market, code)
      await loadWatchlist()
    } catch {
      setActionError(t('homepage.addCustomError'))
    }
  }

  async function handleRemove(securityId: number) {
    setActionError(null)

    try {
      await removeWatchlistItem(securityId)
      await loadWatchlist()
    } catch {
      setActionError(t('homepage.removeError'))
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

  const homepageStatusMessage = watchlistError
    ? { tone: 'error' as const, message: watchlistError }
    : actionError
      ? { tone: 'error' as const, message: actionError }
      : homepageAdviceError
        ? { tone: 'error' as const, message: homepageAdviceError }
        : autoSyncError
          ? { tone: 'warning' as const, message: autoSyncError }
          : isLoadingHomepageAdvice
            ? { tone: 'info' as const, message: t('homepage.loadingAiLabels') }
            : isLoadingWatchlist
              ? { tone: 'info' as const, message: watchlistInfo || t('homepage.loadingWatchlist') }
              : watchlistInfo
                ? { tone: 'info' as const, message: watchlistInfo }
                : null

  return (
    <main className="app-shell">
      {currentPage === 'detail' ? (
        <StockDetailPage
          detail={selectedDetail}
          viewState={detailViewState}
          onBack={handleBackToWatchlist}
        />
      ) : (
        <section
          className={`dashboard-shell dashboard-shell--${settings.density} dashboard-shell--${language}`}
          aria-label="Watchlist page shell"
        >
          <div className="dashboard-toolbar">
            <div>
              <p className="dashboard-toolbar__eyebrow">{t('homepage.marketOverview')}</p>
              <h2>{t('homepage.watchlist')}</h2>
            </div>
            <button
              type="button"
              className="button--ghost dashboard-toolbar__settings-toggle"
              onClick={() => void syncHomepageBoard()}
              disabled={isAutoSyncing || watchlistItems.length === 0}
            >
              {isAutoSyncing ? t('homepage.syncing') : t('homepage.syncNow')}
            </button>
            <button
              type="button"
              className="button--ghost dashboard-toolbar__settings-toggle"
              onClick={() => setIsSettingsOpen((currentValue) => !currentValue)}
            >
              {isSettingsOpen ? t('settings.close') : t('settings.open')}
            </button>
          </div>

          {isSettingsOpen ? (
            <section className="dashboard-panel dashboard-panel--settings" aria-label="Homepage settings panel">
              <div className="dashboard-panel__header">
                <div>
                  <p className="dashboard-panel__eyebrow">{t('settings.title')}</p>
                  <h2>{t('settings.title')}</h2>
                </div>
                <span className="dashboard-panel__hint">{t('settings.description')}</span>
              </div>

              <div className="settings-layout">
                <section className="settings-group settings-group--compact" aria-label={t('settings.general')}>
                  <h3>{t('settings.general')}</h3>
                  <div className="search-box__custom-add-controls">
                    <label>
                      {t('settings.homepageMode')}
                      <select
                        value={settings.homepageMode}
                        onChange={(event) =>
                          updateSettings({ homepageMode: event.target.value as HomepageSettings['homepageMode'] })
                        }
                      >
                        <option value="live">{t('homepage.live')}</option>
                        <option value="focused">{t('homepage.focused')}</option>
                      </select>
                    </label>
                    <label>
                      {t('common.language')}
                      <select
                        value={settings.language}
                        onChange={(event) =>
                          updateSettings({ language: event.target.value as HomepageSettings['language'] })
                        }
                      >
                        <option value="en">{t('common.english')}</option>
                        <option value="zh">{t('common.chinese')}</option>
                      </select>
                    </label>
                  </div>
                  <div className="search-box__custom-add-controls">
                    <label>
                      {t('settings.density')}
                      <select
                        value={settings.density}
                        onChange={(event) =>
                          updateSettings({ density: event.target.value as HomepageSettings['density'] })
                        }
                      >
                        <option value="compact">{t('settings.compact')}</option>
                        <option value="comfortable">{t('settings.comfortable')}</option>
                      </select>
                    </label>
                  </div>
                </section>

                <section className="settings-group settings-group--compact" aria-label={t('settings.presentation')}>
                  <h3>{t('settings.presentation')}</h3>
                  <div className="settings-toggles">
                    <label>
                      <input
                        type="checkbox"
                        checked={settings.showHero}
                        onChange={(event) => updateSettings({ showHero: event.target.checked })}
                      />{' '}
                      {t('settings.showHero')}
                    </label>
                    <label>
                      <input
                        type="checkbox"
                        checked={settings.showSpotlight}
                        onChange={(event) => updateSettings({ showSpotlight: event.target.checked })}
                      />{' '}
                      {t('settings.showSpotlight')}
                    </label>
                    <label>
                      <input
                        type="checkbox"
                        checked={settings.showMarketIndexes}
                        onChange={(event) => updateSettings({ showMarketIndexes: event.target.checked })}
                      />{' '}
                      {t('settings.showMarketIndexes')}
                    </label>
                    <label>
                      <input
                        type="checkbox"
                        checked={settings.showMacroPanel}
                        onChange={(event) => updateSettings({ showMacroPanel: event.target.checked })}
                      />{' '}
                      {t('settings.showMacroPanel')}
                    </label>
                    <label>
                      <input
                        type="checkbox"
                        checked={settings.showAiTags}
                        onChange={(event) => updateSettings({ showAiTags: event.target.checked })}
                      />{' '}
                      {t('settings.showAiTags')}
                    </label>
                  </div>
                </section>

                <section className="settings-group settings-group--compact" aria-label={t('settings.automation')}>
                  <h3>{t('settings.automation')}</h3>
                  <div className="search-box__custom-add-controls">
                    <label>
                      <input
                        type="checkbox"
                        checked={settings.autoRefreshEnabled}
                        onChange={(event) => updateSettings({ autoRefreshEnabled: event.target.checked })}
                      />{' '}
                      {t('settings.autoRefreshEnabled')}
                    </label>
                    <label>
                      {t('settings.autoRefreshInterval')}
                      <select
                        value={settings.autoRefreshIntervalMs}
                        onChange={(event) => updateSettings({ autoRefreshIntervalMs: Number(event.target.value) })}
                      >
                        <option value={60_000}>{t('settings.minutes', { value: 1 })}</option>
                        <option value={120_000}>{t('settings.minutes', { value: 2 })}</option>
                        <option value={300_000}>{t('settings.minutes', { value: 5 })}</option>
                      </select>
                    </label>
                  </div>
                  <div className="search-box__custom-add-controls">
                    <label>
                      <input
                        type="checkbox"
                        checked={settings.autoSyncEnabled}
                        onChange={(event) => updateSettings({ autoSyncEnabled: event.target.checked })}
                      />{' '}
                      {t('settings.autoSyncEnabled')}
                    </label>
                    <label>
                      {t('settings.autoSyncInterval')}
                      <select
                        value={settings.autoSyncIntervalMs}
                        onChange={(event) => updateSettings({ autoSyncIntervalMs: Number(event.target.value) })}
                      >
                        <option value={180_000}>{t('settings.minutes', { value: 3 })}</option>
                        <option value={300_000}>{t('settings.minutes', { value: 5 })}</option>
                        <option value={600_000}>{t('settings.minutes', { value: 10 })}</option>
                      </select>
                    </label>
                  </div>
                </section>
              </div>
            </section>
          ) : null}

          {settings.showHero ? (
            <header className="dashboard-hero">
              <div className="dashboard-hero__copy">
                <p className="watchlist-shell__eyebrow">{t('common.appName')}</p>
                <h1>{t('homepage.title')}</h1>
                <p className="watchlist-shell__description">{t('homepage.description')}</p>
                {overviewUpdatedAt ? (
                  <p className="dashboard-hero__meta">{t('homepage.overviewUpdatedAt', { time: formatDateTime(overviewUpdatedAt) })}</p>
                ) : null}
              </div>
              <div className="dashboard-hero__pulse" aria-label="Watchlist market pulse">
                <p className="dashboard-hero__pulse-label">{t('homepage.leadMover')}</p>
                <strong>
                  {dashboardStats.leadMover
                    ? `${dashboardStats.leadMover.name} ${dashboardStats.leadMover.change_percent}%`
                    : t('homepage.waitingForSyncedPrices')}
                </strong>
                <span>
                  {dashboardStats.leadMover
                    ? `${dashboardStats.leadMover.market}:${dashboardStats.leadMover.code}`
                    : t('homepage.addAndSyncPrompt')}
                </span>
              </div>
            </header>
          ) : null}

          <header className="dashboard-header-compact dashboard-header-compact--with-stats" aria-label="Homepage status">
            <span className="dashboard-header-compact__item dashboard-header-compact__stat">
              <span className="dashboard-header-compact__label">{t('homepage.trackedSecurities')}:</span>{' '}
              <strong>{dashboardStats.trackedCount}</strong>
            </span>
            <span className="dashboard-header-compact__separator" />
            <span className="dashboard-header-compact__item dashboard-header-compact__stat">
              <span className="dashboard-header-compact__label">{t('homepage.syncedQuotes')}:</span>{' '}
              <strong>{dashboardStats.syncedCount}</strong>
            </span>
            <span className="dashboard-header-compact__separator" />
            <span className="dashboard-header-compact__item dashboard-header-compact__stat">
              <span className="dashboard-header-compact__label">{t('homepage.pendingSync')}:</span>{' '}
              <strong>{dashboardStats.pendingSyncCount}</strong>
            </span>
            <span className="dashboard-header-compact__separator" />
            <span className="dashboard-header-compact__item">
              <span className="dashboard-header-compact__label">{t('homepage.autoRefresh')}:</span>{' '}
              {settings.autoRefreshEnabled
                ? isAutoRefreshing
                  ? t('homepage.refreshing')
                  : t('homepage.standby')
                : t('homepage.disabled')}
              {lastRefreshAt && (
                <span className="dashboard-header-compact__meta">
                  {t(isWatchlistCached ? 'homepage.cachedWatchlist' : 'homepage.lastRefresh', {
                    time: formatDateTime(lastRefreshAt),
                  })}
                </span>
              )}
            </span>
            <span className="dashboard-header-compact__separator" />
            <span className="dashboard-header-compact__item">
              <span className="dashboard-header-compact__label">{t('homepage.autoSync')}:</span>{' '}
              {settings.autoSyncEnabled
                ? isAutoSyncing
                  ? t('homepage.syncing')
                  : t('homepage.standby')
                : t('homepage.disabled')}
              {lastSyncAt && (
                <span className="dashboard-header-compact__meta">
                  {t('homepage.lastSync', { time: formatDateTime(lastSyncAt) })}
                </span>
              )}
            </span>
            <span className="dashboard-header-compact__separator" />
            <span className="dashboard-header-compact__item">
              <span className="dashboard-header-compact__label">{t('homepage.boardMode')}:</span>{' '}
              {settings.homepageMode === 'live' ? t('homepage.live') : t('homepage.focused')}
            </span>
          </header>

          <section className="dashboard-grid" aria-label="Homepage dashboard">
            {settings.showMarketIndexes ? (
              <div className="dashboard-panel dashboard-panel--indexes">
                <div className="dashboard-panel__header">
                  <div>
                    <p className="dashboard-panel__eyebrow">{t('homepage.marketOverview')}</p>
                    <h2>{t('homepage.marketIndexes')}</h2>
                  </div>
                  <span className="dashboard-panel__hint">{t('homepage.marketIndexesHint')}</span>
                </div>

                {overviewError ? <StatusMessage tone="error" message={overviewError} /> : null}
                {!overviewError && overviewWarnings.length > 0 ? (
                  <StatusMessage tone="warning" message={`${t('homepage.overviewWarningPrefix')} ${overviewWarnings.join('; ')}`} />
                ) : null}
                {!overviewError && isLoadingOverview ? <StatusMessage message={t('homepage.overviewLoading')} /> : null}
                {!overviewError && !isLoadingOverview && overviewIndexes.length === 0 ? (
                  <p className="dashboard-empty">{t('homepage.noIndexData')}</p>
                ) : null}
                {!overviewError && overviewIndexes.length > 0 ? (
                  <div className="market-index-grid">
                    {overviewIndexes.map((item) => {
                      const tone = getChangeTone(item.change_percent)
                      return (
                        <article key={item.key} className={`market-index-card market-index-card--${tone}`}>
                          <p className="market-index-card__name">{item.name}</p>
                          <strong>{item.last_value ?? '—'}</strong>
                          <div className="market-index-card__change-row">
                            <span>{formatSignedValue(item.change_amount)}</span>
                            <span>{formatSignedValue(item.change_percent, '%')}</span>
                          </div>
                          <span className="market-index-card__meta">
                            {item.market ? `${item.market} · ` : ''}
                            {formatDateTime(item.snapshot_time)}
                          </span>
                        </article>
                      )
                    })}
                  </div>
                ) : null}
              </div>
            ) : null}

            <div className="dashboard-panel dashboard-panel--search">
              <div className="dashboard-panel__header">
                <div>
                  <p className="dashboard-panel__eyebrow">{t('homepage.commandCenter')}</p>
                  <h2>{t('homepage.searchAndAdd')}</h2>
                </div>
                <span className="dashboard-panel__hint">{t('homepage.searchHint')}</span>
              </div>
              <SearchBox
                onAdd={(securityId) => void handleAdd(securityId)}
                onAddCustom={(market, code) => void handleAddCustom(market, code)}
              />
            </div>

            {settings.showSpotlight ? (
              <div className="dashboard-panel dashboard-panel--spotlight" aria-label="Spotlight security">
                <div className="dashboard-panel__header">
                  <div>
                    <p className="dashboard-panel__eyebrow">{t('homepage.spotlight')}</p>
                    <h2>{t('homepage.boardFocus')}</h2>
                  </div>
                  <span className="dashboard-panel__hint">{t('homepage.spotlightHint')}</span>
                </div>
                {spotlightItem ? (
                  <div className="dashboard-spotlight">
                    <div>
                      <p className="dashboard-spotlight__ticker">{`${spotlightItem.market}:${spotlightItem.code}`}</p>
                      <h3>{spotlightItem.name}</h3>
                      <p className="dashboard-spotlight__industry">
                        {spotlightItem.industry ?? t('homepage.industryPending')}
                      </p>
                    </div>
                    <dl className="dashboard-spotlight__metrics">
                      <div>
                        <dt>{t('homepage.lastPrice')}</dt>
                        <dd>{spotlightItem.last_price ?? t('common.pendingSync')}</dd>
                      </div>
                      <div>
                        <dt>{t('homepage.change')}</dt>
                        <dd>
                          {spotlightItem.change_percent
                            ? `${spotlightItem.change_percent}%`
                            : t('common.pendingSync')}
                        </dd>
                      </div>
                    </dl>
                    <button type="button" onClick={() => void handleOpenDetail(spotlightItem.security_id)}>
                      {t('homepage.viewDetailsFor', { name: spotlightItem.name })}
                    </button>
                  </div>
                ) : (
                  <p className="dashboard-empty">{t('homepage.addSecurityPrompt')}</p>
                )}
              </div>
            ) : null}

            {settings.showMacroPanel ? (
              <div className="dashboard-panel dashboard-panel--macro">
                <div className="dashboard-panel__header">
                  <div>
                    <p className="dashboard-panel__eyebrow">{t('homepage.marketOverview')}</p>
                    <h2>{t('homepage.macroPulse')}</h2>
                  </div>
                  <span className="dashboard-panel__hint">{t('homepage.macroHint')}</span>
                </div>

                {overviewError ? <StatusMessage tone="error" message={overviewError} /> : null}
                {!overviewError && isLoadingOverview ? <StatusMessage message={t('homepage.overviewLoading')} /> : null}
                {!overviewError && !isLoadingOverview && overviewMacro.length === 0 ? (
                  <p className="dashboard-empty">{t('homepage.noMacroData')}</p>
                ) : null}
                {!overviewError && overviewMacro.length > 0 ? (
                  <div className="macro-carousel" role="region" aria-label={t('homepage.macroPulse')}>
                    {overviewMacro.map((item) => (
                      <div key={item.key} className="macro-card-slide">
                        <p className="macro-card-slide__category">{item.category}</p>
                        <h3 className="macro-card-slide__title">{item.title}</h3>
                        <p className="macro-card-slide__value">
                          {item.value ?? '—'}{item.unit ?? ''}
                        </p>
                        <p className="macro-card-slide__change">{item.change_text ?? '—'}</p>
                        <p className="macro-card-slide__time">{formatDateTime(item.published_at)}</p>
                      </div>
                    ))}
                  </div>
                ) : null}
              </div>
            ) : null}

            <div className="dashboard-panel dashboard-panel--watchlist">
              <div className="dashboard-panel__header">
                <div>
                  <p className="dashboard-panel__eyebrow">{t('homepage.coreBoard')}</p>
                  <h2>{t('homepage.watchlist')}</h2>
                </div>
                <span className="dashboard-panel__hint">{t('homepage.watchlistHint')}</span>
              </div>

              {homepageStatusMessage ? <StatusMessage tone={homepageStatusMessage.tone} message={homepageStatusMessage.message} /> : null}
              {!watchlistError && !isLoadingWatchlist && watchlistItems.length > 0 ? (
                <WatchlistTable
                  items={watchlistItems}
                  adviceLabels={homepageAdviceLabels}
                  showAiTags={settings.showAiTags}
                  onOpenDetail={handleOpenDetail}
                  onRemove={(securityId) => void handleRemove(securityId)}
                />
              ) : null}
            </div>
          </section>
        </section>
      )}
    </main>
  )
}

export default function App() {
  const [settings, setSettings] = useState<HomepageSettings>(loadHomepageSettings)

  useEffect(() => {
    saveHomepageSettings(settings)
  }, [settings])

  return (
    <I18nProvider language={settings.language}>
      <AppBody settings={settings} onSettingsChange={setSettings} />
    </I18nProvider>
  )
}
