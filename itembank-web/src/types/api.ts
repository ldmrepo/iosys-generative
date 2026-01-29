/**
 * API Types for ItemBank
 */

// Search Request
export interface SearchRequest {
  query_text: string
  query_image?: string
  top_k?: number
  threshold?: number
  use_model?: boolean
}

// Raw API response item
export interface ApiSearchResultItem {
  item_id: string
  score: number
  metadata: {
    id: string
    question_text?: string
    category?: string
    difficulty?: string
    question_type?: string
    school_level?: string
    grade?: string
    subject?: string
    subject_detail?: string
    has_image?: boolean
    answer_text?: string
    explanation_text?: string
    unit_large?: string
    unit_medium?: string
    unit_small?: string
    curriculum?: string
    semester?: string
    keywords?: string
    year?: number
    choices?: string[] | string | null
    is_ai_generated?: boolean
    ai_metadata_id?: string
    question_images?: string[] | string | null
    source_file?: string
  }
}

// Normalized search result item (for UI)
export interface SearchResultItem {
  item_id: string
  similarity: number
  question_text?: string
  category?: string
  difficulty?: string
  question_type?: string
  school_level?: string
  grade?: string
  subject?: string
  has_image?: boolean
  unit_large?: string
  answer_text?: string
  explanation_text?: string
  choices?: string[]
  is_ai_generated?: boolean
  question_images?: string[] | string
}

// Raw API response
export interface ApiSearchResponse {
  results: ApiSearchResultItem[]
  query_time_ms: number
  total_count: number
}

// Normalized search response (for UI)
export interface SearchResponse {
  results: SearchResultItem[]
  query_time_ms: number
  total_count: number
}

// Item Detail
export interface ItemDetail {
  item_id: string
  category: string
  difficulty: string
  question_type: string
  question_text: string
  answer_text?: string
  explanation_text?: string
  has_image: boolean
  question_images?: string[]
  metadata: {
    curriculum?: string
    school_level?: string
    grade?: string
    subject?: string
    keywords?: string[]
  }
}

// API Error
export interface ApiError {
  detail: string
}

// IML Content Response
export interface ImlContentResponse {
  item_id: string
  iml_content: string
  source_file: string
}
