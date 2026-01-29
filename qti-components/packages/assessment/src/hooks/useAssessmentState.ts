import { useState, useCallback, useMemo } from 'react'
import type {
  AssessmentItem,
  CandidateResponse,
  ResponseValue,
  ScoringResult,
  Identifier,
} from '@iosys/qti-core'
import { scoreResponses } from '../scoring'

export interface UseAssessmentStateOptions {
  /** Initial responses */
  initialResponses?: CandidateResponse[] | undefined
  /** Auto-score on submit */
  autoScore?: boolean | undefined
  /** Callback when response changes */
  onResponseChange?: ((responses: CandidateResponse[]) => void) | undefined
  /** Callback when scored */
  onScore?: ((result: ScoringResult) => void) | undefined
}

export interface UseAssessmentStateReturn {
  /** Current responses */
  responses: CandidateResponse[]
  /** Get response value by identifier */
  getResponse: (responseIdentifier: Identifier) => ResponseValue | undefined
  /** Set a response value */
  setResponse: (responseIdentifier: Identifier, value: ResponseValue) => void
  /** Clear a specific response */
  clearResponse: (responseIdentifier: Identifier) => void
  /** Clear all responses */
  clearAllResponses: () => void
  /** Submit and score */
  submit: () => ScoringResult
  /** Current scoring result (after submit) */
  scoringResult: ScoringResult | null
  /** Whether all required responses are filled */
  isComplete: boolean
  /** Reset to initial state */
  reset: () => void
}

/**
 * Hook for managing assessment response state
 */
export function useAssessmentState(
  item: AssessmentItem,
  options: UseAssessmentStateOptions = {}
): UseAssessmentStateReturn {
  const {
    initialResponses = [],
    autoScore = true,
    onResponseChange,
    onScore,
  } = options

  const [responses, setResponses] = useState<CandidateResponse[]>(initialResponses)
  const [scoringResult, setScoringResult] = useState<ScoringResult | null>(null)

  // Get response by identifier
  const getResponse = useCallback(
    (responseIdentifier: Identifier): ResponseValue | undefined => {
      const response = responses.find(r => r.responseIdentifier === responseIdentifier)
      return response?.value
    },
    [responses]
  )

  // Set a response
  const setResponse = useCallback(
    (responseIdentifier: Identifier, value: ResponseValue) => {
      setResponses(prev => {
        const existing = prev.findIndex(r => r.responseIdentifier === responseIdentifier)
        const newResponse: CandidateResponse = {
          responseIdentifier,
          value,
          timestamp: new Date().toISOString(),
        }

        const newResponses =
          existing >= 0
            ? [...prev.slice(0, existing), newResponse, ...prev.slice(existing + 1)]
            : [...prev, newResponse]

        onResponseChange?.(newResponses)
        return newResponses
      })
      // Clear scoring result when response changes
      setScoringResult(null)
    },
    [onResponseChange]
  )

  // Clear a specific response
  const clearResponse = useCallback(
    (responseIdentifier: Identifier) => {
      setResponses(prev => {
        const newResponses = prev.filter(r => r.responseIdentifier !== responseIdentifier)
        onResponseChange?.(newResponses)
        return newResponses
      })
      setScoringResult(null)
    },
    [onResponseChange]
  )

  // Clear all responses
  const clearAllResponses = useCallback(() => {
    setResponses([])
    setScoringResult(null)
    onResponseChange?.([])
  }, [onResponseChange])

  // Submit and score
  const submit = useCallback(() => {
    const result = scoreResponses(item, responses)
    if (autoScore) {
      setScoringResult(result)
    }
    onScore?.(result)
    return result
  }, [item, responses, autoScore, onScore])

  // Check if all responses are complete
  const isComplete = useMemo(() => {
    const { responseDeclarations } = item
    return responseDeclarations.every(decl => {
      const response = responses.find(r => r.responseIdentifier === decl.identifier)
      return response?.value != null
    })
  }, [item, responses])

  // Reset to initial state
  const reset = useCallback(() => {
    setResponses(initialResponses)
    setScoringResult(null)
  }, [initialResponses])

  return {
    responses,
    getResponse,
    setResponse,
    clearResponse,
    clearAllResponses,
    submit,
    scoringResult,
    isComplete,
    reset,
  }
}
