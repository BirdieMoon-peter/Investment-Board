import type { StockDetailNewsItem } from '../types/watchlist'

interface NewsListProps {
  news: StockDetailNewsItem[]
}

export function NewsList({ news }: NewsListProps) {
  return (
    <section className="stock-detail-section" aria-label="News section">
      <h2>News</h2>
      {news.length === 0 ? (
        <p>No news is available yet.</p>
      ) : (
        <ul className="stock-detail-list">
          {news.map((newsItem) => (
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
                  {[newsItem.source, newsItem.published_at].filter(Boolean).join(' · ')}
                </p>
                {newsItem.summary ? <p>{newsItem.summary}</p> : null}
              </article>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
