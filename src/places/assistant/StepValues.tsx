/**
 * Step 2 turns drawn marks into named values. The question sits below a new
 * mark, while labels remain visible throughout setup.
 */

import { Check, Info, Plus, Trash2 } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'

import type { DocumentInfo, ExtractionResult, FieldSpec, ExtractionRun } from '../../api/types'
import { useTexts } from '../../i18n'
import { SectionHeading, Notice } from '../../ui/components'
import type { Highlight } from '../../viewer/OverlayLayer'
import { ViewerHost } from '../../viewer/ViewerHost'
import { freeKey } from './keys'

interface Props {
  document: DocumentInfo
  fields: FieldSpec[]
  run: ExtractionRun | null
  onFields: (fields: FieldSpec[]) => void
  onError: (error: unknown) => void
}

/** An unnamed mark and the window position of its follow-up question. */
interface Draft {
  highlight: Highlight
  anchor: { x: number; y: number }
}

const QUESTION_WIDTH = 236

export function StepValues({ document, fields, run, onFields, onError }: Props) {
  const texts = useTexts()
  const [draft, setDraft] = useState<Draft | null>(null)
  const [chosen, setChosen] = useState<string | null>(null)

  // Marks derive from values, preventing either representation from drifting.
  const highlights = useMemo<Highlight[]>(() => {
    const result = fields.flatMap<Highlight>((f) => {
      const region = f.regions[0]
      if (!region || region.kind === 'sheet_range') return []
      return [{ id: f.name, rect: region, name: f.label || f.name }]
    })
    return draft ? [...result, draft.highlight] : result
  }, [fields, draft])

  const highlightsChanged = useCallback(
    (nextHighlights: Highlight[]) => {
      const available = new Map(nextHighlights.map((mark) => [mark.id, mark]))

      // Removing a mark removes its value definition.
      const updated = fields
        .filter((f) => f.regions.length === 0 || available.has(f.name))
        .map((f) => {
          const m = available.get(f.name)
          return m ? { ...f, regions: [m.rect] } : f
        })

      // Notify only on a real change because each notification triggers a read.
      const changed =
        updated.length !== fields.length ||
        updated.some((f, i) => f.regions[0] !== fields[i]?.regions[0])
      if (changed) onFields(updated)

      if (draft) {
        const m = available.get(draft.highlight.id)
        if (m) setDraft({ ...draft, highlight: m })
        else setDraft(null)
      }
    },
    [fields, draft, onFields],
  )

  const accept = useCallback(
    (displayName: string) => {
      const name = displayName.trim()
      if (!name || !draft) return

      const fieldSpec: FieldSpec = {
        name: freeKey(
          name,
          fields.map((f) => f.name),
        ),
        label: name,
        question: '',
        json_type: 'string',
        required: false,
        method: 'auto',
        regex: null,
        extractor: null,
        normalization: null,
        regions: [draft.highlight.rect],
      }
      onFields([...fields, fieldSpec])
      setDraft(null)
      setChosen(fieldSpec.name)
    },
    [draft, fields, onFields],
  )

  const remove = useCallback(
    (name: string) => {
      onFields(fields.filter((f) => f.name !== name))
      if (chosen === name) setChosen(null)
    },
    [fields, chosen, onFields],
  )

  // Escape discards the unanswered question and its unnamed mark.
  useEffect(() => {
    if (!draft) return
    const keyHandler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.stopPropagation()
        setDraft(null)
      }
    }
    window.addEventListener('keydown', keyHandler, true)
    return () => window.removeEventListener('keydown', keyHandler, true)
  }, [draft])

  const results = new Map(run?.results.map((e) => [e.field, e]) ?? [])

  return (
    <>
      <div className="flex items-start gap-6">
        <div className="h-[calc(100vh-360px)] min-h-[440px] min-w-0 flex-1 overflow-hidden rounded-lg border border-line bg-bg">
          <ViewerHost
            document={document}
            highlights={highlights}
            onHighlights={highlightsChanged}
            onError={onError}
            labels="always"
            onNewHighlight={(highlight, anchor) => setDraft({ highlight, anchor })}
          />
        </div>

        <aside className="w-[340px] shrink-0">
          <SectionHeading>{texts.assistant.values.title}</SectionHeading>

          {fields.length === 0 ? (
            <p className="rounded-md border border-dashed border-line-2 px-4 py-6 text-center text-[13px] text-ink-3">
              {texts.assistant.values.empty}
            </p>
          ) : (
            <ul className="space-y-[7px]">
              {fields.map((fieldSpec) => (
                <li key={fieldSpec.name}>
                  <ValueRow
                    fieldSpec={fieldSpec}
                    result={results.get(fieldSpec.name)}
                    selected={chosen === fieldSpec.name}
                    onChoose={() =>
                      setChosen(chosen === fieldSpec.name ? null : fieldSpec.name)
                    }
                    onRemove={() => remove(fieldSpec.name)}
                  />
                </li>
              ))}
            </ul>
          )}

          <p className="mt-2 flex items-center justify-center gap-2 rounded-md border-[1.5px] border-dashed border-line-2 px-4 py-3 text-[13.5px] text-ink-3">
            <Plus size={15} aria-hidden="true" />
            {texts.assistant.values.waiting}
          </p>

          <Notice className="mt-[18px]" symbol={<Info size={15} />}>
            {texts.assistant.values.notice}
          </Notice>
        </aside>
      </div>

      {draft && (
        <Question
          anchor={draft.anchor}
          onAccept={accept}
          onCancel={() => setDraft(null)}
        />
      )}
    </>
  )
}

