/** Settings holds appearance, language and collapsed technical details. */

import { ChevronDown, ChevronRight, Lock } from 'lucide-react'
import { useState } from 'react'

import type { Status } from '../api/types'
import type { Theme } from '../design/theme'
import { useLanguage, useTexts } from '../i18n'
import { SectionHeading, Surface, Card, Header, Dot, Title } from '../ui/components'

interface Props {
  status: Status | null
  theme: Theme
  onTheme: (theme: Theme) => void
}

export function Settings({ status, theme, onTheme }: Props) {
  const texts = useTexts()
  const [language, setLanguage] = useLanguage()
  const [technical, setTechnical] = useState(false)

  return (
    <Surface>
      <Header>
        <Title subtitle={texts.settings.subtitle}>{texts.settings.title}</Title>
      </Header>

      <SectionHeading>{texts.settings.appearance}</SectionHeading>
      <div className="grid max-w-[520px] grid-cols-2 gap-3">
        <Choice
          selected={theme === 'light'}
          onClick={() => onTheme('light')}
          title={texts.settings.light}
          detail={texts.settings.lightDetail}
          preview="bg-[#F3F3F1] border-[rgba(23,25,29,.12)]"
          fieldSpec="bg-white"
        />
        <Choice
          selected={theme === 'dark'}
          onClick={() => onTheme('dark')}
          title={texts.settings.dark}
          detail={texts.settings.darkDetail}
          preview="bg-[#0D0E11] border-[rgba(255,255,255,.14)]"
          fieldSpec="bg-[#17181C]"
        />
      </div>

      <SectionHeading className="mt-11">{texts.settings.language}</SectionHeading>
      <div className="grid max-w-[520px] grid-cols-2 gap-3">
        <Choice
          selected={language === 'de'}
          onClick={() => setLanguage('de')}
          title={texts.settings.german}
          detail={texts.settings.germanDetail}
          preview="bg-card-2 border-line"
          fieldSpec="bg-card"
          sample={texts.settings.germanCode}
        />
        <Choice
          selected={language === 'en'}
          onClick={() => setLanguage('en')}
          title={texts.settings.english}
          detail={texts.settings.englishDetail}
          preview="bg-card-2 border-line"
          fieldSpec="bg-card"
          sample={texts.settings.englishCode}
        />
      </div>

      <SectionHeading className="mt-11">
        {texts.settings.privacy}
      </SectionHeading>
      <Card padded>
        <div className="flex items-center gap-3.5">
          <Dot tone="good" />
          <div>
            <p className="font-semibold">{texts.settings.noConnection}</p>
            <p className="mt-1 max-w-[64ch] text-[13px] text-ink-2">
              {texts.settings.noConnectionDetail}
            </p>
          </div>
          <Lock size={18} className="ml-auto shrink-0 text-good" aria-hidden="true" />
        </div>

        <div className="mt-6 border-t border-line pt-5">
          <button
            type="button"
            onClick={() => setTechnical(!technical)}
            aria-expanded={technical}
            className="flex items-center gap-1.5 text-[13px] text-ink-2 transition-colors duration-(--dur-1) hover:text-ink"
          >
            {technical ? <ChevronDown size={15} /> : <ChevronRight size={15} />}
            {texts.settings.technical}
          </button>

          {technical && (
            <div className="mt-4">
              <p className="mb-4 max-w-[64ch] text-[12.5px] text-ink-3">
                {texts.settings.technicalDetail}
              </p>
              <dl className="grid grid-cols-[180px_1fr] gap-x-6 gap-y-2.5 text-[13px]">
                <dt className="text-ink-3">{texts.info.mode}</dt>
                <dd>
                  {status ? texts.mode[status.mode] : '—'}
                </dd>

                <dt className="text-ink-3">{texts.info.sidecar}</dt>
                <dd className="font-mono text-[12.5px]">
                  {status?.backend ?? '—'}
                  {status?.version ? ` · ${status.version}` : ''}
                </dd>

                <dt className="text-ink-3">{texts.settings.textRecognition}</dt>
                <dd>{texts.settings.localEngine}</dd>

                <dt className="text-ink-3">{texts.settings.storageLocation}</dt>
                <dd>{texts.settings.thisDevice}</dd>
              </dl>
            </div>
          )}
        </div>
      </Card>
    </Surface>
  )
}

function Choice({
  selected,
  onClick,
  title,
  detail,
  preview,
  fieldSpec,
  sample,
}: {
  selected: boolean
  onClick: () => void
  title: string
  detail: string
  preview: string
  fieldSpec: string
  sample?: string
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={selected}
      className={[
        'rounded-md border bg-card p-4 text-left transition-all duration-(--dur-1) ease-gentle',
        selected ? 'border-ink shadow-[0_0_0_1px_var(--ink)]' : 'border-line hover:border-line-2',
      ].join(' ')}
    >
      {/* A small sample shows the choice directly. */}
      <span
        className={[
          'mb-3 flex h-14 items-center justify-center gap-1.5 rounded-sm border p-2',
          preview,
        ].join(' ')}
        aria-hidden="true"
      >
        {sample ? (
          <span className="text-[17px] font-semibold tracking-[0.08em] text-ink-2">
            {sample}
          </span>
        ) : (
          <>
            <span className={['h-full w-1/3 rounded-[3px]', fieldSpec].join(' ')} />
            <span className={['h-full flex-1 rounded-[3px]', fieldSpec].join(' ')} />
          </>
        )}
      </span>
      <span className="block text-sm font-semibold">{title}</span>
      <span className="mt-0.5 block text-[12.5px] text-ink-2">{detail}</span>
    </button>
  )
}
