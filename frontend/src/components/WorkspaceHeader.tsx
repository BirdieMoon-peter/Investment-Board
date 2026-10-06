import {
  Button,
  Select,
  useRestoreFocusTarget,
} from '@fluentui/react-components'
import { ArrowsClockwise, Database, GearSix, ChartLine } from '@phosphor-icons/react'
import { useI18n } from '../i18n'
import { useAppTheme, type ThemePreference } from '../theme'
interface Props {
  onStrategy?: () => void
  onSettings: () => void
  onDataCenter?: (origin: HTMLElement) => void
  onSync?: () => void
  syncing?: boolean
  syncDisabled?: boolean
}
export function WorkspaceHeader({
  onSettings,
  onStrategy,
  onDataCenter,
  onSync,
  syncing,
  syncDisabled,
}: Props) {
  const restoreFocusTarget = useRestoreFocusTarget()
  const { t, language } = useI18n()
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
          {onStrategy ? <Button id="strategy-workspace-trigger" icon={<ChartLine />} onClick={onStrategy} aria-label={language === 'zh' ? '策略工作台' : 'Strategy workspace'}><span className="workspace-strategy-label">{language === 'zh' ? '策略工作台' : 'Strategy workspace'}</span></Button> : null}
          {onSync ? (
            <Button
              icon={<ArrowsClockwise />}
              disabled={syncDisabled || syncing}
              onClick={onSync}
              aria-label={t(syncing ? 'homepage.syncing' : 'homepage.syncNow')}
            >
              <span className="workspace-header-sync-label">
                {t(syncing ? 'homepage.syncing' : 'homepage.syncNow')}
              </span>
            </Button>
          ) : null}
          {onDataCenter ? <Button id="data-center-trigger" {...restoreFocusTarget} icon={<Database />}
            aria-label={t('dataCenter.title')} onClick={event => onDataCenter(event.currentTarget)}>
            <span className="workspace-data-center-label">{t('dataCenter.title')}</span>
          </Button> : null}
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
