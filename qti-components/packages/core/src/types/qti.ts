/**
 * QTI 3.0 Type Definitions
 * Based on IMS QTI 3.0 Specification
 * https://www.imsglobal.org/spec/qti/v3p0
 */

// Base Types
export type Identifier = string
export type Uri = string

// Cardinality types
export type Cardinality = 'single' | 'multiple' | 'ordered' | 'record'

// Base types for values
export type BaseType =
  | 'identifier'
  | 'boolean'
  | 'integer'
  | 'float'
  | 'string'
  | 'point'
  | 'pair'
  | 'directedPair'
  | 'duration'
  | 'file'
  | 'uri'

// Shape types for hotspot
export type Shape = 'circle' | 'rect' | 'poly' | 'ellipse' | 'default'

// Show/Hide for feedback
export type ShowHide = 'show' | 'hide'

// Navigation mode
export type NavigationMode = 'linear' | 'nonlinear'

// Submission mode
export type SubmissionMode = 'individual' | 'simultaneous'

// -------------------
// Variable Declarations
// -------------------

export interface CorrectResponse {
  interpretation?: string
  values: string[]
}

export interface MapEntry {
  mapKey: string
  mappedValue: number
  caseSensitive?: boolean
}

export interface Mapping {
  lowerBound?: number
  upperBound?: number
  defaultValue: number
  mapEntries: MapEntry[]
}

export interface AreaMapEntry {
  shape: Shape
  coords: number[]
  mappedValue: number
}

export interface AreaMapping {
  lowerBound?: number
  upperBound?: number
  defaultValue: number
  areaMapEntries: AreaMapEntry[]
}

export interface ResponseDeclaration {
  identifier: Identifier
  cardinality: Cardinality
  baseType?: BaseType
  defaultValue?: string[]
  correctResponse?: CorrectResponse
  mapping?: Mapping
  areaMapping?: AreaMapping
}

export interface OutcomeDeclaration {
  identifier: Identifier
  cardinality: Cardinality
  baseType?: BaseType
  defaultValue?: string | number | boolean | null
  interpretation?: string
  longInterpretation?: Uri
  normalMaximum?: number
  normalMinimum?: number
  masteryValue?: number
}

export interface TemplateDeclaration {
  identifier: Identifier
  cardinality: Cardinality
  baseType?: BaseType
  defaultValue?: string[]
  paramVariable?: boolean
  mathVariable?: boolean
}

// -------------------
// Item Body & Content
// -------------------

export interface Stylesheet {
  href: Uri
  type: string
  media?: string
  title?: string
}

export interface RubricBlock {
  use: string
  view?: string[]
  content: string
}

// -------------------
// Interactions
// -------------------

export interface BaseInteraction {
  responseIdentifier: Identifier
}

// Choice Interaction
export interface SimpleChoice {
  identifier: Identifier
  fixed?: boolean
  templateIdentifier?: Identifier
  showHide?: ShowHide
  content: string
}

export interface ChoiceInteraction extends BaseInteraction {
  type: 'choiceInteraction'
  shuffle?: boolean | undefined
  maxChoices?: number | undefined
  minChoices?: number | undefined
  orientation?: 'horizontal' | 'vertical' | undefined
  simpleChoices: SimpleChoice[]
}

// Text Entry Interaction
export interface TextEntryInteraction extends BaseInteraction {
  type: 'textEntryInteraction'
  expectedLength?: number | undefined
  patternMask?: string | undefined
  placeholderText?: string | undefined
  base?: number | undefined
  stringIdentifier?: Identifier | undefined
  expectedLines?: number | undefined
}

// Extended Text Interaction
export interface ExtendedTextInteraction extends BaseInteraction {
  type: 'extendedTextInteraction'
  expectedLength?: number
  expectedLines?: number
  maxStrings?: number
  minStrings?: number
  format?: 'plain' | 'preFormatted' | 'xhtml'
  placeholderText?: string
}

