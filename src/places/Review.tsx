/**
 * Review presents one document and one decision at a time. Technical evidence
 * becomes a plain explanation of what the clerk needs to check.
 */

import { AlertCircle, Check, CircleCheck } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'

import type { ExtractionResult } from '../api/types'
import { useLanguage, useTexts, type Texts } from '../i18n'
import { Surface, Card, Button, Empty, Key, TextLink } from '../ui/components'
import { timeOfDay } from '../ui/format'
import { ViewerHost } from '../viewer/ViewerHost'
import { displayName, openValues, type DocumentRecord, type Session } from '../state/session'

interface Props {
  session: Session
  onError: (error: unknown) => void
  onFinish: () => void
}

export function Review({ session, onError, onFinish }: Props) {
  const texts = useTexts()
  const [language] = useLanguage()
  const [change, setChanging] = useState<string | null>(null)
  const [inputValue, setInputValue] = useState('')

  const queue = useMemo(
    () => session.records.filter((a) => a.state === 'waiting' && openValues(a).length > 0),
    [session.records],
  )

  // Oldest first, so an already waiting document does not wait longer.
  const record = queue[queue.length - 1]
  const openItem = record ? openValues(record) : []
  const question = openItem[0]

  /** Completes one value and the document when no other value is open. */
  const complete = useCallback(
    (patch: Partial<DocumentRecord>) => {
      if (!record) return
      const next = { ...record, ...patch }
      const rest = openValues(next)
      session.change(record.id, {
        ...patch,
        ...(rest.length === 0 ? { state: 'read' as const } : {}),
      })
      setChanging(null)
      setInputValue('')
    },
    [record, session],
  )

  const confirm = useCallback(() => {
    if (!record || !question) return
    complete({ confirmed: [...record.confirmed, question.field] })
  }, [record, question, complete])

  const missingFromDocument = useCallback(() => {
    if (!record || !question) return
    complete({ missing: [...record.missing, question.field] })
  }, [record, question, complete])

  const accept = useCallback(() => {
    if (!record || !question) return
    const valueText = inputValue.trim()
    if (!valueText) return
    complete({ corrections: { ...record.corrections, [question.field]: valueText } })
  }, [record, question, inputValue, complete])

  // Enter confirms unless an input owns it; Escape leaves the queue.
  useEffect(() => {
    const keyHandler = (e: KeyboardEvent) => {
      const targetElement = e.target as HTMLElement | null
      const inInput = targetElement !== null && ['INPUT', 'TEXTAREA'].includes(targetElement.tagName)

      if (e.key === 'Enter' && !inInput && question) {
        e.preventDefault()
        confirm()
      } else if (e.key === 'Escape') {
        if (change) setChanging(null)
        else onFinish()
      }
    }
    window.addEventListener('keydown', keyHandler)
    return () => window.removeEventListener('keydown', keyHandler)
  }, [question, change, confirm, onFinish])

  if (!record || !question) {
    return (
      <Surface>
        <Card>
          <Empty
            title={texts.review.empty}
            detail={texts.review.emptyDetail}
            symbol={<CircleCheck size={22} />}
          />
        </Card>
      </Surface>
    )
  }

  const name = displayName(record.fields, question.field)
  const valueText = question.value?.trim()
  const remaining = record.results.filter((e) => e.field !== question.field)

  return (
    <div className="flex h-full min-h-0">
      <div className="min-w-0 flex-1">
        <ViewerHost
          document={record.document}
          highlights={[]}
          onHighlights={() => undefined}
          onError={onError}
          highlighted={question.locator}
          readOnly
          labels="never"
        />
      </div>

      <aside className="flex w-[432px] shrink-0 flex-col border-l border-line bg-panel">
        <div className="border-b border-line px-7 pt-6 pb-5">
          <div className="flex items-center gap-2.5 text-[12.5px] text-ink-3">
            {texts.review.documentOf(
              queue.length - queue.indexOf(record),
              queue.length,
            )}
            <span className="ml-auto flex gap-1">
              {openItem.map((e, i) => (
                <span
                  key={e.field}
                  className={[
                    'h-[3px] w-4 rounded-full',
                    i === 0 ? 'bg-ink' : 'bg-line-2',
                  ].join(' ')}
                />
              ))}
            </span>
          </div>
          <p className="mt-2.5 truncate font-semibold tracking-[-0.01em]">
            {record.fileName}
          </p>
          <p className="mt-0.5 text-[12.5px] text-ink-3">
            {record.template} · {texts.review.readAt(timeOfDay(record.readAt, language))}
          </p>
        </div>

        <div className="border-b border-line px-7 py-7">
          <p className="flex items-center gap-2 text-[13px] font-semibold text-warn">
            <AlertCircle size={15} aria-hidden="true" />
            {texts.review.unclear}
          </p>

          <p className="mt-5 text-[13px] text-ink-2">{name}</p>

          {change === question.field ? (
            <>
              <input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault()
                    accept()
                  }
                }}
                spellCheck={false}
                /* Choosing Change moves focus directly to the intended input. */
                autoFocus
                className="mt-1.5 w-full rounded-md border border-line-2 bg-card px-4 py-3.5 text-[21px] font-semibold tracking-[-0.025em] outline-none"
              />
              <div className="mt-6 flex gap-2">
                <Button
                  variant="primary"
                  large
                  className="flex-1"
                  disabled={!inputValue.trim()}
                  onClick={accept}
                >
                  {texts.review.accept}
                </Button>
                <Button large onClick={() => setChanging(null)}>
                  {texts.review.discard}
                </Button>
              </div>
              <p className="mt-3.5 text-center text-[12.5px] text-ink-3">
                {texts.review.appliesHere}
              </p>
            </>
          ) : (
            <>
              <p
                className={[
                  'mt-1.5 rounded-md border border-line-2 bg-card px-4 py-3.5',
                  'text-[21px] leading-snug font-semibold tracking-[-0.025em]',
                  valueText ? '' : 'text-ink-3',
                ].join(' ')}
              >
                {valueText || texts.review.none}
              </p>

              <p className="mt-3 text-[12.5px] leading-relaxed text-ink-3">
                {reason(question, texts)}
              </p>

              <div className="mt-6 flex gap-2">
                <Button variant="primary" large className="flex-1" onClick={confirm} autoFocus>
                  {texts.review.looksRight}
                  <Key>{texts.keys.enter}</Key>
                </Button>
                <Button
                  large
                  onClick={() => {
                    setChanging(question.field)
                    setInputValue(valueText ?? '')
                  }}
                >
                  {texts.review.change}
                </Button>
              </div>

              <p className="mt-3.5 text-center text-[12.5px] text-ink-3">
                <TextLink onClick={missingFromDocument}>{texts.review.isMissing}</TextLink>
              </p>
            </>
          )}
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-7 pt-6 pb-10">
          <h2 className="mb-4 text-[13px] font-semibold text-ink-3">
            {texts.review.rest}
          </h2>

          {remaining.length === 0 ? (
            <p className="text-[13px] text-ink-3">{texts.review.noMore}</p>
          ) : (
            remaining.map((e) => {
              const corrected = record.corrections[e.field]
              const isMissing = record.missing.includes(e.field)
              const displayValue = corrected ?? e.value?.trim()
              return (
                <div
                  key={e.field}
                  className="flex items-baseline gap-4 border-b border-line py-2.5 text-[13.5px] last:border-b-0"
                >
                  <span className="w-[136px] shrink-0 text-ink-2">
                    {displayName(record.fields, e.field)}
                  </span>
                  <span
                    className={[
                      'min-w-0 flex-1 font-medium',
                      displayValue && !isMissing ? '' : 'text-ink-3',
                    ].join(' ')}
                  >
                    {isMissing ? texts.review.isMissing : displayValue || texts.review.none}
                  </span>
                  {(e.grounded || corrected) && (
                    <Check size={13} className="shrink-0 self-center text-good" />
                  )}
                </div>
              )
            })
          )}
        </div>
      </aside>
    </div>
  )
}

/** Converts a technical result note into a plain review reason. */
function reason(e: ExtractionResult, texts: Texts): string {
  const w = texts.review.reason
  if (!e.value?.trim()) return w.noValue
  if (!e.locator) return w.noEvidence
  if (e.note.includes('text recognition')) return w.weak
  if (e.note.includes('does not match type')) return w.type
  return w.uncertain
}
