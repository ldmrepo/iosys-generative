import type { ChoiceInteraction, ResponseValue } from '@iosys/qti-core'
import { ChoiceLabel } from '@iosys/qti-ui'

export interface ChoiceViewerProps {
  interaction: ChoiceInteraction
  /** Correct answer identifiers */
  correctAnswers?: string[] | undefined
  /** User's response (for review mode) */
  response?: ResponseValue | undefined
  /** Show correct answers */
  showAnswer?: boolean | undefined
}

export function ChoiceViewer({
  interaction,
  correctAnswers = [],
  response,
  showAnswer = false,
}: ChoiceViewerProps) {
  const { simpleChoices, orientation = 'vertical', columns } = interaction

  // Normalize response to array of strings
  const normalizeResponse = (): string[] => {
    if (response == null) return []
    if (Array.isArray(response)) {
      // Filter to only string values
      return response.filter((v): v is string => typeof v === 'string')
    }
    if (typeof response === 'string') return [response]
    return [String(response)]
  }
  const selectedIds = normalizeResponse()

  const getChoiceStatus = (choiceId: string): 'correct' | 'incorrect' | 'neutral' => {
    if (!showAnswer) return 'neutral'

    const isSelected = selectedIds.includes(choiceId)
    const isCorrect = correctAnswers.includes(choiceId)

    if (isSelected && isCorrect) return 'correct'
    if (isSelected && !isCorrect) return 'incorrect'
    if (!isSelected && isCorrect && response !== undefined) return 'correct' // Show missed correct
    return 'neutral'
  }

  // Determine layout: columns > 1 means grid, otherwise vertical
  const useGrid = columns && columns > 1
  const gridCols = columns || 1

  // Build layout class
  let layoutClass: string
  if (useGrid) {
    // Grid layout based on columns value
    const gridColClass = gridCols === 2 ? 'grid-cols-2' :
                         gridCols === 3 ? 'grid-cols-3' :
                         gridCols === 4 ? 'grid-cols-4' :
                         gridCols === 5 ? 'grid-cols-5' :
                         `grid-cols-${gridCols}`
    layoutClass = `grid ${gridColClass} gap-2`
  } else if (orientation === 'horizontal') {
    layoutClass = 'flex flex-wrap gap-2'
  } else {
    layoutClass = 'flex flex-col gap-1'
  }

  return (
    <div className={layoutClass}>
      {simpleChoices.map((choice, index) => {
        const isSelected = selectedIds.includes(choice.identifier)
        const status = getChoiceStatus(choice.identifier)

        return (
          <div
            key={choice.identifier}
            className={`
              flex items-start gap-2 py-0.5
              ${isSelected ? 'bg-blue-50/50 rounded px-1.5 -mx-1.5' : ''}
              ${status === 'correct' ? 'bg-green-50/50 rounded px-1.5 -mx-1.5' : ''}
              ${status === 'incorrect' ? 'bg-red-50/50 rounded px-1.5 -mx-1.5' : ''}
            `}
          >
            <ChoiceLabel
              index={index}
              style="number"
              selected={isSelected}
              status={status}
              className="mt-0.5"
            />
            <div className="flex-1">
              <div
                className="prose prose-sm max-w-none [&>p]:my-0"
                dangerouslySetInnerHTML={{ __html: choice.content }}
              />
              {showAnswer && correctAnswers.includes(choice.identifier) && (
                <span className="inline-block mt-0.5 text-xs text-qti-correct font-medium">
                  정답
                </span>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}

ChoiceViewer.displayName = 'ChoiceViewer'
