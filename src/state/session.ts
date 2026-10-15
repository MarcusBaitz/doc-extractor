/**
 * Tracks documents read during the current session.
 *
 * Folder watching and a persistent review queue are still open. This state is
 * shaped so those sources can later feed the same overview, queue and history.
 */

import { useCallback, useMemo, useState } from 'react'

import type { OutputFormat, DocumentInfo, ExtractionResult, FieldSpec } from '../api/types'

export type DocumentState = 'waiting' | 'read' | 'filed' | 'error'

/** A read document with everything required for review and filing. */
export interface DocumentRecord {
  /** Ephemeral identifier within this session. */
  id: string
  /** Sidecar identifier, valid only while the document remains open. */
  docId: string
  document: DocumentInfo
  fileName: string
  /** Name of the template used to read the document. */
  template: string
  templateId: number | null
  /** Output selected by the template. */
  output: OutputFormat
  readAt: string
  state: DocumentState
  fields: FieldSpec[]
  results: ExtractionResult[]
  /** Manually entered or corrected values by key. */
  corrections: Record<string, string>
  /** Values explicitly marked as missing from the document. */
  missing: string[]
  /** Confirmed values, which must not return to the queue. */
  confirmed: string[]
}

/** Maximum number of documents retained in the session history. */
const HISTORY_LIMIT = 40

/** Returns values that still require a user decision. */
export function openValues(record: DocumentRecord): ExtractionResult[] {
  return record.results.filter(
    (e) =>
      !e.grounded &&
      !record.confirmed.includes(e.field) &&
      !record.missing.includes(e.field) &&
      record.corrections[e.field] === undefined,
  )
}

/** Returns a value's display name, falling back to its key. */
export function displayName(fields: FieldSpec[], keyName: string): string {
  const fieldSpec = fields.find((f) => f.name === keyName)
  return fieldSpec?.label?.trim() || keyName
}

export interface Session {
  records: DocumentRecord[]
  /** Documents with at least one unresolved value. */
  reviewCount: number
  /** Documents with a value explicitly marked as missing. */
  gaps: number
  add: (
    record: Omit<DocumentRecord, 'id' | 'state' | 'corrections' | 'missing' | 'confirmed'>,
  ) => DocumentRecord
  change: (id: string, patch: Partial<DocumentRecord>) => void
  remove: (id: string) => void
}

export function useSession(): Session {
  const [records, setRecords] = useState<DocumentRecord[]>([])

  const add = useCallback(
    (
      input: Omit<DocumentRecord, 'id' | 'state' | 'corrections' | 'missing' | 'confirmed'>,
    ): DocumentRecord => {
      const record: DocumentRecord = {
        ...input,
        id: `b${Date.now().toString(36)}`,
        corrections: {},
        missing: [],
        confirmed: [],
        state: input.results.some((e) => !e.grounded) ? 'waiting' : 'read',
      }
      setRecords((previous) => [record, ...previous].slice(0, HISTORY_LIMIT))
      return record
    },
    [],
  )

  const change = useCallback((id: string, patch: Partial<DocumentRecord>) => {
    setRecords((previous) => previous.map((a) => (a.id === id ? { ...a, ...patch } : a)))
  }, [])

  const remove = useCallback((id: string) => {
    setRecords((previous) => previous.filter((a) => a.id !== id))
  }, [])

  const reviewCount = useMemo(
    () => records.filter((a) => a.state === 'waiting' && openValues(a).length > 0).length,
    [records],
  )

  // A missing value is a finding, not an application error.
  const gaps = useMemo(
    () => records.filter((a) => a.missing.length > 0).length,
    [records],
  )

  return { records, reviewCount, gaps, add, change, remove }
}