// Match Interaction
export interface SimpleAssociableChoice {
  identifier: Identifier
  fixed?: boolean
  templateIdentifier?: Identifier
  showHide?: ShowHide
  matchMax: number
  matchMin?: number
  matchGroup?: Identifier[]
  content: string
}

export interface SimpleMatchSet {
  simpleAssociableChoices: SimpleAssociableChoice[]
}

export interface MatchInteraction extends BaseInteraction {
  type: 'matchInteraction'
  shuffle?: boolean
  maxAssociations?: number
  minAssociations?: number
  simpleMatchSets: [SimpleMatchSet, SimpleMatchSet]
}

// Order Interaction
export interface OrderInteraction extends BaseInteraction {
  type: 'orderInteraction'
  shuffle?: boolean
  minChoices?: number
  maxChoices?: number
  orientation?: 'horizontal' | 'vertical'
  simpleChoices: SimpleChoice[]
}

// Hotspot Interaction
export interface HotspotChoice {
  identifier: Identifier
  fixed?: boolean
  templateIdentifier?: Identifier
  showHide?: ShowHide
  shape: Shape
  coords: number[]
  hotspotLabel?: string
}

export interface ObjectElement {
  data: Uri
  type: string
  width?: number
  height?: number
}

export interface HotspotInteraction extends BaseInteraction {
  type: 'hotspotInteraction'
  maxChoices?: number
  minChoices?: number
  object: ObjectElement
  hotspotChoices: HotspotChoice[]
}

// Gap Match Interaction
export interface Gap {
  identifier: Identifier
  templateIdentifier?: Identifier
  showHide?: ShowHide
  required?: boolean
  matchGroup?: Identifier[]
}

export interface GapText {
  identifier: Identifier
  fixed?: boolean
  templateIdentifier?: Identifier
  showHide?: ShowHide
  matchMax: number
  matchMin?: number
  matchGroup?: Identifier[]
  content: string
}

export interface GapImg {
  identifier: Identifier
  fixed?: boolean
  templateIdentifier?: Identifier
  showHide?: ShowHide
  matchMax: number
  matchMin?: number
  matchGroup?: Identifier[]
  object: ObjectElement
  objectLabel?: string
}

export interface GapMatchInteraction extends BaseInteraction {
  type: 'gapMatchInteraction'
  shuffle?: boolean
  gapChoices: (GapText | GapImg)[]
  blockQuote?: string
  gaps: Gap[]
}

// Inline Choice Interaction
export interface InlineChoice {
  identifier: Identifier
  fixed?: boolean
  templateIdentifier?: Identifier
  showHide?: ShowHide
  content: string
}

export interface InlineChoiceInteraction extends BaseInteraction {
  type: 'inlineChoiceInteraction'
  shuffle?: boolean
  required?: boolean
  inlineChoices: InlineChoice[]
}

// Union of all interaction types
export type Interaction =
  | ChoiceInteraction
  | TextEntryInteraction
  | ExtendedTextInteraction
  | MatchInteraction
  | OrderInteraction
  | HotspotInteraction
  | GapMatchInteraction
  | InlineChoiceInteraction

export type InteractionType = Interaction['type']

// -------------------
// Feedback
// -------------------

export interface FeedbackBlock {
  outcomeIdentifier: Identifier
  identifier: Identifier
  showHide: ShowHide
  content: string
}

export interface FeedbackInline {
  outcomeIdentifier: Identifier
  identifier: Identifier
  showHide: ShowHide
  content: string
}

export interface ModalFeedback {
  outcomeIdentifier: Identifier
  identifier: Identifier
  showHide: ShowHide
  title?: string
  content: string
}

// -------------------
// Response Processing
// -------------------

export interface ResponseCondition {
  responseIf: ResponseIf
  responseElseIf?: ResponseElseIf[]
  responseElse?: ResponseElse
}

export interface ResponseIf {
  expression: Expression
  rules: ResponseRule[]
}

