import { useId, type ReactNode } from 'react'
import { Field, Select, Tab, TabList } from '@fluentui/react-components'

import { useI18n } from '../i18n'

export type DetailGroup = 'market' | 'news' | 'holdings'
interface DetailWorkspaceTabsProps {
  active: DetailGroup
  onChange: (value: DetailGroup) => void
  market: ReactNode
  news: ReactNode
  holdings: ReactNode
}

export function DetailWorkspaceTabs({ active, onChange, ...panels }: DetailWorkspaceTabsProps) {
  const { t } = useI18n()
  const id = useId()
  const groups: DetailGroup[] = ['market', 'news', 'holdings']
  return (
    <div className="detail-workspace-tabs">
      <TabList className="detail-workspace-tabs__desktop" aria-label={t('detail.researchGroup')}
        selectedValue={active} onTabSelect={(_, data) => onChange(data.value as DetailGroup)}>
        {groups.map((group) => <Tab key={group} id={`${id}-tab-${group}`} value={group}
          aria-controls={`${id}-panel-${group}`}>{t(`detail.group.${group}`)}</Tab>)}
      </TabList>
      <Field className="detail-workspace-tabs__mobile" label={t('detail.researchGroup')}>
        <Select value={active} aria-controls={`${id}-panel-${active}`}
          onChange={(_, data) => onChange(data.value as DetailGroup)}>
          {groups.map((group) => <option key={group} value={group}>{t(`detail.group.${group}`)}</option>)}
        </Select>
      </Field>
      {groups.map((group) => (
        <section key={group} id={`${id}-panel-${group}`} role="tabpanel"
          aria-labelledby={`${id}-tab-${group}`} hidden={active !== group} inert={active !== group}
          className={`detail-workspace-panel detail-workspace-panel--${group}`}>
          {panels[group]}
        </section>
      ))}
    </div>
  )
}