function ValueRow({
  fieldSpec,
  result,
  selected,
  onChoose,
  onRemove,
}: {
  fieldSpec: FieldSpec
  result: ExtractionResult | undefined
  selected: boolean
  onChoose: () => void
  onRemove: () => void
}) {
  const texts = useTexts()
  const valueText = result?.value?.trim()

  return (
    <div
      className={[
        'group flex items-center gap-3 rounded-md border px-3.5 py-2.5',
        'transition-all duration-(--dur-1) ease-gentle',
        selected ? 'border-accent bg-accent-bg' : 'border-line bg-card hover:border-line-2',
      ].join(' ')}
    >
      <button type="button" onClick={onChoose} className="min-w-0 flex-1 text-left">
        <span className="block text-[13.5px] font-medium">{fieldSpec.label || fieldSpec.name}</span>
        <span className="mt-px block truncate text-[12.5px] text-ink-3">
          {valueText || texts.assistant.values.notFound}
        </span>
      </button>

      {valueText && (
        <span className="shrink-0 text-good" title={texts.review.rest}>
          <Check size={15} aria-hidden="true" />
        </span>
      )}

      <button
        type="button"
        onClick={onRemove}
        title={texts.assistant.values.remove}
        aria-label={`${texts.assistant.values.remove}: ${fieldSpec.label || fieldSpec.name}`}
        className="shrink-0 rounded p-1 text-ink-3 opacity-0 transition-opacity duration-(--dur-1) group-hover:opacity-100 hover:text-bad focus-visible:opacity-100"
      >
        <Trash2 size={14} />
      </button>
    </div>
  )
}

/** Floating value-name question clamped to the current window. */
function Question({
  anchor,
  onAccept,
  onCancel,
}: {
  anchor: { x: number; y: number }
  onAccept: (displayName: string) => void
  onCancel: () => void
}) {
  const texts = useTexts()
  const [text, setText] = useState('')

  const left = Math.max(16, Math.min(anchor.x, window.innerWidth - QUESTION_WIDTH - 16))
  const top = Math.max(16, Math.min(anchor.y, window.innerHeight - 220))

  return (
    <div
      className="fixed z-50 rounded-md border border-line-2 bg-card p-4 shadow-3"
      style={{ left: left, top: top, width: QUESTION_WIDTH }}
      role="dialog"
      aria-label={texts.assistant.values.question}
    >
      <p className="mb-2.5 text-[12.5px] text-ink-2">{texts.assistant.values.question}</p>

      <input
        type="text"
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter') {
            e.preventDefault()
            onAccept(text)
          }
        }}
        placeholder={texts.assistant.values.placeholder}
        spellCheck={false}
        /* The question continues the pointer action, so focus belongs here. */
        autoFocus
        className="w-full rounded-sm border border-line-2 bg-card-2 px-2.5 py-2 text-[13px] outline-none placeholder:text-ink-3"
      />

      <div className="mt-2.5 flex flex-wrap gap-1.5">
        {texts.assistant.values.suggestions.map((v) => (
          <button
            key={v}
            type="button"
            onClick={() => onAccept(v)}
            className="rounded-full border border-line bg-card-2 px-2.5 py-1 text-[11.5px] text-ink-2 transition-colors duration-(--dur-1) hover:border-accent hover:text-accent"
          >
            {v}
          </button>
        ))}
      </div>

      <div className="mt-3.5 flex gap-2">
        <button
          type="button"
          onClick={() => onAccept(text)}
          disabled={!text.trim()}
          className="flex-1 rounded-sm bg-ink px-3 py-2 text-[13px] font-medium text-on-ink transition-all duration-(--dur-1) hover:brightness-[1.35] disabled:pointer-events-none disabled:opacity-40"
        >
          {texts.assistant.values.accept}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="rounded-sm px-3 py-2 text-[13px] text-ink-2 transition-colors duration-(--dur-1) hover:text-ink"
        >
          {texts.assistant.values.cancel}
        </button>
      </div>
    </div>
  )
}
