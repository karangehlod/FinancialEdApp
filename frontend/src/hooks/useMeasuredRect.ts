import { useEffect, useRef, useState, RefObject } from 'react'

export type MeasuredRect = { width: number; height: number }

export function useMeasuredRect<T extends HTMLElement>(): { ref: RefObject<T>; rect: MeasuredRect } {
  const ref = useRef<T | null>(null)
  const [rect, setRect] = useState<MeasuredRect>({ width: 0, height: 0 })

  useEffect(() => {
    const el = ref.current
    if (!el || typeof ResizeObserver === 'undefined') return undefined

    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const cr = entry.contentRect
        setRect({ width: cr.width, height: cr.height })
      }
    })

    ro.observe(el)
    // set initial size synchronously
    const initial = el.getBoundingClientRect()
    if (initial.width || initial.height) setRect({ width: initial.width, height: initial.height })

    return () => ro.disconnect()
  }, [ref.current])

  return { ref, rect }
}