export interface ResponseElseIf {
  expression: Expression
  rules: ResponseRule[]
}

export interface ResponseElse {
  rules: ResponseRule[]
}

export type ResponseRule = SetOutcomeValue | ResponseCondition | LookupOutcomeValue

export interface SetOutcomeValue {
  type: 'setOutcomeValue'
  identifier: Identifier
  expression: Expression
}

export interface LookupOutcomeValue {
  type: 'lookupOutcomeValue'
  identifier: Identifier
  expression: Expression
}

// -------------------
// Expressions
// -------------------

export type Expression =
  | BaseValue
  | Variable
  | Correct
  | MapResponse
  | MapResponsePoint
  | Match
  | IsNull
  | And
  | Or
  | Not
  | Sum
  | Product
  | Subtract
  | Divide
  | Equal
  | Lt
  | Lte
  | Gt
  | Gte
  | Member
  | Contains
  | Substring
  | StringMatch

export interface BaseValue {
  type: 'baseValue'
  baseType: BaseType
  value: string
}

export interface Variable {
  type: 'variable'
  identifier: Identifier
}

export interface Correct {
  type: 'correct'
  identifier: Identifier
}

export interface MapResponse {
  type: 'mapResponse'
  identifier: Identifier
}

export interface MapResponsePoint {
  type: 'mapResponsePoint'
  identifier: Identifier
}

export interface Match {
  type: 'match'
  expressions: [Expression, Expression]
}

export interface IsNull {
  type: 'isNull'
  expression: Expression
}

export interface And {
  type: 'and'
  expressions: Expression[]
}

export interface Or {
  type: 'or'
  expressions: Expression[]
}

export interface Not {
  type: 'not'
  expression: Expression
}

export interface Sum {
  type: 'sum'
  expressions: Expression[]
}

export interface Product {
  type: 'product'
  expressions: Expression[]
}

export interface Subtract {
  type: 'subtract'
  expressions: [Expression, Expression]
}

export interface Divide {
  type: 'divide'
  expressions: [Expression, Expression]
}

export interface Equal {
  type: 'equal'
  toleranceMode?: 'exact' | 'absolute' | 'relative'
  tolerance?: [number, number]
  expressions: [Expression, Expression]
}

export interface Lt {
  type: 'lt'
  expressions: [Expression, Expression]
}

export interface Lte {
  type: 'lte'
  expressions: [Expression, Expression]
}

export interface Gt {
  type: 'gt'
  expressions: [Expression, Expression]
}

export interface Gte {
  type: 'gte'
  expressions: [Expression, Expression]
}

export interface Member {
  type: 'member'
  expressions: [Expression, Expression]
}

export interface Contains {
  type: 'contains'
  expressions: [Expression, Expression]
}

export interface Substring {
  type: 'substring'
  caseSensitive?: boolean
  expressions: [Expression, Expression]
}

export interface StringMatch {
  type: 'stringMatch'
  caseSensitive?: boolean
  substring?: boolean
  expressions: [Expression, Expression]
}

// -------------------
// Item Body
// -------------------

export interface ItemBody {
  content: string // HTML content with embedded interactions
  interactions: Interaction[]
  feedbackBlocks?: FeedbackBlock[] | undefined
}

export interface ResponseProcessing {
  template?: Uri
  responseConditions?: ResponseCondition[]
}

// -------------------
// Assessment Item
// -------------------

export interface AssessmentItem {
  identifier: Identifier
  title: string
  label?: string
  language?: string
  toolName?: string
  toolVersion?: string
  adaptive?: boolean
  timeDependent?: boolean

  responseDeclarations: ResponseDeclaration[]
  outcomeDeclarations: OutcomeDeclaration[]
  templateDeclarations?: TemplateDeclaration[]

  stylesheet?: Stylesheet[]
  itemBody: ItemBody
  rubricBlocks?: RubricBlock[]

  responseProcessing?: ResponseProcessing
  modalFeedbacks?: ModalFeedback[]
}
