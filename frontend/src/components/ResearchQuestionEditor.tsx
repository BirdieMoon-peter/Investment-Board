import { Button, Field, Input, Textarea } from '@fluentui/react-components'
import { useI18n } from '../i18n'
import type { ResearchDraft, ResearchProject } from '../types/research'
export function ResearchQuestionEditor({project,draft,onChange,onSave,busy,dirty}:{project:ResearchProject|null;draft:ResearchDraft;onChange:(draft:ResearchDraft)=>void;onSave:()=>void;busy:boolean;dirty:boolean}) {
  const {t}=useI18n();const readOnly=project?.status==='archived'
  return <section className="research-editor" aria-label={t('research.editor')}>
    <h3>{t(project?'research.editQuestion':'research.newQuestion')}</h3>
    {project&&<p className="stock-detail-subtle">{t('research.version')} {project.version} · {t(`research.${project.status}`)}</p>}
    <Field label={t('research.question')} required><Textarea value={draft.question} maxLength={2000} resize="vertical" disabled={busy||readOnly} onChange={(_,d)=>onChange({...draft,question:d.value})}/></Field>
    <Field label={t('research.hypothesis')}><Textarea value={draft.hypothesis} maxLength={4000} resize="vertical" disabled={busy||readOnly} onChange={(_,d)=>onChange({...draft,hypothesis:d.value})}/></Field>
    <Field label={t('research.horizon')}><Input value={draft.horizon} maxLength={200} disabled={busy||readOnly} onChange={(_,d)=>onChange({...draft,horizon:d.value})}/></Field>
    {!readOnly&&<Button appearance="primary" onClick={onSave} disabled={busy||!draft.question.trim()||(!!project&&!dirty)}>{t(busy?'research.working':'research.saveQuestion')}</Button>}
    {dirty&&<p className="stock-detail-subtle">{t('research.saveFirst')}</p>}
  </section>
}
