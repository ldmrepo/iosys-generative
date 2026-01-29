import type { GapMatchInteraction, ResponseValue } from '@iosys/qti-core'

export interface GapMatchViewerProps {
  interaction: GapMatchInteraction
  /** Correct answer pairs (format: "choiceId gapId") */
  correctAnswers?: string[] | undefined
  /** User's response */
  response?: ResponseValue | undefined
  /** Show correct answers */
  showAnswer?: boolean | undefined
}

export function GapMatchViewer({
  interaction,
  correctAnswers = [],
  response,
  showAnswer = false,
}: GapMatchViewerProps) {
  const { gapChoices, gaps } = interaction

  // Parse correct answers into a map (gapId -> correctChoiceId)
  const correctMap: Record<string, string> = {}
  for (const pair of correctAnswers) {
    const [choiceId, gapId] = pair.split(' ')
    if (choiceId && gapId) {
      correctMap[gapId] = choiceId
    }
  }

  // Parse user response into a map
  const responseMap: Record<string, string> = {}
  if (response && Array.isArray(response)) {
    for (const pair of response) {
      if (typeof pair === 'string') {
        const [choiceId, gapId] = pair.split(' ')
        if (choiceId && gapId) {
          responseMap[gapId] = choiceId
        }
      }
    }
  }

  // Get choice content by identifier
  const getChoiceContent = (identifier: string): string => {
    const choice = gapChoices.find(c => c.identifier === identifier)
    if (!choice) return identifier
    // GapText has 'content', GapImg has 'objectLabel'
    if ('content' in choice) {
      return choice.content
    } else if ('objectLabel' in choice && choice.objectLabel) {
      return choice.objectLabel
    }
    return identifier
  }

  return (
    <div className="space-y-3">
      {/* Gap choices (available options) */}
      <div className="flex flex-wrap gap-2 p-3 bg-slate-50 border border-slate-200">
        <span className="text-xs text-slate-500 w-full mb-1">선택 항목:</span>
        {gapChoices.map((choice) => (
          <span
            key={choice.identifier}
            className="inline-flex items-center px-2 py-1 text-sm bg-white border border-slate-300"
          >
            {'content' in choice ? choice.content : choice.objectLabel || choice.identifier}
          </span>
        ))}
      </div>

      {/* Gaps with answers */}
      <div className="space-y-2">
        {gaps.map((gap, index) => {
          const userAnswer = responseMap[gap.identifier]
          const correctAnswer = correctMap[gap.identifier]
          const isCorrect = userAnswer === correctAnswer
          const hasAnswer = !!userAnswer

          return (
            <div key={gap.identifier} className="flex items-center gap-2">
              <span className="text-sm font-semibold text-slate-600 w-8">
                ({index + 1})
              </span>
              <div
                className={`
                  flex-1 min-w-[120px] px-3 py-1.5 border text-sm
                  ${showAnswer && hasAnswer
                    ? isCorrect
                      ? 'border-green-500 bg-green-50 text-green-700'
                      : 'border-red-500 bg-red-50 text-red-700'
                    : 'border-slate-300 bg-white'
                  }
                `}
              >
                {hasAnswer ? getChoiceContent(userAnswer) : (
                  <span className="text-slate-400">___________</span>
                )}
              </div>
              {showAnswer && correctAnswer && !isCorrect && (
                <span className="text-sm text-green-600">
                  (정답: {getChoiceContent(correctAnswer)})
                </span>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

GapMatchViewer.displayName = 'GapMatchViewer'
