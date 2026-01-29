import type { MatchInteraction, ResponseValue, DirectedPair } from '@iosys/qti-core'

export interface MatchViewerProps {
  interaction: MatchInteraction
  /** Correct matches */
  correctMatches?: DirectedPair[] | undefined
  /** User's response (for review mode) */
  response?: ResponseValue | undefined
  /** Show correct answers */
  showAnswer?: boolean | undefined
}

export function MatchViewer({
  interaction,
  correctMatches = [],
  response,
  showAnswer = false,
}: MatchViewerProps) {
  const [sourceSet, targetSet] = interaction.simpleMatchSets
  const sourceItems = sourceSet?.simpleAssociableChoices ?? []
  const targetItems = targetSet?.simpleAssociableChoices ?? []

  // Parse response
  const userMatches: DirectedPair[] = Array.isArray(response)
    ? (response as DirectedPair[])
    : []

  const findMatch = (sourceId: string): string | undefined => {
    const match = userMatches.find(m => m.source === sourceId)
    return match?.target
  }

  const findCorrectMatch = (sourceId: string): string | undefined => {
    const match = correctMatches.find(m => m.source === sourceId)
    return match?.target
  }

  const getTargetContent = (targetId: string): string => {
    const target = targetItems.find(t => t.identifier === targetId)
    return target?.content ?? targetId
  }

  return (
    <div className="space-y-4">
      {/* Source items with their matches */}
      <div className="space-y-2">
        {sourceItems.map(source => {
          const matchedTargetId = findMatch(source.identifier)
          const correctTargetId = findCorrectMatch(source.identifier)
          const isCorrect = matchedTargetId === correctTargetId

          return (
            <div
              key={source.identifier}
              className="flex items-center gap-4"
            >
              {/* Source */}
              <div className="flex-1 p-3 rounded-lg border border-gray-200 bg-white">
                <div
                  className="prose prose-sm max-w-none"
                  dangerouslySetInnerHTML={{ __html: source.content }}
                />
              </div>

              {/* Arrow */}
              <span className="text-gray-400">→</span>

              {/* Matched target */}
              <div
                className={`
                  flex-1 p-3 rounded-lg border
                  ${!matchedTargetId ? 'border-dashed border-gray-300 bg-gray-50' : ''}
                  ${matchedTargetId && showAnswer && isCorrect ? 'border-qti-correct bg-green-50' : ''}
                  ${matchedTargetId && showAnswer && !isCorrect ? 'border-qti-incorrect bg-red-50' : ''}
                  ${matchedTargetId && !showAnswer ? 'border-gray-200 bg-white' : ''}
                `}
              >
                {matchedTargetId ? (
                  <div
                    className="prose prose-sm max-w-none"
                    dangerouslySetInnerHTML={{ __html: getTargetContent(matchedTargetId) }}
                  />
                ) : (
                  <span className="text-gray-400">매칭 없음</span>
                )}
              </div>

              {/* Show correct answer if wrong */}
              {showAnswer && !isCorrect && correctTargetId && (
                <div className="text-sm text-qti-correct">
                  (정답: <span dangerouslySetInnerHTML={{ __html: getTargetContent(correctTargetId) }} />)
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Available targets (reference) */}
      <div className="pt-4 border-t">
        <div className="text-sm text-gray-500 mb-2">선택지:</div>
        <div className="flex flex-wrap gap-2">
          {targetItems.map(target => (
            <div
              key={target.identifier}
              className="px-3 py-1 rounded-full border border-gray-200 bg-gray-50 text-sm"
            >
              <span dangerouslySetInnerHTML={{ __html: target.content }} />
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

MatchViewer.displayName = 'MatchViewer'
