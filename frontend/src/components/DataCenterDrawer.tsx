import { useEffect, useRef, useState } from 'react'
import {
  Button,
  Dialog,
  DialogActions,
  DialogBody,
  DialogContent,
  DialogSurface,
  DialogTitle,
  DrawerBody,
  DrawerHeader,
  DrawerHeaderTitle,
  Field,
  OverlayDrawer,
  Select,
  Tab,
  TabList,
} from '@fluentui/react-components'
import { X } from '@phosphor-icons/react'
import {
  fetchDataSources,
  fetchSecurityData,
  saveDataSource,
  saveSecurityMetadata,
  syncSecurityData,
} from '../api/dataCenter'
import {
  categories,
  type DataCategory,
  type DataSource,
  type MetadataDraft,
  type PriceSource,
  type SecurityData,
  type SyncResult,
} from '../types/dataCenter'
import type { WatchlistItem } from '../types/watchlist'
import { useDataCenterFormat } from './dataCenterFormatting'
import { AcquisitionAttempts } from './AcquisitionAttempts'
import { SourceVendorDetails } from './SourceVendorDetails'
import { SecurityMetadataPanel } from './SecurityMetadataPanel'
import { StatusMessage } from './StatusMessage'
interface Props {
  items: WatchlistItem[]
  initialSecurityId?: number | null
  onClose: () => void
  onSynced: (securityId: number) => void
}
function draftFor(data: SecurityData): MetadataDraft {
  return {
    instrument_type: data.metadata.effective_instrument_type,
    benchmark_code: data.metadata.benchmark_code,
    benchmark_name: data.metadata.benchmark_name,
  }
}
export function DataCenterDrawer({ items, initialSecurityId, onClose, onSynced }: Props) {
  const { t, label, date } = useDataCenterFormat()
  const [tab, setTab] = useState<'sources' | 'datasets'>(
    initialSecurityId ? 'datasets' : 'sources',
  )
  const [sources, setSources] = useState<DataSource[]>([]),
    [vendor, setVendor] = useState('eastmoney')
  const [securityId, setSecurityId] = useState<number | null>(
    initialSecurityId && items.some((i) => i.security_id === initialSecurityId)
      ? initialSecurityId
      : (items[0]?.security_id ?? null),
  )
  const [data, setData] = useState<SecurityData | null>(null),
    [draft, setDraft] = useState<MetadataDraft | null>(null)
  const [sourceLoading, setSourceLoading] = useState(true),
    [dataLoading, setDataLoading] = useState(false)
  const [sourceError, setSourceError] = useState(false),
    [dataError, setDataError] = useState(false),
    [mutationError, setMutationError] = useState(false)
  const [busy, setBusy] = useState(false),
    [confirmDiscard, setConfirmDiscard] = useState(false),
    [pendingSecurity, setPendingSecurity] = useState<number | null>(null)
  const [sourceReload, setSourceReload] = useState(0),
    [dataReload, setDataReload] = useState(0),
    [priceSource, setPriceSource] = useState<PriceSource | ''>('')
  const [result, setResult] = useState<SyncResult | null>(null)
  const busyRef = useRef(false),
    mutationController = useRef<AbortController | null>(null),
    sourceController = useRef<AbortController | null>(null),
    securityRef = useRef(securityId)
  securityRef.current = securityId
  const dirty =
    !!draft && !!data && JSON.stringify(draft) !== JSON.stringify(draftFor(data))
  const dirtyRef = useRef(dirty)
  dirtyRef.current = dirty
  useEffect(() => {
    const controller = new AbortController()
    sourceController.current = controller
    setSourceLoading(true)
    setSourceError(false)
    fetchDataSources(controller.signal)
      .then((s) => {
        if (!controller.signal.aborted) setSources(s)
      })
      .catch(() => {
        if (!controller.signal.aborted) setSourceError(true)
      })
      .finally(() => {
        if (!controller.signal.aborted) setSourceLoading(false)
      })
    return () => controller.abort()
  }, [sourceReload])
  useEffect(() => {
    setData(null)
    setDraft(null)
    setResult(null)
    setDataError(false)
    setMutationError(false)
    if (securityId === null) return
    const controller = new AbortController()
    setDataLoading(true)
    fetchSecurityData(securityId, controller.signal)
      .then((d) => {
        if (!controller.signal.aborted) setData(d)
      })
      .catch(() => {
        if (!controller.signal.aborted) setDataError(true)
      })
      .finally(() => {
        if (!controller.signal.aborted) setDataLoading(false)
      })
    return () => controller.abort()
  }, [securityId, dataReload])
  useEffect(() => () => mutationController.current?.abort(), [])
  const selected = sources.find((s) => s.vendor_key === vendor)
  function close() {
    if (busyRef.current) return
    if (dirtyRef.current) {
      setPendingSecurity(null)
      setConfirmDiscard(true)
    } else onClose()
  }
  function chooseSecurity(next: number) {
    if (busyRef.current) return
    if (dirtyRef.current) {
      setPendingSecurity(next)
      setConfirmDiscard(true)
    } else setSecurityId(next)
  }
  async function mutate(action: (signal: AbortSignal) => Promise<void>) {
    if (busyRef.current) return
    busyRef.current = true
    setBusy(true)
    setMutationError(false)
    const c = new AbortController()
    mutationController.current = c
    try {
      await action(c.signal)
    } catch {
      if (!c.signal.aborted) setMutationError(true)
    } finally {
      if (!c.signal.aborted) {
        busyRef.current = false
        setBusy(false)
      }
    }
  }
  function retry(category: DataCategory) {
    if (securityId === null || dirtyRef.current) return
    const id = securityId
    void mutate(async (signal) => {
      const r = await syncSecurityData(
        id,
        category,
        category === 'price_history' && priceSource ? priceSource : undefined,
        signal,
      )
      if (signal.aborted || securityRef.current !== id) return
      setData(r.data)
      setResult(r)
      setSourceReload((v) => v + 1)
      // Every completed response carries authoritative health, even when no data
      // was acquired. The parent rereads saved data only; this cannot retry remotely.
      onSynced(id)
    })
  }
  function save() {
    if (!draft || securityId === null) return
    const id = securityId,
      value = {
        ...draft,
        benchmark_code: draft.benchmark_code?.trim() || null,
        benchmark_name: draft.benchmark_name?.trim() || null,
      }
    void mutate(async (signal) => {
      const d = await saveSecurityMetadata(id, value, signal)
      if (!signal.aborted && securityRef.current === id) {
        setData(d)
        setDraft(null)
        onSynced(id)
      }
    })
  }
  const validBenchmark =
    !draft?.benchmark_code || /^(SH|SZ):\d{6}$/.test(draft.benchmark_code.trim())
  return (
    <>
      <OverlayDrawer
        open
        position="end"
        size="large"
        className="data-center-drawer"
        onOpenChange={(_, d) => {
          if (!d.open && !confirmDiscard) close()
        }}
      >
        <DrawerHeader>
          <DrawerHeaderTitle
            action={
              <Button
                appearance="subtle"
                icon={<X />}
                disabled={busy}
                aria-label={t('dataCenter.close')}
                onClick={close}
              />
            }
          >
            {t('dataCenter.title')}
          </DrawerHeaderTitle>
          <p className="workspace-muted">{t('dataCenter.description')}</p>
          <TabList
            selectedValue={tab}
            onTabSelect={(_, d) => setTab(d.value as typeof tab)}
          >
            <Tab value="sources">{t('dataCenter.sources')}</Tab>
            <Tab value="datasets">{t('dataCenter.datasets')}</Tab>
          </TabList>
        </DrawerHeader>
        <DrawerBody aria-busy={busy || sourceLoading || dataLoading}>
          {busy ? <StatusMessage message={t('dataCenter.busy')} /> : null}
          {mutationError ? (
            <StatusMessage tone="error" message={t('dataCenter.error')} />
          ) : null}
          {tab === 'sources' ? (
            <>
              <Field label={t('dataCenter.vendor')}>
                <Select
                  value={vendor}
                  disabled={busy}
                  onChange={(_, d) => setVendor(d.value)}
                >
                  {['eastmoney', 'sina', 'netease', 'tencent', 'ifeng'].map((key) => (
                    <option key={key} value={key}>
                      {sources.find((s) => s.vendor_key === key)?.name ?? key}
                    </option>
                  ))}
                </Select>
              </Field>
              {sourceLoading ? <StatusMessage message={t('dataCenter.loading')} /> : null}
              {sourceError ? (
                <>
                  <StatusMessage tone="error" message={t('dataCenter.error')} />
                  <Button onClick={() => setSourceReload((v) => v + 1)} disabled={busy}>
                    {t('dataCenter.retry')}
                  </Button>
                </>
              ) : null}
              {selected ? (
                <SourceVendorDetails
                  source={selected}
                  busy={busy}
                  onEnabledChange={(enabled) => {
                    void mutate(async (signal) => {
                      // A catalog read started before this write cannot supersede
                      // the provider configuration confirmed by the PUT response.
                      sourceController.current?.abort()
                      setSourceLoading(false)
                      const updated = await saveDataSource(
                        selected.vendor_key,
                        enabled,
                        signal,
                      )
                      if (signal.aborted) return
                      setSources((ss) =>
                        ss.map((source) =>
                          source.vendor_key === updated.vendor_key ? updated : source,
                        ),
                      )
                      if (!updated.enabled && priceSource === updated.vendor_key)
                        setPriceSource('')
                    })
                  }}
                />
              ) : null}
            </>
          ) : (
            <>
              {items.length ? (
                <Field label={t('dataCenter.security')}>
                  <Select
                    value={securityId ?? ''}
                    disabled={busy}
                    onChange={(_, d) => chooseSecurity(Number(d.value))}
                  >
                    {items.map((i) => (
                      <option key={i.security_id} value={i.security_id}>
                        {i.name} ({i.market}:{i.code})
                      </option>
                    ))}
                  </Select>
                </Field>
              ) : (
                <p>{t('dataCenter.emptyWatchlist')}</p>
              )}
              {dataLoading ? <StatusMessage message={t('dataCenter.loading')} /> : null}
              {dataError ? (
                <>
                  <StatusMessage tone="error" message={t('dataCenter.error')} />
                  <Button disabled={busy} onClick={() => setDataReload((v) => v + 1)}>
                    {t('dataCenter.retry')}
                  </Button>
                </>
              ) : null}
              {data ? (
                <>
                  <section className="data-center-section">
                    <h2>{data.security.name}</h2>
                    <p className="workspace-muted">{t('dataCenter.calendar')}</p>
                    {data.metadata.effective_instrument_type === 'index' ? (
                      <StatusMessage
                        tone="warning"
                        message={t('dataCenter.indexDisclosure')}
                      />
                    ) : null}
                    <SecurityMetadataPanel
                      data={data}
                      draft={draft}
                      setDraft={setDraft}
                      busy={busy}
                      dirty={dirty}
                      validBenchmark={validBenchmark}
                      onSave={save}
                    />
                  </section>
                  {result ? (
                    <section role="status" className="data-center-section">
                      <h3>{t('dataCenter.result')}</h3>
                      {Object.entries(result.category_outcomes).map(([k, o]) => (
                        <p key={k}>
                          {label(k)}: {label(o?.outcome)} · {t('dataCenter.received')}:{' '}
                          {o?.received ?? '—'} {o?.received_count_unit ?? ''} ·{' '}
                          {t('dataCenter.written')}: {o?.written ?? '—'}{' '}
                          {o?.written_count_unit ?? ''}
                        </p>
                      ))}
                      <p className="workspace-muted">{t('dataCenter.countNote')}</p>
                      {result.warnings.map((w, i) => (
                        <p key={i}>{w}</p>
                      ))}
                    </section>
                  ) : null}
                  {categories.map((k) => {
                    const d = data.categories[k]
                    return (
                      <section key={k} className="data-center-section">
                        <div className="data-center-section-heading">
                          <h3>{label(k)}</h3>
                          <span className={`data-health data-health--${d.health}`}>
                            {label(d.health)}
                          </span>
                        </div>
                        <dl className="data-center-facts">
                          <div>
                            <dt>{t('dataCenter.source')}</dt>
                            <dd>{d.source_key ?? t('dataCenter.missing')}</dd>
                          </div>
                          <div>
                            <dt>{t('dataCenter.observation')}</dt>
                            <dd>
                              {d.observation_precision === 'date'
                                ? (d.observation_at?.slice(0, 10) ??
                                  t('dataCenter.missing'))
                                : date(d.observation_at)}
                            </dd>
                          </div>
                          <div>
                            <dt>{t('dataCenter.fetched')}</dt>
                            <dd>{date(d.fetched_at)}</dd>
                          </div>
                          <div>
                            <dt>{t('dataCenter.unit')}</dt>
                            <dd>
                              {label(d.unit)} / {label(d.frequency)}
                            </dd>
                          </div>
                          <div>
                            <dt>{t('dataCenter.basis')}</dt>
                            <dd>{label(d.valuation_basis ?? d.price_basis)}</dd>
                          </div>
                          <div>
                            <dt>{t('dataCenter.coverage')}</dt>
                            <dd>
                              {d.coverage_start ?? '—'} / {d.coverage_end ?? '—'}
                            </dd>
                          </div>
                        </dl>
                        <p className="workspace-muted">
                          {d.observation_precision === 'date'
                            ? t('dataCenter.dateOnly')
                            : d.observation_time_note}
                        </p>
                        {d.context_disclosures.map((note) => (
                          <p key={note}>{note}</p>
                        ))}
                        <details>
                          <summary>
                            {t('dataCenter.issues')} ({d.unresolved_issues.length}) /{' '}
                            {t('dataCenter.history')}
                          </summary>
                          <p>
                            {d.unit_provenance} · {d.freshness_basis} ·{' '}
                            {d.freshness_threshold_days ?? '—'}
                          </p>
                          {d.unresolved_issues.map((i) => (
                            <p key={i.id}>
                              {i.message} ({i.code})
                            </p>
                          ))}
                          <AcquisitionAttempts list={d.recent_attempts} />
                        </details>
                        {k === 'price_history' ? (
                          <Field label={t('dataCenter.priceSource')}>
                            <Select
                              value={priceSource}
                              disabled={busy || dirty || sourceLoading || sourceError}
                              onChange={(_, d) =>
                                setPriceSource(d.value as PriceSource | '')
                              }
                            >
                              <option value="">{t('dataCenter.default')}</option>
                              {(['eastmoney', 'sina', 'netease'] as const).map((key) => (
                                <option
                                  key={key}
                                  value={key}
                                  disabled={
                                    !sources.find((s) => s.vendor_key === key)?.enabled
                                  }
                                >
                                  {key} ·{' '}
                                  {label(
                                    data.metadata.effective_instrument_type === 'index'
                                      ? 'unknown'
                                      : key === 'eastmoney'
                                        ? 'qfq'
                                        : 'unknown',
                                  )}
                                </option>
                              ))}
                            </Select>
                          </Field>
                        ) : null}
                        <Button
                          disabled={
                            busy ||
                            dirty ||
                            d.health === 'not_applicable' ||
                            sourceLoading ||
                            sourceError
                          }
                          onClick={() => retry(k)}
                        >
                          {t('dataCenter.retry')} · {label(k)}
                        </Button>
                        {d.health !== 'not_applicable' ? (
                          <p className="workspace-muted">{t('dataCenter.retained')}</p>
                        ) : null}
                      </section>
                    )
                  })}
                  <section className="data-center-section">
                    <h3>{t('dataCenter.nav')}</h3>
                    {data.nav_observations.length ? (
                      <div
                        className="data-center-table-scroll"
                        tabIndex={0}
                        role="region"
                        aria-label={t('dataCenter.formats')}
                      >
                        <table>
                          <thead>
                            <tr>
                              <th>{label('date')}</th>
                              <th>{t('dataCenter.type')}</th>
                              <th>{t('dataCenter.value')}</th>
                              <th>{t('dataCenter.source')}</th>
                              <th>{t('dataCenter.fetched')}</th>
                              <th>{t('dataCenter.published')}</th>
                            </tr>
                          </thead>
                          <tbody>
                            {data.nav_observations.map((n, i) => (
                              <tr key={`${n.nav_date}-${n.nav_kind}-${i}`}>
                                <td>{n.nav_date}</td>
                                <td>{label(n.nav_kind)}</td>
                                <td>{n.value}</td>
                                <td>{n.source_key}</td>
                                <td>{date(n.fetched_at)}</td>
                                <td>{date(n.published_at)}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <p>{t('dataCenter.missing')}</p>
                    )}
                  </section>
                </>
              ) : null}
            </>
          )}
        </DrawerBody>
      </OverlayDrawer>
      <Dialog
        open={confirmDiscard}
        onOpenChange={(_, d) => {
          if (!d.open) setConfirmDiscard(false)
        }}
      >
        <DialogSurface>
          <DialogBody>
            <DialogTitle>{t('dataCenter.discardTitle')}</DialogTitle>
            <DialogContent>{t('dataCenter.manual')}</DialogContent>
            <DialogActions>
              <Button onClick={() => setConfirmDiscard(false)}>
                {t('dataCenter.continue')}
              </Button>
              <Button
                appearance="primary"
                onClick={() => {
                  setConfirmDiscard(false)
                  setDraft(null)
                  if (pendingSecurity !== null) setSecurityId(pendingSecurity)
                  else onClose()
                }}
              >
                {t('dataCenter.discard')}
              </Button>
            </DialogActions>
          </DialogBody>
        </DialogSurface>
      </Dialog>
    </>
  )
}
