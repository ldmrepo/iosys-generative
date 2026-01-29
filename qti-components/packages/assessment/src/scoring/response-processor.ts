/**
 * Response Processing Engine
 * Based on QTI 3.0 Response Processing specification
 */

import type {
  AssessmentItem,
  ResponseDeclaration,
  CandidateResponse,
  ScoringResult,
  ResponseDetail,
  OutcomeValue,
  FeedbackResult,
  ResponseValue,
  ScoringOptions,
  Cardinality,
} from '@iosys/qti-core'

/**
 * Score an assessment item based on candidate responses
 */
export function scoreResponses(
  item: AssessmentItem,
  responses: CandidateResponse[],
  options: ScoringOptions = {}
): ScoringResult {
  const { responseDeclarations, outcomeDeclarations } = item
  const details: ResponseDetail[] = []
  let totalScore = 0
  let totalMaxScore = 0

  // Process each response
  for (const decl of responseDeclarations) {
    const response = responses.find(r => r.responseIdentifier === decl.identifier)
    const candidateValue = response?.value ?? null
    const correctValue = decl.correctResponse?.values ?? []

    // Calculate score for this response
    const { score, maxScore, isCorrect } = scoreResponse(
      decl,
      candidateValue,
      correctValue,
      options
    )

    details.push({
      responseIdentifier: decl.identifier,
      candidateValue,
      correctValue: correctValue.length > 0 ? correctValue : undefined,
      isCorrect,
      score,
      maxScore,
    })

    totalScore += score
    totalMaxScore += maxScore
  }

  // Calculate overall result
  const isCorrect = details.every(d => d.isCorrect)
  const partiallyCorrect = !isCorrect && totalScore > 0

  // Build outcome values
  const outcomes: OutcomeValue[] = outcomeDeclarations.map(decl => ({
    identifier: decl.identifier,
    cardinality: decl.cardinality,
    baseType: decl.baseType,
    value: decl.identifier === 'SCORE' ? totalScore : (decl.defaultValue ?? null),
  }))

  // Determine feedback to show
  const feedbacks: FeedbackResult[] = []
  if (item.itemBody.feedbackBlocks) {
    for (const fb of item.itemBody.feedbackBlocks) {
      const shouldShow = fb.showHide === 'show'
        ? (isCorrect && fb.identifier === 'correct') ||
          (!isCorrect && fb.identifier === 'incorrect')
        : false
      feedbacks.push({
        identifier: fb.identifier,
        show: shouldShow,
        content: shouldShow ? fb.content : undefined,
      })
    }
  }

  return {
    score: totalScore,
    maxScore: totalMaxScore,
    isCorrect,
    partiallyCorrect,
    outcomes,
    feedbacks,
    details,
  }
}

/**
 * Score a single response against its declaration
 */
function scoreResponse(
  decl: ResponseDeclaration,
  candidateValue: ResponseValue,
  correctValues: string[],
  options: ScoringOptions
): { score: number; maxScore: number; isCorrect: boolean } {
  // Use mapping if available
  if (decl.mapping) {
    return scoreMappedResponse(decl, candidateValue, options)
  }

  // Default: match/correct scoring
  const maxScore = 1
  const isCorrect = compareValues(
    candidateValue,
    correctValues,
    decl.cardinality,
    options
  )

  return {
    score: isCorrect ? maxScore : 0,
    maxScore,
    isCorrect,
  }
}

/**
 * Score using mapping table
 */
function scoreMappedResponse(
  decl: ResponseDeclaration,
  candidateValue: ResponseValue,
  options: ScoringOptions
): { score: number; maxScore: number; isCorrect: boolean } {
  const mapping = decl.mapping!
  let score = mapping.defaultValue

  if (candidateValue == null) {
    return { score: 0, maxScore: 1, isCorrect: false }
  }

  // Get candidate values as array
  const values = Array.isArray(candidateValue)
    ? candidateValue.filter((v): v is string => typeof v === 'string')
    : [String(candidateValue)]

  // Sum up mapped values
  for (const val of values) {
    const entry = mapping.mapEntries.find(e => {
      const caseSensitive = e.caseSensitive ?? options.caseSensitive ?? false
      return caseSensitive
        ? e.mapKey === val
        : e.mapKey.toLowerCase() === val.toLowerCase()
    })
    if (entry) {
      score += entry.mappedValue
    }
  }

  // Apply bounds
  if (mapping.lowerBound !== undefined) {
    score = Math.max(score, mapping.lowerBound)
  }
  if (mapping.upperBound !== undefined) {
    score = Math.min(score, mapping.upperBound)
  }

  const maxScore = mapping.upperBound ?? 1
  const isCorrect = score >= maxScore

  return { score, maxScore, isCorrect }
}

/**
 * Compare candidate value against correct values
 */
function compareValues(
  candidateValue: ResponseValue,
  correctValues: string[],
  cardinality: Cardinality,
  options: ScoringOptions
): boolean {
  if (candidateValue == null || correctValues.length === 0) {
    return false
  }

  const caseSensitive = options.caseSensitive ?? false
  const normalizeWhitespace = options.normalizeWhitespace ?? true

  const normalize = (s: string): string => {
    let result = caseSensitive ? s : s.toLowerCase()
    if (normalizeWhitespace) {
      result = result.trim().replace(/\s+/g, ' ')
    }
    return result
  }

  switch (cardinality) {
    case 'single': {
      const candidate = normalize(String(candidateValue))
      return correctValues.some(cv => normalize(cv) === candidate)
    }

    case 'multiple': {
      // All correct values must be selected, no extras
      const candidateSet = new Set(
        (Array.isArray(candidateValue) ? candidateValue : [candidateValue])
          .filter((v): v is string => typeof v === 'string')
          .map(normalize)
      )
      const correctSet = new Set(correctValues.map(normalize))

      if (candidateSet.size !== correctSet.size) return false
      for (const v of candidateSet) {
        if (!correctSet.has(v)) return false
      }
      return true
    }

    case 'ordered': {
      // Order must match exactly
      const candidateArr = (Array.isArray(candidateValue) ? candidateValue : [candidateValue])
        .filter((v): v is string => typeof v === 'string')
        .map(normalize)

      if (candidateArr.length !== correctValues.length) return false
      return candidateArr.every((v, i) => v === normalize(correctValues[i] ?? ''))
    }

    default:
      return false
  }
}

/**
 * Calculate partial credit score
 */
export function calculatePartialCredit(
  candidateValues: string[],
  correctValues: string[],
  options: ScoringOptions = {}
): number {
  const caseSensitive = options.caseSensitive ?? false
  const normalize = (s: string): string => caseSensitive ? s : s.toLowerCase()

  const correctSet = new Set(correctValues.map(normalize))
  let matches = 0

  for (const cv of candidateValues) {
    if (correctSet.has(normalize(cv))) {
      matches++
    }
  }

  return correctValues.length > 0 ? matches / correctValues.length : 0
}
