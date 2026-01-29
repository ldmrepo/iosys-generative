'use client'

import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { parseIml, imlToQti } from '@iosys/qti-core'
import { QtiViewer } from '@iosys/qti-viewer'
import { api } from '@/lib/api'

interface QtiItemViewerProps {
  itemId: string
  showAnswer?: boolean
  showExplanation?: boolean
  className?: string
}

/**
 * Fetches IML content, parses to QTI format, and renders with QtiViewer.
 * Shows error details if parsing fails.
 */
export function QtiItemViewer({
  itemId,
  showAnswer = false,
  showExplanation = false,
  className,
}: QtiItemViewerProps) {
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
    <div className={className}>
      <div className="mb-4 p-2 bg-blue-100 text-blue-800 text-xs rounded">
        ✓ QtiViewer 적용됨 | ID: {itemId.slice(0, 8)}...
      </div>
      <QtiViewer
        item={assessmentItem}
        showAnswer={showAnswer}
        showExplanation={showExplanation}
      />
    </div>
  )
}
