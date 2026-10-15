/** Image mode aligned with the sidecar's already-applied EXIF rotation. */

import { useEffect, useRef, useState } from 'react'

import { api } from '../api/client'
import type { Rotation } from './coords'

interface Props {
  docId: string
  page: number
  scale: number
  rotation: Rotation
  width: number
  height: number
  onError: (message: string) => void
}

export function ImageCanvas({
  docId,
  page,
  scale,
  rotation,
  width,
  height,
  onError,
}: Props) {
  const [sourceValue, setSource] = useState<string | null>(null)
  const objectUrl = useRef<string | null>(null)

  useEffect(() => {
    let discarded = false

    void api
      .renderPage(docId, page, 1)
      .then((blob) => {
        if (discarded) return
        // Release the previous URL so viewed images do not accumulate in memory.
        if (objectUrl.current) URL.revokeObjectURL(objectUrl.current)
        objectUrl.current = URL.createObjectURL(blob)
        setSource(objectUrl.current)
      })
      .catch((error: unknown) => {
        if (!discarded) onError(String(error))
      })

    return () => {
      discarded = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [docId, page])

  useEffect(
    () => () => {
      if (objectUrl.current) URL.revokeObjectURL(objectUrl.current)
    },
    [],
  )

  const landscape = rotation === 90 || rotation === 270

  // The overlay uses these visible dimensions, including the rotated axis swap.
  const outerWidth = (landscape ? height : width) * scale
  const outerHeight = (landscape ? width : height) * scale

  if (!sourceValue) {
    return (
      <div
        className="rounded-sm bg-card-2"
        style={{ width: outerWidth, height: outerHeight }}
      />
    )
  }

  return (
    // The frame rotates dimensions while the image rotates around its centre.
    <div className="relative shadow-lg" style={{ width: outerWidth, height: outerHeight }}>
      <img
        src={sourceValue}
        alt=""
        className="absolute block"
        style={{
          width: width * scale,
          height: height * scale,
          left: '50%',
          top: '50%',
          transform: `translate(-50%, -50%) rotate(${rotation}deg)`,
        }}
        draggable={false}
      />
    </div>
  )
}
