import { FormEvent, useEffect, useState } from 'react'

import { useI18n } from '../i18n'
import { searchSecurities } from '../api/watchlist'
import { StatusMessage } from './StatusMessage'
import type { SecuritySearchResult } from '../types/watchlist'

function inferDefaultMarket(query: string) {
  if (/^(6|9)\d{5}$/.test(query)) {
    return 'SH'
  }
  if (/^(0|2|3)\d{5}$/.test(query)) {
    return 'SZ'
  }
  return 'SZ'
}

function isCustomCodeCandidate(query: string) {
  return /^\d{6}$/.test(query)
}

interface SearchBoxProps {
  onAdd: (securityId: number) => void
  onAddCustom: (market: string, code: string) => void
}

export function SearchBox({ onAdd, onAddCustom }: SearchBoxProps) {
  const { t } = useI18n()
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SecuritySearchResult[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [hasSearched, setHasSearched] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [customMarket, setCustomMarket] = useState('SZ')

  useEffect(() => {
    const trimmedQuery = query.trim()
    if (isCustomCodeCandidate(trimmedQuery)) {
      setCustomMarket(inferDefaultMarket(trimmedQuery))
    }
  }, [query])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    const trimmedQuery = query.trim()
    setHasSearched(true)
    setErrorMessage(null)

    if (!trimmedQuery) {
      setResults([])
      return
    }

    setIsLoading(true)

    try {
      const nextResults = await searchSecurities(trimmedQuery)
      setResults(nextResults)
    } catch {
      setResults([])
      setErrorMessage(t('search.error'))
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <section className="search-box" aria-label={t('search.ariaLabel')}>
      <form className="search-box__form" onSubmit={handleSubmit}>
        <label className="watchlist-shell__search-label" htmlFor="watchlist-search">
          {t('search.label')}
        </label>
        <div className="search-box__controls">
          <input
            id="watchlist-search"
            className="watchlist-shell__search-input"
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder={t('search.placeholder')}
          />
          <button type="submit">{t('common.search')}</button>
        </div>
      </form>

      {isLoading ? <StatusMessage message={t('search.searching')} /> : null}
      {!isLoading && errorMessage ? <StatusMessage tone="error" message={errorMessage} /> : null}
      {!isLoading && !errorMessage && hasSearched && results.length === 0 ? (
        <div className="search-box__empty-state">
          <p className="dashboard-empty">{t('search.empty')}</p>
          {isCustomCodeCandidate(query.trim()) ? (
            <div className="search-box__custom-add">
              <label htmlFor="custom-stock-market">{t('search.customMarket')}</label>
              <div className="search-box__custom-add-controls">
                <select
                  id="custom-stock-market"
                  value={customMarket}
                  onChange={(event) => setCustomMarket(event.target.value)}
                >
                  <option value="SH">SH</option>
                  <option value="SZ">SZ</option>
                </select>
                <button type="button" onClick={() => onAddCustom(customMarket, query.trim())}>
                  {t('search.addCustom', { market: customMarket, code: query.trim() })}
                </button>
              </div>
            </div>
          ) : null}
        </div>
      ) : null}
      {!isLoading && results.length > 0 ? (
        <ul className="search-box__results" aria-label={t('search.results')}>
          {results.map((result) => (
            <li key={result.security_id} className="search-box__result-item">
              <div>
                <strong>{result.name}</strong>
                <div>{`${result.market}:${result.code}`}</div>
                {result.industry ? <div>{result.industry}</div> : null}
              </div>
              <button type="button" onClick={() => onAdd(result.security_id)}>
                {t('common.add')}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  )
}
