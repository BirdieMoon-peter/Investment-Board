import { useI18n } from '../i18n'
export function useDataCenterFormat() {
  const { t, formatDateTime } = useI18n()
  const label = (value: string | null | undefined) => {
    if (!value) return t('dataCenter.missing')
    const key = `dataCenter.${value}`
    const translated = t(key)
    return translated === key ? value.replace(/_/g, ' ') : translated
  }
  const date = (value: string | null | undefined) =>
    value ? formatDateTime(value) : t('dataCenter.missing')
  return { t, label, date }
}
