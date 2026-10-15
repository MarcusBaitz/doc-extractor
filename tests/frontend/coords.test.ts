/**
 * TypeScript and Python must produce exactly the same coordinate values. Both
 * sides use the shared fixture checked by `tests/sidecar/test_coordinates.py`,
 * so a drift fails here instead of looking like an inaccurate read later.
 */

import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

import {
  clampToPage,
  docToScreen,
  screenToDoc,
  pageSizeOnScreen,
  mergeRects,
  type PdfRect,
  type Rotation,
  type PageSize,
} from '../../src/viewer/coords'

interface FixtureCase {
  rotation: number
  scale: number
  dpr: number
  page: { width: number; height: number }
  doc: { x0: number; y0: number; x1: number; y1: number }
  screen: { x: number; y: number; width: number; height: number }
}

const FIXTURE: FixtureCase[] = JSON.parse(
  readFileSync(join(__dirname, '../sidecar/fixtures/coordinates.json'), 'utf-8'),
)

const TOLERANCE = 0.001

describe('the Python coordinate contract', () => {
  it('has a non-empty shared fixture', () => {
    expect(FIXTURE.length).toBeGreaterThan(0)
  })

  FIXTURE.forEach((fixtureCase, i) => {
    it(`case ${i}: rot=${fixtureCase.rotation} scale=${fixtureCase.scale} dpr=${fixtureCase.dpr}`, () => {
      const page: PageSize = {
        width: fixtureCase.page.width,
        height: fixtureCase.page.height,
        rotation: fixtureCase.rotation as Rotation,
      }
      const rect: PdfRect = { kind: 'pdf_rect', page: 0, ...fixtureCase.doc }

      const screen = docToScreen(rect, page, { scale: fixtureCase.scale, dpr: fixtureCase.dpr })

      expect(screen.x).toBeCloseTo(fixtureCase.screen.x, 3)
      expect(screen.y).toBeCloseTo(fixtureCase.screen.y, 3)
      expect(screen.b).toBeCloseTo(fixtureCase.screen.width, 3)
      expect(screen.h).toBeCloseTo(fixtureCase.screen.height, 3)
    })
  })
})

describe('the document-to-screen round trip', () => {
  const rotations: Rotation[] = [0, 90, 180, 270]
  const scales = [0.5, 1.0, 2.5, 4.0]
  const dprs = [1.0, 2.0]

  const basePage = { width: 595.2756, height: 841.8898 }

  for (const rotation of rotations) {
    for (const scale of scales) {
      for (const dpr of dprs) {
        it(`rot=${rotation} scale=${scale} dpr=${dpr}`, () => {
          const page: PageSize = { ...basePage, rotation }

          // A fixed seed keeps a coordinate failure reproducible.
          let seed = 20260727
          const random = () => {
            seed = (seed * 1103515245 + 12345) & 0x7fffffff
            return seed / 0x7fffffff
          }

          for (let i = 0; i < 200; i++) {
            const x0 = random() * (page.width - 10)
            const y0 = random() * (page.height - 10)
            const rect: PdfRect = {
              kind: 'pdf_rect',
              page: 0,
              x0,
              y0,
              x1: x0 + 1 + random() * Math.min(200, page.width - x0 - 1),
              y1: y0 + 1 + random() * Math.min(200, page.height - y0 - 1),
            }

            const screen = docToScreen(rect, page, { scale, dpr })
            const back = screenToDoc(screen, page, { scale, dpr }, 0) as PdfRect

            expect(back.x0).toBeCloseTo(rect.x0, 6)
            expect(back.y0).toBeCloseTo(rect.y0, 6)
            expect(back.x1).toBeCloseTo(rect.x1, 6)
            expect(back.y1).toBeCloseTo(rect.y1, 6)
          }
        })
      }
    }
  }
})

describe('page size on screen', () => {
  const page = { width: 600, height: 800 }

  it('stays unchanged at 0 and 180 degrees', () => {
    for (const rotation of [0, 180] as Rotation[]) {
      const g = pageSizeOnScreen({ ...page, rotation }, { scale: 1, dpr: 1 })
      expect(g.width).toBe(600)
      expect(g.height).toBe(800)
    }
  })

  it('swaps width and height at 90 and 270 degrees', () => {
    for (const rotation of [90, 270] as Rotation[]) {
      const g = pageSizeOnScreen({ ...page, rotation }, { scale: 1, dpr: 1 })
      expect(g.width).toBe(800)
      expect(g.height).toBe(600)
    }
  })

  it('scales with zoom and device pixel ratio', () => {
    const g = pageSizeOnScreen({ ...page, rotation: 0 }, { scale: 2, dpr: 2 })
    expect(g.width).toBe(2400)
    expect(g.height).toBe(3200)
  })
})

