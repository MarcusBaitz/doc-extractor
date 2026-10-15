/** Template detail keeps Read document primary and shows later output keys. */

import { ArrowLeft, ArrowRight, FileText, Loader2, Trash2 } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'

import { api } from '../api/client'
import type { DocumentType } from '../api/types'
import { useLanguage, useTexts } from '../i18n'
import {
  SectionHeading,
  Surface,
  Card,
  Button,
  Header,
  TextLink,
  Title,
} from '../ui/components'
import { relativeTime } from '../ui/format'

interface Props {
  typeId: number
  reading: boolean
  onBack: () => void
  onReadDocument: () => void
  onChange: () => void
  onDeleted: () => void
  onError: (error: unknown) => void
}

export function TemplateView({
  typeId,
  reading,
  onBack,
  onReadDocument,
  onChange,
  onDeleted,
  onError,
}: Props) {
  const texts = useTexts()
  const [language] = useLanguage()
  const [template, setTemplate] = useState<DocumentType | null>(null)
  const [confirmingDelete, setConfirmingDelete] = useState(false)

  useEffect(() => {
    let discarded = false
    void api
      .documentType(typeId)
      .then((v) => {
        if (!discarded) setTemplate(v)
      })
      .catch((f: unknown) => {
        if (!discarded) onError(f)
      })
    return () => {
      discarded = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [typeId])

  const deleteTemplate = useCallback(async () => {
    try {
      await api.deleteDocumentType(typeId)
      onDeleted()
    } catch (f) {
      onError(f)
    }
  }, [typeId, onDeleted, onError])

  if (!template) {
    return (
      <Surface>
        <p className="text-[13.5px] text-ink-3">…</p>
      </Surface>
    )
  }

  return (
    <Surface>
      <div className="mb-8">
        <Button variant="quiet" onClick={onBack} className="mb-2.5 !px-2.5 !py-1.5">
          <ArrowLeft size={16} />
          {texts.assistant.backToTemplates}
        </Button>

        <Header>
          <Title
            subtitle={`${texts.templates.values(template.fields.length)} · ${texts.templates.changed} ${relativeTime(template.updated_at, language, texts)}`}
          >
            {template.name}
          </Title>

          <div className="flex shrink-0 gap-2">
            <Button onClick={onChange}>{texts.templates.changeValues}</Button>
            <Button variant="primary" onClick={onReadDocument} disabled={reading}>
              {reading ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  {texts.templates.reading}
                </>
              ) : (
                <>
                  {texts.templates.readDocument}
                  <ArrowRight size={16} />
                </>
              )}
            </Button>
          </div>
        </Header>
      </div>

      <SectionHeading>{texts.assistant.values.title}</SectionHeading>
      <Card className="overflow-hidden">
        {template.fields.map((fieldSpec) => (
          <div
            key={fieldSpec.name}
            className="flex items-baseline gap-4 border-b border-line px-6 py-3.5 last:border-b-0"
          >
            <span className="grid size-6 shrink-0 place-items-center self-center text-ink-3">
              <FileText size={14} aria-hidden="true" />
            </span>
            <span className="min-w-0 flex-1">
              <span className="block font-medium">{fieldSpec.label || fieldSpec.name}</span>
              {fieldSpec.regions.length > 0 && (
                <span className="mt-0.5 block text-[12.5px] text-ink-3">
                  {texts.highlight.count(fieldSpec.regions.length)}
                </span>
              )}
            </span>
            <span className="shrink-0 font-mono text-[12.5px] text-ink-3">
              {fieldSpec.name}
            </span>
          </div>
        ))}
      </Card>

      <div className="mt-9 border-t border-line pt-5">
        {confirmingDelete ? (
          <div className="flex items-center gap-4">
            <p className="text-[13px] text-ink-2">
              {texts.templates.deleteQuestion(template.name)}
            </p>
            <div className="ml-auto flex shrink-0 gap-2">
              <Button onClick={() => setConfirmingDelete(false)}>
                {texts.templates.cancel}
              </Button>
              <Button
                onClick={() => void deleteTemplate()}
                className="!border-bad !bg-bad-bg !text-bad"
              >
                <Trash2 size={15} />
                {texts.templates.confirmDelete}
              </Button>
            </div>
          </div>
        ) : (
          <span className="text-[12.5px] text-ink-3">
            <TextLink onClick={() => setConfirmingDelete(true)}>
              {texts.templates.delete}
            </TextLink>
          </span>
        )}
      </div>
    </Surface>
  )
}
