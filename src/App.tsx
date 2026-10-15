/**
 * Application shell with a sidebar and one of four places.
 *
 * Template detail and the setup assistant are paths from Templates rather
 * than additional places, so the sidebar remains on Templates during them.
 */

import { open } from '@tauri-apps/plugin-dialog'
import { AlertCircle, X } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'

import { api, SubstraktError } from './api/client'
import type { DocumentType, Status } from './api/types'
import { applyTheme, storedTheme, type Theme } from './design/theme'
import { LanguageProvider, errorText, useTexts } from './i18n'
import { Assistant } from './places/Assistant'
import { Settings } from './places/Settings'
import { Review } from './places/Review'
import { Overview } from './places/Overview'
import { Templates } from './places/Templates'
import { TemplateView } from './places/TemplateView'
import { Sidebar, type Place } from './shell/Sidebar'
import { useSession } from './state/session'

/** Current place or nested template path, including the path's required data. */
type View =
  | { place: Place }
  | { place: 'template'; typeId: number }
  | { place: 'assistant'; typeId: number | null }

/** Opens the file picker and returns null when the user cancels. */
export async function chooseDocument(filterName: string): Promise<string | null> {
  const selection = await open({
    multiple: false,
    filters: [{
      name: filterName,
      extensions: [
        'pdf', 'xlsx', 'xlsm', 'xls', 'csv', 'tsv',
        'png', 'jpg', 'jpeg', 'tif', 'tiff', 'bmp', 'webp',
      ],
    }],
  })
  return typeof selection === 'string' ? selection : null
}

export function App() {
  return (
    <LanguageProvider>
      <Application />
    </LanguageProvider>
  )
}

function Application() {
  const texts = useTexts()
  const [status, setStatus] = useState<Status | null>(null)
  const [view, setView] = useState<View>({ place: 'overview' })
  const [theme, setTheme] = useState<Theme>(storedTheme)
  const [templates, setTemplates] = useState<DocumentType[]>([])
  const [reading, setReading] = useState(false)
  // `detail` explicitly includes undefined because exact optional properties
  // distinguish a missing member from a member whose value is undefined.
  const [error, setError] = useState<{
    key: string
    fallback: string
    detail?: string | undefined
  } | null>(null)

  const session = useSession()

  const showError = useCallback((f: unknown) => {
    if (f instanceof SubstraktError) {
      setError({ key: f.key, fallback: f.message, detail: f.detail ?? undefined })
    } else {
      setError({ key: 'internal-error', fallback: texts.errors.title, detail: String(f) })
    }
  }, [texts.errors.title])

  // Poll during sidecar start-up instead of claiming that it is already ready.
  useEffect(() => {
    let discarded = false
    let attempts = 0

    const check = () => {
      void api
        .status()
        .then((s) => {
          if (discarded) return
          setStatus(s)
          if (!s.connected && attempts < 60) {
            attempts++
            setTimeout(check, 500)
          }
        })
        .catch(() => {
          if (!discarded && attempts < 60) {
            attempts++
            setTimeout(check, 500)
          }
        })
    }

    check()
    return () => {
      discarded = true
    }
  }, [])

  const loadTemplates = useCallback(async () => {
    try {
      setTemplates(await api.documentTypes())
    } catch {
      // The application remains usable without saved templates.
    }
  }, [])

  useEffect(() => {
    if (status?.connected) void loadTemplates()
  }, [status?.connected, loadTemplates])

  const changeTheme = useCallback((nextTheme: Theme) => {
    setTheme(nextTheme)
    applyTheme(nextTheme)
  }, [])

  /** Reads one document and opens Review immediately when a value is unresolved. */
  const readDocument = useCallback(
    async (typeId: number) => {
      setError(null)
      setReading(true)
      try {
        const template = await api.documentType(typeId)
        const pathValue = await chooseDocument(texts.document.formats)
        if (!pathValue) return

        const document = await api.loadDocument(pathValue)
        const run = await api.extract(document.id, template.fields)

        const record = session.add({
          docId: document.id,
          document,
          fileName: document.filename,
          template: template.name,
          templateId: template.id,
          output: template.output,
          readAt: new Date().toISOString(),
          fields: template.fields,
          results: run.results,
        })

        setView({ place: record.state === 'waiting' ? 'review' : 'overview' })
      } catch (f) {
        showError(f)
      } finally {
        setReading(false)
      }
    },
    [session, showError, texts.document.formats],
  )

  // Escape closes the global error; all other shortcuts belong to a place.
  useEffect(() => {
    const keyHandler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setError(null)
    }
    window.addEventListener('keydown', keyHandler)
    return () => window.removeEventListener('keydown', keyHandler)
  }, [])

  const sidebarPlace: Place =
    view.place === 'template' || view.place === 'assistant' ? 'templates' : view.place

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar
        place={sidebarPlace}
        onPlace={(place) => setView({ place })}
        waiting={session.reviewCount}
        theme={theme}
        onTheme={changeTheme}
        version={status?.version ?? '—'}
      />

      <main className="flex min-w-0 flex-1 flex-col">
        {error && (
          <div
            role="alert"
            className="flex shrink-0 items-start gap-2.5 border-b border-line bg-bad-bg px-6 py-3 text-[13.5px] text-bad"
          >
            <AlertCircle size={16} className="mt-0.5 shrink-0" aria-hidden="true" />
            <div className="flex-1">
              <p>{errorText(texts, error.key, error.fallback)}</p>
              {error.detail && (
                <details className="mt-1">
                  <summary className="cursor-pointer text-xs opacity-70">
                    {texts.errors.showDetails}
                  </summary>
                  <pre className="mt-1 overflow-x-auto font-mono text-xs opacity-70">
                    {error.detail}
                  </pre>
                </details>
              )}
            </div>
            <button
              type="button"
              onClick={() => setError(null)}
              aria-label={texts.errors.close}
              className="rounded p-0.5 opacity-70 hover:opacity-100"
            >
              <X size={14} />
            </button>
          </div>
        )}

        <div className="min-h-0 flex-1 overflow-y-auto">
          {view.place === 'overview' && (
            <Overview
              status={status}
              session={session}
              templates={templates}
              onReview={() => setView({ place: 'review' })}
              onTemplates={() => setView({ place: 'templates' })}
              onNewTemplate={() => setView({ place: 'assistant', typeId: null })}
              onError={showError}
            />
          )}

          {view.place === 'review' && (
            <Review
              session={session}
              onError={showError}
              onFinish={() => setView({ place: 'overview' })}
            />
          )}

          {view.place === 'templates' && (
            <Templates
              templates={templates}
              onOpen={(typeId) => setView({ place: 'template', typeId })}
              onNew={() => setView({ place: 'assistant', typeId: null })}
            />
          )}

          {view.place === 'template' && (
            <TemplateView
              typeId={view.typeId}
              reading={reading}
              onBack={() => setView({ place: 'templates' })}
              onReadDocument={() => void readDocument(view.typeId)}
              onChange={() => setView({ place: 'assistant', typeId: view.typeId })}
              onDeleted={() => {
                void loadTemplates()
                setView({ place: 'templates' })
              }}
              onError={showError}
            />
          )}

          {view.place === 'assistant' && (
            <Assistant
              typeId={view.typeId}
              onCancel={() => setView({ place: 'templates' })}
              onFinish={(typeId) => {
                void loadTemplates()
                setView({ place: 'template', typeId })
              }}
              onError={showError}
            />
          )}

          {view.place === 'settings' && (
            <Settings status={status} theme={theme} onTheme={changeTheme} />
          )}
        </div>
      </main>
    </div>
  )
}
