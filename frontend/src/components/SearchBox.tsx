import { FormEvent, useEffect, useState } from 'react'

import { searchSecurities } from '../api/watchlist'
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
      setErrorMessage('Search failed. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <section aria-label="Security search">
      <form onSubmit={handleSubmit}>
        <label className="watchlist-shell__search-label" htmlFor="watchlist-search">
          Search securities
        </label>
        <input
          id="watchlist-search"
          className="watchlist-shell__search-input"
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search by code or name"
        />
        <button type="submit">Search</button>
      </form>

      {isLoading ? <p>Searching…</p> : null}
      {!isLoading && errorMessage ? <p role="alert">{errorMessage}</p> : null}
      {!isLoading && !errorMessage && hasSearched && results.length === 0 ? (
        <div>
          <p>No securities matched your search.</p>
          {isCustomCodeCandidate(query.trim()) ? (
            <div>
              <label htmlFor="custom-stock-market">Market for custom stock</label>
              <select
                id="custom-stock-market"
                value={customMarket}
                onChange={(event) => setCustomMarket(event.target.value)}
              >
                <option value="SH">SH</option>
                <option value="SZ">SZ</option>
              </select>
              <button type="button" onClick={() => onAddCustom(customMarket, query.trim())}>
                {`Add ${customMarket}:${query.trim()}`}
              </button>
            </div>
          ) : null}
        </div>
      ) : null}
      {!isLoading && results.length > 0 ? (
        <ul aria-label="Search results">
          {results.map((result) => (
            <li key={result.security_id}>
              <strong>{result.name}</strong>
              <div>{`${result.market}:${result.code}`}</div>
              {result.industry ? <div>{result.industry}</div> : null}
              <button type="button" onClick={() => onAdd(result.security_id)}>
                Add
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  )
}
