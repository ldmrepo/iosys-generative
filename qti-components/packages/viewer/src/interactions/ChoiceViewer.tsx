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

    // 정답인 선택지는 번호 박스 배경색으로 표시
    if (isCorrect) return 'correct'
    // 사용자가 선택했지만 오답인 경우
    if (isSelected && !isCorrect) return 'incorrect'
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
            className="flex items-start gap-2 py-0.5"
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
            </div>
          </div>
        )
      })}
    </div>
  )
}

ChoiceViewer.displayName = 'ChoiceViewer'
