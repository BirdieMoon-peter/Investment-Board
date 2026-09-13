import { useEffect, useMemo, useRef, useState } from 'react'
import { Button, Field, Input, Select, Textarea } from '@fluentui/react-components'
import { ArrowLeft, ArrowClockwise } from '@phosphor-icons/react'

import { generateHoldingAdvice, generateStockAdvice, fetchInvestmentAdviceHistory } from '../api/investmentAdvice'
import { fetchHoldings, removeHolding, upsertHolding, updateHolding } from '../api/holdings'
import { fetchStockDetail, syncStock } from '../api/stocks'
import { useI18n } from '../i18n'
import { DetailWorkspaceTabs, type DetailGroup } from '../components/DetailWorkspaceTabs'
import { AnnouncementList } from '../components/AnnouncementList'
import { CompanyProfilePanel } from '../components/CompanyProfilePanel'
import { FinancialMetricsPanel } from '../components/FinancialMetricsPanel'
import { NewsList } from '../components/NewsList'
import { PriceContextPanel } from '../components/PriceContextPanel'
import { PriceHistoryChart } from '../components/PriceHistoryChart'
import { QuoteSummary } from '../components/QuoteSummary'
import { StatusMessage } from '../components/StatusMessage'
import { StockHeader } from '../components/StockHeader'
import { getLatestPriceContextBar, sortPriceContext } from '../priceContext'
import type { HoldingTargetHorizon, HoldingResponse } from '../types/holdings'
import type { InvestmentAdviceResponse } from '../types/investmentAdvice'
import type {
  StockDetailPageData,
  StockDetailPageViewState,
} from '../types/watchlist'

interface StockDetailPageProps {
  detail: StockDetailPageData | null
  viewState: StockDetailPageViewState
  onBack: () => void
}

interface HoldingFormState {
  quantity: string
  averageCost: string
  notes: string
  targetHorizon: '' | HoldingTargetHorizon
}

const EMPTY_HOLDING_FORM: HoldingFormState = {
  quantity: '',
  averageCost: '',
  notes: '',
  targetHorizon: '',
}

function toHoldingFormState(holding: HoldingResponse | null): HoldingFormState {
  if (!holding) {
    return EMPTY_HOLDING_FORM
  }

  return {
    quantity: holding.quantity,
    averageCost: holding.average_cost,
    notes: holding.notes ?? '',
    targetHorizon: holding.target_horizon ?? '',
  }
}

