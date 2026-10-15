/**
 * Shared coordinate overlay for every viewer mode.
 *
 * All marks stay in document coordinates. This component converts them only
 * for drawing, so zoom and rotation change presentation rather than data.
 */

import { useCallback, useEffect, useRef, useState } from 'react'

import { useTexts } from '../i18n'
import {
  clampToPage,
  docToScreen,
  rectFromPoints,
  screenToDoc,
  type View,
  type ImageRect,
  type PdfRect,
  type ScreenRect,
  type PageSize,
} from './coords'

/** A document mark whose optional name identifies it without relying on colour. */
export interface Highlight {
  id: string
  rect: PdfRect | ImageRect
  name?: string
}

export type ViewerMode = 'selection' | 'read'

/** Controls labels: always in setup, never while reviewing one focused value. */
export type Labels = 'always' | 'never' | 'when-selected'

interface Props {
  page: PageSize
  view: View
  pageNumber: number
  highlights: Highlight[]
  mode: ViewerMode
  /** Evidence currently brought into focus. */
  highlighted?: string | null
  labels?: Labels
  onChange: (highlights: Highlight[]) => void
  onSelection?: (id: string | null) => void
  /** A new mark and an anchor below it for the follow-up question. */
  onNewHighlight?: (highlight: Highlight, anchor: { x: number; y: number }) => void
  kind?: 'pdf_rect' | 'image_rect'
}

/** Minimum screen size prevents a click from becoming an accidental mark. */
const MIN_SIZE = 6
const HANDLE_SIZE = 8

type Drag =
  | { kind: 'new'; startX: number; startY: number; x: number; y: number }
  | { kind: 'move'; id: string; dx: number; dy: number; start: ScreenRect }
  | { kind: 'resize'; id: string; corner: Corner; start: ScreenRect }

type Corner = 'nw' | 'ne' | 'sw' | 'se'

