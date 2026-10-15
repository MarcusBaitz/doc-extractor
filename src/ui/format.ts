/**
 * Formats numbers, dates and times in the active interface language.
 *
 * Human-readable dates are written out. ISO dates belong in saved results,
 * not on a screen where they read like reference numbers.
 */

import type { Language, Texts } from '../i18n'

function locale(language: Language): string {
  return language === 'de' ? 'de-DE' : 'en-GB'
}

export function formatNumber(value: number, language: Language): string {
  return value.toLocaleString(locale(language))
}

export function formatBytes(bytes: number, language: Language): string {
  if (bytes < 1024) return `${bytes} B`
  const units = ['KB', 'MB', 'GB']
  let value = bytes / 1024
  let index = 0
  while (value >= 1024 && index < units.length - 1) {
    value /= 1024
    index++
  }
  return `${value.toLocaleString(locale(language), {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  })} ${units[index]}`
}

/** Returns a written date, or the original text when it cannot be parsed. */
export function longDate(
  value: string | Date | null | undefined,
  language: Language,
): string {
  if (!value) return ''
  const date = typeof value === 'string' ? new Date(value) : value
  if (Number.isNaN(date.getTime())) return typeof value === 'string' ? value : ''
  return new Intl.DateTimeFormat(locale(language), {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  }).format(date)
}

export function timeOfDay(value: string | Date, language: Language): string {
  const date = typeof value === 'string' ? new Date(value) : value
  if (Number.isNaN(date.getTime())) return ''
  return new Intl.DateTimeFormat(locale(language), {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(date)
}

/** Returns a short relative time, switching to a written date after a week. */
export function relativeTime(value: string | Date, language: Language, texts: Texts): string {
  const date = typeof value === 'string' ? new Date(value) : value
  if (Number.isNaN(date.getTime())) return ''

  const seconds = Math.round((Date.now() - date.getTime()) / 1000)
  if (seconds < 60) return texts.time.justNow

  const minutes = Math.round(seconds / 60)
  if (minutes < 60) {
    return minutes === 1 ? texts.time.minuteAgo : texts.time.minutesAgo(minutes)
  }

  const hours = Math.round(minutes / 60)
  if (hours < 24) {
    return hours === 1 ? texts.time.hourAgo : texts.time.hoursAgo(hours)
  }

  const days = Math.round(hours / 24)
  if (days === 1) return texts.time.yesterday
  if (days < 7) return texts.time.daysAgo(days)

  return longDate(date, language)
}
