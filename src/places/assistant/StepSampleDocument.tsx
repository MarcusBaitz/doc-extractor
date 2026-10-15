/** Step 1 asks only for a representative sample document. */

import { FileText, Info, Loader2 } from 'lucide-react'

import type { DocumentInfo } from '../../api/types'
import { useLanguage, useTexts } from '../../i18n'
import { Notice, Button } from '../../ui/components'
import { formatBytes } from '../../ui/format'

interface Props {
  document: DocumentInfo | null
  loading: boolean
  onChoose: () => void
}

export function StepSampleDocument({ document, loading, onChoose }: Props) {
  const texts = useTexts()
  const [language] = useLanguage()
  if (document) {
    return (
      <>
        <div className="flex items-center gap-4 rounded-lg border border-line bg-card p-6 shadow-1">
          <span className="grid size-11 shrink-0 place-items-center rounded-md bg-card-2 text-ink-3">
            <FileText size={20} aria-hidden="true" />
          </span>
          <div className="min-w-0">
            <p className="truncate font-medium">{document.filename}</p>
            <p className="mt-0.5 text-[12.5px] text-ink-3">
              {texts.assistant.document.loaded} ·{' '}
              {document.pages.length > 1
                ? `${document.pages.length} ${texts.info.pages}`
                : formatBytes(document.meta.size_bytes, language)}
            </p>
          </div>
          <div className="ml-auto shrink-0">
            <Button onClick={onChoose}>{texts.assistant.document.other}</Button>
          </div>
        </div>

        <Notice className="mt-5" symbol={<Info size={15} />}>
          {texts.assistant.document.notice}
        </Notice>
      </>
    )
  }

  return (
    <>
      <button
        type="button"
        onClick={onChoose}
        disabled={loading}
        className="w-full rounded-lg border-[1.5px] border-dashed border-line-2 bg-card px-8 py-16 text-center transition-all duration-(--dur-2) ease-gentle hover:border-accent hover:bg-accent-bg disabled:pointer-events-none"
      >
        <span className="mx-auto mb-5 grid size-[46px] place-items-center rounded-md bg-card-2 text-ink-3">
          {loading ? (
            <Loader2 size={22} className="animate-spin" />
          ) : (
            <FileText size={22} aria-hidden="true" />
          )}
        </span>
        <span className="block text-[17px] font-semibold tracking-[-0.02em]">
          {loading ? texts.document.loading : texts.assistant.document.title}
        </span>
        <span className="mx-auto mt-2 block max-w-[54ch] text-[13.5px] text-ink-2">
          {texts.assistant.document.subtitle}
        </span>
        <span className="mt-6 inline-flex rounded-sm border border-line bg-card px-[18px] py-2.5 text-sm font-medium shadow-1">
          {texts.assistant.document.choose}
        </span>
      </button>

      <Notice className="mt-5" symbol={<Info size={15} />}>
        {texts.assistant.document.notice}
      </Notice>
    </>
  )
}
