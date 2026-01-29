import type { OrderInteraction, ResponseValue } from '@iosys/qti-core'

export interface OrderViewerProps {
  interaction: OrderInteraction
  /** Correct order of identifiers */
  correctOrder?: string[] | undefined
  /** User's response (for review mode) */
  response?: ResponseValue | undefined
  /** Show correct answers */
  showAnswer?: boolean | undefined
}

export function OrderViewer({
  interaction,
  correctOrder = [],
  response,
  showAnswer = false,
}: OrderViewerProps) {
  const { simpleChoices } = interaction

  // Parse response as ordered list of identifiers
  const userOrder: string[] = Array.isArray(response) ? (response as string[]) : []

  const getChoiceContent = (id: string): string => {
    const choice = simpleChoices.find(c => c.identifier === id)
    return choice?.content ?? id
  }

  const isPositionCorrect = (index: number, id: string): boolean => {
    return correctOrder[index] === id
  }

  // Display order: user's order or original order if no response
  const displayOrder = userOrder.length > 0 ? userOrder : simpleChoices.map(c => c.identifier)

  return (
    <div className="space-y-2">
      {displayOrder.map((id, index) => {
        const positionCorrect = showAnswer && userOrder.length > 0 && isPositionCorrect(index, id)
        const positionIncorrect = showAnswer && userOrder.length > 0 && !isPositionCorrect(index, id)

        return (
          <div
            key={id}
            className={`
              flex items-center gap-3 p-3 rounded-lg border
              ${positionCorrect ? 'border-qti-correct bg-green-50' : ''}
              ${positionIncorrect ? 'border-qti-incorrect bg-red-50' : ''}
              ${!showAnswer || userOrder.length === 0 ? 'border-gray-200 bg-white' : ''}
            `}
          >
            {/* Position number */}
            <span
              className={`
                flex items-center justify-center w-7 h-7 rounded-full text-sm font-medium
                ${positionCorrect ? 'bg-qti-correct text-white' : ''}
                ${positionIncorrect ? 'bg-qti-incorrect text-white' : ''}
                ${!showAnswer || userOrder.length === 0 ? 'bg-gray-100 text-gray-700' : ''}
              `}
            >
              {index + 1}
            </span>

            {/* Content */}
            <div
              className="flex-1 prose prose-sm max-w-none"
              dangerouslySetInnerHTML={{ __html: getChoiceContent(id) }}
            />

            {/* Show correct position if wrong */}
            {showAnswer && positionIncorrect && (
              <span className="text-sm text-qti-correct">
                (정답: {correctOrder.indexOf(id) + 1}번)
              </span>
            )}
          </div>
        )
      })}

      {/* Show correct order if completely wrong */}
      {showAnswer && userOrder.length > 0 && !userOrder.every((id, i) => correctOrder[i] === id) && (
        <div className="mt-4 p-3 rounded-lg border border-qti-correct bg-green-50">
          <div className="text-sm font-medium text-qti-correct mb-2">정답 순서</div>
          <div className="text-sm text-gray-700">
            {correctOrder.map((id, i) => (
              <span key={id}>
                {i + 1}. <span dangerouslySetInnerHTML={{ __html: getChoiceContent(id) }} />
                {i < correctOrder.length - 1 && ' → '}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

OrderViewer.displayName = 'OrderViewer'
