import {
  Button,
  Select,
  useRestoreFocusTarget,
} from '@fluentui/react-components'
import { ArrowsClockwise, GearSix } from '@phosphor-icons/react'
import { useI18n } from '../i18n'
import { useAppTheme, type ThemePreference } from '../theme'
interface Props {
  onSettings: () => void
  onSync?: () => void
  syncing?: boolean
  syncDisabled?: boolean
}
export function WorkspaceHeader({
  onSettings,
  onSync,
  syncing,
  syncDisabled,
}: Props) {
  const restoreFocusTarget = useRestoreFocusTarget()
  const { t } = useI18n()
  const { preference, setPreference } = useAppTheme()
  return (
    <header className="workspace-header">
      <div className="workspace-header-inner">
        <div className="workspace-brand">
          <span className="workspace-brand-mark" aria-hidden="true">
            IB
          </span>
          <div>
            <h1>{t('common.appName')}</h1>
            <span>{t('workspace.research')}</span>
          </div>
        </div>
        <div className="workspace-header-actions">
          <Select
            aria-label={t('workspace.theme')}
            className="workspace-header-theme"
            value={preference}
            onChange={(_, data) => setPreference(data.value as ThemePreference)}
          >
            <option value="system">{t('workspace.themeSystem')}</option>
            <option value="light">{t('workspace.themeLight')}</option>
            <option value="dark">{t('workspace.themeDark')}</option>
          </Select>
          {onSync ? (
            <Button
              icon={<ArrowsClockwise />}
              disabled={syncDisabled || syncing}
              onClick={onSync}
            >
              <span>
                {t(syncing ? 'homepage.syncing' : 'homepage.syncNow')}
              </span>
            </Button>
          ) : null}
          <Button
            {...restoreFocusTarget}
            icon={<GearSix />}
            aria-label={t('settings.open')}
            onClick={onSettings}
          >
            <span className="workspace-settings-label">
              {t('settings.open')}
            </span>
          </Button>
        </div>
      </div>
    </header>
  )
}
