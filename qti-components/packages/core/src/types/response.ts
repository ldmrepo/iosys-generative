/**
 * Response and Scoring Types
 */

import type { Identifier, BaseType, Cardinality } from './qti'

// -------------------
// Response Values
// -------------------

/** 응답 값 타입 */
export type ResponseValue =
  | string
  | string[]
  | number
  | boolean
  | null
  | DirectedPair[]
  | Point[]

/** 방향성 쌍 (배합형, 빈칸 채우기용) */
export interface DirectedPair {
  source: string
  target: string
}

/** 좌표 (핫스팟용) */
export interface Point {
  x: number
  y: number
}

// -------------------
// Candidate Response
// -------------------

/** 응시자 응답 */
export interface CandidateResponse {
  /** 응답 식별자 (responseIdentifier) */
  responseIdentifier: Identifier
  /** 응답 값 */
  value: ResponseValue
  /** 응답 시각 */
  timestamp?: string
}

// -------------------
// Scoring Result
// -------------------

/** 채점 결과 */
export interface ScoringResult {
  /** 획득 점수 */
  score: number
  /** 최대 점수 */
  maxScore: number
  /** 정답 여부 */
  isCorrect: boolean
  /** 부분 정답 여부 */
  partiallyCorrect: boolean
  /** 결과 변수 값 */
  outcomes: OutcomeValue[]
  /** 피드백 결과 */
  feedbacks: FeedbackResult[]
  /** 응답별 상세 결과 */
  details: ResponseDetail[]
}

/** 결과 변수 값 */
export interface OutcomeValue {
  identifier: Identifier
  cardinality: Cardinality
  baseType?: BaseType | undefined
  value: ResponseValue
}

/** 피드백 결과 */
export interface FeedbackResult {
  identifier: Identifier
  show: boolean
  content?: string | undefined
}

/** 응답 상세 결과 */
export interface ResponseDetail {
  responseIdentifier: Identifier
  candidateValue: ResponseValue
  correctValue?: ResponseValue | undefined
  isCorrect: boolean
  score: number
  maxScore: number
}

// -------------------
// Scoring Options
// -------------------

/** 채점 옵션 */
export interface ScoringOptions {
  /** 대소문자 구분 (텍스트 응답) */
  caseSensitive?: boolean
  /** 공백 정규화 */
  normalizeWhitespace?: boolean
  /** 부분 점수 허용 */
  allowPartialCredit?: boolean
  /** 순서 무시 (multiple cardinality) */
  ignoreOrder?: boolean
}

// -------------------
// Assessment Session
// -------------------

/** 응시 세션 상태 */
export type SessionState = 'initial' | 'interacting' | 'suspended' | 'closed'

/** 응시 세션 */
export interface AssessmentSession {
  /** 세션 ID */
  sessionId: string
  /** 문항 ID */
  itemId: Identifier
  /** 세션 상태 */
  state: SessionState
  /** 응답 목록 */
  responses: CandidateResponse[]
  /** 시작 시각 */
  startedAt: string
  /** 종료 시각 */
  endedAt?: string
  /** 남은 시간 (초) */
  remainingTime?: number
  /** 시도 횟수 */
  attemptCount: number
  /** 최대 시도 횟수 */
  maxAttempts?: number
  /** 채점 결과 */
  scoringResult?: ScoringResult
}

// -------------------
// Render Context
// -------------------

/** 렌더링 모드 */
export type RenderMode = 'edit' | 'view' | 'assess'

/** 응시 모드 서브타입 */
export type AssessMode = 'practice' | 'test' | 'review'

/** 렌더링 컨텍스트 */
export interface RenderContext {
  /** 렌더링 모드 */
  mode: RenderMode
  /** 응시 모드 (assess 모드일 때) */
  assessMode?: AssessMode
  /** 현재 응답 */
  responses?: Record<Identifier, ResponseValue>
  /** 정답 표시 여부 (view 모드) */
  showAnswer?: boolean
  /** 해설 표시 여부 (view 모드) */
  showExplanation?: boolean
  /** 채점 결과 (review 모드) */
  scoringResult?: ScoringResult
  /** 읽기 전용 여부 */
  readOnly?: boolean
  /** 비활성화 여부 */
  disabled?: boolean
}