function isPositiveDecimal(value: string): boolean {
  return /^[+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/.test(value.trim()) &&
    Number.isFinite(Number(value)) && Number(value) > 0
}

function getAdviceTone(
  recommendation: InvestmentAdviceResponse['recommendation'],
): 'positive' | 'neutral' | 'negative' {
  if (recommendation === 'buy' || recommendation === 'accumulate') {
    return 'positive'
  }

  if (recommendation === 'trim' || recommendation === 'sell') {
    return 'negative'
  }

  return 'neutral'
}

export function StockDetailPage({ detail, viewState, onBack }: StockDetailPageProps) {
  const { t, formatDateTime } = useI18n()
  const [activeGroup, setActiveGroup] = useState<DetailGroup>('market')
  const [currentDetail, setCurrentDetail] = useState(detail)
  const [isSyncing, setIsSyncing] = useState(false)
  const [syncMessage, setSyncMessage] = useState<string | null>(null)
  const [syncWarningMessage, setSyncWarningMessage] = useState<string | null>(null)
  const [syncError, setSyncError] = useState<string | null>(null)
  const [holdings, setHoldings] = useState<HoldingResponse[]>([])
  const [isLoadingHoldings, setIsLoadingHoldings] = useState(false)
  const [holdingsError, setHoldingsError] = useState<string | null>(null)
  const [holdingMessage, setHoldingMessage] = useState<string | null>(null)
  const [holdingForm, setHoldingForm] = useState<HoldingFormState>(EMPTY_HOLDING_FORM)
  const [isSavingHolding, setIsSavingHolding] = useState(false)
  const [adviceHistory, setAdviceHistory] = useState<InvestmentAdviceResponse[]>([])
  const [isLoadingAdviceHistory, setIsLoadingAdviceHistory] = useState(false)
  const [isGeneratingAdvice, setIsGeneratingAdvice] = useState(false)
  const [adviceError, setAdviceError] = useState<string | null>(null)
  const [adviceMessage, setAdviceMessage] = useState<string | null>(null)
  const [selectedAdvice, setSelectedAdvice] = useState<InvestmentAdviceResponse | null>(null)
  const adviceSelectionVersionRef = useRef(0)

  useEffect(() => {
    setCurrentDetail(detail)
  }, [detail])

  const sortedPriceContext = useMemo(
    () => sortPriceContext(currentDetail?.price_context ?? []),
    [currentDetail?.price_context],
  )
  const latestPriceContextBar = useMemo(
    () => getLatestPriceContextBar(currentDetail?.price_context ?? []),
    [currentDetail?.price_context],
  )

  const currentSecurity = currentDetail?.security ?? detail?.security ?? null
  const securityName = currentSecurity?.name ?? t('detail.unknownSecurity')
  const securityId = currentSecurity?.security_id ?? null
  const currentHolding = useMemo(
    () => holdings.find((holding) => holding.security_id === securityId) ?? null,
    [holdings, securityId],
  )
  const relevantAdviceHistory = useMemo(
    () => adviceHistory.filter((item) => item.security_id === securityId),
    [adviceHistory, securityId],
  )

  useEffect(() => {
    setHoldingForm(toHoldingFormState(currentHolding))
  }, [currentHolding])

  useEffect(() => {
    if (viewState !== 'ready' || securityId === null) {
      return
    }

    let cancelled = false

    async function loadHoldings() {
      setIsLoadingHoldings(true)
      setHoldingsError(null)

      try {
        const nextHoldings = await fetchHoldings()
        if (!cancelled) {
          setHoldings(nextHoldings)
        }
      } catch (error) {
        if (!cancelled) {
          setHoldingsError(error instanceof Error ? error.message : t('detail.holdingLoadError'))
        }
      } finally {
        if (!cancelled) {
          setIsLoadingHoldings(false)
        }
      }
    }

    async function loadAdviceHistory() {
      const selectionVersion = adviceSelectionVersionRef.current
      setIsLoadingAdviceHistory(true)
      setAdviceError(null)

      try {
        const historyResponse = await fetchInvestmentAdviceHistory()
        if (cancelled || selectionVersion !== adviceSelectionVersionRef.current) {
          return
        }

        const matchingAdvice = historyResponse.items.filter((item) => item.security_id === securityId)
        setAdviceHistory(historyResponse.items)
        setSelectedAdvice(matchingAdvice[0] ?? null)
      } catch (error) {
        if (!cancelled && selectionVersion === adviceSelectionVersionRef.current) {
          setAdviceError(error instanceof Error ? error.message : t('detail.adviceLoadError'))
        }
      } finally {
        if (!cancelled && selectionVersion === adviceSelectionVersionRef.current) {
          setIsLoadingAdviceHistory(false)
        }
      }
    }

    void loadHoldings()
    void loadAdviceHistory()

    return () => {
      cancelled = true
    }
  }, [securityId, t, viewState])

  async function refreshHoldings() {
    const nextHoldings = await fetchHoldings()
    setHoldings(nextHoldings)
  }

  async function refreshAdviceHistory(preferredAdvice?: InvestmentAdviceResponse) {
    const historyResponse = await fetchInvestmentAdviceHistory()
    const matchingAdvice = historyResponse.items.filter((item) => item.security_id === securityId)
    setAdviceHistory(historyResponse.items)
    setSelectedAdvice(preferredAdvice ?? matchingAdvice[0] ?? null)
  }

  async function handleSync() {
    if (securityId === null || isSyncing) {
      return
    }

    setIsSyncing(true)
    setSyncMessage(t('detail.syncInProgress'))
    setSyncWarningMessage(null)
    setSyncError(null)

    try {
      const result = await syncStock(securityId)
      const refreshedDetail = await fetchStockDetail(securityId)
      setCurrentDetail(refreshedDetail)
      const warningCount = result.warnings.length
      const companyProfileState = result.company_profile_updated
        ? t('detail.companyProfileUpdated')
        : t('detail.companyProfileUnchanged')
      setSyncMessage(
        warningCount > 0
          ? t('detail.syncPartial', {
              announcements: result.announcements_upserted,
              newsItems: result.news_items_upserted,
              priceBars: result.price_bars_upserted,
              financialMetrics: result.financial_metrics_upserted,
              companyProfile: companyProfileState,
            })
          : t('detail.syncComplete', {
              announcements: result.announcements_upserted,
              newsItems: result.news_items_upserted,
              priceBars: result.price_bars_upserted,
              financialMetrics: result.financial_metrics_upserted,
              companyProfile: companyProfileState,
            }),
      )
      setSyncWarningMessage(
        warningCount > 0 ? t('detail.warnings', { warnings: result.warnings.join('; ') }) : null,
      )
    } catch (error) {
      setSyncMessage(null)
      setSyncWarningMessage(null)
      setSyncError(error instanceof Error ? error.message : t('detail.loadError'))
    } finally {
      setIsSyncing(false)
    }
  }

  async function handleSaveHolding() {
    if (securityId === null || isSavingHolding) {
      return
    }

    if (!holdingForm.quantity.trim() || !holdingForm.averageCost.trim()) {
      setHoldingMessage(null)
      setHoldingsError(t('detail.holdingValidationError'))
      return
    }

    if (!isPositiveDecimal(holdingForm.quantity) || !isPositiveDecimal(holdingForm.averageCost)) {
      setHoldingMessage(null)
      setHoldingsError(t(!isPositiveDecimal(holdingForm.quantity)
        ? 'detail.holdingQuantityValidationError'
        : 'detail.holdingCostValidationError'))
      return
    }

    setIsSavingHolding(true)
    setHoldingMessage(null)
    setHoldingsError(null)

    try {
      const payload = {
        security_id: securityId,
        quantity: holdingForm.quantity.trim(),
        average_cost: holdingForm.averageCost.trim(),
        notes: holdingForm.notes.trim() || null,
        target_horizon: holdingForm.targetHorizon || null,
      }

      if (currentHolding) {
        await updateHolding(currentHolding.holding_id, payload)
      } else {
        await upsertHolding(payload)
      }

      await refreshHoldings()
      setHoldingMessage(
        currentHolding ? t('detail.holdingUpdated') : t('detail.holdingSaved'),
      )
    } catch (error) {
      setHoldingMessage(null)
      setHoldingsError(error instanceof Error ? error.message : t('detail.holdingLoadError'))
    } finally {
      setIsSavingHolding(false)
    }
  }

  async function handleRemoveHolding() {
    if (!currentHolding || isSavingHolding) {
      return
    }

    setIsSavingHolding(true)
    setHoldingMessage(null)
    setHoldingsError(null)

    try {
      await removeHolding(currentHolding.holding_id)
      await refreshHoldings()
      setHoldingMessage(t('detail.holdingRemoved'))
    } catch (error) {
      setHoldingMessage(null)
      setHoldingsError(error instanceof Error ? error.message : t('detail.holdingLoadError'))
    } finally {
      setIsSavingHolding(false)
    }
  }

  async function handleGenerateAdvice(target: 'stock' | 'holding', useCache: boolean) {
    if (isGeneratingAdvice || securityId === null) {
      return
    }

    if (target === 'holding' && currentHolding === null) {
      return
    }

    adviceSelectionVersionRef.current += 1
    setIsLoadingAdviceHistory(false)
    setIsGeneratingAdvice(true)
    setAdviceError(null)
    setAdviceMessage(
      useCache
        ? target === 'holding'
          ? t('detail.loadingCachedHoldingAdvice')
          : t('detail.loadingCachedStockAdvice')
        : target === 'holding'
          ? t('detail.generatingFreshHoldingAdvice')
          : t('detail.generatingFreshStockAdvice'),
    )

    try {
      if (useCache) {
        const historyResponse = await fetchInvestmentAdviceHistory()
        const matchingAdvice = historyResponse.items.find((item) =>
          item.security_id === securityId && item.target_type === target &&
          (target === 'stock'
            ? item.target_id === securityId
            : item.target_id === currentHolding?.holding_id && item.holding_id === currentHolding?.holding_id),
        )
        setAdviceHistory(historyResponse.items)
        setSelectedAdvice(matchingAdvice ? { ...matchingAdvice, cached: true } : null)
        setAdviceMessage(t(matchingAdvice ? 'detail.adviceLoadedCached' : 'detail.noCachedAdvice'))
        return
      }

      const advice =
        target === 'holding' && currentHolding
          ? await generateHoldingAdvice(currentHolding.holding_id, false)
          : await generateStockAdvice(securityId, false)
      setSelectedAdvice(advice)
      setAdviceMessage(advice.cached ? t('detail.adviceLoadedCached') : t('detail.adviceGenerated'))
      await refreshAdviceHistory(advice)
    } catch (error) {
      setAdviceMessage(null)
      setAdviceError(error instanceof Error ? error.message : t('detail.adviceLoadError'))
    } finally {
      setIsGeneratingAdvice(false)
    }
  }

  return (
    <section className="detail-workspace" aria-label="Stock detail page shell">
      <header className="detail-workspace-header">
        <Button appearance="subtle" icon={<ArrowLeft />} onClick={onBack}>
          {t('detail.backToWatchlist')}
        </Button>
        {currentSecurity ? <StockHeader security={currentSecurity} latestBar={latestPriceContextBar} />
          : <h1>{t('detail.title')}</h1>}
        {securityId !== null ? (
          <Button appearance="primary" icon={<ArrowClockwise />} onClick={() => void handleSync()} disabled={isSyncing}>
            {isSyncing ? t('detail.syncingLatest') : t('detail.syncLatest')}
          </Button>
        ) : null}
      </header>

      {viewState === 'loading' ? <StatusMessage message={t('detail.loading')} /> : null}
      {viewState === 'error' ? (
        <StatusMessage tone="error" message={t('detail.loadError')} />
      ) : null}
      {viewState === 'not-found' ? (
        <StatusMessage tone="error" message={t('detail.notFound')} />
      ) : null}
      {viewState === 'ready' && syncError ? <StatusMessage tone="error" message={syncError} /> : null}
      {viewState === 'ready' && syncMessage ? <StatusMessage message={syncMessage} /> : null}
      {viewState === 'ready' && syncWarningMessage ? (
        <StatusMessage tone="warning" message={syncWarningMessage} />
      ) : null}

      {viewState === 'ready' && currentDetail ? (
        <DetailWorkspaceTabs active={activeGroup} onChange={setActiveGroup}
          market={<>
            <div className="detail-market-grid">
              <PriceHistoryChart priceHistory={currentDetail.price_history} />
              <aside className="detail-quote-aside">
                <QuoteSummary latestBar={latestPriceContextBar} />
                <PriceContextPanel priceContext={sortedPriceContext} />
              </aside>
            </div>
            <div className="detail-fundamentals-grid">
              <FinancialMetricsPanel financialMetrics={currentDetail.financial_metrics} />
              <CompanyProfilePanel companyProfile={currentDetail.company_profile} />
            </div>
          </>}
          news={<div className="detail-news-grid">
            <AnnouncementList announcements={currentDetail.announcements} />
            <NewsList news={currentDetail.news} />
          </div>}
          holdings={<div className="detail-holdings-grid">
          <div className="detail-holding-column">
            <section className="stock-detail-section" aria-label={t('detail.holdingsSection')}>
              <div className="dashboard-panel__header">
                <div>
                  <p className="dashboard-panel__eyebrow">{t('detail.positionContext')}</p>
                  <h2>{t('detail.holdings')}</h2>
                </div>
                <span className="dashboard-panel__hint">{t('detail.holdingsHint')}</span>
              </div>

              {isLoadingHoldings ? <StatusMessage message={t('detail.loadingHoldings')} /> : null}
              {holdingsError ? <StatusMessage tone="error" message={holdingsError} /> : null}
              {holdingMessage ? <StatusMessage message={holdingMessage} /> : null}

              {currentHolding ? (
                <dl className="stock-detail-grid holding-summary">
                  <div>
                    <dt>{t('detail.holdingQuantity')}</dt>
                    <dd>{currentHolding.quantity}</dd>
                  </div>
                  <div>
                    <dt>{t('detail.holdingAverageCost')}</dt>
                    <dd>{currentHolding.average_cost}</dd>
                  </div>
                  <div>
                    <dt>{t('detail.holdingTargetHorizon')}</dt>
                    <dd>
                      {currentHolding.target_horizon
                        ? t(`detail.holdingTargetHorizon.${currentHolding.target_horizon}`)
                        : t('detail.noneYet')}
                    </dd>
                  </div>
                  <div>
                    <dt>{t('detail.holdingNotes')}</dt>
                    <dd>{currentHolding.notes || t('detail.noneYet')}</dd>
                  </div>
                </dl>
              ) : (
                <p className="dashboard-empty">{t('detail.noHolding')}</p>
              )}

              <div className="holding-form">
                <Field label={t('detail.holdingQuantity')}>
                  <Input
                    inputMode="decimal"
                    value={holdingForm.quantity}
                    onChange={(event) =>
                      setHoldingForm((currentValue) => ({
                        ...currentValue,
                        quantity: event.target.value,
                      }))
                    }
                  />
                </Field>
                <Field label={t('detail.holdingAverageCost')}>
                  <Input
                    inputMode="decimal"
                    value={holdingForm.averageCost}
                    onChange={(event) =>
                      setHoldingForm((currentValue) => ({
                        ...currentValue,
                        averageCost: event.target.value,
                      }))
                    }
                  />
                </Field>
                <Field label={t('detail.holdingTargetHorizon')}>
                  <Select
                    value={holdingForm.targetHorizon}
                    onChange={(event) =>
                      setHoldingForm((currentValue) => ({
                        ...currentValue,
                        targetHorizon: event.target.value as HoldingFormState['targetHorizon'],
                      }))
                    }
                  >
                    <option value="">{t('detail.selectTargetHorizon')}</option>
                    <option value="swing">{t('detail.holdingTargetHorizon.swing')}</option>
                    <option value="medium_term">{t('detail.holdingTargetHorizon.medium_term')}</option>
                    <option value="long_term">{t('detail.holdingTargetHorizon.long_term')}</option>
                  </Select>
                </Field>
                <Field label={t('detail.holdingNotes')} className="holding-form__notes">
                  <Textarea
                    resize="vertical"
                    value={holdingForm.notes}
                    onChange={(event) =>
                      setHoldingForm((currentValue) => ({
                        ...currentValue,
                        notes: event.target.value,
                      }))
                    }
                  />
                </Field>
              </div>

              <div className="stock-detail-shell__actions">
                <Button appearance="primary" type="button" onClick={() => void handleSaveHolding()} disabled={isSavingHolding}>
                  {isSavingHolding
                    ? t('detail.savingHolding')
                    : currentHolding
                      ? t('detail.updateHolding')
                      : t('detail.saveHolding')}
                </Button>
                {currentHolding ? (
                  <Button
                    type="button"
                    appearance="secondary"
                    onClick={() => void handleRemoveHolding()}
                    disabled={isSavingHolding}
                  >
                    {t('detail.removeHolding')}
                  </Button>
                ) : null}
              </div>
            </section>
          </div>
          <div className="detail-advice-column">
            <section className="stock-detail-section" aria-label={t('detail.aiAdviceSection')}>
              <div className="dashboard-panel__header">
                <div>
                  <p className="dashboard-panel__eyebrow">{t('detail.aiAdviceEyebrow')}</p>
                  <h2>{t('detail.aiAdvice')}</h2>
                </div>
                <span className="dashboard-panel__hint">{t('detail.aiAdviceHint')}</span>
              </div>

              <div className="stock-detail-shell__actions">
                <Button
                  type="button"
                  onClick={() => void handleGenerateAdvice('stock', true)}
                  disabled={isGeneratingAdvice}
                >
                  {isGeneratingAdvice ? t('detail.generatingAdvice') : t('detail.loadStockAdvice')}
                </Button>
                <Button
                  type="button"
                  appearance="secondary"
                  onClick={() => void handleGenerateAdvice('stock', false)}
                  disabled={isGeneratingAdvice}
                >
                  {t('detail.refreshStockAdvice')}
                </Button>
                <Button
                  type="button"
                  appearance="secondary"
                  onClick={() => void handleGenerateAdvice('holding', true)}
                  disabled={isGeneratingAdvice || currentHolding === null}
                >
                  {t('detail.loadHoldingAdvice')}
                </Button>
                <Button
                  type="button"
                  appearance="secondary"
                  onClick={() => void handleGenerateAdvice('holding', false)}
                  disabled={isGeneratingAdvice || currentHolding === null}
                >
                  {t('detail.refreshHoldingAdvice')}
                </Button>
              </div>

              {isLoadingAdviceHistory ? <StatusMessage message={t('detail.loadingAdviceHistory')} /> : null}
              {adviceError ? <StatusMessage tone="error" message={adviceError} /> : null}
              {adviceMessage ? <StatusMessage message={adviceMessage} /> : null}

              {relevantAdviceHistory.length > 0 ? (
                <ul className="advice-history-list" aria-label={t('detail.adviceHistory')}>
                  {relevantAdviceHistory.map((item) => (
                    <li key={`${item.advice_id ?? item.generated_at}-${item.target_type}-${item.target_id}`}>
                      <Button
                        type="button"
                        className={`advice-history-item ${selectedAdvice?.generated_at === item.generated_at ? 'advice-history-item--active' : ''}`}
                        aria-pressed={selectedAdvice?.advice_id === item.advice_id && selectedAdvice?.generated_at === item.generated_at}
                        onClick={() => setSelectedAdvice(item)}
                      >
                        <span>{`${t(`detail.recommendation.${item.recommendation}`)} · ${t(`detail.confidence.${item.confidence}`)}`}</span>
                        <strong>{formatDateTime(item.generated_at)}</strong>
                      </Button>
                    </li>
                  ))}
                </ul>
              ) : null}

              {selectedAdvice ? (
                <article className={`advice-card advice-card--${getAdviceTone(selectedAdvice.recommendation)}`}>
                  <div className="advice-card__header">
                    <div>
                      <p className="dashboard-panel__eyebrow">{`${selectedAdvice.market}:${selectedAdvice.code}`}</p>
                      <h3>{selectedAdvice.name}</h3>
                    </div>
                    <div className="advice-card__badges">
                      <span className="stock-detail-meta__badge">
                        {t(`detail.recommendation.${selectedAdvice.recommendation}`)}
                      </span>
                      <span className="stock-detail-meta__badge">
                        {t(`detail.confidence.${selectedAdvice.confidence}`)}
                      </span>
                      <span className="stock-detail-meta__badge">
                        {selectedAdvice.cached ? t('detail.cachedAdvice') : t('detail.liveAdvice')}
                      </span>
                    </div>
                  </div>

                  <p className="advice-card__summary">{selectedAdvice.summary}</p>
                  <p className="stock-detail-subtle">
                    {t('detail.adviceGeneratedAt', { time: formatDateTime(selectedAdvice.generated_at) })}
                  </p>

                  <div className="advice-card__grid">
                    <section>
                      <h3>{t('detail.thesisPoints')}</h3>
                      <ul className="stock-detail-list">
                        {selectedAdvice.thesis_points.map((point) => (
                          <li key={point}>{point}</li>
                        ))}
                      </ul>
                    </section>
                    <section>
                      <h3>{t('detail.riskPoints')}</h3>
                      <ul className="stock-detail-list">
                        {selectedAdvice.risk_points.map((point) => (
                          <li key={point}>{point}</li>
                        ))}
                      </ul>
                    </section>
                  </div>

                  {selectedAdvice.position_notes.length > 0 ? (
                    <section>
                      <h3>{t('detail.positionNotes')}</h3>
                      <ul className="stock-detail-list">
                        {selectedAdvice.position_notes.map((point) => (
                          <li key={point}>{point}</li>
                        ))}
                      </ul>
                    </section>
                  ) : null}

                  {selectedAdvice.recent_catalysts.length > 0 ? (
                    <section>
                      <h3>{t('detail.recentCatalysts')}</h3>
                      <ul className="stock-detail-list">
                        {selectedAdvice.recent_catalysts.map((point) => (
                          <li key={point}>{point}</li>
                        ))}
                      </ul>
                    </section>
                  ) : null}

                  <section>
                    <h3>{t('detail.fullAnalysis')}</h3>
                    <p className="advice-card__analysis">{selectedAdvice.full_analysis}</p>
                  </section>

                  {selectedAdvice.warnings.length > 0 ? (
                    <StatusMessage
                      tone="warning"
                      message={t('detail.warnings', { warnings: selectedAdvice.warnings.join('; ') })}
                    />
                  ) : null}

                  <p className="stock-detail-subtle">{selectedAdvice.disclaimer}</p>
                </article>
              ) : (
                <p className="dashboard-empty">{t('detail.noAdviceYet')}</p>
              )}
            </section>
          </div>
          </div>}
        />
      ) : null}
    </section>
  )
}
