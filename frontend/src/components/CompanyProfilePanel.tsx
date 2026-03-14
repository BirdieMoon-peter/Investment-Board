import type { StockDetailCompanyProfile } from '../types/watchlist'

interface CompanyProfilePanelProps {
  companyProfile: StockDetailCompanyProfile | null
}

interface CompanyProfileEntry {
  label: string
  value: string | number
  isLink?: boolean
}

const profileFields: Array<{
  key: keyof StockDetailCompanyProfile
  label: string
}> = [
  { key: 'full_name', label: 'Full name' },
  { key: 'english_name', label: 'English name' },
  { key: 'registered_capital', label: 'Registered capital' },
  { key: 'establishment_date', label: 'Establishment date' },
  { key: 'website', label: 'Website' },
  { key: 'main_business', label: 'Main business' },
  { key: 'employees', label: 'Employees' },
]

export function CompanyProfilePanel({ companyProfile }: CompanyProfilePanelProps) {
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
    <section className="stock-detail-section" aria-label="Company profile section">
      <h2>Company profile</h2>
      {entries.length === 0 ? (
        <p>No company profile is available yet.</p>
      ) : (
        <ul className="stock-detail-list" aria-label="Company profile">
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
