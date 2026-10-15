/** Step 3 previews real sample values and exposes output keys for integration. */

import { Braces, FileText, Table } from 'lucide-react'

import type { OutputFormat, FieldSpec, ExtractionRun } from '../../api/types'
import { useTexts } from '../../i18n'
import { SectionHeading, Card, TextInput } from '../../ui/components'
import { IDENTIFIER } from './keys'

interface Props {
  fields: FieldSpec[]
  run: ExtractionRun | null
  format: OutputFormat
  onFormat: (format: OutputFormat) => void
  onFields: (fields: FieldSpec[]) => void
}

export function StepResult({ fields, run, format, onFormat, onFields }: Props) {
  const texts = useTexts()
  const valuesMap = new Map(run?.results.map((e) => [e.field, e]) ?? [])

  const changeKey = (oldKey: string, newKey: string) => {
    onFields(fields.map((f) => (f.name === oldKey ? { ...f, name: newKey } : f)))
  }

  const errorFor = (fieldSpec: FieldSpec): string | undefined => {
    if (!IDENTIFIER.test(fieldSpec.name)) return texts.assistant.result.keyError
    if (fields.filter((f) => f.name === fieldSpec.name).length > 1) {
      return texts.assistant.result.duplicateKey
    }
    return undefined
  }

  return (
    <div className="max-w-[860px]">
      <SectionHeading>{texts.assistant.result.title}</SectionHeading>

      <div className="grid grid-cols-3 gap-3">
        <Choice
          selected={format === 'table'}
          onClick={() => onFormat('table')}
          symbol={<Table size={17} />}
          title={texts.assistant.result.table}
          detail={texts.assistant.result.tableDetail}
        />
        <Choice
          selected={format === 'file'}
          onClick={() => onFormat('file')}
          symbol={<FileText size={17} />}
          title={texts.assistant.result.file}
          detail={texts.assistant.result.fileDetail}
        />
        <Choice
          selected={false}
          locked
          onClick={() => undefined}
          symbol={<Braces size={17} />}
          title={texts.assistant.result.custom}
          detail={texts.assistant.result.customDetail}
        />
      </div>

      <SectionHeading className="mt-9">
        {texts.assistant.result.preview}
      </SectionHeading>
      <Card className="overflow-hidden bg-card-2! p-7">
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-[13px] whitespace-nowrap">
            <thead>
              <tr className="text-left text-[11.5px] text-ink-3">
                {fields.map((f) => (
                  <th key={f.name} className="pr-6 pb-2 font-medium">
                    {f.label || f.name}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="tabular-number">
              <tr className="border-t border-line">
                {fields.map((f) => {
                  const e = valuesMap.get(f.name)
                  const valueText =
                    e?.normalized !== null && e?.normalized !== undefined
                      ? String(e.normalized)
                      : (e?.value ?? '')
                  return (
                    <td
                      key={f.name}
                      className={['py-2.5 pr-6', valueText ? '' : 'text-ink-3'].join(' ')}
                    >
                      {valueText || '—'}
                    </td>
                  )
                })}
              </tr>
            </tbody>
          </table>
        </div>
      </Card>

      <SectionHeading className="mt-9">
        {texts.assistant.result.keyName}
      </SectionHeading>
      <p className="mb-4 max-w-[68ch] text-[13px] text-ink-2">
        {texts.assistant.result.keyDetail}
      </p>

      <Card className="overflow-hidden">
        {fields.map((fieldSpec) => (
          <div
            key={`${fieldSpec.label}-${fieldSpec.name}`}
            className="flex items-center gap-6 border-b border-line px-6 py-3.5 last:border-b-0"
          >
            <span className="w-[220px] shrink-0 text-[13.5px] font-medium">
              {fieldSpec.label || fieldSpec.name}
            </span>
            <span className="max-w-[280px] flex-1">
              <TextInput
                valueText={fieldSpec.name}
                onChange={(newKey) => changeKey(fieldSpec.name, newKey)}
                error={errorFor(fieldSpec)}
                mono
              />
            </span>
          </div>
        ))}
      </Card>
    </div>
  )
}

function Choice({
  selected,
  locked = false,
  onClick,
  symbol,
  title,
  detail,
}: {
  selected: boolean
  locked?: boolean
  onClick: () => void
  symbol: React.ReactNode
  title: string
  detail: string
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={locked}
      aria-pressed={selected}
      className={[
        'rounded-md border bg-card p-5 text-left transition-all duration-(--dur-1) ease-gentle',
        locked
          ? 'cursor-default border-line opacity-50'
          : selected
            ? 'border-ink shadow-[0_0_0_1px_var(--ink)]'
            : 'border-line hover:border-line-2',
      ].join(' ')}
    >
      <span className="mb-3 grid size-[34px] place-items-center rounded-sm bg-card-2 text-ink-2">
        {symbol}
      </span>
      <span className="block text-sm font-semibold tracking-[-0.015em]">{title}</span>
      <span className="mt-1 block text-[12.5px] leading-snug text-ink-2">{detail}</span>
    </button>
  )
}
