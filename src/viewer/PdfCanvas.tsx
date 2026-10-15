/**
 * PDF.js renders directly from file bytes with a locally bundled worker.
 * This keeps zoom responsive and introduces no runtime download path.
 */

import { useEffect, useRef, useState } from 'react'
import * as pdfjs from 'pdfjs-dist'
import WorkerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url'

import type { Rotation } from './coords'

pdfjs.GlobalWorkerOptions.workerSrc = WorkerUrl

interface Props {
  bytes: Uint8Array
  page: number
  scale: number
  rotation: Rotation
  onPageSize: (width: number, height: number) => void
  onError: (message: string) => void
}

export function PdfCanvas({
  bytes,
  page,
  scale,
  rotation,
  onPageSize,
  onError,
}: Props) {
  const canvas = useRef<HTMLCanvasElement>(null)
  const document = useRef<pdfjs.PDFDocumentProxy | null>(null)
  const [ready, setReady] = useState(false)

  // Load the document once for each byte sequence.
  useEffect(() => {
    let discarded = false
    setReady(false)

    // PDF.js transfers and empties its buffer, so each load receives a copy.
    const task = pdfjs.getDocument({
      data: new Uint8Array(bytes),
      // Keep fonts inside PDF.js and leave the external font URL unset.
      useSystemFonts: false,
    })

    task.promise
      .then((pdf) => {
        if (discarded) return
        document.current = pdf
        setReady(true)
      })
      .catch((error: unknown) => {
        if (!discarded) onError(String(error))
      })

    return () => {
      discarded = true
      // PDF.js 6 cleans up through the loading task, not the document proxy.
      void task.destroy()
      document.current = null
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bytes])

  // Render again when page, zoom or rotation changes.
  useEffect(() => {
    if (!ready || !document.current) return

    let cancelled = false
    let task: pdfjs.RenderTask | null = null

    void (async () => {
      try {
        const pdf = document.current
        if (!pdf) return

        const pageObject = await pdf.getPage(page + 1)
        if (cancelled) return

        const dpr = window.devicePixelRatio || 1
        // Add the page and user rotations so an existing rotation stays correct.
        const viewport = pageObject.getViewport({ scale: scale * dpr, rotation })

        onPageSize(pageObject.view[2]! - pageObject.view[0]!, pageObject.view[3]! - pageObject.view[1]!)

        const area = canvas.current
        if (!area) return

        area.width = Math.floor(viewport.width)
        area.height = Math.floor(viewport.height)
        area.style.width = `${Math.floor(viewport.width / dpr)}px`
        area.style.height = `${Math.floor(viewport.height / dpr)}px`

        const context = area.getContext('2d')
        if (!context) return

        task = pageObject.render({ canvas: area, canvasContext: context, viewport })
        await task.promise
      } catch (error) {
        // Fast zooming routinely cancels an obsolete render.
        const message = String(error)
        if (!cancelled && !message.includes('Rendering cancelled')) {
          onError(message)
        }
      }
    })()

    return () => {
      cancelled = true
      task?.cancel()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, page, scale, rotation])

  return <canvas ref={canvas} className="block shadow-lg" />
}
