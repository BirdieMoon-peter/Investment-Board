import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { FinancialMetricsPanel } from './FinancialMetricsPanel'

describe('FinancialMetricsPanel', () => {
  it('renders an empty state when no financial metrics are available', () => {
    render(<FinancialMetricsPanel financialMetrics={[]} />)

    expect(
      screen.getByRole('heading', { name: 'Financial metrics', level: 2 }),
    ).toBeInTheDocument()
    expect(screen.getByText('No financial metrics are available yet.')).toBeInTheDocument()
    expect(screen.queryByRole('table', { name: 'Financial metrics' })).not.toBeInTheDocument()
  })

  it('renders a financial metrics table with preserved string values', () => {
    render(
      <FinancialMetricsPanel
        financialMetrics={[
          {
            report_period: '2025-Q4',
            revenue: '123456789.00',
            net_profit: '9876543.21',
            eps: '1.2300',
            roe: '15.60%',
            debt_to_asset_ratio: '42.10%',
          },
          {
            report_period: '2025-Q3',
            revenue: null,
            net_profit: null,
            eps: null,
            roe: null,
            debt_to_asset_ratio: null,
          },
        ]}
      />,
    )

    expect(screen.getByRole('table', { name: 'Financial metrics' })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'Report period' })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'Revenue' })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'Net profit' })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'EPS' })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'ROE' })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'Debt-to-asset ratio' })).toBeInTheDocument()

    expect(screen.getByRole('cell', { name: '2025-Q4' })).toBeInTheDocument()
    expect(screen.getByRole('cell', { name: '123456789.00' })).toBeInTheDocument()
    expect(screen.getByRole('cell', { name: '9876543.21' })).toBeInTheDocument()
    expect(screen.getByRole('cell', { name: '1.2300' })).toBeInTheDocument()
    expect(screen.getByRole('cell', { name: '15.60%' })).toBeInTheDocument()
    expect(screen.getByRole('cell', { name: '42.10%' })).toBeInTheDocument()

    expect(screen.getAllByRole('cell', { name: '—' })).toHaveLength(5)
  })
})
