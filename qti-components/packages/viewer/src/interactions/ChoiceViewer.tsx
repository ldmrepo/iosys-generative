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
  const { simpleChoices, orientation = 'vertical', maxChoices = 1 } = interaction
  const isMultiple = maxChoices !== 1

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

  return (
    <div
      className={
        orientation === 'horizontal' ? 'flex flex-wrap gap-4' : 'flex flex-col gap-2'
      }
    >
      {simpleChoices.map((choice, index) => {
        const isSelected = selectedIds.includes(choice.identifier)
        const status = getChoiceStatus(choice.identifier)

        return (
          <div
            key={choice.identifier}
            className={`
              flex items-start gap-3 p-3 rounded-lg border
              ${isSelected ? 'border-qti-primary bg-blue-50' : 'border-gray-200'}
              ${status === 'correct' ? 'border-qti-correct bg-green-50' : ''}
              ${status === 'incorrect' ? 'border-qti-incorrect bg-red-50' : ''}
            `}
          >
            <ChoiceLabel
              index={index}
              selected={isSelected}
              status={status}
            />
            <div className="flex-1">
              <div
                className="prose prose-sm max-w-none"
                dangerouslySetInnerHTML={{ __html: choice.content }}
              />
              {showAnswer && correctAnswers.includes(choice.identifier) && (
                <span className="inline-block mt-1 text-xs text-qti-correct font-medium">
                  {isMultiple ? '정답' : '정답'}
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
