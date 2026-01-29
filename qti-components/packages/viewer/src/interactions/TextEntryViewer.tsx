import type { TextEntryInteraction, ResponseValue } from '@iosys/qti-core'

export interface TextEntryViewerProps {
  interaction: TextEntryInteraction
  /** Correct answers */
  correctAnswers?: string[] | undefined
  /** User's response (for review mode) */
  response?: ResponseValue | undefined
  /** Show correct answers */
  showAnswer?: boolean | undefined
}

export function TextEntryViewer({
  interaction: _interaction,
  correctAnswers = [],
  response,
  showAnswer = false,
}: TextEntryViewerProps) {
  void _interaction // Preserve for future use
  const userAnswer = response ? String(response) : ''
  const isCorrect = correctAnswers.some(
    ans => ans.toLowerCase() === userAnswer.toLowerCase()
  )

  const status = showAnswer && response !== undefined
    ? isCorrect ? 'correct' : 'incorrect'
    : 'neutral'

  // Don't render anything if no response in view mode
  if (!userAnswer) {
    return null
  }

  return (
    <span className="inline-flex items-center gap-2">
      <span
        className={`
          inline-block min-w-[80px] px-2 py-1 border-b-2
          ${status === 'correct' ? 'border-qti-correct bg-green-50' : ''}
          ${status === 'incorrect' ? 'border-qti-incorrect bg-red-50' : ''}
          ${status === 'neutral' ? 'border-gray-300' : ''}
        `}
      >
        {userAnswer}
      </span>
      {showAnswer && !isCorrect && correctAnswers.length > 0 && (
        <span className="text-sm text-qti-correct">
          (정답: {correctAnswers.join(', ')})
        </span>
      )}
    </span>
  )
}

TextEntryViewer.displayName = 'TextEntryViewer'
