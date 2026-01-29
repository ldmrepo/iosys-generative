/**
 * MatchInput - Interactive matching interaction component
 * Allows users to connect source items to target items
 */

import { useState, useCallback } from 'react'
import type { MatchInteraction, DirectedPair } from '@iosys/qti-core'

export interface MatchInputProps {
  interaction: MatchInteraction
  /** Current response value */
  value: DirectedPair[]
  /** Callback when response changes */
  onChange: (value: DirectedPair[]) => void
  /** Whether the input is disabled */
  disabled?: boolean | undefined
  /** Maximum number of associations allowed (0 = unlimited) */
  maxAssociations?: number | undefined
}

export function MatchInput({
  interaction,
  value = [],
  onChange,
  disabled = false,
  maxAssociations = 0,
}: MatchInputProps) {
  const [sourceSet, targetSet] = interaction.simpleMatchSets
  const sourceItems = sourceSet?.simpleAssociableChoices ?? []
  const targetItems = targetSet?.simpleAssociableChoices ?? []

  // Track which source is currently being connected
  const [selectedSource, setSelectedSource] = useState<string | null>(null)

  // Find current match for a source
  const findMatch = useCallback(
    (sourceId: string): string | undefined => {
      const match = value.find(m => m.source === sourceId)
      return match?.target
    },
    [value]
  )

  // Count how many times a target is used
  const getTargetUsageCount = useCallback(
    (targetId: string): number => {
      return value.filter(m => m.target === targetId).length
    },
    [value]
  )

  // Check if target can accept more matches
  const canTargetAcceptMore = useCallback(
    (targetId: string): boolean => {
      const target = targetItems.find(t => t.identifier === targetId)
      if (!target) return false
      const currentCount = getTargetUsageCount(targetId)
      return currentCount < target.matchMax
    },
    [targetItems, getTargetUsageCount]
  )

  // Handle source click
  const handleSourceClick = (sourceId: string) => {
    if (disabled) return

    if (selectedSource === sourceId) {
      // Deselect
      setSelectedSource(null)
    } else {
      setSelectedSource(sourceId)
    }
  }

  // Handle target click
  const handleTargetClick = (targetId: string) => {
    if (disabled || !selectedSource) return

    // Check if we can add more associations
    if (maxAssociations > 0 && value.length >= maxAssociations) {
      // Remove existing match for this source first
      const existingMatch = findMatch(selectedSource)
      if (!existingMatch) return
    }

    // Check if target can accept more matches
    if (!canTargetAcceptMore(targetId)) {
      // Unless we're replacing the same source's match to this target
      const existingMatch = findMatch(selectedSource)
      if (existingMatch !== targetId) return
    }

    // Remove existing match for this source
    const newValue = value.filter(m => m.source !== selectedSource)

    // Add new match
    newValue.push({ source: selectedSource, target: targetId })

    onChange(newValue)
    setSelectedSource(null)
  }

  // Remove a match
  const handleRemoveMatch = (sourceId: string) => {
    if (disabled) return
    const newValue = value.filter(m => m.source !== sourceId)
    onChange(newValue)
  }

  // Get target content by ID
  const getTargetContent = (targetId: string): string => {
    const target = targetItems.find(t => t.identifier === targetId)
    return target?.content ?? targetId
  }

  return (
    <div className="space-y-4">
      {/* Source items */}
      <div className="space-y-2">
        <div className="text-sm text-gray-500 mb-2">왼쪽 항목을 선택한 후 오른쪽 항목을 선택하세요:</div>

        {sourceItems.map(source => {
          const matchedTargetId = findMatch(source.identifier)
          const isSelected = selectedSource === source.identifier

          return (
            <div
              key={source.identifier}
              className="flex items-center gap-4"
            >
              {/* Source item */}
              <button
                type="button"
                onClick={() => handleSourceClick(source.identifier)}
                disabled={disabled}
                className={`
                  flex-1 p-3 rounded-lg border text-left transition-colors
                  ${isSelected
                    ? 'border-qti-primary bg-blue-50 ring-2 ring-qti-primary'
                    : 'border-gray-200 bg-white hover:border-gray-300'}
                  ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
                `}
              >
                <div
                  className="prose prose-sm max-w-none"
                  dangerouslySetInnerHTML={{ __html: source.content }}
                />
              </button>

              {/* Arrow / Connection indicator */}
              <span className="text-gray-400 w-8 text-center">
                {matchedTargetId ? '→' : '—'}
              </span>

              {/* Matched target display */}
              <div
                className={`
                  flex-1 p-3 rounded-lg border min-h-[48px] flex items-center
                  ${matchedTargetId
                    ? 'border-gray-200 bg-white'
                    : 'border-dashed border-gray-300 bg-gray-50'}
                `}
              >
                {matchedTargetId ? (
                  <div className="flex items-center justify-between w-full">
                    <div
                      className="prose prose-sm max-w-none"
                      dangerouslySetInnerHTML={{ __html: getTargetContent(matchedTargetId) }}
                    />
                    {!disabled && (
                      <button
                        type="button"
                        onClick={() => handleRemoveMatch(source.identifier)}
                        className="ml-2 p-1 text-gray-400 hover:text-red-500 transition-colors"
                        title="연결 해제"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    )}
                  </div>
                ) : (
                  <span className="text-gray-400 text-sm">선택하세요</span>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {/* Target items to select from */}
      <div className="pt-4 border-t">
        <div className="text-sm text-gray-500 mb-2">선택지:</div>
        <div className="flex flex-wrap gap-2">
          {targetItems.map(target => {
            const usageCount = getTargetUsageCount(target.identifier)
            const canAccept = canTargetAcceptMore(target.identifier)
            const isSelectable = selectedSource && canAccept

            return (
              <button
                key={target.identifier}
                type="button"
                onClick={() => handleTargetClick(target.identifier)}
                disabled={disabled || !selectedSource || !canAccept}
                className={`
                  px-4 py-2 rounded-lg border text-sm transition-colors
                  ${isSelectable
                    ? 'border-qti-primary bg-blue-50 hover:bg-blue-100 cursor-pointer'
                    : 'border-gray-200 bg-gray-50'}
                  ${!canAccept ? 'opacity-50' : ''}
                  ${disabled || !selectedSource ? 'cursor-default' : ''}
                `}
              >
                <span dangerouslySetInnerHTML={{ __html: target.content }} />
                {target.matchMax > 1 && (
                  <span className="ml-1 text-xs text-gray-400">
                    ({usageCount}/{target.matchMax})
                  </span>
                )}
              </button>
            )
          })}
        </div>
      </div>

      {/* Instructions */}
      {selectedSource && (
        <div className="text-sm text-qti-primary bg-blue-50 p-2 rounded">
          선택지에서 연결할 항목을 클릭하세요
        </div>
      )}
    </div>
  )
}

MatchInput.displayName = 'MatchInput'
