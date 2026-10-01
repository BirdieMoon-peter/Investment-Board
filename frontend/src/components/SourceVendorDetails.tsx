import { Switch } from '@fluentui/react-components'
import type { DataSource } from '../types/dataCenter'
import { AcquisitionAttempts } from './AcquisitionAttempts'
import { useDataCenterFormat } from './dataCenterFormatting'
export function SourceVendorDetails({
  source,
  busy,
  onEnabledChange,
}: {
  source: DataSource
  busy: boolean
  onEnabledChange: (enabled: boolean) => void
}) {
  const { t, label, date } = useDataCenterFormat()
  return (
    <section className="data-center-section">
      <h2>{source.name}</h2>
      <p>
        {t('dataCenter.registered')} · {label(source.runtime.state)}
      </p>
      <p className="workspace-muted">{t('dataCenter.scope')}</p>
      {source.configurable ? (
        <Switch
          label={t(source.enabled ? 'dataCenter.enabled' : 'dataCenter.disabled')}
          checked={source.enabled}
          disabled={busy}
          onChange={(_, d) => onEnabledChange(d.checked)}
        />
      ) : null}
      <dl className="data-center-facts">
        <div>
          <dt>{t('dataCenter.attempt')}</dt>
          <dd>
            {date(
              source.runtime.latest_attempt?.finished_at ??
                source.runtime.latest_attempt?.started_at,
            )}
          </dd>
        </div>
        <div>
          <dt>{t('dataCenter.success')}</dt>
          <dd>{date(source.runtime.last_succeeded_attempt?.finished_at)}</dd>
        </div>
      </dl>
      <AcquisitionAttempts list={source.runtime.recent_attempts} />
      {source.index_context_disclosures?.map((note) => (
        <p key={note}>{note}</p>
      ))}
      {source.endpoints.map((e) => (
        <section className="data-center-endpoint" key={`${e.key}-${e.category}`}>
          <h3>{label(e.category)}</h3>
          <p className="workspace-muted">
            {label(e.integration_scope)} · {label(e.frequency)} · {label(e.price_basis)}
          </p>
          <details>
            <summary>{t('dataCenter.formats')}</summary>
            <p>
              {e.key} · {e.payload_format}
            </p>
            <p className="data-center-code">{e.endpoint_url}</p>
            <p>{e.time_rule}</p>
            {e.limitations.map((l) => (
              <p key={l}>{l}</p>
            ))}
            <div
              className="data-center-table-scroll"
              tabIndex={0}
              role="region"
              aria-label={t('dataCenter.formats')}
            >
              <table>
                <thead>
                  <tr>
                    <th>{t('dataCenter.native')}</th>
                    <th>{t('dataCenter.normalized')}</th>
                    <th>{t('dataCenter.conversion')}</th>
                    <th>{t('dataCenter.verification')}</th>
                  </tr>
                </thead>
                <tbody>
                  {e.fields.map((f, i) => (
                    <tr key={`${f.raw_field}-${i}`}>
                      <td>
                        {f.raw_field}
                        <br />
                        {f.raw_type} · {f.raw_unit}
                      </td>
                      <td>
                        {f.target_field}
                        <br />
                        {f.normalized_type} · {f.normalized_unit}
                      </td>
                      <td>
                        {f.conversion}
                        <br />
                        {f.missing_rule}
                      </td>
                      <td>{label(f.verification)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
        </section>
      ))}
    </section>
  )
}
