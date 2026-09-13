import { useState } from 'react'
import {
  useRestoreFocusTarget,
  Button,
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableCell,
  TableHeaderCell,
  Dialog,
  DialogSurface,
  DialogBody,
  DialogTitle,
  DialogContent,
  DialogActions,
  Menu,
  MenuTrigger,
  MenuPopover,
  MenuList,
  MenuItem,
} from '@fluentui/react-components'
import {
  DotsThree,
  ArrowUp,
  ArrowDown,
  ArrowsDownUp,
  Trash,
} from '@phosphor-icons/react'
import type { SortingState } from '@tanstack/react-table'
import { useI18n } from '../i18n'
import type { HomepageAdviceLabel } from '../types/homepageAdvice'
import type { WatchlistItem } from '../types/watchlist'
interface WatchlistTableProps {
  items: WatchlistItem[]
  adviceLabels?: Record<number, HomepageAdviceLabel>
  showAiTags?: boolean
  onOpenDetail: (securityId: number) => void
  onRemove: (securityId: number) => void | Promise<void>
  sorting?: SortingState
  onSort?: (id: string) => void
}
export function WatchlistTable({
  items,
  adviceLabels = {},
  showAiTags = true,
  onOpenDetail,
  onRemove,
  sorting = [],
  onSort,
}: WatchlistTableProps) {
  const restoreFocusTarget = useRestoreFocusTarget()
  const { t } = useI18n()
  const [removing, setRemoving] = useState<WatchlistItem | null>(null)
  const [busy, setBusy] = useState(false)
  const [removeError, setRemoveError] = useState(false)
  const headers = [
    { id: 'name', label: 'watchlist.name' },
    { id: 'last_price', label: 'watchlist.lastPrice' },
    { id: 'change_percent', label: 'watchlist.changePercent' },
  ]
  const advice = (item: WatchlistItem) => {
    const label = adviceLabels[item.security_id]
    return showAiTags && label?.recommendation ? (
      <span
        className={`watchlist-table__ai-tag watchlist-table__ai-tag--${['buy', 'accumulate'].includes(label.recommendation) ? 'positive' : ['trim', 'sell'].includes(label.recommendation) ? 'negative' : 'neutral'}`}
      >
        {t(`detail.recommendation.${label.recommendation}`)}
        {label.has_holding_context ? (
          <small className="watchlist-table__ai-meta">
            {t('homepage.holdingAware')}
          </small>
        ) : null}
      </span>
    ) : (
      <span className="workspace-muted">
        {t(showAiTags ? 'homepage.aiPending' : 'common.notAvailable')}
      </span>
    )
  }
  async function confirmRemove() {
    if (!removing || busy) return
    setBusy(true)
    setRemoveError(false)
    try {
      await onRemove(removing.security_id)
      setRemoving(null)
    } catch {
      setRemoveError(true)
    } finally {
      setBusy(false)
    }
  }
  return (
    <>
      <div className="watchlist-table-wrap">
        <Table
          className="watchlist-table workspace-table"
          aria-label={t('watchlist.tableLabel')}
        >
          <TableHeader>
            <TableRow>
              {headers.map((header) => {
                const direction = sorting.find((sort) => sort.id === header.id)
                return (
                  <TableHeaderCell
                    key={header.id}
                    scope="col"
                    aria-sort={
                      direction
                        ? direction.desc
                          ? 'descending'
                          : 'ascending'
                        : 'none'
                    }
                    className={header.id !== 'name' ? 'workspace-numeric' : ''}
                  >
                    {onSort ? (
                      <Button
                        appearance="transparent"
                        size="small"
                        onClick={() => onSort(header.id)}
                        iconPosition="after"
                        icon={
                          direction ? (
                            direction.desc ? (
                              <ArrowDown />
                            ) : (
                              <ArrowUp />
                            )
                          ) : (
                            <ArrowsDownUp />
                          )
                        }
                      >
                        {t(header.label)}
                      </Button>
                    ) : (
                      t(header.label)
                    )}
                  </TableHeaderCell>
                )
              })}
              <TableHeaderCell scope="col" className="watchlist-secondary">
                {t('watchlist.industry')}
              </TableHeaderCell>
              {showAiTags ? (
                <TableHeaderCell scope="col" className="watchlist-secondary">
                  {t('homepage.aiRecommendation')}
                </TableHeaderCell>
              ) : null}
              <TableHeaderCell scope="col">
                <span className="sr-only">{t('watchlist.actions')}</span>
              </TableHeaderCell>
            </TableRow>
          </TableHeader>
          <TableBody>
            {items.map((item) => (
              <TableRow key={item.security_id}>
                <TableCell>
                  <Button
                    id={`watchlist-security-${item.security_id}`}
                    className="security-name"
                    appearance="transparent"
                    aria-label={t('homepage.viewDetailsFor', {
                      name: item.name,
                    })}
                    onClick={() => onOpenDetail(item.security_id)}
                  >
                    {item.name}
                  </Button>
                  <span className="security-code">
                    {item.market}:{item.code}
                  </span>
                  <details className="watchlist-mobile-details">
                    <summary>{t('workspace.moreDetails')}</summary>
                    <dl>
                      <dt>{t('watchlist.industry')}</dt>
                      <dd>{item.industry ?? t('common.notAvailable')}</dd>
                      {showAiTags ? (
                        <>
                          <dt>{t('homepage.aiRecommendation')}</dt>
                          <dd>{advice(item)}</dd>
                        </>
                      ) : null}
                    </dl>
                  </details>
                </TableCell>
                <TableCell className="workspace-numeric">
                  {item.last_price ?? t('common.pendingSync')}
                </TableCell>
                <TableCell
                  className={`workspace-numeric change-${item.change_percent === null || Number(item.change_percent) === 0 ? 'neutral' : Number(item.change_percent) > 0 ? 'positive' : 'negative'}`}
                >
                  {item.change_percent === null
                    ? t('common.pendingSync')
                    : `${Number(item.change_percent) > 0 ? '+' : ''}${item.change_percent}%`}
                </TableCell>
                <TableCell className="watchlist-secondary">
                  {item.industry ?? t('common.notAvailable')}
                </TableCell>
                {showAiTags ? (
                  <TableCell className="watchlist-secondary">
                    {advice(item)}
                  </TableCell>
                ) : null}
                <TableCell className="watchlist-row-menu">
                  <Menu>
                    <MenuTrigger disableButtonEnhancement>
                      <Button
                        appearance="subtle"
                        size="small"
                        {...restoreFocusTarget}
                        icon={<DotsThree />}
                        aria-label={t('workspace.actionsFor', {
                          name: item.name,
                        })}
                      />
                    </MenuTrigger>
                    <MenuPopover>
                      <MenuList>
                        <MenuItem
                          icon={<Trash />}
                          onClick={() => {
                            setRemoving(item)
                            setRemoveError(false)
                          }}
                        >
                          {t('watchlist.remove', { name: item.name })}
                        </MenuItem>
                      </MenuList>
                    </MenuPopover>
                  </Menu>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      <Dialog
        open={removing !== null}
        onOpenChange={(_, data) => {
          if (!data.open && !busy) setRemoving(null)
        }}
      >
        <DialogSurface>
          <DialogBody>
            <DialogTitle>
              {t('workspace.removeTitle', { name: removing?.name ?? '' })}
            </DialogTitle>
            <DialogContent>
              {t('workspace.removeDescription', { name: removing?.name ?? '' })}
              {removeError ? (
                <p role="alert">{t('homepage.removeError')}</p>
              ) : null}
            </DialogContent>
            <DialogActions>
              <Button disabled={busy} onClick={() => setRemoving(null)}>
                {t('aiSettings.cancel')}
              </Button>
              <Button
                appearance="primary"
                disabled={busy}
                onClick={() => void confirmRemove()}
              >
                {t('watchlist.remove', { name: removing?.name ?? '' })}
              </Button>
            </DialogActions>
          </DialogBody>
        </DialogSurface>
      </Dialog>
    </>
  )
}
