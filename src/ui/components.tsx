/**
 * Shared interface components built only from semantic colour tokens.
 *
 * A screen has at most one dark primary button, while colour never carries a
 * meaning alone. Keeping the primary surface neutral leaves colour available
 * for status and selection.
 */

import { Search } from 'lucide-react'
import type { ReactNode } from 'react'

// --- Buttons ---------------------------------------------------------------

type ButtonVariant = 'primary' | 'normal' | 'quiet'

interface ButtonProps {
  children: ReactNode
  onClick?: () => void
  variant?: ButtonVariant
  large?: boolean
  disabled?: boolean
  title?: string
  /** Accessible label for icon-only buttons. */
  label?: string
  className?: string
  autoFocus?: boolean
}

const BUTTON_VARIANT: Record<ButtonVariant, string> = {
  primary: 'bg-ink text-on-ink border-transparent shadow-2 hover:brightness-[1.35]',
  normal: 'bg-card text-ink border-line shadow-1 hover:border-line-2',
  quiet: 'bg-transparent text-ink-2 border-transparent hover:bg-card hover:text-ink',
}

export function Button({
  children,
  onClick,
  variant = 'normal',
  large = false,
  disabled = false,
  title,
  label,
  className = '',
  autoFocus = false,
}: ButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={title}
      aria-label={label}
      /* Review continues from the primary decision, so focus starts there. */
      autoFocus={autoFocus}
      className={[
        'inline-flex items-center justify-center gap-2 rounded-sm border font-medium',
        'whitespace-nowrap transition-all duration-(--dur-1) ease-gentle',
        'disabled:pointer-events-none disabled:opacity-40',
        large ? 'px-6 py-3 text-[15px]' : 'px-[18px] py-2.5 text-sm',
        BUTTON_VARIANT[variant],
        className,
      ].join(' ')}
    >
      {children}
    </button>
  )
}

/** A quiet text action for the third route out of a review decision. */
export function TextLink({
  children,
  onClick,
}: {
  children: ReactNode
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="text-ink-2 underline decoration-1 underline-offset-[3px] transition-colors duration-(--dur-1) hover:text-ink"
    >
      {children}
    </button>
  )
}

/** Shows a shortcut on its button instead of hiding it in help. */
export function Key({ children }: { children: ReactNode }) {
  return (
    <span className="ml-1.5 inline-flex items-center text-[11px] font-normal opacity-60">
      <kbd className="rounded border border-current/25 px-1.5 py-px font-mono">
        {children}
      </kbd>
    </span>
  )
}

// --- Surfaces --------------------------------------------------------------

export function Card({
  children,
  className = '',
  padded = false,
}: {
  children: ReactNode
  className?: string
  padded?: boolean
}) {
  return (
    <div
      className={[
        'rounded-lg border border-line bg-card shadow-1',
        padded ? 'p-7' : '',
        className,
      ].join(' ')}
    >
      {children}
    </div>
  )
}

/** One title per screen. */
export function Title({ children, subtitle }: { children: ReactNode; subtitle?: string }) {
  return (
    <div>
      <h1 className="text-[30px] leading-tight font-semibold tracking-[-0.035em]">
        {children}
      </h1>
      {subtitle && <p className="mt-2 max-w-[64ch] text-[14.5px] text-ink-2">{subtitle}</p>}
    </div>
  )
}

/** Sentence-case section heading; capitals would make the page feel like a form. */
export function SectionHeading({
  children,
  className = '',
}: {
  children: ReactNode
  className?: string
}) {
  return (
    <h2 className={['mb-4 text-[13px] font-semibold text-ink-3', className].join(' ')}>
      {children}
    </h2>
  )
}

/** Screen header with a title and at most one action. */
export function Header({ children }: { children: ReactNode }) {
  return <div className="mb-8 flex items-end justify-between gap-6">{children}</div>
}

/** Place content; lists may use more width than prose. */
export function Surface({
  children,
  wide = false,
}: {
  children: ReactNode
  wide?: boolean
}) {
  return (
    <div
      className={[
        'mx-auto px-8 pt-12 pb-16',
        wide ? 'max-w-[1180px]' : 'max-w-[920px]',
      ].join(' ')}
    >
      {children}
    </div>
  )
}

// --- States ----------------------------------------------------------------

export type Tone = 'neutral' | 'good' | 'waiting' | 'error'

const DOT_TONE: Record<Tone, string> = {
  neutral: 'bg-ink-3 shadow-[0_0_0_4px_var(--card-2)]',
  good: 'bg-good shadow-[0_0_0_4px_var(--good-bg)]',
  waiting: 'bg-warn shadow-[0_0_0_4px_var(--warn-bg)]',
  error: 'bg-bad shadow-[0_0_0_4px_var(--bad-bg)]',
}

