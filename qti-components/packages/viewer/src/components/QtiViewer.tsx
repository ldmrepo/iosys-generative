import type {
  AssessmentItem,
  Interaction,
  ResponseValue,
  ScoringResult,
} from '@iosys/qti-core'
import { Feedback, Score } from '@iosys/qti-ui'
import {
  ChoiceViewer,
  TextEntryViewer,
  ExtendedTextViewer,
  MatchViewer,
  OrderViewer,
  GapMatchViewer,
} from '../interactions'

export interface QtiViewerProps {
  /** Assessment item to display */
  item: AssessmentItem
  /** User responses (keyed by responseIdentifier) */
  responses?: Record<string, ResponseValue>
  /** Scoring result (for review mode) */
  scoringResult?: ScoringResult
  /** Show correct answers */
  showAnswer?: boolean
  /** Show explanation/rationale */
  showExplanation?: boolean
  /** Custom class name */
  className?: string
}

export function QtiViewer({
  item,
  responses = {},
  scoringResult,
  showAnswer = false,
  showExplanation = false,
  className,
}: QtiViewerProps) {
  const { itemBody, responseDeclarations } = item

  // Get correct answer for an interaction
  const getCorrectAnswer = (responseId: string): string[] => {
    const decl = responseDeclarations.find(d => d.identifier === responseId)
    return decl?.correctResponse?.values ?? []
  }

  // Render a single interaction
  const renderInteraction = (interaction: Interaction) => {
    const { responseIdentifier } = interaction
    const response = responses[responseIdentifier]
    const correctAnswers = getCorrectAnswer(responseIdentifier)

    switch (interaction.type) {
      case 'choiceInteraction':
        return (
          <ChoiceViewer
            key={responseIdentifier}
            interaction={interaction}
            correctAnswers={correctAnswers}
            response={response}
            showAnswer={showAnswer}
          />
        )

      case 'textEntryInteraction':
        return (
          <TextEntryViewer
            key={responseIdentifier}
            interaction={interaction}
            correctAnswers={correctAnswers}
            response={response}
            showAnswer={showAnswer}
          />
        )

      case 'extendedTextInteraction':
        return (
          <ExtendedTextViewer
            key={responseIdentifier}
            interaction={interaction}
            sampleAnswer={correctAnswers[0]}
            response={response}
            showAnswer={showAnswer}
          />
        )

      case 'matchInteraction':
        return (
          <MatchViewer
            key={responseIdentifier}
            interaction={interaction}
            correctMatches={correctAnswers.map(pair => {
              const [source, target] = pair.split(' ')
              return { source: source ?? '', target: target ?? '' }
            })}
            response={response}
            showAnswer={showAnswer}
          />
        )

      case 'orderInteraction':
        return (
          <OrderViewer
            key={responseIdentifier}
            interaction={interaction}
            correctOrder={correctAnswers}
            response={response}
            showAnswer={showAnswer}
          />
        )

      case 'gapMatchInteraction':
        return (
          <GapMatchViewer
            key={responseIdentifier}
            interaction={interaction}
            correctAnswers={correctAnswers}
            response={response}
            showAnswer={showAnswer}
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
    <div className={`qti-viewer ${className ?? ''}`}>
      {/* Item Title */}
      {item.title && (
        <h2 className="text-lg font-semibold text-gray-900 mb-2">{item.title}</h2>
      )}

      {/* Item Body Content (Question) */}
      <div className="prose prose-sm max-w-none mb-3 [&>p]:my-1 qti-question">
        <div dangerouslySetInnerHTML={{ __html: itemBody.content }} />
      </div>

      {/* Interactions */}
      <div className="space-y-3">
        {itemBody.interactions.map(renderInteraction)}
      </div>

      {/* Scoring Result */}
      {scoringResult && (
        <div className="mt-6 pt-6 border-t">
          <div className="flex items-center justify-between mb-4">
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
        </div>
      )}

      {/* Explanation */}
      {showExplanation && itemBody.feedbackBlocks && itemBody.feedbackBlocks.length > 0 && (
        <div className="mt-6 pt-6 border-t">
          <h3 className="text-lg font-medium text-gray-900 mb-3">해설</h3>
          {itemBody.feedbackBlocks.map((feedback, index) => (
            <div
              key={index}
              className="prose prose-sm max-w-none"
              dangerouslySetInnerHTML={{ __html: feedback.content }}
            />
          ))}
        </div>
      )}
    </div>
  )
}

QtiViewer.displayName = 'QtiViewer'
