/**
 * Renders every user place in both languages and enforces the interface
 * vocabulary. The rendered gate catches a raw internal key even when the
 * dictionaries themselves are complete.
 *
 * The assistant and template detail are intentionally excluded because their
 * result-name step is the one place where technical keys are the subject.
 */

import { renderToStaticMarkup } from 'react-dom/server'
import { afterEach, describe, expect, it, vi } from 'vitest'

// PDF.js reads `DOMMatrix` while its module loads, but Node does not provide
// it. These tests cover interface language and structure, not PDF drawing.
vi.mock('pdfjs-dist', () => ({
  GlobalWorkerOptions: { workerSrc: '' },
  getDocument: () => ({ promise: Promise.resolve(null) }),
}))
vi.mock('pdfjs-dist/build/pdf.worker.min.mjs?url', () => ({ default: '' }))

import type { DocumentType, FieldSpec, Status } from '../../src/api/types'
import {
  applyLanguage,
  LanguageProvider,
  storedLanguage,
  type Language,
} from '../../src/i18n'
import { Overview } from '../../src/places/Overview'
import { Review } from '../../src/places/Review'
import { Settings } from '../../src/places/Settings'
import { Templates } from '../../src/places/Templates'
import { Sidebar } from '../../src/shell/Sidebar'
import type { DocumentRecord, Session } from '../../src/state/session'

const noop = () => undefined

const STATUS: Status = {
  connected: true,
  version: '0.1.0',
  mode: 'airgap',
  backend: 'sidecar',
}

function field(name: string, label: string): FieldSpec {
  return {
    name,
    label,
    question: '',
    json_type: 'string',
    required: false,
    method: 'auto',
    regex: null,
    extractor: null,
    normalization: null,
    regions: [],
  }
}

const TEMPLATES: DocumentType[] = [
  {
    id: 1,
    name: 'Rechnung — Nordwind Maschinenbau',
    description: '',
    fields: [],
    updated_at: new Date(Date.now() - 4 * 60_000).toISOString(),
    output: 'table',
    value_count: 9,
  },
  {
    id: 2,
    name: 'Lieferschein — Hansen Logistik',
    description: '',
    fields: [],
    updated_at: new Date(Date.now() - 3 * 86_400_000).toISOString(),
    output: 'file',
    value_count: 6,
  },
]

/** A record with one unclear value: the case the review place is built for. */
function record(): DocumentRecord {
  return {
    id: 'b1',
    docId: 'd1',
    document: {
      id: 'd1',
      filename: 'Rechnung 2026-0145.pdf',
      sha256: '',
      kind: 'pdf',
      pages: [
        {
          number: 1,
          width: 595,
          height: 842,
          rotation: 0,
          sheet_name: null,
          has_text_layer: true,
        },
      ],
      meta: {
        size_bytes: 120_000,
        page_count: 1,
        word_count: 300,
        text_source: 'text_layer',
        encoding: null,
        delimiter: null,
        producer: null,
        created: null,
        warnings: [],
      },
    },
    fileName: 'Rechnung 2026-0145.pdf',
    template: 'Rechnung — Nordwind Maschinenbau',
    templateId: 1,
    output: 'table',
    readAt: new Date(Date.now() - 5 * 60_000).toISOString(),
    state: 'waiting',
    fields: [field('zahlungsbedingungen', 'Zahlungsbedingungen'), field('iban', 'IBAN')],
    results: [
      {
        field: 'zahlungsbedingungen',
        value: '14 Tage 2 % Skonto, 30 Tage netto',
        normalized: null,
        confidence: 0.74,
        source: 'region',
        locator: { kind: 'pdf_rect', page: 0, x0: 50, y0: 600, x1: 300, y1: 620 },
        matched_text: '14 Tage',
        grounded: false,
        note: 'Confidence too low — review required',
      },
      {
        field: 'iban',
        value: 'DE21 2105 0170 1002 3456 78',
        normalized: null,
        confidence: 0.99,
        source: 'extractor',
        locator: null,
        matched_text: 'DE21',
        grounded: true,
        note: '',
      },
    ],
    corrections: {},
    missing: [],
    confirmed: [],
  }
}

