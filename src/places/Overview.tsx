/** Overview shows whether the application is running and needs attention. */

import { Check, CircleAlert, Download, Plus } from 'lucide-react'
import { useCallback, useState } from 'react'

import { api } from '../api/client'
import type { DocumentType, Status } from '../api/types'
import { saveResult } from '../results/save'
import { useLanguage, useTexts } from '../i18n'
import {
  SectionHeading,
  Surface,
  Card,
  Button,
  Header,
  Empty,
  Badge,
  Dot,
  Title,
} from '../ui/components'
import { formatNumber, timeOfDay, relativeTime } from '../ui/format'
import { openValues, type DocumentRecord, type Session } from '../state/session'

interface Props {
  status: Status | null
  session: Session
  templates: DocumentType[]
  onReview: () => void
  onTemplates: () => void
  onNewTemplate: () => void
  onError: (error: unknown) => void
}

export function Overview({
  status,
  session,
  templates,
  onReview,
  onTemplates,
  onNewTemplate,
  onError,
}: Props) {
  const texts = useTexts()
  const [language] = useLanguage()
  const [savingNow, setSavingNow] = useState<string | null>(null)

  const running = status?.connected === true
  const starting = status === null || (!status.connected && status.version === '')
  const waiting = session.reviewCount

  const fileResult = useCallback(
    async (record: DocumentRecord) => {
      setSavingNow(record.id)
      try {
        const result = await api.export(record.docId, record.fields, record.corrections)
        saveResult(result, record.fields, record.output, record.fileName)
        session.change(record.id, { state: 'filed' })
      } catch (f) {
        onError(f)
      } finally {
        setSavingNow(null)
      }
    },
    [session, onError],
  )

  return (
    <Surface>
      <Header>
        <Title subtitle={texts.overview.subtitle}>{texts.overview.title}</Title>
        {templates.length > 0 && (
          <Button variant={waiting > 0 ? 'normal' : 'primary'} onClick={onTemplates}>
            {texts.overview.readDocument}
          </Button>
        )}
      </Header>

      <Card className="overflow-hidden">
        <div className="flex items-center gap-5 p-7">
          <Dot tone={running ? 'good' : starting ? 'neutral' : 'error'} />
          <div>
            <p className="text-[19px] font-semibold tracking-[-0.02em]">
              {running
                ? texts.state.running
                : starting
                  ? texts.state.starting
                  : texts.state.unavailable}
            </p>
            <p className="mt-0.5 text-[13.5px] text-ink-2">
              {running
                ? templates.length > 0
                  ? texts.state.ready(templates.length)
                  : texts.state.noTemplates
                : starting
                  ? texts.state.startingDetail
                  : texts.state.unavailableDetail}
            </p>
          </div>
          {session.records[0] && (
            <p className="ml-auto text-right text-[12.5px] text-ink-3">
              {texts.overview.lastRead}
              <br />
              {relativeTime(session.records[0].readAt, language, texts)}
            </p>
          )}
        </div>

        <div className="grid grid-cols-3 gap-px border-t border-line bg-line">
          <Metric valueText={session.records.length} label={texts.overview.documents} />

          <Metric valueText={waiting} label={texts.overview.waiting} actionable={waiting > 0}>
            {waiting > 0 && (
              <Button variant="primary" onClick={onReview} className="mt-3.5">
                {texts.overview.reviewNow}
              </Button>
            )}
          </Metric>

          <Metric valueText={session.gaps} label={texts.overview.gaps} />
        </div>
      </Card>

      <SectionHeading className="mt-11">{texts.overview.recent}</SectionHeading>

      {session.records.length === 0 ? (
        <Card>
          <Empty
            title={texts.overview.nothingYet}
            detail={
              templates.length === 0
                ? texts.overview.nothingYetDetail
                : texts.overview.folderDetail
            }
            action={
              templates.length === 0 ? (
                <Button variant="primary" onClick={onNewTemplate}>
                  <Plus size={16} />
                  {texts.overview.firstTemplate}
                </Button>
              ) : undefined
            }
          />
        </Card>
      ) : (
        <div>
          {session.records.map((record) => (
            <HistoryRow
              key={record.id}
              record={record}
              saving={savingNow === record.id}
              onReview={onReview}
              onFile={() => void fileResult(record)}
            />
          ))}
        </div>
      )}
    </Surface>
  )
}

function Metric({
  valueText,
  label,
  actionable = false,
  children,
}: {
  valueText: number
  label: string
  actionable?: boolean
  children?: React.ReactNode
}) {
  const [language] = useLanguage()
  return (
    // The places test enforces at most one actionable metric.
    <div
      data-actionable={actionable}
      className={['px-7 py-6', actionable ? 'bg-warn-bg' : 'bg-card'].join(' ')}
    >
      <p
        className={[
          'tabular-number text-[32px] leading-tight font-semibold tracking-[-0.04em]',
          actionable ? 'text-warn' : '',
        ].join(' ')}
      >
        {formatNumber(valueText, language)}
      </p>
      <p className={['mt-1 text-[13px]', actionable ? 'text-warn' : 'text-ink-2'].join(' ')}>
        {label}
      </p>
      {children}
    </div>
  )
}

function HistoryRow({
  record,
  saving,
  onReview,
  onFile,
}: {
  record: DocumentRecord
  saving: boolean
  onReview: () => void
  onFile: () => void
}) {
  const texts = useTexts()
  const [language] = useLanguage()
  const openItem = record.state === 'waiting' && openValues(record).length > 0

  return (
    <div className="flex items-center gap-4 border-b border-line py-2.5 text-[13.5px] text-ink-2 last:border-b-0">
      <span className="tabular-number w-[46px] shrink-0 text-[12.5px] text-ink-3">
        {timeOfDay(record.readAt, language)}
      </span>
      <span className="min-w-0 truncate font-medium text-ink">{record.fileName}</span>
      <span className="truncate text-[12.5px]">{record.template}</span>

      <span className="ml-auto flex shrink-0 items-center gap-3">
        {openItem ? (
          <>
            <Badge tone="waiting">
              <CircleAlert size={12} aria-hidden="true" />
              {texts.document.state.waiting}
            </Badge>
            <button
              type="button"
              onClick={onReview}
              className="text-[12.5px] underline underline-offset-[3px] hover:text-ink"
            >
              {texts.overview.reviewNow}
            </button>
          </>
        ) : record.state === 'filed' ? (
          <Badge tone="good">
            <Check size={12} aria-hidden="true" />
            {texts.document.state.filed}
          </Badge>
        ) : (
          <>
            <Badge>{texts.document.state.read}</Badge>
            <button
              type="button"
              onClick={onFile}
              disabled={saving}
              className="flex items-center gap-1.5 text-[12.5px] underline underline-offset-[3px] hover:text-ink disabled:opacity-50"
            >
              <Download size={13} aria-hidden="true" />
              {texts.document.saveResult}
            </button>
          </>
        )}
      </span>
    </div>
  )
}
