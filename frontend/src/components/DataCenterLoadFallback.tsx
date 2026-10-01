import {
  Button,
  DrawerBody,
  DrawerHeader,
  DrawerHeaderTitle,
  OverlayDrawer,
} from '@fluentui/react-components'
import { X } from '@phosphor-icons/react'
import { useI18n } from '../i18n'
import { StatusMessage } from './StatusMessage'
export function DataCenterLoadFallback({
  failed = false,
  onClose,
}: {
  failed?: boolean
  onClose: () => void
}) {
  const { t } = useI18n()
  return (
    <OverlayDrawer
      open
      position="end"
      size="large"
      className="data-center-drawer"
      onOpenChange={(_, d) => {
        if (!d.open) onClose()
      }}
    >
      <DrawerHeader>
        <DrawerHeaderTitle
          action={
            <Button
              appearance="subtle"
              icon={<X />}
              aria-label={t('dataCenter.close')}
              onClick={onClose}
            />
          }
        >
          {t('dataCenter.title')}
        </DrawerHeaderTitle>
      </DrawerHeader>
      <DrawerBody>
        <StatusMessage
          tone={failed ? 'error' : 'info'}
          message={t(failed ? 'workspace.loadFailed' : 'dataCenter.loading')}
        />
        {failed ? (
          <Button onClick={() => window.location.reload()}>
            {t('workspace.reloadPage')}
          </Button>
        ) : null}
      </DrawerBody>
    </OverlayDrawer>
  )
}
