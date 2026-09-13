import {
  Button,
  Dialog,
  DialogSurface,
  DialogBody,
  DialogTitle,
  DialogContent,
} from '@fluentui/react-components'
import { X } from '@phosphor-icons/react'
import { useI18n } from '../i18n'
import { SearchBox, type SearchBoxProps } from './SearchBox'
export function SecuritySearchDialog({
  onClose,
  ...props
}: SearchBoxProps & { onClose: () => void }) {
  const { t } = useI18n()
  return (
    <Dialog
      open
      onOpenChange={(_, data) => {
        if (!data.open) onClose()
      }}
    >
      <DialogSurface className="security-search-dialog">
        <DialogBody>
          <DialogTitle
            action={
              <Button
                appearance="subtle"
                icon={<X />}
                aria-label={t('workspace.closeSearch')}
                onClick={onClose}
              />
            }
          >
            {t('homepage.searchAndAdd')}
          </DialogTitle>
          <DialogContent>
            <p className="workspace-muted">{t('homepage.searchHint')}</p>
            <SearchBox {...props} />
          </DialogContent>
        </DialogBody>
      </DialogSurface>
    </Dialog>
  )
}
