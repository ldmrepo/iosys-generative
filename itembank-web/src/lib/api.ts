/**
 * API Client for ItemBank Backend
 */

import type {
  SearchRequest,
  SearchResponse,
  ItemDetail,
  ApiSearchResponse,
  SearchResultItem,
  ImlContentResponse,
} from '@/types/api'

const API_BASE = '/api'

/**
 * Normalize API response to UI format
 */
function normalizeSearchResponse(raw: ApiSearchResponse): SearchResponse {
  return {
    results: raw.results.map((item): SearchResultItem => {
      // Parse choices - can be string (JSON) or array
      let choices: string[] | undefined
      if (item.metadata.choices) {
        if (typeof item.metadata.choices === 'string') {
          try {
            choices = JSON.parse(item.metadata.choices)
          } catch {
            choices = [item.metadata.choices]
          }
        } else if (Array.isArray(item.metadata.choices)) {
          choices = item.metadata.choices
        }
      }

      return {
        item_id: item.item_id,
        similarity: item.score,
        question_text: item.metadata.question_text,
        category: item.metadata.category,
        difficulty: item.metadata.difficulty,
        question_type: item.metadata.question_type,
        school_level: item.metadata.school_level,
        grade: item.metadata.grade,
        subject: item.metadata.subject,
        has_image: item.metadata.has_image,
        unit_large: item.metadata.unit_large,
        answer_text: item.metadata.answer_text,
        explanation_text: item.metadata.explanation_text,
        choices,
        is_ai_generated: item.metadata.is_ai_generated,
      }
    }),
    query_time_ms: raw.query_time_ms,
    total_count: raw.total_count,
  }
}

class ApiClient {
  private async fetch<T>(
    endpoint: string,
    options?: RequestInit
  ): Promise<T> {
    const url = `${API_BASE}${endpoint}`
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
      throw new Error(error.detail || `HTTP ${response.status}`)
    }

    return response.json()
  }

  /**
   * Natural language search using Qwen3VL model
   */
  async searchText(query: string, topK = 10): Promise<SearchResponse> {
    const raw = await this.fetch<ApiSearchResponse>('/search/text', {
      method: 'POST',
      body: JSON.stringify({
        query_text: query,
        top_k: topK,
        threshold: 0.1,
      } satisfies SearchRequest),
    })
    return normalizeSearchResponse(raw)
  }

  /**
   * Find similar items by item ID
   */
  async searchSimilar(itemId: string, topK = 10): Promise<SearchResponse> {
    const raw = await this.fetch<ApiSearchResponse>('/search/similar', {
      method: 'POST',
      body: JSON.stringify({
        query_text: itemId,
        top_k: topK,
        threshold: 0.1,
        use_model: false,
      } satisfies SearchRequest),
    })
    return normalizeSearchResponse(raw)
  }

  /**
   * Get item details by ID
   */
  async getItem(itemId: string): Promise<ItemDetail> {
    return this.fetch<ItemDetail>(`/search/items/${itemId}`)
  }

  /**
   * Health check
   */
  async health(): Promise<{ status: string }> {
    return this.fetch('/health')
  }

  /**
   * Get raw IML content for an item
   */
  async getItemIml(itemId: string): Promise<ImlContentResponse> {
    return this.fetch<ImlContentResponse>(`/search/items/${itemId}/iml`)
  }

  /**
   * Delete an AI-generated item
   */
  async deleteItem(itemId: string): Promise<{ item_id: string; success: boolean; message: string }> {
    return this.fetch(`/generate/item/${itemId}`, {
      method: 'DELETE',
    })
  }
}

export const api = new ApiClient()
