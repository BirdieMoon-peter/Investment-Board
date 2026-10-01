import type { Dispatch, SetStateAction } from 'react'
import { Button, Field, Input, Select } from '@fluentui/react-components'
import { feePercentage } from '../api/dataCenter'
import {
  instrumentTypes,
  type MetadataDraft,
  type SecurityData,
} from '../types/dataCenter'
import { useDataCenterFormat } from './dataCenterFormatting'
export function SecurityMetadataPanel({
  data,
  draft,
  setDraft,
  busy,
  dirty,
  validBenchmark,
  onSave,
}: {
  data: SecurityData
  draft: MetadataDraft | null
  setDraft: Dispatch<SetStateAction<MetadataDraft | null>>
  busy: boolean
  dirty: boolean
  validBenchmark: boolean
  onSave: () => void
}) {
  const { t, label, date } = useDataCenterFormat()
  return (
    <>
      <h3>{t('dataCenter.metadata')}</h3>
      <p>
        {label(data.metadata.effective_instrument_type)} ·{' '}
        {data.metadata.classification_origin === 'manual'
          ? t('dataCenter.manual')
          : label(data.metadata.classification_origin)}
      </p>
      <p>
        {data.metadata.benchmark_code ?? t('dataCenter.unknownBenchmark')}{' '}
        {data.metadata.benchmark_name}
      </p>
      {draft ? (
        <div className="data-center-editor">
          <Field label={t('dataCenter.type')}>
            <Select
              value={draft.instrument_type}
              disabled={busy}
              onChange={(_, d) =>
                setDraft({
                  ...draft,
                  instrument_type: d.value as MetadataDraft['instrument_type'],
                })
              }
            >
              {instrumentTypes.map((k) => (
                <option key={k} value={k}>
                  {label(k)}
                </option>
              ))}
            </Select>
          </Field>
          <Field
            label={t('dataCenter.benchmark')}
            validationState={validBenchmark ? 'none' : 'error'}
            validationMessage={
              validBenchmark
                ? t('dataCenter.benchmarkHint')
                : t('dataCenter.invalidBenchmark')
            }
          >
            <Input
              value={draft.benchmark_code ?? ''}
              disabled={busy}
              onChange={(_, d) => setDraft({ ...draft, benchmark_code: d.value || null })}
            />
          </Field>
          <Field label={t('dataCenter.benchmarkName')}>
            <Input
              value={draft.benchmark_name ?? ''}
              maxLength={500}
              disabled={busy}
              onChange={(_, d) => setDraft({ ...draft, benchmark_name: d.value || null })}
            />
          </Field>
          <div className="data-center-actions">
            <Button
              appearance="primary"
              disabled={busy || !dirty || !validBenchmark}
              onClick={onSave}
            >
              {t('dataCenter.save')}
            </Button>
            <Button disabled={busy} onClick={() => setDraft(null)}>
              {t('dataCenter.cancel')}
            </Button>
          </div>
        </div>
      ) : (
        <Button
          disabled={busy}
          onClick={() =>
            setDraft({
              instrument_type: data.metadata.effective_instrument_type,
              benchmark_code: data.metadata.benchmark_code,
              benchmark_name: data.metadata.benchmark_name,
            })
          }
        >
          {t('dataCenter.edit')}
        </Button>
      )}
      <h3>{t('dataCenter.provider')}</h3>
      <p className="workspace-muted">
        {data.metadata.provider_fields_source ?? t('dataCenter.missing')} ·{' '}
        {t('dataCenter.asOf')}: {data.metadata.as_of ?? t('dataCenter.missing')} ·{' '}
        {t('dataCenter.published')}: {date(data.metadata.publication_at)}
      </p>
      <dl className="data-center-facts">
        {[
          [t('dataCenter.manager'), data.metadata.manager],
          [t('dataCenter.managementFee'), feePercentage(data.metadata.management_fee)],
          [t('dataCenter.custodyFee'), feePercentage(data.metadata.custody_fee)],
          [t('dataCenter.assets'), data.metadata.fund_assets],
          [t('dataCenter.asOf'), data.metadata.assets_as_of],
        ].map(([key, value]) => (
          <div key={key}>
            <dt>{key}</dt>
            <dd>{value ?? t('dataCenter.missing')}</dd>
          </div>
        ))}
      </dl>
    </>
  )
}
