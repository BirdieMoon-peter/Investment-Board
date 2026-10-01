import type { AcquisitionAttempt } from '../types/dataCenter'
import { useDataCenterFormat } from './dataCenterFormatting'
export function AcquisitionAttempts({ list }: { list: AcquisitionAttempt[] }) {
  const { t, label, date } = useDataCenterFormat()
  return list.length ? (
    <div
      className="data-center-table-scroll"
      tabIndex={0}
      role="region"
      aria-label={t('dataCenter.formats')}
    >
      <table>
        <caption>{t('dataCenter.history')}</caption>
        <thead>
          <tr>
            <th>{t('dataCenter.source')}</th>
            <th>{t('dataCenter.datasets')}</th>
            <th>{t('dataCenter.result')}</th>
            <th>{t('dataCenter.attempt')}</th>
            <th>
              {t('dataCenter.received')} / {t('dataCenter.written')}
            </th>
          </tr>
        </thead>
        <tbody>
          {list.map((a) => (
            <tr key={a.id}>
              <td>{a.provider_key}</td>
              <td>{label(a.category)}</td>
              <td>
                {label(a.state)}
                {a.error_code ? ` (${a.error_code})` : ''}
              </td>
              <td>{date(a.finished_at ?? a.started_at)}</td>
              <td>
                {a.records_received} / {a.records_written} ({a.records_rejected})
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  ) : (
    <p className="workspace-muted">{t('dataCenter.noAttempt')}</p>
  )
}
