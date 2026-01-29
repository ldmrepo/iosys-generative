import { useCallback } from 'react'
import type {
  AssessmentItem,
  Interaction,
  ResponseValue,
  ScoringResult,
  AssessMode,
} from '@iosys/qti-core'
import { Button, Feedback, Score } from '@iosys/qti-ui'
import { useAssessmentState } from '../hooks'
import { ChoiceInput, TextEntryInput, ExtendedTextInput } from '../interactions'

export interface QtiAssessmentProps {
  /** Assessment item */
  item: AssessmentItem
  /** Assessment mode */
  mode?: AssessMode | undefined
  /** Callback when submitted */
  onSubmit?: ((result: ScoringResult) => void) | undefined
  /** Show submit button */
  showSubmitButton?: boolean | undefined
  /** Submit button text */
  submitButtonText?: string | undefined
  /** Custom class name */
  className?: string | undefined
}

export function QtiAssessment({
  item,
  mode = 'practice',
  onSubmit,
  showSubmitButton = true,
  submitButtonText = '제출',
  className,
}: QtiAssessmentProps) {
  const {
    getResponse,
    setResponse,
    submit,
    scoringResult,
    isComplete,
    reset,
  } = useAssessmentState(item, {
    onScore: onSubmit,
  })

  const { itemBody } = item
  const isReviewMode = mode === 'review'
  const isSubmitted = scoringResult !== null

  // Handle response change
  const handleResponseChange = useCallback(
    (responseIdentifier: string) => (value: ResponseValue) => {
      setResponse(responseIdentifier, value)
    },
    [setResponse]
  )

  // Handle submit
  const handleSubmit = useCallback(() => {
    submit()
  }, [submit])

  // Render a single interaction
  const renderInteraction = (interaction: Interaction) => {
    const { responseIdentifier } = interaction
    const response = getResponse(responseIdentifier)
    const disabled = isSubmitted || isReviewMode

    switch (interaction.type) {
      case 'choiceInteraction':
        return (
          <ChoiceInput
            key={responseIdentifier}
            interaction={interaction}
            value={response}
            onChange={handleResponseChange(responseIdentifier)}
            disabled={disabled}
          />
        )

      case 'textEntryInteraction':
        return (
          <TextEntryInput
            key={responseIdentifier}
            interaction={interaction}
            value={response}
            onChange={handleResponseChange(responseIdentifier)}
            disabled={disabled}
            inline={false}
          />
        )

      case 'extendedTextInteraction':
        return (
          <ExtendedTextInput
            key={responseIdentifier}
            interaction={interaction}
            value={response}
            onChange={handleResponseChange(responseIdentifier)}
            disabled={disabled}
          />
        )

      default:
        return (
          <div key={responseIdentifier} className="p-4 bg-gray-100 rounded-lg text-gray-500">
            지원하지 않는 문항 유형입니다: {(interaction as Interaction).type}
          </div>
        )
    }
  }

  return (
    <div className={`qti-assessment ${className ?? ''}`}>
      {/* Item Title */}
      {item.title && (
        <h2 className="text-xl font-semibold text-gray-900 mb-4">{item.title}</h2>
      )}

      {/* Item Body Content */}
      <div className="prose prose-lg max-w-none mb-6">
        <div dangerouslySetInnerHTML={{ __html: itemBody.content }} />
      </div>

      {/* Interactions */}
      <div className="space-y-6">
        {itemBody.interactions.map(renderInteraction)}
      </div>

      {/* Submit Button */}
      {showSubmitButton && !isSubmitted && !isReviewMode && (
        <div className="mt-6">
          <Button
            onClick={handleSubmit}
            disabled={!isComplete}
            size="lg"
          >
            {submitButtonText}
          </Button>
          {!isComplete && (
            <p className="mt-2 text-sm text-gray-500">
              모든 문항에 답변해 주세요.
            </p>
          )}
        </div>
      )}

      {/* Scoring Result (Practice Mode) */}
      {isSubmitted && mode === 'practice' && scoringResult && (
        <div className="mt-6 pt-6 border-t space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-gray-700 font-medium">채점 결과</span>
            <Score score={scoringResult.score} maxScore={scoringResult.maxScore} />
          </div>

          {scoringResult.isCorrect && (
            <Feedback type="correct">정답입니다!</Feedback>
          )}

          {scoringResult.partiallyCorrect && !scoringResult.isCorrect && (
            <Feedback type="partial">부분 정답입니다.</Feedback>
          )}

          {!scoringResult.isCorrect && !scoringResult.partiallyCorrect && (
            <Feedback type="incorrect">오답입니다.</Feedback>
          )}

          {/* Show correct answers in practice mode */}
          {!scoringResult.isCorrect && (
            <div className="p-4 bg-green-50 border border-qti-correct rounded-lg">
              <div className="text-sm font-medium text-qti-correct mb-2">정답</div>
              {scoringResult.details.map(detail => {
                const correctValue = detail.correctValue
                if (!correctValue) return null
                return (
                  <div key={detail.responseIdentifier} className="text-sm text-gray-700">
                    {Array.isArray(correctValue) ? correctValue.join(', ') : String(correctValue)}
                  </div>
                )
              })}
            </div>
          )}

          {/* Retry button */}
          <Button onClick={reset} variant="outline">
            다시 풀기
          </Button>
        </div>
      )}

      {/* Test mode - no immediate feedback */}
      {isSubmitted && mode === 'test' && (
        <div className="mt-6 pt-6 border-t">
          <Feedback type="info">
            답안이 제출되었습니다.
          </Feedback>
        </div>
      )}
    </div>
  )
}

QtiAssessment.displayName = 'QtiAssessment'
