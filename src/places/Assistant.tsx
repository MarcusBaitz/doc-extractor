/** Four-step template setup path using one plain question per step. */

import { ArrowLeft, ArrowRight, Check } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'

import { api } from '../api/client'
import type { OutputFormat, DocumentInfo, FieldSpec, ExtractionRun } from '../api/types'
import { chooseDocument } from '../App'
import { useTexts } from '../i18n'
import { Surface, Button, Title } from '../ui/components'
import { StepFinish } from './assistant/StepFinish'
import { StepValues } from './assistant/StepValues'
import { StepResult } from './assistant/StepResult'
import { StepSampleDocument } from './assistant/StepSampleDocument'

interface Props {
  /** Set when editing an existing template. */
  typeId: number | null
  onCancel: () => void
  onFinish: (typeId: number) => void
  onError: (error: unknown) => void
}

export function Assistant({ typeId, onCancel, onFinish, onError }: Props) {
  const texts = useTexts()
  const [step, setStep] = useState(1)
  const [document, setDocument] = useState<DocumentInfo | null>(null)
  const [fields, setFieldsState] = useState<FieldSpec[]>([])
  const [run, setRun] = useState<ExtractionRun | null>(null)
  const [name, setName] = useState('')
  const [format, setFormat] = useState<OutputFormat>('table')
  const [loading, setLoading] = useState(false)

  // Existing templates have values but still need a sample document.
  useEffect(() => {
    if (typeId === null) return
    let discarded = false
    void api
      .documentType(typeId)
      .then((v) => {
        if (discarded) return
        setFieldsState(v.fields)
        setName(v.name)
        setFormat(v.output)
      })
      .catch((f: unknown) => {
        if (!discarded) onError(f)
      })
    return () => {
      discarded = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [typeId])

  /** Reads values again after their definitions change. */
  const reread = useCallback(
    async (currentItem: FieldSpec[], doc: DocumentInfo | null) => {
      if (!doc || currentItem.length === 0) {
        setRun(null)
        return
      }
      try {
        setRun(await api.extract(doc.id, currentItem))
      } catch (f) {
        onError(f)
      }
    },
    [onError],
  )

  const loadDocument = useCallback(async () => {
    try {
      const pathValue = await chooseDocument(texts.document.formats)
      if (!pathValue) return
      setLoading(true)
      const loaded = await api.loadDocument(pathValue)
      setDocument(loaded)
      await reread(fields, loaded)
    } catch (f) {
      onError(f)
    } finally {
      setLoading(false)
    }
  }, [fields, reread, onError, texts.document.formats])

  // Debounce pointer movement so one drag does not start hundreds of reads.
  const readTimer = useRef<number | null>(null)

  const setFields = useCallback(
    (newLabel: FieldSpec[]) => {
      setFieldsState(newLabel)
      if (readTimer.current !== null) clearTimeout(readTimer.current)
      readTimer.current = window.setTimeout(() => {
        void reread(newLabel, document)
      }, 300)
    },
    [document, reread],
  )

  useEffect(
    () => () => {
      if (readTimer.current !== null) clearTimeout(readTimer.current)
    },
    [],
  )

  const save = useCallback(async () => {
    const clean = name.trim()
    if (!clean || fields.length === 0) return
    setLoading(true)
    try {
      const stored = await api.saveDocumentType({
        name: clean,
        description: '',
        fields: fields,
        output: format,
      })
      if (stored.id !== null) onFinish(stored.id)
    } catch (f) {
      onError(f)
    } finally {
      setLoading(false)
    }
  }, [name, fields, format, onFinish, onError])

  // Continue only when the current step is complete.
  const canContinue =
    (step === 1 && document !== null) ||
    (step === 2 && fields.length > 0) ||
    step === 3

  const wide = step === 2

  return (
    <Surface wide={wide}>
      <div className="mb-8">
        <Button variant="quiet" onClick={onCancel} className="mb-2.5 !px-2.5 !py-1.5">
          <ArrowLeft size={16} />
          {texts.assistant.backToTemplates}
        </Button>
        <Title>{typeId === null ? texts.assistant.title : texts.assistant.editTitle}</Title>
      </div>

      <StepBar current={step} onStep={setStep} />

      {step === 1 && (
        <StepSampleDocument
          document={document}
          loading={loading}
          onChoose={() => void loadDocument()}
        />
      )}

      {step === 2 && document && (
        <StepValues
          document={document}
          fields={fields}
          run={run}
          onFields={setFields}
          onError={onError}
        />
      )}

      {step === 3 && (
        <StepResult
          fields={fields}
          run={run}
          format={format}
          onFormat={setFormat}
          onFields={setFieldsState}
        />
      )}

      {step === 4 && (
        <StepFinish
          name={name}
          onName={setName}
          fields={fields}
          format={format}
          loading={loading}
          onSave={() => void save()}
        />
      )}

      {/* Navigation appears only after the first step has something to keep. */}
      {(step > 1 || document) && step < 4 && (
        <div className="mt-8 flex items-center gap-3 border-t border-line pt-4">
          <span className="text-[12.5px] text-ink-3">
            {step === 2 && texts.assistant.values.marked(fields.length)}
          </span>
          <div className="flex-1" />
          {step > 1 && (
            <Button onClick={() => setStep(step - 1)}>
              {texts.assistant.back}
            </Button>
          )}
          <Button variant="primary" disabled={!canContinue} onClick={() => setStep(step + 1)}>
            {texts.assistant.nextStep}
            <ArrowRight size={16} />
          </Button>
        </div>
      )}
    </Surface>
  )
}

function StepBar({
  current,
  onStep,
}: {
  current: number
  onStep: (n: number) => void
}) {
  const texts = useTexts()
  const steps = [
    texts.assistant.steps.document,
    texts.assistant.steps.values,
    texts.assistant.steps.result,
    texts.assistant.steps.finish,
  ]

  return (
    <div className="mb-8 flex items-center gap-3">
      {steps.map((label, i) => {
        const numberValue = i + 1
        const completed = numberValue < current
        const selected = numberValue === current
        return (
          <div key={label} className="flex items-center gap-3">
            {i > 0 && <span className="h-px w-[18px] bg-line-2" />}
            <button
              type="button"
              // Backward steps stay available; forward movement uses Next.
              disabled={numberValue > current}
              onClick={() => onStep(numberValue)}
              aria-current={selected ? 'step' : undefined}
              className={[
                'flex items-center gap-2.5 rounded-full py-1.5 pr-3.5 pl-2 text-[13px]',
                'transition-all duration-(--dur-1) disabled:cursor-default',
                selected
                  ? 'bg-card font-medium text-ink shadow-1'
                  : completed
                    ? 'text-ink-2 hover:text-ink'
                    : 'text-ink-3',
              ].join(' ')}
            >
              <span
                className={[
                  'tabular-number grid size-[21px] place-items-center rounded-full border text-[11.5px] font-semibold',
                  completed
                    ? 'border-transparent bg-good text-white'
                    : selected
                      ? 'border-transparent bg-ink text-on-ink'
                      : 'border-line-2 bg-card',
                ].join(' ')}
              >
                {completed ? <Check size={12} strokeWidth={3} /> : numberValue}
              </span>
              {label}
            </button>
          </div>
        )
      })}
    </div>
  )
}
