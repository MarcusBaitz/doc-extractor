/** Step 4 names the template and summarises exactly what will happen. */

import { Check, Loader2, Lock } from 'lucide-react'

import type { OutputFormat, FieldSpec } from '../../api/types'
import { useTexts } from '../../i18n'
import { SectionHeading, Notice, Card, Button, TextInput } from '../../ui/components'

interface Props {
  name: string
  onName: (name: string) => void
  fields: FieldSpec[]
  format: OutputFormat
  loading: boolean
  onSave: () => void
}

export function StepFinish({
  name,
  onName,
  fields,
  format,
  loading,
  onSave,
}: Props) {
  const texts = useTexts()
  const ready = name.trim().length > 0 && fields.length > 0

  return (
    <div className="max-w-[760px]">
      <SectionHeading>{texts.assistant.finish.name}</SectionHeading>
      <div className="max-w-[420px]">
        <TextInput
          valueText={name}
          onChange={onName}
          placeholder={texts.assistant.finish.namePlaceholder}
          onEnter={() => ready && onSave()}
        />
      </div>

      <Card className="mt-8 overflow-hidden">
        <Row keyName={texts.assistant.finish.summary.template}>
          {name.trim() || (
            <span className="text-ink-3">{texts.assistant.finish.nameMissing}</span>
          )}
        </Row>

        <Row keyName={texts.assistant.finish.summary.values}>
          {fields.length}
          <small className="mt-0.5 block text-[12.5px] font-normal text-ink-3">
            {fields.map((f) => f.label || f.name).join(', ')}
          </small>
        </Row>

        <Row keyName={texts.assistant.finish.summary.result}>
          {format === 'table'
            ? texts.assistant.result.table
            : texts.assistant.result.file}
        </Row>

        <Row keyName={texts.assistant.finish.summary.unclear}>
          {texts.assistant.finish.summary.unclearValue}
          <small className="mt-0.5 block text-[12.5px] font-normal text-ink-3">
            {texts.assistant.finish.summary.unclearDetail}
          </small>
        </Row>
      </Card>

      <Notice className="mt-5" tone="good" symbol={<Lock size={15} />}>
        {texts.assistant.finish.promise}
      </Notice>

      <div className="mt-8 flex items-center gap-3 border-t border-line pt-4">
        <div className="flex-1" />
        <Button variant="primary" large disabled={!ready || loading} onClick={onSave}>
          {loading ? (
            <>
              <Loader2 size={16} className="animate-spin" />
              {texts.assistant.finish.running}
            </>
          ) : (
            <>
              <Check size={16} />
              {texts.assistant.finish.save}
            </>
          )}
        </Button>
      </div>
    </div>
  )
}

function Row({
  keyName,
  children,
}: {
  keyName: string
  children: React.ReactNode
}) {
  return (
    <div className="flex gap-4 border-b border-line px-6 py-4 text-[13.5px] last:border-b-0">
      <span className="w-[170px] shrink-0 text-ink-2">{keyName}</span>
      <span className="min-w-0 font-medium">{children}</span>
    </div>
  )
}
