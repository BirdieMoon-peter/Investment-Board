import { useCallback, useRef, useState } from 'react'
import {
  useRestoreFocusTarget,
  Button,
  Checkbox,
  Dialog,
  DialogActions,
  DialogBody,
  DialogContent,
  DialogSurface,
  DialogTitle,
  DrawerBody,
  DrawerHeader,
  DrawerHeaderTitle,
  Field,
  OverlayDrawer,
  Select,
  Tab,
  TabList,
} from '@fluentui/react-components'
import { X } from '@phosphor-icons/react'
import type { HomepageSettings } from '../homepageSettings'
import { useI18n } from '../i18n'
import { useAppTheme, type ThemePreference } from '../theme'
import { AiSettingsPanel, type AiPanelState } from './AiSettingsPanel'
interface Props {
  settings: HomepageSettings
  onSettingsChange: (patch: Partial<HomepageSettings>) => void
  onClose: () => void
}
export function SettingsDrawer({
  settings,
  onSettingsChange: update,
  onClose,
}: Props) {
  const restoreFocusTarget = useRestoreFocusTarget()
  const { t } = useI18n()
  const { preference, setPreference } = useAppTheme()
  const [tab, setTab] = useState<'general' | 'ai'>('general')
  const [aiVisited, setAiVisited] = useState(false)
  const [aiState, setAiState] = useState<AiPanelState>({
    dirty: false,
    busy: false,
  })
  const aiStateRef = useRef(aiState)
  const [confirmDiscard, setConfirmDiscard] = useState(false)
  const handleAiState = useCallback((state: AiPanelState) => {
    aiStateRef.current = state
    setAiState(state)
  }, [])
  const requestClose = () => {
    if (aiStateRef.current.busy) return
    if (aiStateRef.current.dirty) setConfirmDiscard(true)
    else onClose()
  }
  const toggles = [
    'showHero',
    'showSpotlight',
    'showMarketIndexes',
    'showMacroPanel',
    'showAiTags',
  ] as const
  return (
    <>
      <OverlayDrawer
        open
        position="end"
        size="large"
        className="settings-drawer"
        onOpenChange={(_, data) => {
          if (!data.open && !confirmDiscard) requestClose()
        }}
      >
        <DrawerHeader>
          <DrawerHeaderTitle
            action={
              <Button
                appearance="subtle"
                {...restoreFocusTarget}
                aria-label={t('settings.close')}
                disabled={aiState.busy}
                icon={<X />}
                onClick={requestClose}
              />
            }
          >
            {t('settings.title')}
          </DrawerHeaderTitle>
          <p className="workspace-muted">{t('settings.description')}</p>
          <TabList
            selectedValue={tab}
            onTabSelect={(_, data) => {
              const next = data.value as 'general' | 'ai'
              if (next === 'ai') setAiVisited(true)
              setTab(next)
            }}
            aria-label={t('settings.title')}
          >
            <Tab
              value="general"
              id="settings-general-tab"
              aria-controls="settings-general-panel"
            >
              {t('workspace.interfaceSettings')}
            </Tab>
            <Tab
              value="ai"
              id="settings-ai-tab"
              aria-controls="settings-ai-panel"
            >
              {t('workspace.aiSettings')}
            </Tab>
          </TabList>
        </DrawerHeader>
        <DrawerBody>
          <div
            role="tabpanel"
            id="settings-general-panel"
            aria-labelledby="settings-general-tab"
            hidden={tab !== 'general'}
          >
            <section
              className="workspace-settings-group"
              aria-label={t('settings.general')}
            >
              <h3>{t('settings.general')}</h3>
              <div className="workspace-settings-grid">
                <Field label={t('settings.homepageMode')}>
                  <Select
                    value={settings.homepageMode}
                    onChange={(_, data) =>
                      update({
                        homepageMode:
                          data.value as HomepageSettings['homepageMode'],
                      })
                    }
                  >
                    <option value="live">{t('homepage.live')}</option>
                    <option value="focused">{t('homepage.focused')}</option>
                  </Select>
                </Field>
                <Field label={t('common.language')}>
                  <Select
                    value={settings.language}
                    onChange={(_, data) =>
                      update({
                        language: data.value as HomepageSettings['language'],
                      })
                    }
                  >
                    <option value="en">{t('common.english')}</option>
                    <option value="zh">{t('common.chinese')}</option>
                  </Select>
                </Field>
                <Field label={t('settings.density')}>
                  <Select
                    value={settings.density}
                    onChange={(_, data) =>
                      update({
                        density: data.value as HomepageSettings['density'],
                      })
                    }
                  >
                    <option value="compact">{t('settings.compact')}</option>
                    <option value="comfortable">
                      {t('settings.comfortable')}
                    </option>
                  </Select>
                </Field>
                <Field label={t('workspace.theme')}>
                  <Select
                    value={preference}
                    onChange={(_, data) =>
                      setPreference(data.value as ThemePreference)
                    }
                  >
                    <option value="system">{t('workspace.themeSystem')}</option>
                    <option value="light">{t('workspace.themeLight')}</option>
                    <option value="dark">{t('workspace.themeDark')}</option>
                  </Select>
                </Field>
              </div>
            </section>
            <section
              className="workspace-settings-group"
              aria-label={t('settings.presentation')}
            >
              <h3>{t('settings.presentation')}</h3>
              <div className="workspace-settings-toggles">
                {toggles.map((key) => (
                  <Checkbox
                    key={key}
                    label={t(`settings.${key}`)}
                    checked={settings[key]}
                    onChange={(_, data) =>
                      update({ [key]: data.checked === true })
                    }
                  />
                ))}
              </div>
            </section>
            <section
              className="workspace-settings-group"
              aria-label={t('settings.automation')}
            >
              <h3>{t('settings.automation')}</h3>
              <div className="workspace-settings-grid">
                <Checkbox
                  label={t('settings.autoRefreshEnabled')}
                  checked={settings.autoRefreshEnabled}
                  onChange={(_, data) =>
                    update({ autoRefreshEnabled: data.checked === true })
                  }
                />
                <Field label={t('settings.autoRefreshInterval')}>
                  <Select
                    value={String(settings.autoRefreshIntervalMs)}
                    onChange={(_, data) =>
                      update({ autoRefreshIntervalMs: Number(data.value) })
                    }
                  >
                    {[1, 2, 5].map((value) => (
                      <option key={value} value={value * 60000}>
                        {t('settings.minutes', { value })}
                      </option>
                    ))}
                  </Select>
                </Field>
                <Checkbox
                  label={t('settings.autoSyncEnabled')}
                  checked={settings.autoSyncEnabled}
                  onChange={(_, data) =>
                    update({ autoSyncEnabled: data.checked === true })
                  }
                />
                <Field label={t('settings.autoSyncInterval')}>
                  <Select
                    value={String(settings.autoSyncIntervalMs)}
                    onChange={(_, data) =>
                      update({ autoSyncIntervalMs: Number(data.value) })
                    }
                  >
                    {[3, 5, 10].map((value) => (
                      <option key={value} value={value * 60000}>
                        {t('settings.minutes', { value })}
                      </option>
                    ))}
                  </Select>
                </Field>
              </div>
            </section>
          </div>
          <div
            role="tabpanel"
            id="settings-ai-panel"
            aria-labelledby="settings-ai-tab"
            hidden={tab !== 'ai'}
          >
            {aiVisited ? (
              <AiSettingsPanel onStateChange={handleAiState} />
            ) : null}
          </div>
        </DrawerBody>
        {confirmDiscard ? (
          <Dialog open onOpenChange={(_, data) => setConfirmDiscard(data.open)}>
            <DialogSurface>
              <DialogBody>
                <DialogTitle>{t('workspace.discardTitle')}</DialogTitle>
                <DialogContent>
                  {t('workspace.discardDescription')}
                </DialogContent>
                <DialogActions>
                  <Button
                    appearance="primary"
                    onClick={() => setConfirmDiscard(false)}
                  >
                    {t('workspace.continueEditing')}
                  </Button>
                  <Button
                    onClick={() => {
                      if (!aiStateRef.current.busy) onClose()
                    }}
                  >
                    {t('workspace.discard')}
                  </Button>
                </DialogActions>
              </DialogBody>
            </DialogSurface>
          </Dialog>
        ) : null}
      </OverlayDrawer>
    </>
  )
}
