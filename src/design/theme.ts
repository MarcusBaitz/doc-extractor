/**
 * Persists the light or dark theme inside the frontend window.
 *
 * Light is deliberately the default instead of following the system theme.
 * The choice is local until the sidecar owns application settings.
 */

export type Theme = 'light' | 'dark'

const STORAGE_KEY = 'substrakt.theme'

/** Returns the stored choice, or light when storage cannot be read. */
export function storedTheme(): Theme {
  try {
    return localStorage.getItem(STORAGE_KEY) === 'dark' ? 'dark' : 'light'
  } catch {
    // Private or locked storage must not prevent the default theme.
    return 'light'
  }
}

/** Applies the theme immediately and remembers it when storage is available. */
export function applyTheme(theme: Theme): void {
  document.documentElement.dataset['theme'] = theme
  try {
    localStorage.setItem(STORAGE_KEY, theme)
  } catch {
    // A live theme change still works when persistence is unavailable.
  }
}
