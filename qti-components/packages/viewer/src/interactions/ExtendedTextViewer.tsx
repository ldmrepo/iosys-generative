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
  interaction: _interaction,
  sampleAnswer,
  response,
  showAnswer = false,
}: ExtendedTextViewerProps) {
  void _interaction // Preserve for future use
  const userAnswer = response ? String(response) : ''

  return (
    <div className="space-y-3">
      {/* User's answer - only show if there's a response */}
      {userAnswer && (
        <div className="w-full min-h-[60px] p-3 border border-gray-300 bg-white">
          <div className="whitespace-pre-wrap">{userAnswer}</div>
        </div>
      )}

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
