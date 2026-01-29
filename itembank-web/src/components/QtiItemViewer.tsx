'use client'

import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { parseIml, imlToQti, setImlToQtiOptions } from '@iosys/qti-core'
import type { AssessmentItem } from '@iosys/qti-core'
import { QtiViewer } from '@iosys/qti-viewer'
import { api } from '@/lib/api'

// Set image base URL for IML to QTI conversion
// Images are served from the backend at /api/search/images/
setImlToQtiOptions({ imageBaseUrl: '/api/search/images/' })

// Props for fetching by itemId
interface QtiItemViewerByIdProps {
  itemId: string
  item?: never
  showAnswer?: boolean
  showExplanation?: boolean
  className?: string
}

// Props for direct item data
interface QtiItemViewerDirectProps {
  itemId?: never
  item: AssessmentItem
  showAnswer?: boolean
  showExplanation?: boolean
  className?: string
}

type QtiItemViewerProps = QtiItemViewerByIdProps | QtiItemViewerDirectProps

/**
 * QTI Item Viewer component.
 *
 * Usage:
 * 1. Fetch by itemId: <QtiItemViewer itemId="xxx" />
 * 2. Direct data: <QtiItemViewer item={assessmentItem} />
 */
export function QtiItemViewer(props: QtiItemViewerProps) {
  const {
    showAnswer = false,
    showExplanation = false,
    className,
  } = props

  // Direct item mode - render immediately
  if ('item' in props && props.item) {
    return (
      <QtiViewer
        item={props.item}
        showAnswer={showAnswer}
        showExplanation={showExplanation}
        className={className}
      />
    )
  }

  // Fetch mode - requires itemId
  return (
    <QtiItemViewerById
      itemId={(props as QtiItemViewerByIdProps).itemId}
      showAnswer={showAnswer}
      showExplanation={showExplanation}
      className={className}
    />
  )
}

/**
 * Internal component that fetches IML by itemId
 */
function QtiItemViewerById({
  itemId,
  showAnswer,
  showExplanation,
  className,
}: {
  itemId: string
  showAnswer: boolean
  showExplanation: boolean
  className?: string
}) {
  // Fetch IML content
  const { data, isLoading, error: fetchError } = useQuery({
    queryKey: ['iml', itemId],
    queryFn: () => api.getItemIml(itemId),
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 1,
  })

  // Parse IML and convert to QTI
  const { assessmentItem, parseError } = useMemo(() => {
    if (!data?.iml_content) return { assessmentItem: null, parseError: null }

    try {
      const imlItem = parseIml(data.iml_content)
      const qtiItem = imlToQti(imlItem)
      return { assessmentItem: qtiItem, parseError: null }
    } catch (e) {
      console.error('IML parse/convert error:', e)
      return { assessmentItem: null, parseError: e as Error }
    }
  }, [data?.iml_content])

  // Loading state
  if (isLoading) {
    return (
      <div className={`animate-pulse ${className ?? ''}`}>
        <div className="h-4 bg-gray-200 rounded w-3/4 mb-4"></div>
        <div className="h-4 bg-gray-200 rounded w-full mb-2"></div>
        <div className="h-4 bg-gray-200 rounded w-5/6 mb-2"></div>
        <div className="h-4 bg-gray-200 rounded w-2/3"></div>
      </div>
    )
  }

  // Fetch error
  if (fetchError) {
    return (
      <div className={`border border-red-300 bg-red-50 p-4 rounded ${className ?? ''}`}>
        <div className="font-bold text-red-700 mb-2">API Error</div>
        <pre className="text-xs text-red-600 whitespace-pre-wrap">
          {fetchError instanceof Error ? fetchError.message : String(fetchError)}
        </pre>
      </div>
    )
  }

  // Parse error
  if (parseError) {
    return (
      <div className={`border border-orange-300 bg-orange-50 p-4 rounded ${className ?? ''}`}>
        <div className="font-bold text-orange-700 mb-2">IML Parse Error</div>
        <pre className="text-xs text-orange-600 whitespace-pre-wrap">
          {parseError.message}
        </pre>
        {parseError.stack && (
          <details className="mt-2">
            <summary className="text-xs text-orange-500 cursor-pointer">Stack trace</summary>
            <pre className="text-xs text-orange-400 whitespace-pre-wrap mt-1">
              {parseError.stack}
            </pre>
          </details>
        )}
      </div>
    )
  }

  // No data
  if (!assessmentItem) {
    return (
      <div className={`border border-gray-300 bg-gray-50 p-4 rounded ${className ?? ''}`}>
        <div className="text-gray-500">No IML content available</div>
      </div>
    )
  }

  // Render QTI item
  return (
    <QtiViewer
      item={assessmentItem}
      showAnswer={showAnswer}
      showExplanation={showExplanation}
      className={className}
    />
  )
}
