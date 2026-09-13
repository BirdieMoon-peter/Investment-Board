import { useI18n } from '../i18n'
import type { StockDetailCompanyProfile } from '../types/watchlist'

interface CompanyProfilePanelProps {
  companyProfile: StockDetailCompanyProfile | null
}

interface CompanyProfileEntry {
  label: string
  value: string | number
  isLink?: boolean
}

export function CompanyProfilePanel({ companyProfile }: CompanyProfilePanelProps) {
  const { t } = useI18n()

  const profileFields: Array<{
    key: keyof StockDetailCompanyProfile
    label: string
  }> = [
    { key: 'full_name', label: t('detail.fullName') },
    { key: 'english_name', label: t('detail.englishName') },
    { key: 'registered_capital', label: t('detail.registeredCapital') },
    { key: 'establishment_date', label: t('detail.establishmentDate') },
    { key: 'website', label: t('detail.website') },
    { key: 'main_business', label: t('detail.mainBusiness') },
    { key: 'employees', label: t('detail.employees') },
  ]

  const entries: CompanyProfileEntry[] = companyProfile
    ? profileFields.flatMap((field) => {
        const value = companyProfile[field.key]

        return value === null
          ? []
          : [
              {
                label: field.label,
                value,
                isLink: field.key === 'website',
              },
            ]
      })
    : []

  return (
    <section className="stock-detail-section" aria-label={t('detail.companyProfileSection')}>
      <h2>{t('detail.companyProfile')}</h2>
      {entries.length === 0 ? (
        <p>{t('detail.noCompanyProfile')}</p>
      ) : (
        <ul className="stock-detail-list" aria-label={t('detail.companyProfile')}>
          {entries.map((entry) => (
            <li key={entry.label}>
              <p>
                <strong>{entry.label}</strong>
              </p>
              <p>
                {entry.isLink ? (
                  <a href={String(entry.value)} target="_blank" rel="noreferrer">
                    {entry.value}
                  </a>
                ) : (
                  entry.value
                )}
              </p>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