describe('image coordinates', () => {
  // A4 at 150 dpi, matching the scans in the test corpus.
  const WIDTH = 1240
  const HEIGHT = 1754
  const rect = { kind: 'image_rect' as const, page: 0, x0: 100, y0: 200, x1: 300, y1: 250 }

  it('does not mirror coordinates whose origin is already at the top left', () => {
    const page: PageSize = { width: WIDTH, height: HEIGHT, rotation: 0 }
    expect(docToScreen(rect, page, { scale: 1, dpr: 1 })).toEqual({
      x: 100,
      y: 200,
      b: 200,
      h: 50,
    })
  })

  // This regression once left the mark in place while the image rotated.
  it('rotates at 90 degrees and swaps width and height', () => {
    const page: PageSize = { width: WIDTH, height: HEIGHT, rotation: 90 }
    const s = docToScreen(rect, page, { scale: 1, dpr: 1 })
    expect(s).toEqual({ x: HEIGHT - 250, y: 100, b: 50, h: 200 })
  })

  it('rotates at 180 degrees and mirrors both axes', () => {
    const page: PageSize = { width: WIDTH, height: HEIGHT, rotation: 180 }
    expect(docToScreen(rect, page, { scale: 1, dpr: 1 })).toEqual({
      x: WIDTH - 300,
      y: HEIGHT - 250,
      b: 200,
      h: 50,
    })
  })

  it('rotates at 270 degrees', () => {
    const page: PageSize = { width: WIDTH, height: HEIGHT, rotation: 270 }
    expect(docToScreen(rect, page, { scale: 1, dpr: 1 })).toEqual({
      x: 200,
      y: WIDTH - 300,
      b: 50,
      h: 200,
    })
  })

  it.each([0, 90, 180, 270] as Rotation[])(
    'round-trips at %i degrees',
    (rotation) => {
      const page: PageSize = { width: WIDTH, height: HEIGHT, rotation }

      let seed = 20260728
      const random = () => {
        seed = (seed * 1103515245 + 12345) & 0x7fffffff
        return seed / 0x7fffffff
      }

      for (const scale of [0.5, 1, 2.5, 4]) {
        for (const dpr of [1, 2]) {
          for (let i = 0; i < 50; i++) {
            const x0 = Math.round(random() * (WIDTH - 20))
            const y0 = Math.round(random() * (HEIGHT - 20))
            const original = {
              kind: 'image_rect' as const,
              page: 0,
              x0,
              y0,
              x1: x0 + 1 + Math.round(random() * Math.min(300, WIDTH - x0 - 1)),
              y1: y0 + 1 + Math.round(random() * Math.min(300, HEIGHT - y0 - 1)),
            }

            const s = docToScreen(original, page, { scale, dpr })
            const back = screenToDoc(s, page, { scale, dpr }, 0, 'image_rect')

            expect(back).toEqual(original)
          }
        }
      }
    },
  )

  it('keeps the visible rectangle inside the rotated page', () => {
    for (const rotation of [0, 90, 180, 270] as Rotation[]) {
      const page: PageSize = { width: WIDTH, height: HEIGHT, rotation }
      const landscape = rotation === 90 || rotation === 270
      const s = docToScreen(rect, page, { scale: 1, dpr: 1 })

      expect(s.x).toBeGreaterThanOrEqual(0)
      expect(s.y).toBeGreaterThanOrEqual(0)
      expect(s.x + s.b).toBeLessThanOrEqual(landscape ? HEIGHT : WIDTH)
      expect(s.y + s.h).toBeLessThanOrEqual(landscape ? WIDTH : HEIGHT)
    }
  })
})

describe('coordinate helpers', () => {
  const page: PageSize = { width: 595, height: 842, rotation: 0 }

  it('clampToPage clips values outside the page', () => {
    const rect: PdfRect = { kind: 'pdf_rect', page: 0, x0: -50, y0: -20, x1: 700, y1: 900 }
    const clamped = clampToPage(rect, page)
    expect(clamped.x0).toBe(0)
    expect(clamped.y0).toBe(0)
    expect(clamped.x1).toBe(595)
    expect(clamped.y1).toBe(842)
  })

  it('mergeRects encloses every rectangle', () => {
    const a: PdfRect = { kind: 'pdf_rect', page: 0, x0: 10, y0: 10, x1: 20, y1: 20 }
    const b: PdfRect = { kind: 'pdf_rect', page: 0, x0: 50, y0: 5, x1: 60, y1: 30 }
    expect(mergeRects([a, b])).toMatchObject({ x0: 10, y0: 5, x1: 60, y1: 30 })
  })

  it('mergeRects returns null for an empty list', () => {
    expect(mergeRects([])).toBeNull()
  })
})

describe('the comparison tolerance', () => {
  it('is tight enough to detect coordinate drift', () => {
    expect(TOLERANCE).toBeLessThan(0.01)
  })
})
