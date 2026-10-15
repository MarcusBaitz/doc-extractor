/**
 * Hosts PDF, image and spreadsheet viewers with one shared navigation state.
 * The current place decides whether marks can be edited; users do not need a
 * separate mode switch.
 */

import { ChevronLeft, ChevronRight, RotateCw, ZoomIn, ZoomOut } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'

import { api } from '../api/client'
import type { DocumentInfo, SheetInfo, SheetRaster } from '../api/types'
import { useTexts } from '../i18n'
import { ImageCanvas } from './ImageCanvas'
import { OverlayLayer, type Highlight, type Labels } from './OverlayLayer'
import { PdfCanvas } from './PdfCanvas'
import { SheetGrid } from './SheetGrid'
import type { Locator, Rotation, PageSize } from './coords'

const ZOOM_LEVELS = [0.25, 0.5, 0.75, 1, 1.25, 1.5, 2, 3, 4] as const

/** Reserved identifier for displayed evidence, not a user-created mark. */
const EVIDENCE_ID = '__evidence__'

interface Props {
  document: DocumentInfo
  highlights: Highlight[]
  onHighlights: (highlights: Highlight[]) => void
  onError: (message: unknown) => void
  /** Evidence for a read value, brought into view and highlighted. */
  highlighted?: Locator | null
  /** Review reads the document without editing marks. */
  readOnly?: boolean
  labels?: Labels
  /** A freshly drawn mark and the anchor for its question. */
  onNewHighlight?: (highlight: Highlight, anchor: { x: number; y: number }) => void
}

