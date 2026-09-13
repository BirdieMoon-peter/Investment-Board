import { type FormEvent, useEffect, useRef, useState } from 'react'
import {
  Button,
  Field,
  Input,
  Select,
  Spinner,
} from '@fluentui/react-components'
import { useI18n } from '../i18n'
import { searchSecurities } from '../api/watchlist'
import { StatusMessage } from './StatusMessage'
import type { SecuritySearchResult } from '../types/watchlist'
export interface SearchBoxProps {
  onAdd: (securityId: number) => void | Promise<void>
  onAddCustom: (market: string, code: string) => void | Promise<void>
  addedSecurityIds?: number[]
}
export function SearchBox({
  onAdd,
  onAddCustom,
  addedSecurityIds = [],
}: SearchBoxProps) {
  const { t } = useI18n()
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SecuritySearchResult[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [hasSearched, setHasSearched] = useState(false)
  const [errorKey, setErrorKey] = useState<string | null>(null)
  const [customMarket, setCustomMarket] = useState('SZ')
  const [adding, setAdding] = useState<string | null>(null)
  const [added, setAdded] = useState<number[]>([])
  const [customAdded, setCustomAdded] = useState<string[]>([])
  const requestVersion = useRef(0)
  const mounted = useRef(true)
  const addInFlight = useRef(false)
  useEffect(() => {
    mounted.current = true
    return () => {
      mounted.current = false
      requestVersion.current += 1
    }
  }, [])
  function changeQuery(value: string) {
    requestVersion.current += 1
    setQuery(value)
    setResults([])
    setHasSearched(false)
    setIsLoading(false)
    setErrorKey(null)
    if (/^\d{6}$/.test(value.trim()))
      setCustomMarket(/^[69]/.test(value.trim()) ? 'SH' : 'SZ')
  }
  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const value = query.trim(),
      version = ++requestVersion.current
    setErrorKey(null)
    setResults([])
    setHasSearched(false)
    if (!value) {
      setIsLoading(false)
      return
    }
    setIsLoading(true)
    try {
      const next = await searchSecurities(value)
      if (mounted.current && requestVersion.current === version) {
        setResults(next)
        setHasSearched(true)
      }
    } catch {
      if (mounted.current && requestVersion.current === version)
        setErrorKey('search.error')
    } finally {
      if (mounted.current && requestVersion.current === version)
        setIsLoading(false)
    }
  }
  async function add(id?: number) {
    if (addInFlight.current) return
    const code = query.trim(),
      market = customMarket,
      identity = id === undefined ? `${market}:${code}` : String(id)
    if (id !== undefined && [...addedSecurityIds, ...added].includes(id)) return
    if (id === undefined && customAdded.includes(identity)) return
    const version = requestVersion.current
    addInFlight.current = true
    setAdding(identity)
    setErrorKey(null)
    try {
      if (id === undefined) await onAddCustom(market, code)
      else await onAdd(id)
      if (mounted.current) {
        if (id === undefined)
          setCustomAdded((previous) => [...previous, identity])
        else setAdded((previous) => [...previous, id])
      }
    } catch {
      if (mounted.current && requestVersion.current === version)
        setErrorKey(
          id === undefined ? 'homepage.addCustomError' : 'homepage.addError',
        )
    } finally {
      addInFlight.current = false
      if (mounted.current) setAdding(null)
    }
  }
  const customIdentity = `${customMarket}:${query.trim()}`
  return (
    <section className="security-search" aria-label={t('search.ariaLabel')}>
      <form onSubmit={handleSubmit}>
        <Field label={t('search.label')}>
          <div className="security-search-controls">
            <Input
              type="search"
              value={query}
              onChange={(_, data) => changeQuery(data.value)}
              placeholder={t('search.placeholder')}
            />
            <Button appearance="primary" type="submit">
              {t('common.search')}
            </Button>
          </div>
        </Field>
      </form>
      {isLoading ? <Spinner size="tiny" label={t('search.searching')} /> : null}
      {errorKey ? <StatusMessage tone="error" message={t(errorKey)} /> : null}
      {!isLoading && hasSearched && results.length === 0 ? (
        <div className="workspace-empty">
          <p>{t('search.empty')}</p>
          {/^\d{6}$/.test(query.trim()) ? (
            <div className="security-search-custom">
              <Field label={t('search.customMarket')}>
                <Select
                  value={customMarket}
                  disabled={adding !== null}
                  onChange={(_, data) => setCustomMarket(data.value)}
                >
                  <option value="SH">SH</option>
                  <option value="SZ">SZ</option>
                </Select>
              </Field>
              <Button
                disabled={
                  adding !== null || customAdded.includes(customIdentity)
                }
                onClick={() => void add()}
              >
                {customAdded.includes(customIdentity)
                  ? t('workspace.alreadyAdded')
                  : t('search.addCustom', {
                      market: customMarket,
                      code: query.trim(),
                    })}
              </Button>
            </div>
          ) : null}
        </div>
      ) : null}
      {!isLoading && results.length > 0 ? (
        <ul
          className="security-search-results"
          aria-label={t('search.results')}
        >
          {results.map((result) => {
            const isAdded = [...addedSecurityIds, ...added].includes(
              result.security_id,
            )
            return (
              <li key={result.security_id}>
                <div>
                  <strong>{result.name}</strong>
                  <span className="security-code">
                    {result.market}:{result.code}
                  </span>
                  {result.industry ? (
                    <span className="workspace-muted">{result.industry}</span>
                  ) : null}
                </div>
                <Button
                  disabled={isAdded || adding !== null}
                  onClick={() => void add(result.security_id)}
                >
                  {isAdded ? t('workspace.alreadyAdded') : t('common.add')}
                </Button>
              </li>
            )
          })}
        </ul>
      ) : null}
    </section>
  )
}
