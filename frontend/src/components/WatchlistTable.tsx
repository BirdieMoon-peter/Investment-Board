import type { WatchlistItem } from '../types/watchlist'

interface WatchlistTableProps {
  items: WatchlistItem[]
  onOpenDetail: (securityId: number) => void
  onRemove: (securityId: number) => void
}

function formatChangePercent(value: string | null) {
  return value === null ? 'Pending sync' : `${value}%`
}

function formatLastPrice(value: string | null) {
  return value ?? 'Pending sync'
}

export function WatchlistTable({ items, onOpenDetail, onRemove }: WatchlistTableProps) {
  return (
    <table aria-label="Watchlist holdings">
      <thead>
        <tr>
          <th scope="col">Market / Code</th>
          <th scope="col">Name</th>
          <th scope="col">Industry</th>
          <th scope="col">Last price</th>
          <th scope="col">Change percent</th>
          <th scope="col">Actions</th>
        </tr>
      </thead>
      <tbody>
        {items.map((item) => (
          <tr key={item.security_id}>
            <td>{`${item.market}:${item.code}`}</td>
            <td>{item.name}</td>
            <td>{item.industry ?? '—'}</td>
            <td>{formatLastPrice(item.last_price)}</td>
            <td>{formatChangePercent(item.change_percent)}</td>
            <td>
              <button type="button" onClick={() => onOpenDetail(item.security_id)}>
                {`View details for ${item.name}`}
              </button>
              <button type="button" onClick={() => onRemove(item.security_id)}>
                {`Remove ${item.name}`}
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