export function ViewerHost({
  document,
  highlights,
  onHighlights,
  onError,
  highlighted,
  readOnly = false,
  labels = 'when-selected',
  onNewHighlight,
}: Props) {
  const texts = useTexts()

  const [page, setPage] = useState(0)
  const [scale, setScale] = useState(1)
  const [rotation, setRotation] = useState<Rotation>(0)
  const [bytes, setBytes] = useState<Uint8Array | null>(null)
  const [sheetsList, setSheets] = useState<SheetInfo[]>([])
  const [raster, setRaster] = useState<SheetRaster | null>(null)
  const [cellSelection, setCellSelection] = useState<{
    row1: number
    column1: number
    row2: number
    column2: number
  } | null>(null)

  const dpr = typeof window !== 'undefined' ? window.devicePixelRatio || 1 : 1
  const currentPage = document.pages[page]
  const mode = readOnly ? 'read' : 'selection'

  // A new document must not inherit page, zoom or selection state.
  useEffect(() => {
    setPage(0)
    setScale(1)
    setRotation(0)
    setCellSelection(null)
    setBytes(null)
    setRaster(null)
  }, [document.id])

  const changeSheet = useCallback(
    (index: number) => {
      setPage(index)
      setCellSelection(null)
      void api.sheetRaster(document.id, index).then(setRaster).catch(onError)
    },
    [document.id, onError],
  )

  // Bring evidence on another page or sheet into view.
  useEffect(() => {
    if (!highlighted) return
    if (highlighted.kind === 'sheet_range') {
      const sheet = document.pages.findIndex((p) => p.sheet_name === highlighted.sheet)
      if (sheet >= 0 && sheet !== page) changeSheet(sheet)
    } else if (highlighted.page !== page) {
      setPage(highlighted.page)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [highlighted])

  // Load PDF bytes.
  useEffect(() => {
    if (document.kind !== 'pdf') return
    let discarded = false

    void api
      .documentBytes(document.id)
      .then((data) => {
        if (!discarded) setBytes(data)
      })
      .catch((error: unknown) => {
        if (!discarded) onError(error)
      })

    return () => {
      discarded = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [document.id, document.kind])

  // Load spreadsheet sheets and the first raster.
  useEffect(() => {
    if (document.kind !== 'sheet') return
    let discarded = false

    void api
      .sheets(document.id)
      .then((list) => {
        if (discarded) return
        setSheets(list)
        return api.sheetRaster(document.id, 0)
      })
      .then((r) => {
        if (!discarded && r) setRaster(r)
      })
      .catch((error: unknown) => {
        if (!discarded) onError(error)
      })

    return () => {
      discarded = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [document.id, document.kind])

  const zoom = useCallback((direction: 1 | -1) => {
    setScale((current) => {
      const i = ZOOM_LEVELS.findIndex((column) => column >= current - 0.001)
      const nextIndex = Math.min(Math.max(i + direction, 0), ZOOM_LEVELS.length - 1)
      return ZOOM_LEVELS[nextIndex] ?? current
    })
  }, [])

  // Viewer keyboard navigation.
  useEffect(() => {
    const keyHandler = (e: KeyboardEvent) => {
      const targetElement = e.target as HTMLElement | null
      if (targetElement && ['INPUT', 'TEXTAREA'].includes(targetElement.tagName)) return

      if (e.key === 'PageDown') {
        e.preventDefault()
        setPage((column) => Math.min(column + 1, document.pages.length - 1))
      } else if (e.key === 'PageUp') {
        e.preventDefault()
        setPage((column) => Math.max(column - 1, 0))
      } else if ((e.ctrlKey || e.metaKey) && (e.key === '+' || e.key === '=')) {
        e.preventDefault()
        zoom(1)
      } else if ((e.ctrlKey || e.metaKey) && e.key === '-') {
        e.preventDefault()
        zoom(-1)
      } else if ((e.ctrlKey || e.metaKey) && e.key === '0') {
        e.preventDefault()
        setScale(1)
      }
    }
    window.addEventListener('keydown', keyHandler)
    return () => window.removeEventListener('keydown', keyHandler)
  }, [document.pages.length, zoom])

  const pageSize: PageSize = {
    width: currentPage?.width ?? 595,
    height: currentPage?.height ?? 842,
    rotation,
  }

  const isSheet = document.kind === 'sheet'
  const multiplePages = document.pages.length > 1

  return (
    <div className="flex h-full min-h-0 flex-col bg-bg">
      <div className="flex shrink-0 items-center gap-1 border-b border-line bg-panel px-4 py-2">
        {!isSheet && (
          <>
            {multiplePages && (
              <>
                <Tool
                  title={texts.viewer.previous}
                  disabled={page === 0}
                  onClick={() => setPage((column) => Math.max(0, column - 1))}
                >
                  <ChevronLeft size={16} />
                </Tool>

                <span className="tabular-number min-w-[104px] text-center text-[13px] text-ink-2">
                  {texts.viewer.page} {page + 1} {texts.viewer.of}{' '}
                  {document.pages.length}
                </span>

                <Tool
                  title={texts.viewer.next}
                  disabled={page >= document.pages.length - 1}
                  onClick={() => setPage((column) => Math.min(document.pages.length - 1, column + 1))}
                >
                  <ChevronRight size={16} />
                </Tool>

                <span className="mx-2 h-5 w-px bg-line" />
              </>
            )}

            <Tool title={texts.viewer.zoomOut} onClick={() => zoom(-1)}>
              <ZoomOut size={16} />
            </Tool>
            <button
              type="button"
              onClick={() => setScale(1)}
              title={texts.viewer.resetZoom}
              className="tabular-number min-w-14 rounded-sm px-2 py-1 text-[13px] text-ink-2 transition-colors duration-(--dur-1) hover:bg-card-2 hover:text-ink"
            >
              {Math.round(scale * 100)} %
            </button>
            <Tool title={texts.viewer.zoomIn} onClick={() => zoom(1)}>
              <ZoomIn size={16} />
            </Tool>

            <Tool
              title={texts.viewer.rotate}
              onClick={() => setRotation(((rotation + 90) % 360) as Rotation)}
            >
              <RotateCw size={16} />
            </Tool>
          </>
        )}

        <span className="ml-auto text-[12.5px] text-ink-3">
          {readOnly
            ? document.filename
            : highlights.length > 0
              ? texts.highlight.count(highlights.length)
              : texts.highlight.none}
        </span>
      </div>

      {isSheet ? (
        <SheetGrid
          sheetsList={sheetsList}
          raster={raster}
          activeSheet={page}
          selection={cellSelection}
          onSheetChange={changeSheet}
          onSelection={setCellSelection}
        />
      ) : (
        <div className="flex-1 overflow-auto p-8">
          <div className="relative mx-auto inline-block shadow-2">
            {document.kind === 'pdf' && bytes && (
              <PdfCanvas
                bytes={bytes}
                page={page}
                scale={scale}
                rotation={rotation}
                onPageSize={() => undefined}
                onError={onError}
              />
            )}

            {document.kind === 'image' && currentPage && (
              <ImageCanvas
                docId={document.id}
                page={page}
                scale={scale}
                rotation={rotation}
                width={currentPage.width}
                height={currentPage.height}
                onError={onError}
              />
            )}

            <OverlayLayer
              page={pageSize}
              view={{ scale, dpr }}
              pageNumber={page}
              highlights={
                // Evidence is displayed separately from user-created marks.
                highlighted && highlighted.kind !== 'sheet_range'
                  ? [...highlights, { id: EVIDENCE_ID, rect: highlighted }]
                  : highlights
              }
              mode={mode}
              labels={labels}
              highlighted={highlighted ? EVIDENCE_ID : null}
              onChange={(nextHighlights) =>
                onHighlights(nextHighlights.filter((mark) => mark.id !== EVIDENCE_ID))
              }
              {...(onNewHighlight ? { onNewHighlight } : {})}
              kind={document.kind === 'image' ? 'image_rect' : 'pdf_rect'}
            />
          </div>
        </div>
      )}
    </div>
  )
}

function Tool({
  children,
  title,
  onClick,
  disabled,
}: {
  children: React.ReactNode
  title: string
  onClick: () => void
  disabled?: boolean
}) {
  return (
    <button
      type="button"
      title={title}
      aria-label={title}
      onClick={onClick}
      disabled={disabled}
      className="rounded-sm p-1.5 text-ink-2 transition-colors duration-(--dur-1) hover:bg-card-2 hover:text-ink disabled:pointer-events-none disabled:opacity-30"
    >
      {children}
    </button>
  )
}