function session(records: DocumentRecord[]): Session {
  return {
    records,
    reviewCount: records.filter((item) => item.state === 'waiting').length,
    gaps: records.filter((item) => item.missing.length > 0).length,
    add: () => records[0]!,
    change: noop,
    remove: noop,
  }
}

function storage(value: string | null) {
  return {
    getItem: () => value,
    setItem: vi.fn(),
  }
}

function renderIn(language: Language, node: React.ReactNode): string {
  vi.stubGlobal('localStorage', storage(language))
  return renderToStaticMarkup(<LanguageProvider>{node}</LanguageProvider>)
}

/** Removes presentation attributes, leaving the text and semantic markup. */
function readable(markup: string): string {
  return markup.replace(/\sclass="[^"]*"/g, '').replace(/\sstyle="[^"]*"/g, '')
}

function places(language: Language) {
  return {
    'overview with records': renderIn(
      language,
      <Overview
        status={STATUS}
        session={session([record()])}
        templates={TEMPLATES}
        onReview={noop}
        onTemplates={noop}
        onNewTemplate={noop}
        onError={noop}
      />,
    ),
    'empty overview': renderIn(
      language,
      <Overview
        status={null}
        session={session([])}
        templates={[]}
        onReview={noop}
        onTemplates={noop}
        onNewTemplate={noop}
        onError={noop}
      />,
    ),
    'review with one open value': renderIn(
      language,
      <Review session={session([record()])} onError={noop} onFinish={noop} />,
    ),
    'empty review': renderIn(
      language,
      <Review session={session([])} onError={noop} onFinish={noop} />,
    ),
    templates: renderIn(
      language,
      <Templates templates={TEMPLATES} onOpen={noop} onNew={noop} />,
    ),
    'empty templates': renderIn(
      language,
      <Templates templates={[]} onOpen={noop} onNew={noop} />,
    ),
    settings: renderIn(
      language,
      <Settings status={STATUS} theme="light" onTheme={noop} />,
    ),
    sidebar: renderIn(
      language,
      <Sidebar
        place="overview"
        onPlace={noop}
        waiting={3}
        theme="light"
        onTheme={noop}
        version="0.1.0"
      />,
    ),
  }
}

afterEach(() => vi.unstubAllGlobals())

describe.each<Language>(['de', 'en'])('the four places in %s', (language) => {
  it('render with and without data', () => {
    for (const [place, markup] of Object.entries(places(language))) {
      expect(markup.length, place).toBeGreaterThan(80)
    }
  })

  it('show their core message rather than an empty shell', () => {
    const rendered = places(language)
    if (language === 'de') {
      expect(rendered['overview with records']).toContain('Alles läuft')
      expect(rendered['review with one open value']).toContain('Eine Angabe ist nicht eindeutig')
      expect(rendered['empty review']).toContain('Nichts zu prüfen')
      expect(rendered['empty templates']).toContain('Noch keine Vorlage')
      expect(rendered.sidebar).toContain('Alle Belege bleiben auf diesem Gerät')
    } else {
      expect(rendered['overview with records']).toContain('Everything is running')
      expect(rendered['review with one open value']).toContain('One detail is unclear')
      expect(rendered['empty review']).toContain('Nothing to review')
      expect(rendered['empty templates']).toContain('No template yet')
      expect(rendered.sidebar).toContain('All documents stay on this device')
    }
  })

  it('emphasises no more than one of the three overview numbers', () => {
    for (const markup of Object.values(places(language))) {
      const actionable = markup.match(/data-actionable="true"/g)?.length ?? 0
      expect(actionable).toBeLessThanOrEqual(1)
    }
    expect(places(language)['overview with records']).toContain('data-actionable="true"')
  })

  it('keeps the review metric quiet when nothing is waiting', () => {
    const markup = renderIn(
      language,
      <Overview
        status={STATUS}
        session={session([])}
        templates={TEMPLATES}
        onReview={noop}
        onTemplates={noop}
        onNewTemplate={noop}
        onError={noop}
      />,
    )
    expect(markup).not.toContain('bg-warn-bg')
  })

  it('has at most one dark button on each screen', () => {
    for (const [place, markup] of Object.entries(places(language))) {
      if (place === 'sidebar') continue
      const darkButtons = markup.match(/<button[^>]*class="[^"]*\bbg-ink(?![-\w])/g)?.length ?? 0
      expect(darkButtons, place).toBeLessThanOrEqual(1)
    }
  })
})

