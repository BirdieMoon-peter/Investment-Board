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

interface SettingsLoadFallbackProps {
  failed?: boolean
  onClose: () => void
}

// The lazy entrance has the same modal/focus contract as the loaded settings.
// There is no AI draft yet, so every official dismissal route can close it.
export function SettingsLoadFallback({ failed = false, onClose }: SettingsLoadFallbackProps) {
  const { t } = useI18n()
  return (
    <OverlayDrawer open position="end" size="large" className="settings-drawer"
      onOpenChange={(_, data) => { if (!data.open) onClose() }}>
      <DrawerHeader>
        <DrawerHeaderTitle action={
          <Button appearance="subtle" aria-label={t('settings.close')} icon={<X />} onClick={onClose} />
        }>
          {t('settings.title')}
        </DrawerHeaderTitle>
      </DrawerHeader>
      <DrawerBody>
        <StatusMessage tone={failed ? 'error' : 'info'}
          message={t(failed ? 'workspace.loadFailed' : 'workspace.loadingSettings')} />
        {failed ? <Button appearance="primary" onClick={() => window.location.reload()}>
          {t('workspace.reloadPage')}
        </Button> : null}
      </DrawerBody>
    </OverlayDrawer>
  )
}
