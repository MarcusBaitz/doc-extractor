/**
 * Types for the sidecar contract.
 *
 * This mirrors `sidecar/substrakt/model.py`, which is authoritative.
 * `scripts/check-api.py` compares both views with `schema/openapi.json`.
 */

export type { ImageRect, Locator, PdfRect, Rotation, SheetRange } from '../viewer/coords'

import type { Locator } from '../viewer/coords'

export type DocumentFormat = 'pdf' | 'sheet' | 'image'

/** Origin of the text, recorded and displayed per document. */
export type TextSource = 'text_layer' | 'ocr' | 'vlm' | 'cells' | 'none'

export interface Page {
  number: number
  /** PDF points or pixels; column count for spreadsheets. */
  width: number
  /** PDF points or pixels; row count for spreadsheets. */
  height: number
  rotation: 0 | 90 | 180 | 270
  sheet_name: string | null
  has_text_layer: boolean
}

export interface Word {
  text: string
  page: number
  locator: Locator
  /** `null` for an exact text layer, set for OCR. */
  confidence: number | null
}

export interface DocumentMeta {
  size_bytes: number
  page_count: number
  word_count: number
  text_source: TextSource
  encoding: string | null
  delimiter: string | null
  producer: string | null
  created: string | null
  warnings: string[]
}

/** Document without its word index — the response from `load_document`. */
export interface DocumentInfo {
  id: string
  filename: string
  sha256: string
  kind: DocumentFormat
  pages: Page[]
  meta: DocumentMeta
}

export interface TextChunk {
  page: number
  text: string
  sheet_name: string | null
}

export interface DocumentText {
  chunks: TextChunk[]
  text_source: TextSource
}

export interface WordList {
  page: number
  words: Word[]
}

export interface SheetInfo {
  index: number
  name: string
  rows: number
  columns: number
}

export interface SheetRaster {
  index: number
  name: string
  rows: string[][]
}

// --- Extraction ------------------------------------------------------------

export type JsonType = 'string' | 'number' | 'integer' | 'date' | 'boolean'
export type Method = 'auto' | 'region' | 'regex' | 'extractor'
export type Source = 'region' | 'regex' | 'extractor' | 'manual' | 'none'

export interface FieldSpec {
  /** Key in ExtractionResult, such as `document_number`; never shown in the UI. */
  name: string
  /** User-facing label, such as “Rechnungsnummer”. */
  label: string
  question: string
  json_type: JsonType
  required: boolean
  method: Method
  regex: string | null
  extractor: string | null
  normalization: string | null
  regions: Locator[]
  /**
   * How a value is found next to its label. This comes from the document-kind
   * YAML file; user-created fields have no rule.
   */
  label_rule?: LabelRule | null
}

/** Rule from `sidecar/substrakt/document_kinds/*.yml`; mirrors Python `LabelRule`. */
export interface LabelRule {
  patterns: string[]
  value: 'identifier' | 'date' | 'amount' | 'code' | 'vat_id' | 'company' | 'title'
  values: string[]
  skip_tax_rate: boolean
  unlabelled: boolean
  letterhead_until: string[]
}

/** An extracted value together with its review evidence. */
export interface ExtractionResult {
  field: string
  value: string | null
  normalized: string | number | boolean | null
  confidence: number
  source: Source
  locator: Locator | null
  matched_text: string
  /** False below the threshold or without evidence, requiring review. */
  grounded: boolean
  note: string
}

export interface ExtractionRun {
  results: ExtractionResult[]
  duration_ms: number
  ungrounded: number
}

export interface Export {
  document: { file_name: string; sha256: string; pages: number; kind: DocumentFormat }
  data: Record<string, unknown>
  provenance: Record<string, unknown>
  run: { duration_ms: number; ungrounded: number; fields: number; version: string }
}

/**
 * A persisted, named set of values. List responses omit `fields` and include
 * `value_count`, avoiding one request per template just to show a count.
 */
export interface DocumentType {
  id: number | null
  name: string
  description: string
  fields: FieldSpec[]
  updated_at: string
  /** Whether each document becomes a table row or a separate file. */
  output: OutputFormat
  value_count: number
}

export type OutputFormat = 'table' | 'file'

export interface Status {
  connected: boolean
  version: string
  mode: 'airgap' | 'onprem' | 'cloud'
  /** Label shown in the technical status row. */
  backend: string
}

/** Bridge error whose stable key is resolved through the active dictionary. */
export interface BridgeError {
  key: string
  title: string
  detail: string | null
  status: number
}

export function isBridgeError(value: unknown): value is BridgeError {
  return (
    typeof value === 'object' &&
    value !== null &&
    'key' in value &&
    typeof (value as BridgeError).key === 'string'
  )
}