export function OverlayLayer({
  page,
  view,
  pageNumber,
  highlights,
  mode,
  highlighted,
  labels = 'when-selected',
  onChange,
  onSelection,
  onNewHighlight,
  kind = 'pdf_rect',
}: Props) {
  const texts = useTexts()

  const area = useRef<HTMLDivElement>(null)
  const [drag, setDrag] = useState<Drag | null>(null)
  const [active, setActive] = useState<string | null>(null)

  // Only rectangles belonging to the current page are visible.
  const visible = highlights.filter((m) => m.rect.page === pageNumber)

  const showRect = useCallback(
    (rect: PdfRect | ImageRect): ScreenRect => docToScreen(rect, page, view),
    [page, view],
  )

  const mousePosition = (event: React.MouseEvent | MouseEvent): [number, number] => {
    const box = area.current?.getBoundingClientRect()
    if (!box) return [0, 0]
    // CSS size has divided by DPR; restore it before document conversion.
    return [
      (event.clientX - box.left) * view.dpr,
      (event.clientY - box.top) * view.dpr,
    ]
  }

  const startDrag = (event: React.MouseEvent) => {
    if (mode !== 'selection' || event.button !== 0) return
    const [x, y] = mousePosition(event)
    setDrag({ kind: 'new', startX: x, startY: y, x, y })
    setActive(null)
    onSelection?.(null)
  }

  useEffect(() => {
    if (!drag) return

    const move = (event: MouseEvent) => {
      const [x, y] = mousePosition(event)
      setDrag((current) => {
        if (!current) return null
        if (current.kind === 'new') return { ...current, x, y }
        return current
      })

      if (drag.kind === 'move') {
        const movedScreen = { ...drag.start, x: x - drag.dx, y: y - drag.dy }
        update(drag.id, movedScreen)
      } else if (drag.kind === 'resize') {
        update(drag.id, resize(drag.start, drag.corner, x, y))
      }
    }

    const release = (event: MouseEvent) => {
      if (drag.kind === 'new') {
        const [x, y] = mousePosition(event)
        const box = rectFromPoints(drag.startX, drag.startY, x, y)
        if (box.b >= MIN_SIZE && box.h >= MIN_SIZE) {
          const rect = screenToDoc(box, page, view, pageNumber, kind)
          const newItem: Highlight = {
            id: `m${Date.now().toString(36)}`,
            rect: kind === 'pdf_rect' ? clampToPage(rect as PdfRect, page) : rect,
          }
          onChange([...highlights, newItem])
          setActive(newItem.id)
          onSelection?.(newItem.id)

          // Window coordinates keep the question anchored after scrolling.
          const areaBox = area.current?.getBoundingClientRect()
          if (areaBox) {
            onNewHighlight?.(newItem, {
              x: areaBox.left + box.x / view.dpr,
              y: areaBox.top + (box.y + box.h) / view.dpr + 10,
            })
          }
        }
      }
      setDrag(null)
    }

    window.addEventListener('mousemove', move)
    window.addEventListener('mouseup', release)
    return () => {
      window.removeEventListener('mousemove', move)
      window.removeEventListener('mouseup', release)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [drag, highlights, page, view, pageNumber, kind])

  const update = (id: string, screen: ScreenRect) => {
    const rect = screenToDoc(screen, page, view, pageNumber, kind)
    onChange(
      highlights.map((m) =>
        m.id === id
          ? {
              ...m,
              rect: kind === 'pdf_rect' ? clampToPage(rect as PdfRect, page) : rect,
            }
          : m,
      ),
    )
  }

  const deleteItem = useCallback(
    (id: string) => {
      onChange(highlights.filter((m) => m.id !== id))
      setActive(null)
      onSelection?.(null)
    },
    [highlights, onChange, onSelection],
  )

  // Delete removes a mark; arrow keys move it by screen pixels.
  useEffect(() => {
    if (!active) return

    const keyHandler = (event: KeyboardEvent) => {
      if (event.key === 'Delete' || event.key === 'Backspace') {
        event.preventDefault()
        deleteItem(active)
        return
      }

      const steps: Record<string, [number, number]> = {
        ArrowLeft: [-1, 0],
        ArrowRight: [1, 0],
        ArrowUp: [0, -1],
        ArrowDown: [0, 1],
      }
      const step = steps[event.key]
      if (!step) return

      event.preventDefault()
      const extent = event.shiftKey ? 10 : 1
      const highlight = highlights.find((m) => m.id === active)
      if (!highlight) return

      const s = showRect(highlight.rect)
      update(active, {
        ...s,
        x: s.x + step[0]! * extent,
        y: s.y + step[1]! * extent,
      })
    }

    window.addEventListener('keydown', keyHandler)
    return () => window.removeEventListener('keydown', keyHandler)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active, highlights, deleteItem, showRect])

  const f = view.dpr // Convert device pixels back to CSS pixels.

  return (
    <div
      ref={area}
      className="absolute inset-0"
      style={{ cursor: mode === 'selection' ? 'crosshair' : 'default' }}
      onMouseDown={startDrag}
      role="application"
      aria-label={texts.highlight.newLabel}
    >
      {visible.map((highlight) => {
        const s = showRect(highlight.rect)
        const isActive = highlight.id === active
        const isLight = highlight.id === highlighted
        // Only the current mark is strong, keeping the document readable.
        const emphasised = isLight || isActive
        const showLabel =
          highlight.name &&
          (labels === 'always' || (labels === 'when-selected' && emphasised))

        return (
          <div
            key={highlight.id}
            className="absolute rounded-[2px] transition-all duration-(--dur-1) ease-gentle"
            style={{
              left: s.x / f,
              top: s.y / f,
              width: s.b / f,
              height: s.h / f,
              background: emphasised ? 'var(--mark-fill-on)' : 'var(--mark-fill)',
              boxShadow: `0 0 0 ${emphasised ? 1.8 : 1.2}px ${
                emphasised ? 'var(--mark-line-on)' : 'var(--mark-line)'
              }`,
            }}
            tabIndex={0}
            role="button"
            aria-label={highlight.name ?? texts.highlight.newLabel}
            onMouseDown={(event) => {
              if (mode !== 'selection') return
              event.stopPropagation()
              const [x, y] = mousePosition(event)
              setActive(highlight.id)
              onSelection?.(highlight.id)
              setDrag({
                kind: 'move',
                id: highlight.id,
                dx: x - s.x,
                dy: y - s.y,
                start: s,
              })
            }}
            onFocus={() => {
              setActive(highlight.id)
              onSelection?.(highlight.id)
            }}
          >
            {showLabel && (
              <span
                className="pointer-events-none absolute -top-[17px] left-0 rounded-t-[3px] rounded-br-[3px] px-1.5 py-px text-[10px] font-semibold whitespace-nowrap text-on-ink"
                style={{
                  background: emphasised ? 'var(--mark-line-on)' : 'var(--accent)',
                  color: '#fff',
                }}
              >
                {highlight.name}
              </span>
            )}

            {isActive && mode === 'selection' && (
              <>
                {(['nw', 'ne', 'sw', 'se'] as Corner[]).map((corner) => (
                  <div
                    key={corner}
                    className="absolute rounded-[2px] border border-card bg-accent"
                    style={{
                      width: HANDLE_SIZE,
                      height: HANDLE_SIZE,
                      left: corner.includes('w') ? -HANDLE_SIZE / 2 : undefined,
                      right: corner.includes('e') ? -HANDLE_SIZE / 2 : undefined,
                      top: corner.startsWith('n') ? -HANDLE_SIZE / 2 : undefined,
                      bottom: corner.startsWith('s') ? -HANDLE_SIZE / 2 : undefined,
                      cursor: `${corner}-resize`,
                    }}
                    onMouseDown={(event) => {
                      event.stopPropagation()
                      setDrag({ kind: 'resize', id: highlight.id, corner, start: s })
                    }}
                  />
                ))}

                <button
                  type="button"
                  className="absolute -top-2 -right-2 flex size-5 items-center justify-center rounded-full bg-bad text-xs leading-none text-white shadow-1 hover:brightness-110"
                  title={texts.highlight.delete}
                  aria-label={texts.highlight.delete}
                  onMouseDown={(event) => event.stopPropagation()}
                  onClick={() => deleteItem(highlight.id)}
                >
                  ×
                </button>
              </>
            )}
          </div>
        )
      })}

      {drag?.kind === 'new' && (
        <div
          className="pointer-events-none absolute rounded-[2px] border-[1.5px] border-dashed border-accent bg-accent-bg"
          style={{
            left: Math.min(drag.startX, drag.x) / f,
            top: Math.min(drag.startY, drag.y) / f,
            width: Math.abs(drag.x - drag.startX) / f,
            height: Math.abs(drag.y - drag.startY) / f,
          }}
        />
      )}
    </div>
  )
}

function resize(start: ScreenRect, corner: Corner, x: number, y: number): ScreenRect {
  const left = corner.includes('w') ? x : start.x
  const top = corner.startsWith('n') ? y : start.y
  const right = corner.includes('e') ? x : start.x + start.b
  const bottom = corner.startsWith('s') ? y : start.y + start.h

  return {
    x: Math.min(left, right),
    y: Math.min(top, bottom),
    b: Math.max(MIN_SIZE, Math.abs(right - left)),
    h: Math.max(MIN_SIZE, Math.abs(bottom - top)),
  }
}
