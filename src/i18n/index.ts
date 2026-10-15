/**
 * Runtime language selection for the two complete interface dictionaries.
 *
 * The choice stays in window-local storage. It does not cross the frontend
 * boundary and falls back to German whenever storage is unavailable or holds
 * an unknown value.
 */

import {
  createContext,
  createElement,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type JSX,
  type ReactNode,
} from 'react'

import { de } from './de'
import { en } from './en'

export type Language = 'de' | 'en'
export type Texts = typeof de

export const LANGUAGES: Language[] = ['de', 'en']

const STORAGE_KEY = 'substrakt.language'
const TEXTS: Record<Language, Texts> = { de, en }

interface LanguageContextValue {
  language: Language
  setLanguage: (language: Language) => void
  texts: Texts
}

const LanguageContext = createContext<LanguageContextValue | null>(null)

export function storedLanguage(): Language {
  try {
    const language = localStorage.getItem(STORAGE_KEY)
    return language === 'en' || language === 'de' ? language : 'de'
  } catch {
    return 'de'
  }
}

export function applyLanguage(language: Language): void {
  document.documentElement.lang = language
  try {
    localStorage.setItem(STORAGE_KEY, language)
  } catch {
    // The live interface can still change when private storage is unavailable.
  }
}

export function LanguageProvider({ children }: { children: ReactNode }): JSX.Element {
  const [language, setStoredLanguage] = useState<Language>(storedLanguage)

  useEffect(() => applyLanguage(language), [language])

  const setLanguage = useCallback((nextLanguage: Language) => {
    applyLanguage(nextLanguage)
    setStoredLanguage(nextLanguage)
  }, [])

  const value = useMemo(
    () => ({ language, setLanguage, texts: TEXTS[language] }),
    [language, setLanguage],
  )

  return createElement(LanguageContext.Provider, { value }, children)
}

function useLanguageContext(): LanguageContextValue {
  const context = useContext(LanguageContext)
  if (!context) throw new Error('LanguageProvider is missing')
  return context
}

export function useTexts(): Texts {
  return useLanguageContext().texts
}

export function useLanguage(): [Language, (language: Language) => void] {
  const { language, setLanguage } = useLanguageContext()
  return [language, setLanguage]
}

export function errorText(texts: Texts, key: string, fallback: string): string {
  return texts.errors.messages[key] ?? fallback
}
