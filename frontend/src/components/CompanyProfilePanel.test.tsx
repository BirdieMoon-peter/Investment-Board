import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { CompanyProfilePanel } from './CompanyProfilePanel'

describe('CompanyProfilePanel', () => {
  it('renders an empty state when no company profile is available', () => {
    render(<CompanyProfilePanel companyProfile={null} />)

    expect(screen.getByRole('heading', { name: 'Company profile', level: 2 })).toBeInTheDocument()
    expect(screen.getByText('No company profile is available yet.')).toBeInTheDocument()
    expect(screen.queryByRole('list', { name: 'Company profile' })).not.toBeInTheDocument()
  })

  it('renders the available company profile fields from the backend contract', () => {
    render(
      <CompanyProfilePanel
        companyProfile={{
          full_name: 'Ping An Bank Co., Ltd.',
          english_name: 'Ping An Bank Company Limited',
          registered_capital: '19,405,918,198 CNY',
          establishment_date: '1987-12-22',
          website: 'https://bank.pingan.com',
          main_business: 'Commercial banking services',
          employees: 41157,
        }}
      />,
    )

    expect(screen.getByRole('list', { name: 'Company profile' })).toBeInTheDocument()
    expect(screen.getByText('Full name')).toBeInTheDocument()
    expect(screen.getByText('Ping An Bank Co., Ltd.')).toBeInTheDocument()
    expect(screen.getByText('English name')).toBeInTheDocument()
    expect(screen.getByText('Ping An Bank Company Limited')).toBeInTheDocument()
    expect(screen.getByText('Registered capital')).toBeInTheDocument()
    expect(screen.getByText('19,405,918,198 CNY')).toBeInTheDocument()
    expect(screen.getByText('Establishment date')).toBeInTheDocument()
    expect(screen.getByText('1987-12-22')).toBeInTheDocument()
    expect(screen.getByText('Website')).toBeInTheDocument()
    expect(
      screen.getByRole('link', { name: 'https://bank.pingan.com' }),
    ).toHaveAttribute('href', 'https://bank.pingan.com')
    expect(
      screen.getByRole('link', { name: 'https://bank.pingan.com' }),
    ).toHaveAttribute('target', '_blank')
    expect(
      screen.getByRole('link', { name: 'https://bank.pingan.com' }),
    ).toHaveAttribute('rel', 'noreferrer')
    expect(screen.getByText('Main business')).toBeInTheDocument()
    expect(screen.getByText('Commercial banking services')).toBeInTheDocument()
    expect(screen.getByText('Employees')).toBeInTheDocument()
    expect(screen.getByText('41157')).toBeInTheDocument()
    expect(screen.queryByText('Listing date')).not.toBeInTheDocument()
    expect(screen.queryByText('Business scope')).not.toBeInTheDocument()
  })

  it('renders only fields with values when the profile is partial', () => {
    render(
      <CompanyProfilePanel
        companyProfile={{
          full_name: null,
          english_name: null,
          registered_capital: null,
          establishment_date: null,
          website: 'https://example.com',
          main_business: null,
          employees: null,
        }}
      />,
    )

    expect(screen.getByRole('list', { name: 'Company profile' })).toBeInTheDocument()
    expect(screen.getByText('Website')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'https://example.com' })).toHaveAttribute(
      'href',
      'https://example.com',
    )
    expect(screen.queryByText('Full name')).not.toBeInTheDocument()
    expect(screen.queryByText('English name')).not.toBeInTheDocument()
    expect(screen.queryByText('Registered capital')).not.toBeInTheDocument()
    expect(screen.queryByText('Establishment date')).not.toBeInTheDocument()
    expect(screen.queryByText('Main business')).not.toBeInTheDocument()
    expect(screen.queryByText('Employees')).not.toBeInTheDocument()
  })
})
