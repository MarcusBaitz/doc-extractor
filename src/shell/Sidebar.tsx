/**
 * Navigation for exactly four places, using words as well as icons.
 *
 * The review count is the only unsolicited number. It disappears at zero,
 * without adding a toast, celebration or competing status message.
 */

import { CircleCheck, House, LayoutTemplate, Lock, Moon, Settings, Sun } from 'lucide-react'

import type { Theme } from '../design/theme'
import { useTexts } from '../i18n'

export type Place = 'overview' | 'review' | 'templates' | 'settings'

interface Props {
  place: Place
  onPlace: (place: Place) => void
  /** Documents waiting for review; zero hides the count. */
  waiting: number
  theme: Theme
  onTheme: (theme: Theme) => void
  version: string
}

export function Sidebar({ place, onPlace, waiting, theme, onTheme, version }: Props) {
  const texts = useTexts()

  return (
    <aside className="flex w-[236px] shrink-0 flex-col border-r border-line bg-panel px-3 py-5">
      <div className="flex items-center gap-2.5 px-3 pb-8">
        <span className="grid size-[26px] place-items-center rounded-sm bg-ink text-on-ink">
          <Badge />
        </span>
        <b className="text-[15px] font-semibold tracking-[-0.02em]">{texts.app.title}</b>
      </div>

      <nav className="flex flex-col gap-0.5">
        <Entry
          selected={place === 'overview'}
          onClick={() => onPlace('overview')}
          symbol={<House size={17} />}
        >
          {texts.places.overview}
        </Entry>

        <Entry
          selected={place === 'review'}
          onClick={() => onPlace('review')}
          symbol={<CircleCheck size={17} />}
          count={waiting}
        >
          {texts.places.review}
        </Entry>

        <Entry
          selected={place === 'templates'}
          onClick={() => onPlace('templates')}
          symbol={<LayoutTemplate size={17} />}
        >
          {texts.places.templates}
        </Entry>

        <div className="mx-3 my-4 h-px bg-line" />

        <Entry
          selected={place === 'settings'}
          onClick={() => onPlace('settings')}
          symbol={<Settings size={17} />}
        >
          {texts.places.settings}
        </Entry>
      </nav>

      <div className="mt-auto p-3">
        {/* The locality promise stays visible instead of living in a dialog. */}
        <div className="flex gap-2.5 rounded-md bg-good-bg px-3 py-2.5 text-xs leading-snug text-good">
          <Lock size={14} className="mt-0.5 shrink-0" aria-hidden="true" />
          <span>{texts.app.promise}</span>
        </div>

        <div className="mt-3 flex items-center justify-between px-1 text-[11.5px] text-ink-3">
          <span>
            {texts.app.version} {version}
          </span>
          <button
            type="button"
            onClick={() => onTheme(theme === 'light' ? 'dark' : 'light')}
            title={texts.theme.toggle}
            aria-label={texts.theme.toggle}
            className="rounded p-1 text-ink-3 transition-colors duration-(--dur-1) hover:text-ink"
          >
            {theme === 'light' ? <Moon size={15} /> : <Sun size={15} />}
          </button>
        </div>
      </div>
    </aside>
  )
}

function Entry({
  children,
  symbol,
  selected,
  onClick,
  count = 0,
}: {
  children: React.ReactNode
  symbol: React.ReactNode
  selected: boolean
  onClick: () => void
  count?: number
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-current={selected ? 'page' : undefined}
      className={[
        'flex w-full items-center gap-2.5 rounded-sm px-3 py-2 text-left',
        'transition-colors duration-(--dur-1)',
        selected
          ? 'bg-card font-medium text-ink shadow-1'
          : 'text-ink-2 hover:bg-card-2 hover:text-ink',
      ].join(' ')}
    >
      <span className="shrink-0 opacity-75" aria-hidden="true">
        {symbol}
      </span>
      {children}
      {count > 0 && (
        <span className="tabular-number ml-auto grid h-5 min-w-5 place-items-center rounded-full bg-warn-bg px-1.5 text-[11.5px] font-semibold text-warn">
          {count}
        </span>
      )}
    </button>
  )
}

/** Word mark: three strokes with a shortened middle line. */
function Badge() {
  return (
    <svg viewBox="0 0 24 24" className="size-3.5" aria-hidden="true">
      <path
        d="M4 6h16M4 12h10M4 18h16"
        stroke="currentColor"
        strokeWidth="2.4"
        strokeLinecap="round"
        fill="none"
      />
    </svg>
  )
}
