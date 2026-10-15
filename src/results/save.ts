/**
 * Saves a read result in either user-facing table form or machine-facing JSON.
 *
 * The CSV uses display names, semicolons, a byte-order mark and German decimal
 * commas. This combination was measured to open correctly in German Excel.
 */

import type { OutputFormat, Export, FieldSpec } from '../api/types'

/** Escapes one CSV cell by doubling quotation marks. */
function csvCell(valueText: string): string {
  return /[";\n\r]/.test(valueText) ? `"${valueText.replace(/"/g, '""')}"` : valueText
}

/** Produces one header row and one value row in value-definition order. */
export function asTable(fields: FieldSpec[], data: Record<string, unknown>): string {
  const head = fields.map((f) => csvCell(f.label || f.name)).join(';')
  const row = fields
    .map((f) => {
      const valueText = data[f.name]
      if (valueText === null || valueText === undefined) return ''
      // German Excel requires a decimal comma to recognise the cell as numeric.
      if (typeof valueText === 'number') return csvCell(valueText.toString().replace('.', ','))
      return csvCell(String(valueText))
    })
    .join(';')
  return `\uFEFF${head}\r\n${row}\r\n`
}

/** File extension and media type for each output format. */
const FORMATS: Record<OutputFormat, { extension: string; mediaType: string }> = {
  table: { extension: 'csv', mediaType: 'text/csv;charset=utf-8' },
  file: { extension: 'json', mediaType: 'application/json' },
}

/**
 * Saves through a browser download. The application does not write to an
 * arbitrary filesystem location until templates gain an explicit target.
 */
export function saveResult(
  result: Export,
  fields: FieldSpec[],
  format: OutputFormat,
  fileName: string,
): void {
  const { extension, mediaType } = FORMATS[format]
  const content =
    format === 'table'
      ? asTable(fields, result.data)
      : JSON.stringify(result, null, 2)

  const blob = new Blob([content], { type: mediaType })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${fileName.replace(/\.[^.]+$/, '')}.${extension}`
  a.click()
  URL.revokeObjectURL(url)
}