const FORBIDDEN_DE: Array<[string, RegExp]> = [
  ['Konfidenz', /Konfidenz/i],
  ['Locator', /Locator/i],
  ['Provenance', /Provenance/i],
  ['Bounding-Box', /Bounding/i],
  ['OCR', /\bOCR\b/],
  ['Dokumenttyp', /Dokumenttyp/i],
  ['Template', /Template/i],
  ['Feld statt Angabe', /\bFeld(er)?\b/],
  ['Dokument statt Beleg', /\bDokument(e|s)?\b/],
  ['Extraktion', /Extrakt/i],
  ['Regex', /Regex/i],
  ['Modellname', /GLiNER|Granite|Tesseract|Q4_K_M|rapidfuzz/i],
  ['Schlüssel in snake_case', /\b[a-zäöü]+_[a-zäöü]+\b/],
]

const FORBIDDEN_EN: Array<[string, RegExp]> = [
  ['confidence', /\bconfidence\b/i],
  ['locator', /\blocator\b/i],
  ['provenance', /\bprovenance\b/i],
  ['bounding box', /\bbounding[ -]box\b/i],
  ['OCR', /\bOCR\b/],
  ['document type', /\bdocument type\b/i],
  ['extraction', /\bextraction\b/i],
  ['regex', /\bregex\b/i],
  ['field', /\bfields?\b/i],
  ['threshold', /\bthreshold\b/i],
  ['model name', /GLiNER|Granite|Tesseract|Q4_K_M|rapidfuzz/i],
  ['snake_case key', /\b[a-z]+_[a-z]+\b/],
]

describe('the interface vocabulary', () => {
  it('keeps engine-room terms off German user screens', () => {
    for (const [place, markup] of Object.entries(places('de'))) {
      const text = readable(markup)
      for (const [term, pattern] of FORBIDDEN_DE) {
        expect(pattern.test(text), `“${term}” appears on “${place}”`).toBe(false)
      }
    }
  })

  it('keeps engine-room terms and German copy off English user screens', () => {
    for (const [place, markup] of Object.entries(places('en'))) {
      const text = readable(markup)
      for (const [term, pattern] of FORBIDDEN_EN) {
        expect(pattern.test(text), `“${term}” appears on “${place}”`).toBe(false)
      }
      expect(/[äöüß]/i.test(text), `German copy appears on “${place}”`).toBe(false)
    }
  })
})

describe('language persistence', () => {
  it('falls back to German for an unknown stored value', () => {
    vi.stubGlobal('localStorage', storage('fr'))
    expect(storedLanguage()).toBe('de')
  })

  it('falls back to German when storage is unavailable', () => {
    vi.stubGlobal('localStorage', { getItem: () => { throw new Error('blocked') } })
    expect(storedLanguage()).toBe('de')
  })

  it('stores the language and updates the document language', () => {
    const localStorage = storage(null)
    const documentElement = { lang: 'de' }
    vi.stubGlobal('localStorage', localStorage)
    vi.stubGlobal('document', { documentElement })

    applyLanguage('en')

    expect(documentElement.lang).toBe('en')
    expect(localStorage.setItem).toHaveBeenCalledWith('substrakt.language', 'en')
  })
})
