import { useEffect, useMemo, useState } from 'react'

import { useI18n } from '../i18n'
import type { StockDetailNewsItem } from '../types/watchlist'

const PAGE_SIZE = 10

interface NewsListProps {
  news: StockDetailNewsItem[]
}

export function NewsList({ news }: NewsListProps) {
  const { t, formatDateTime } = useI18n()
  const [page, setPage] = useState(1)

  useEffect(() => {
    setPage(1)
  }, [news])

  const totalPages = Math.ceil(news.length / PAGE_SIZE)
  const pagedNews = useMemo(() => {
    const start = (page - 1) * PAGE_SIZE
    return news.slice(start, start + PAGE_SIZE)
  }, [news, page])

  return (
    <section className="stock-detail-section" aria-label={t('detail.newsSection')}>
      <h2>{t('detail.news')}</h2>
      {news.length === 0 ? (
        <p>{t('detail.noNews')}</p>
      ) : (
        <>
          <ul className="stock-detail-list">
            {pagedNews.map((newsItem) => (
              <li key={`${newsItem.published_at}-${newsItem.title}`}>
                <article>
                  <h3>
                    {newsItem.url ? (
                      <a href={newsItem.url} target="_blank" rel="noreferrer">
                        {newsItem.title}
                      </a>
                    ) : (
                      newsItem.title
                    )}
                  </h3>
                  <p className="stock-detail-subtle">
                    {[newsItem.source, formatDateTime(newsItem.published_at)].filter(Boolean).join(' · ')}
                  </p>
                  {newsItem.summary ? <p>{newsItem.summary}</p> : null}
                </article>
              </li>
            ))}
          </ul>
          {totalPages > 1 ? (
            <nav aria-label={t('detail.newsPagination')}>
              <button type="button" onClick={() => setPage((current) => current - 1)} disabled={page === 1}>
                {t('common.previous')}
              </button>
              <span>{t('common.pageOf', { page, total: totalPages })}</span>
              <button
                type="button"
                onClick={() => setPage((current) => current + 1)}
                disabled={page === totalPages}
              >
                {t('common.next')}
              </button>
            </nav>
          ) : null}
        </>
      )}
    </section>
  )
}
