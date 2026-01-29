import type { ExtendedTextInteraction, ResponseValue } from '@iosys/qti-core'

export interface ExtendedTextViewerProps {
  interaction: ExtendedTextInteraction
  /** Sample/model answer */
  sampleAnswer?: string | undefined
  /** User's response (for review mode) */
  response?: ResponseValue | undefined
  /** Show sample answer */
  showAnswer?: boolean | undefined
}

export function ExtendedTextViewer({
  interaction,
  sampleAnswer,
  response,
  showAnswer = false,
}: ExtendedTextViewerProps) {
  const userAnswer = response ? String(response) : ''

  return (
    <div className="space-y-3">
      {/* User's answer */}
      <div
        className={`
          w-full min-h-[100px] p-3 rounded-lg border
          ${userAnswer ? 'border-gray-300 bg-white' : 'border-gray-200 bg-gray-50'}
        `}
      >
        {userAnswer ? (
          <div className="whitespace-pre-wrap">{userAnswer}</div>
        ) : (
          <span className="text-gray-400">
            {interaction.placeholderText || '응답이 없습니다'}
          </span>
        )}
      </div>

      {/* Sample answer */}
      {showAnswer && sampleAnswer && (
        <div className="p-3 rounded-lg border border-qti-correct bg-green-50">
          <div className="text-sm font-medium text-qti-correct mb-2">예시 답안</div>
          <div className="whitespace-pre-wrap text-gray-700">{sampleAnswer}</div>
        </div>
      )}
    </div>
  )
}

ExtendedTextViewer.displayName = 'ExtendedTextViewer'
