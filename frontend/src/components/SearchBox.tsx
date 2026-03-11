import { FormEvent, useState } from 'react'

import { searchSecurities } from '../api/watchlist'
import type { SecuritySearchResult } from '../types/watchlist'

interface SearchBoxProps {
  onAdd: (securityId: number) => void
}

export function SearchBox({ onAdd }: SearchBoxProps) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SecuritySearchResult[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [hasSearched, setHasSearched] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

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
        <p>No securities matched your search.</p>
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
