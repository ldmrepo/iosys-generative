/**
 * IML (IOSYS Markup Language) Type Definitions
 * Based on preprocessing/dtd/IML(영문).dtd
 */

// -------------------
// IML Item Types
// -------------------

/**
 * IML 문항 유형 코드
 * - 11: 선다형 (Multiple Choice)
 * - 21: 진위형 (True/False)
 * - 31: 단답형 (Short Answer)
 * - 34: 완성형 (Fill-in-the-blank)
 * - 37: 배합형 (Matching)
 * - 41: 서술형 (Essay - Short)
 * - 51: 논술형 (Essay - Long)
 */
export type ImlItemTypeCode = '11' | '21' | '31' | '34' | '37' | '41' | '51'

export const IML_ITEM_TYPES = {
  CHOICE: '11',
  TRUE_FALSE: '21',
  SHORT_ANSWER: '31',
  FILL_BLANK: '34',
  MATCHING: '37',
  ESSAY_SHORT: '41',
  ESSAY_LONG: '51',
} as const

// -------------------
// Content Elements
// -------------------

/** 단락 (Paragraph) */
export interface ImlParagraph {
  type: 'paragraph'
  align?: 'left' | 'center' | 'right' | 'justify' | undefined
  content: ImlInlineContent[]
}

/** 그림 (Image) */
export interface ImlImage {
  type: 'image'
  src: string
  alt?: string | undefined
  width?: number | undefined
  height?: number | undefined
  align?: 'left' | 'center' | 'right' | undefined
}

/** 수식 (Math - LaTeX) */
export interface ImlMath {
  type: 'math'
  latex: string
  display?: 'inline' | 'block'
}

/** 테이블 (Table) */
export interface ImlTable {
  type: 'table'
  rows: ImlTableRow[]
  border?: number | undefined
  width?: string | undefined
}

export interface ImlTableRow {
  cells: ImlTableCell[]
}

export interface ImlTableCell {
  type: 'td' | 'th'
  content: ImlBlockContent[]
  colspan?: number | undefined
  rowspan?: number | undefined
  align?: 'left' | 'center' | 'right' | undefined
  valign?: 'top' | 'middle' | 'bottom' | undefined
}

/** 동영상 (Video) */
export interface ImlVideo {
  type: 'video'
  src: string
  poster?: string
  width?: number
  height?: number
}

/** 오디오 (Audio) */
export interface ImlAudio {
  type: 'audio'
  src: string
}

/** 보기박스 (Example Box) */
export interface ImlExampleBox {
  type: 'exampleBox'
  title?: string
  content: ImlBlockContent[]
}

/** 인라인 콘텐츠 */
export type ImlInlineContent =
  | string
  | ImlMath
  | ImlImage
  | ImlTextStyle
  | ImlLink
  | ImlBlank

/** 텍스트 스타일 */
export interface ImlTextStyle {
  type: 'textStyle'
  style: 'bold' | 'italic' | 'underline' | 'strikethrough' | 'superscript' | 'subscript'
  content: ImlInlineContent[]
}

/** 링크 */
export interface ImlLink {
  type: 'link'
  href: string
  content: ImlInlineContent[]
}

/** 빈칸 (완성형 문항용) */
export interface ImlBlank {
  type: 'blank'
  id: string
  size?: number
}

/** 블록 콘텐츠 */
export type ImlBlockContent =
  | ImlParagraph
  | ImlImage
  | ImlMath
  | ImlTable
  | ImlVideo
  | ImlAudio
  | ImlExampleBox

// -------------------
// Answer Elements
// -------------------

/** 선다형 답항 */
export interface ImlChoiceAnswer {
  id: string
  content: ImlBlockContent[]
  isCorrect: boolean
}

/** 배합형 항목 */
export interface ImlMatchItem {
  id: string
  content: ImlBlockContent[]
}

/** 배합형 매칭 */
export interface ImlMatchPair {
  sourceId: string
  targetId: string
}

// -------------------
// Item Structure
// -------------------

/** 문제 (Question) */
export interface ImlQuestion {
  content: ImlBlockContent[]
}

/** 해설 (Explanation) */
export interface ImlExplanation {
  content: ImlBlockContent[]
}

