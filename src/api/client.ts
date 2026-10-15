/**
 * The frontend's only route to the backend.
 *
 * The browser knows neither the sidecar port nor its session token. Every call
 * goes through a Tauri command in `src-tauri/src/bridge.rs`; ESLint and the
 * repository egress gate reject a direct browser network path.
 */

import { invoke } from '@tauri-apps/api/core'

import type {
  DocumentInfo,
  DocumentText,
  DocumentType,
  Export,
  FieldSpec,
  ExtractionRun,
  SheetInfo,
  SheetRaster,
  Status,
  WordList,
} from './types'
import { isBridgeError } from './types'
import { errorText } from '../i18n'
import { de } from '../i18n/de'

/** Error with an already translated display message and a stable key. */
export class SubstraktError extends Error {
  readonly key: string
  readonly detail: string | null

  constructor(key: string, message: string, detail: string | null = null) {
    super(message)
    this.name = 'SubstraktError'
    this.key = key
    this.detail = detail
  }
}

async function call<T>(command: string, args?: Record<string, unknown>): Promise<T> {
  try {
    return await invoke<T>(command, args)
  } catch (error) {
    if (isBridgeError(error)) {
      throw new SubstraktError(
        error.key,
        errorText(de, error.key, error.title),
        error.detail,
      )
    }
    // A non-bridge error is a frontend defect and receives its own stable key.
    throw new SubstraktError(
      'internal-error',
      errorText(de, 'internal-error', de.errors.title),
      String(error),
    )
  }
}

export const api = {
  status: () => call<Status>('sidecar_status'),

  loadDocument: (path: string) => call<DocumentInfo>('load_document', { path }),

  documentInfo: (docId: string) => call<DocumentInfo>('document_info', { docId }),

  closeDocument: (docId: string) =>
    call<{ removed: boolean }>('close_document', { docId }),

  /** Raw file bytes for PDF.js. */
  documentBytes: async (docId: string): Promise<Uint8Array> => {
    const data = await call<ArrayBuffer | number[]>('document_bytes', { docId })
    return data instanceof ArrayBuffer ? new Uint8Array(data) : new Uint8Array(data)
  },

  documentText: (docId: string) => call<DocumentText>('document_text', { docId }),

  pageWords: (docId: string, page: number) =>
    call<WordList>('page_words', { docId, page }),

  /** Rendered PNG page for images; PDF.js renders PDF pages itself. */
  renderPage: async (docId: string, page: number, scale = 1): Promise<Blob> => {
    const data = await call<ArrayBuffer | number[]>('render_page', { docId, page, scale })
    const bytes = data instanceof ArrayBuffer ? new Uint8Array(data) : new Uint8Array(data)
    return new Blob([bytes], { type: 'image/png' })
  },

  sheets: (docId: string) => call<SheetInfo[]>('sheets', { docId }),

  sheetRaster: (docId: string, index: number) =>
    call<SheetRaster>('sheet_raster', { docId, index }),

  /**
   * Extraction path A: region, regular expression and built-in extractors.
   * Manual values take precedence, which is the only path for handwriting.
   */
  extract: (docId: string, fields: FieldSpec[], manual?: Record<string, string>) =>
    call<ExtractionRun>('extract', { docId, fields, manual }),

  /** Like `extract`, but with values and provenance separated for export. */
  export: (docId: string, fields: FieldSpec[], manual?: Record<string, string>) =>
    call<Export>('export', { docId, fields, manual }),

  sampleFields: () => call<FieldSpec[]>('sample_fields'),

  /** Persisted value sets without their values, used by the template list. */
  documentTypes: () => call<DocumentType[]>('document_types'),

  documentType: (typeId: number) => call<DocumentType>('document_type', { typeId }),

  saveDocumentType: (
    type: Omit<DocumentType, 'id' | 'updated_at' | 'value_count'>,
  ) => call<DocumentType>('save_document_type', { documentType: type }),

  deleteDocumentType: (typeId: number) =>
    call<{ deleted: boolean }>('delete_document_type', { typeId }),
}
