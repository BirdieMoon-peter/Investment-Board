import { useEffect, useMemo, useState } from 'react'

import { useI18n } from '../i18n'
import type { StockDetailAnnouncement } from '../types/watchlist'

const PAGE_SIZE = 10

interface AnnouncementListProps {
  announcements: StockDetailAnnouncement[]
}

export function AnnouncementList({ announcements }: AnnouncementListProps) {
  const { t, formatDateTime } = useI18n()
  const [page, setPage] = useState(1)

  useEffect(() => {
    setPage(1)
  }, [announcements])

  const totalPages = Math.ceil(announcements.length / PAGE_SIZE)
  const pagedAnnouncements = useMemo(() => {
    const start = (page - 1) * PAGE_SIZE
    return announcements.slice(start, start + PAGE_SIZE)
  }, [announcements, page])

  return (
    <section className="stock-detail-section" aria-label={t('detail.announcementsSection')}>
      <h2>{t('detail.announcements')}</h2>
      {announcements.length === 0 ? (
        <p>{t('detail.noAnnouncements')}</p>
      ) : (
        <>
          <ul className="stock-detail-list">
            {pagedAnnouncements.map((announcement) => (
              <li key={`${announcement.published_at}-${announcement.title}`}>
                <article>
                  <h3>
                    {announcement.url ? (
                      <a href={announcement.url} target="_blank" rel="noreferrer">
                        {announcement.title}
                      </a>
                    ) : (
                      announcement.title
                    )}
                  </h3>
                  <p className="stock-detail-subtle">
                    {[announcement.source, formatDateTime(announcement.published_at)].filter(Boolean).join(' · ')}
                  </p>
                  {announcement.summary ? <p>{announcement.summary}</p> : null}
                </article>
              </li>
            ))}
          </ul>
          {totalPages > 1 ? (
            <nav aria-label={t('detail.announcementsPagination')}>
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
