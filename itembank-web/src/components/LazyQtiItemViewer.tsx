'use client'

import { useState, useEffect, useRef } from 'react'
import dynamic from 'next/dynamic'

const QtiItemViewer = dynamic(
  () => import('@/components/QtiItemViewer').then(mod => mod.QtiItemViewer),
  {
    ssr: false,
    loading: () => (
      <div className="space-y-3">
        <div className="skeleton h-4 w-3/4"></div>
        <div className="skeleton h-4 w-full"></div>
        <div className="skeleton h-4 w-5/6"></div>
      </div>
    ),
  }
)

export function LazyQtiItemViewer({
  itemId,
  forceLoad = false,
}: {
  itemId: string
  forceLoad?: boolean
}) {
  const [isVisible, setIsVisible] = useState(forceLoad)
  const [hasLoaded, setHasLoaded] = useState(forceLoad)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (forceLoad) {
      setIsVisible(true)
      setHasLoaded(true)
      return
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry?.isIntersecting) {
          setIsVisible(true)
          setHasLoaded(true)
        } else if (hasLoaded) {
          setIsVisible(true)
        }
      },
      {
        rootMargin: '200px',
        threshold: 0,
      }
    )

    if (ref.current) {
      observer.observe(ref.current)
    }

    return () => observer.disconnect()
  }, [hasLoaded, forceLoad])

  return (
    <div ref={ref}>
      {isVisible ? (
        <QtiItemViewer
          itemId={itemId}
          showAnswer={false}
          showExplanation={false}
        />
      ) : (
        <div className="space-y-2">
          <div className="skeleton h-4 w-3/4"></div>
          <div className="skeleton h-4 w-full"></div>
          <div className="skeleton h-4 w-5/6"></div>
        </div>
      )}
    </div>
  )
}
