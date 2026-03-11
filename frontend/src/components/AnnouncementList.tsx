import type { StockDetailAnnouncement } from '../types/watchlist'

interface AnnouncementListProps {
  announcements: StockDetailAnnouncement[]
}

export function AnnouncementList({ announcements }: AnnouncementListProps) {
  return (
    <section className="stock-detail-section" aria-label="Announcements section">
      <h2>Announcements</h2>
      {announcements.length === 0 ? (
        <p>No announcements are available yet.</p>
      ) : (
        <ul className="stock-detail-list">
          {announcements.map((announcement) => (
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
                  {[announcement.source, announcement.published_at].filter(Boolean).join(' · ')}
                </p>
                {announcement.summary ? <p>{announcement.summary}</p> : null}
              </article>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
