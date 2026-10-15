/**
 * Virtualised spreadsheet grid with sheet tabs and cell-range selection.
 * A spreadsheet range is not a pixel rectangle, so it remains a distinct
 * viewer mode. The small fixed-row virtualiser avoids another dependency.
 */

import { useMemo, useRef, useState } from 'react'

import { useTexts } from '../i18n'
import type { SheetInfo, SheetRaster } from '../api/types'

const ROW_HEIGHT = 26
const COLUMN_WIDTH = 128
const HEADER_WIDTH = 56
const OVERSCAN = 6

// A stable empty array keeps the memoised column count effective.
const EMPTY: string[][] = []

interface Props {
  sheetsList: SheetInfo[]
  raster: SheetRaster | null
  activeSheet: number
  selection: { row1: number; column1: number; row2: number; column2: number } | null
  onSheetChange: (index: number) => void
  onSelection: (range: { row1: number; column1: number; row2: number; column2: number } | null) => void
}

/** Converts a one-based column number to its spreadsheet name. */
export function columnName(index: number): string {
  let name = ''
  let n = index
  while (n > 0) {
    const rest = (n - 1) % 26
    name = String.fromCharCode(65 + rest) + name
    n = Math.floor((n - 1) / 26)
  }
  return name
}

export function SheetGrid({
  sheetsList,
  raster,
  activeSheet,
  selection,
  onSheetChange,
  onSelection,
}: Props) {
  const texts = useTexts()
  const scrollArea = useRef<HTMLDivElement>(null)
  const [scrollTop, setScrollTop] = useState(0)
  const [height, setHeight] = useState(600)
  const [dragging, setDragging] = useState<{ row: number; column: number } | null>(null)

  const rowsList = raster?.rows ?? EMPTY
  const columnNumber = useMemo(
    () => rowsList.reduce((max, r) => Math.max(max, r.length), 0),
    [rowsList],
  )

  const firstRow = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - OVERSCAN)
  const lastRow = Math.min(
    rowsList.length,
    Math.ceil((scrollTop + height) / ROW_HEIGHT) + OVERSCAN,
  )

  const inSelection = (row: number, column: number): boolean => {
    if (!selection) return false
    return (
      row >= Math.min(selection.row1, selection.row2) &&
      row <= Math.max(selection.row1, selection.row2) &&
      column >= Math.min(selection.column1, selection.column2) &&
      column <= Math.max(selection.column1, selection.column2)
    )
  }

  const startSelection = (row: number, column: number) => {
    setDragging({ row, column })
    onSelection({ row1: row, column1: column, row2: row, column2: column })
  }

  const extend = (row: number, column: number) => {
    if (!dragging) return
    onSelection({ row1: dragging.row, column1: dragging.column, row2: row, column2: column })
  }

  return (
    <div className="flex h-full flex-col">
      {sheetsList.length > 1 && (
        <div
          className="flex shrink-0 gap-1 overflow-x-auto border-b border-line bg-panel px-2 pt-2"
          role="tablist"
          aria-label={texts.viewer.sheet}
        >
          {sheetsList.map((sheet) => (
            <button
              key={sheet.index}
              type="button"
              role="tab"
              aria-selected={sheet.index === activeSheet}
              onClick={() => onSheetChange(sheet.index)}
              className={[
                'rounded-t-sm px-3 py-1.5 text-sm whitespace-nowrap transition-colors duration-(--dur-1)',
                sheet.index === activeSheet
                  ? 'bg-card font-medium text-ink shadow-1'
                  : 'text-ink-2 hover:bg-card-2 hover:text-ink',
              ].join(' ')}
            >
              {sheet.name}
            </button>
          ))}
        </div>
      )}

      <div
        ref={scrollArea}
        className="flex-1 overflow-auto bg-card"
        onScroll={(e) => {
          setScrollTop(e.currentTarget.scrollTop)
          setHeight(e.currentTarget.clientHeight)
        }}
        onMouseUp={() => setDragging(null)}
        onMouseLeave={() => setDragging(null)}
      >
        <div
          style={{
            height: rowsList.length * ROW_HEIGHT + ROW_HEIGHT,
            width: HEADER_WIDTH + columnNumber * COLUMN_WIDTH,
            position: 'relative',
          }}
        >
          {/* Column headings */}
          <div
            className="sticky top-0 z-20 flex border-b border-line-2 bg-card-2"
            style={{ height: ROW_HEIGHT }}
          >
            <div
              className="shrink-0 border-r border-line-2"
              style={{ width: HEADER_WIDTH }}
            />
            {Array.from({ length: columnNumber }, (_, i) => (
              <div
                key={i}
                className="shrink-0 border-r border-line-2 px-2 text-center text-xs leading-[26px] font-medium text-ink-2"
                style={{ width: COLUMN_WIDTH }}
              >
                {columnName(i + 1)}
              </div>
            ))}
          </div>

          {/* Render only visible rows. */}
          {rowsList.slice(firstRow, lastRow).map((rowValues, offset) => {
            const rowIndex = firstRow + offset
            return (
              <div
                key={rowIndex}
                className="absolute flex"
                style={{ top: (rowIndex + 1) * ROW_HEIGHT, height: ROW_HEIGHT }}
              >
                <div
                  className="sticky left-0 z-10 shrink-0 border-r border-b border-line bg-card-2 text-center text-xs leading-[26px] text-ink-3"
                  style={{ width: HEADER_WIDTH }}
                >
                  {rowIndex + 1}
                </div>
                {Array.from({ length: columnNumber }, (_, column) => {
                  const valueText = rowValues[column] ?? ''
                  const marked = inSelection(rowIndex + 1, column + 1)
                  return (
                    <div
                      key={column}
                      className={[
                        'shrink-0 truncate border-r border-b px-2 text-sm leading-[26px] select-none',
                        marked
                          ? 'border-accent bg-accent-bg'
                          : 'border-line',
                      ].join(' ')}
                      style={{ width: COLUMN_WIDTH }}
                      title={valueText || undefined}
                      onMouseDown={() => startSelection(rowIndex + 1, column + 1)}
                      onMouseEnter={() => extend(rowIndex + 1, column + 1)}
                    >
                      {valueText}
                    </div>
                  )
                })}
              </div>
            )
          })}
        </div>
      </div>

      {selection && (
        <div className="tabular-number shrink-0 border-t border-line bg-panel px-3 py-1.5 text-xs text-ink-2">
          {raster?.name}!{columnName(Math.min(selection.column1, selection.column2))}
          {Math.min(selection.row1, selection.row2)}:
          {columnName(Math.max(selection.column1, selection.column2))}
          {Math.max(selection.row1, selection.row2)}
        </div>
      )}
    </div>
  )
}