/** Status dot that always appears next to a written state. */
export function Dot({ tone = 'good' }: { tone?: Tone }) {
  return (
    <span
      aria-hidden="true"
      className={['size-[9px] shrink-0 rounded-full', DOT_TONE[tone]].join(' ')}
    />
  )
}

const BADGE_TONE: Record<Tone, string> = {
  neutral: 'bg-card-2 text-ink-2 border-line',
  good: 'bg-good-bg text-good border-transparent',
  waiting: 'bg-warn-bg text-warn border-transparent',
  error: 'bg-bad-bg text-bad border-transparent',
}

export function Badge({
  children,
  tone = 'neutral',
}: {
  children: ReactNode
  tone?: Tone
}) {
  return (
    <span
      className={[
        'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5',
        'text-xs font-medium',
        BADGE_TONE[tone],
      ].join(' ')}
    >
      {children}
    </span>
  )
}

// --- Notices ---------------------------------------------------------------

/** Quiet explanatory copy; warning colour is reserved for an actual warning. */
export function Notice({
  children,
  tone = 'accent',
  symbol,
  className = '',
}: {
  children: ReactNode
  tone?: 'accent' | 'good' | 'waiting'
  symbol?: ReactNode
  className?: string
}) {
  const tones = {
    accent: 'bg-accent-bg text-ink-2 [&_svg]:text-accent',
    good: 'bg-good-bg text-good [&_svg]:text-good',
    waiting: 'bg-warn-bg text-warn [&_svg]:text-warn',
  }
  return (
    <div
      className={[
        'flex gap-2.5 rounded-md px-4 py-3.5 text-[12.5px] leading-relaxed',
        tones[tone],
        className,
      ].join(' ')}
    >
      {symbol && <span className="mt-0.5 shrink-0">{symbol}</span>}
      <span>{children}</span>
    </div>
  )
}

// --- Inputs ----------------------------------------------------------------

export function SearchInput({
  valueText,
  onChange,
  placeholder,
}: {
  valueText: string
  onChange: (valueText: string) => void
  placeholder: string
}) {
  return (
    <label className="flex max-w-[380px] flex-1 items-center gap-2.5 rounded-sm border border-line bg-card px-3.5 py-2.5 shadow-1">
      <Search size={16} className="shrink-0 text-ink-3" aria-hidden="true" />
      <input
        type="search"
        value={valueText}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        aria-label={placeholder}
        className="w-full border-0 bg-transparent text-sm outline-none placeholder:text-ink-3"
      />
    </label>
  )
}

export function TextInput({
  valueText,
  onChange,
  label,
  placeholder,
  error,
  mono = false,
  autoFocus = false,
  onEnter,
}: {
  valueText: string
  onChange: (valueText: string) => void
  label?: string
  placeholder?: string
  error?: string | undefined
  mono?: boolean
  autoFocus?: boolean
  onEnter?: () => void
}) {
  return (
    <label className="block">
      {label && (
        <span className="mb-1.5 block text-[13px] text-ink-2">{label}</span>
      )}
      <input
        type="text"
        value={valueText}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && onEnter) {
            e.preventDefault()
            onEnter()
          }
        }}
        placeholder={placeholder}
        spellCheck={false}
        /* The floating question follows a pointer action, so focus belongs here. */
        autoFocus={autoFocus}
        aria-invalid={error ? true : undefined}
        className={[
          'w-full rounded-sm border bg-card-2 px-2.5 py-2 text-[13px]',
          'outline-none placeholder:text-ink-3',
          error ? 'border-bad' : 'border-line-2',
          mono ? 'font-mono' : '',
        ].join(' ')}
      />
      {error && <span className="mt-1 block text-xs text-bad">{error}</span>}
    </label>
  )
}

// --- Empty states ----------------------------------------------------------

/** Explains why a screen is empty and what can happen next. */
export function Empty({
  title,
  detail,
  symbol,
  action,
}: {
  title: string
  detail?: string
  symbol?: ReactNode
  action?: ReactNode
}) {
  return (
    <div className="flex flex-col items-center justify-center px-8 py-20 text-center">
      {symbol && (
        <div className="mb-5 grid size-12 place-items-center rounded-md bg-card-2 text-ink-3">
          {symbol}
        </div>
      )}
      <p className="text-[17px] font-semibold tracking-[-0.02em]">{title}</p>
      {detail && <p className="mt-2 max-w-[46ch] text-[13.5px] text-ink-2">{detail}</p>}
      {action && <div className="mt-6">{action}</div>}
    </div>
  )
}