/** 채점기준 (Scoring Criteria) */
export interface ImlScoringCriteria {
  content: ImlBlockContent[]
  maxScore?: number
}

/** 피드백 */
export interface ImlFeedback {
  type: 'correct' | 'incorrect' | 'partial'
  content: ImlBlockContent[]
}

// -------------------
// Assessment Item
// -------------------

/** IML 문항 기본 인터페이스 */
export interface ImlItemBase {
  /** 문항 고유 ID */
  id: string
  /** 문항 유형 코드 */
  itemType: ImlItemTypeCode
  /** 문제 내용 */
  question: ImlQuestion
  /** 해설 */
  explanation?: ImlExplanation | undefined
  /** 채점기준 */
  scoringCriteria?: ImlScoringCriteria | undefined
  /** 피드백 */
  feedbacks?: ImlFeedback[] | undefined
  /** 배점 */
  score?: number | undefined
  /** 난이도 (상/중/하) */
  difficulty?: 'high' | 'medium' | 'low' | undefined
  /** 교육과정 */
  curriculum?: string | undefined
  /** 성취기준 */
  achievementStandard?: string | undefined
  /** 출처 */
  source?: string | undefined
}

/** 선다형 문항 (11) */
export interface ImlChoiceItem extends ImlItemBase {
  itemType: '11'
  /** 답항 목록 */
  choices: ImlChoiceAnswer[]
  /** 복수 정답 허용 여부 */
  multipleAnswers?: boolean | undefined
  /** 정답 섞기 여부 */
  shuffle?: boolean | undefined
}

/** 진위형 문항 (21) */
export interface ImlTrueFalseItem extends ImlItemBase {
  itemType: '21'
  /** 정답 (true/false) */
  correctAnswer: boolean
}

/** 단답형 문항 (31) */
export interface ImlShortAnswerItem extends ImlItemBase {
  itemType: '31'
  /** 정답 목록 (동의어 허용) */
  correctAnswers: string[]
  /** 대소문자 구분 */
  caseSensitive?: boolean | undefined
  /** 최대 글자 수 */
  maxLength?: number | undefined
}

/** 완성형 문항 (34) */
export interface ImlFillBlankItem extends ImlItemBase {
  itemType: '34'
  /** 빈칸별 정답 */
  blanks: {
    id: string
    correctAnswers: string[]
    caseSensitive?: boolean | undefined
  }[]
}

/** 배합형 문항 (37) */
export interface ImlMatchingItem extends ImlItemBase {
  itemType: '37'
  /** 왼쪽 항목 */
  sourceItems: ImlMatchItem[]
  /** 오른쪽 항목 */
  targetItems: ImlMatchItem[]
  /** 정답 매칭 */
  correctMatches: ImlMatchPair[]
}

/** 서술형 문항 (41) */
export interface ImlEssayShortItem extends ImlItemBase {
  itemType: '41'
  /** 예시 답안 */
  sampleAnswer?: ImlBlockContent[] | undefined
  /** 최소 글자 수 */
  minLength?: number | undefined
  /** 최대 글자 수 */
  maxLength?: number | undefined
}

/** 논술형 문항 (51) */
export interface ImlEssayLongItem extends ImlItemBase {
  itemType: '51'
  /** 예시 답안 */
  sampleAnswer?: ImlBlockContent[] | undefined
  /** 최소 글자 수 */
  minLength?: number | undefined
  /** 최대 글자 수 */
  maxLength?: number | undefined
}

/** IML 문항 통합 타입 */
export type ImlItem =
  | ImlChoiceItem
  | ImlTrueFalseItem
  | ImlShortAnswerItem
  | ImlFillBlankItem
  | ImlMatchingItem
  | ImlEssayShortItem
  | ImlEssayLongItem

// -------------------
// Document Structure
// -------------------

/** IML 문서 */
export interface ImlDocument {
  /** 문서 버전 */
  version: string
  /** 문항 목록 */
  items: ImlItem[]
  /** 메타데이터 */
  metadata?: ImlDocumentMetadata
}

/** 문서 메타데이터 */
export interface ImlDocumentMetadata {
  title?: string
  author?: string
  createdAt?: string
  updatedAt?: string
  subject?: string
  grade?: string
  semester?: string
}
