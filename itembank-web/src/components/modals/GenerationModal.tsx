'use client'

import { useState } from 'react'
import dynamic from 'next/dynamic'
import { motion } from 'framer-motion'
import { GenerateIcon, CloseIcon } from '@/components/icons'
import { DifficultyBadge, AIBadge } from '@/components/badges'
import type { SearchResultItem } from '@/types/api'
import type { AssessmentItem } from '@iosys/qti-core'

const QtiItemViewer = dynamic(
  () => import('@/components/QtiItemViewer').then(mod => mod.QtiItemViewer),
  { ssr: false }
)

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

// Generated Item type matching API response (QTI format)
export interface GeneratedItem {
  temp_id: string
  assessment_item: AssessmentItem
  variation_note: string
  metadata: {
    source_item_id: string
    variation_type: string
    is_ai_generated: boolean
    generation_model: string
    generation_timestamp: string
    confidence_score: number
    used_vision_api: boolean
  }
}

interface GenerateSimilarResponse {
  generated_items: GeneratedItem[]
  generation_time_ms: number
  model: string
  tokens_used: number | null
}

interface SaveGeneratedItemsResponse {
  saved_items: Array<{
    temp_id: string
    item_id: string
    ai_metadata_id: string
    success: boolean
    error: string | null
  }>
  total_saved: number
  total_failed: number
}

interface GenerationModalProps {
  sourceItem: SearchResultItem
  onClose: () => void
  onSaveSuccess?: () => void | Promise<void>
}

export function GenerationModal({ sourceItem, onClose, onSaveSuccess }: GenerationModalProps) {
  const [generateCount, setGenerateCount] = useState(3)
  const [variationType, setVariationType] = useState('mixed')
  const [additionalPrompt, setAdditionalPrompt] = useState('')
  const [isGenerating, setIsGenerating] = useState(false)
  const [generatedItems, setGeneratedItems] = useState<GeneratedItem[]>([])
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [generationStats, setGenerationStats] = useState<{
    time_ms: number
    model: string
    tokens: number | null
  } | null>(null)

  const handleGenerate = async () => {
    setIsGenerating(true)
    setGeneratedItems([])
    setSelectedIds(new Set())
    setError(null)
    setGenerationStats(null)

    try {
      const response = await fetch(`${API_BASE_URL}/generate/similar`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          source_item_id: sourceItem.item_id,
          count: generateCount,
          options: {
            variation_type: variationType,
            additional_prompt: additionalPrompt,
          },
        }),
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }))
        throw new Error(errorData.detail || `HTTP ${response.status}`)
      }

      const data: GenerateSimilarResponse = await response.json()
      setGeneratedItems(data.generated_items)
      setGenerationStats({
        time_ms: data.generation_time_ms,
        model: data.model,
        tokens: data.tokens_used,
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Generation failed')
    } finally {
      setIsGenerating(false)
    }
  }

  const handleToggleSelect = (id: string) => {
    const newSelected = new Set(selectedIds)
    if (newSelected.has(id)) {
      newSelected.delete(id)
    } else {
      newSelected.add(id)
    }
    setSelectedIds(newSelected)
  }

  const handleSelectAll = () => {
    if (selectedIds.size === generatedItems.length) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(generatedItems.map(item => item.temp_id)))
    }
  }

  // Helper to extract flat data from QTI AssessmentItem
  const extractFromQti = (item: GeneratedItem) => {
    const ai = item.assessment_item
    const itemBody = ai.itemBody || {}
    const interactions = itemBody.interactions || []
    const feedbackBlocks = itemBody.feedbackBlocks || []
    const responseDecl = (ai.responseDeclarations || [])[0]
    const correctValues = responseDecl?.correctResponse?.values || []

    // Get question text (strip HTML tags for plain text)
    const questionText = (itemBody.content || '').replace(/<[^>]*>/g, ' ').trim()

    // Get choices from interaction
    const choiceInteraction = interactions.find((i: { type?: string }) => i.type === 'choiceInteraction')
    const simpleChoices = choiceInteraction?.simpleChoices || []
    const choices = simpleChoices.map((c: { content?: string }) =>
      (c.content || '').replace(/<[^>]*>/g, ' ').trim()
    )

    // Get answer text from correct response
    const correctId = correctValues[0] || ''
    const correctChoice = simpleChoices.find((c: { identifier?: string }) => c.identifier === correctId)
    const answerText = correctChoice
      ? (correctChoice.content || '').replace(/<[^>]*>/g, ' ').trim()
      : ''

    // Get explanation from feedback
    const explanationText = feedbackBlocks[0]?.content
      ? feedbackBlocks[0].content.replace(/<[^>]*>/g, ' ').trim()
      : ''

    return { questionText, choices, answerText, explanationText }
  }

  const handleSave = async () => {
    if (selectedIds.size === 0) return

    setIsSaving(true)
    setError(null)

    try {
      const itemsToSave = generatedItems
        .filter(item => selectedIds.has(item.temp_id))
        .map(item => {
          const { questionText, choices, answerText, explanationText } = extractFromQti(item)
          return {
            temp_id: item.temp_id,
            question_text: questionText,
            choices: choices,
            answer_text: answerText,
            explanation_text: explanationText,
            source_item_id: item.metadata.source_item_id,
            variation_type: item.metadata.variation_type,
            generation_model: item.metadata.generation_model,
            confidence_score: item.metadata.confidence_score,
            additional_prompt: additionalPrompt,
          }
        })

      const response = await fetch(`${API_BASE_URL}/generate/save`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ items: itemsToSave }),
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }))
        throw new Error(errorData.detail || `HTTP ${response.status}`)
      }

      const data: SaveGeneratedItemsResponse = await response.json()

      if (data.total_failed > 0) {
        const failedItems = data.saved_items.filter(item => !item.success)
        const errorMessages = failedItems.map(item => item.error).join(', ')
        alert(`${data.total_saved}개 저장됨, ${data.total_failed}개 실패\n실패 원인: ${errorMessages}`)
      } else {
        alert(`${data.total_saved}개의 문항이 저장되었습니다.\n\n원본 문항(${sourceItem.item_id})의 유사 문항 목록에서 확인할 수 있습니다.`)
      }

      // Trigger refresh before closing - wait a bit to ensure database is updated
      await new Promise(resolve => setTimeout(resolve, 500))
      if (onSaveSuccess) {
        await onSaveSuccess()
      }
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed')
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.95, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.95, opacity: 0 }}
        transition={{ duration: 0.2 }}
        className="w-[90vw] h-[85vh] bg-white flex flex-col overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="shrink-0 px-4 py-3 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <GenerateIcon />
            <h2 className="text-base font-semibold text-slate-800">유사문제 생성</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-200 transition-fast"
          >
            <CloseIcon />
          </button>
        </div>

        {/* Content: 1:3 split */}
        <div className="flex-1 flex overflow-hidden">
          {/* Left: Source Item (1/4) */}
          <div className="w-1/4 min-w-[300px] border-r border-slate-200 overflow-y-auto bg-slate-50">
            <div className="p-4">
              <h3 className="text-sm font-medium text-slate-600 mb-3">원본 문항</h3>
              <div className="border border-slate-300 bg-white overflow-hidden">
                <div className="px-3 py-2 border-b border-slate-200 bg-slate-100">
                  <div className="flex flex-wrap items-center gap-1">
                    {sourceItem.subject && <span className="badge badge-primary">{sourceItem.subject}</span>}
                    {sourceItem.grade && <span className="badge badge-primary">{sourceItem.grade}</span>}
                    {sourceItem.difficulty && <DifficultyBadge difficulty={sourceItem.difficulty} />}
                    {sourceItem.question_type && <span className="badge badge-neutral">{sourceItem.question_type}</span>}
                  </div>
                </div>
                <div className="p-3">
                  <QtiItemViewer
                    itemId={sourceItem.item_id}
                    showAnswer={true}
                    showExplanation={false}
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Right: Generation Area (3/4) */}
          <div className="flex-1 flex flex-col overflow-hidden">
            {/* Generation Controls */}
            <div className="shrink-0 px-4 py-3 border-b border-slate-200 bg-white">
              <div className="flex items-end gap-4">
                {/* Count selector */}
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">생성 개수</label>
                  <select
                    value={generateCount}
                    onChange={(e) => setGenerateCount(Number(e.target.value))}
                    className="px-3 py-2 text-sm border border-slate-300 bg-white focus:outline-none focus:border-primary-500"
                    disabled={isGenerating}
                  >
                    {[1, 2, 3, 4, 5, 6].map(n => (
                      <option key={n} value={n}>{n}개</option>
                    ))}
                  </select>
                </div>

                {/* Variation type selector */}
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">변형 유형</label>
                  <select
                    value={variationType}
                    onChange={(e) => setVariationType(e.target.value)}
                    className="px-3 py-2 text-sm border border-slate-300 bg-white focus:outline-none focus:border-primary-500"
                    disabled={isGenerating}
                  >
                    <option value="mixed">복합 변형</option>
                    <option value="numeric">숫자 변형</option>
                    <option value="context">맥락 변형</option>
                    <option value="structure">구조 변형</option>
                    <option value="auto">자동 선택</option>
                  </select>
                </div>

                {/* Additional prompt */}
                <div className="flex-1">
                  <label className="block text-xs font-medium text-slate-600 mb-1">추가 프롬프트 (선택)</label>
                  <input
                    type="text"
                    value={additionalPrompt}
                    onChange={(e) => setAdditionalPrompt(e.target.value)}
                    placeholder="예: 난이도를 높여서, 숫자만 변경해서..."
                    className="w-full px-3 py-2 text-sm border border-slate-300 focus:outline-none focus:border-primary-500"
                    disabled={isGenerating}
                  />
                </div>

                {/* Generate button */}
                <button
                  onClick={handleGenerate}
                  disabled={isGenerating}
                  className="btn btn-primary px-6 py-2 text-sm flex items-center gap-2 disabled:opacity-50"
                >
                  {isGenerating ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      생성 중...
                    </>
                  ) : (
                    <>
                      <GenerateIcon />
                      생성하기
                    </>
                  )}
                </button>
              </div>

              {/* Error message */}
              {error && (
                <div className="mt-2 p-2 bg-red-50 border border-red-200 text-red-700 text-sm">
                  {error}
                </div>
              )}

              {/* Generation stats */}
              {generationStats && (
                <div className="mt-2 text-xs text-slate-500">
                  모델: {generationStats.model} |
                  생성 시간: {(generationStats.time_ms / 1000).toFixed(1)}초
                  {generationStats.tokens && ` | 토큰: ${generationStats.tokens}`}
                </div>
              )}
            </div>

            {/* Generated Items Area */}
            <div className="flex-1 overflow-y-auto p-4 bg-slate-50">
              {isGenerating ? (
                <div className="flex flex-col items-center justify-center h-full">
                  <div className="w-12 h-12 border-3 border-slate-200 border-t-primary-600 rounded-full animate-spin mb-4" />
                  <p className="text-sm text-slate-500">AI가 유사문제를 생성하고 있습니다...</p>
                  <p className="text-xs text-slate-400 mt-1">잠시만 기다려주세요</p>
                </div>
              ) : generatedItems.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-slate-400">
                  <GenerateIcon />
                  <p className="text-sm mt-2">생성된 문항이 없습니다</p>
                  <p className="text-xs mt-1">위에서 생성 버튼을 클릭하세요</p>
                </div>
              ) : (
                <>
                  {/* Select all */}
                  <div className="flex items-center justify-between mb-3">
                    <label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={selectedIds.size === generatedItems.length}
                        onChange={handleSelectAll}
                        className="w-4 h-4 accent-primary-600"
                      />
                      전체 선택 ({selectedIds.size}/{generatedItems.length})
                    </label>
                  </div>

                  {/* Generated items grid - max 2 columns */}
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
                    {generatedItems.map((item, index) => (
                      <motion.div
                        key={item.temp_id}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: index * 0.1 }}
                        className={`
                          border bg-white overflow-hidden cursor-pointer transition-fast
                          ${selectedIds.has(item.temp_id)
                            ? 'border-primary-500 ring-2 ring-primary-200'
                            : 'border-slate-200 hover:border-primary-300'
                          }
                        `}
                        onClick={() => handleToggleSelect(item.temp_id)}
                      >
                        <div className="px-3 py-2 border-b border-slate-100 bg-slate-50 flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <input
                              type="checkbox"
                              checked={selectedIds.has(item.temp_id)}
                              onChange={() => handleToggleSelect(item.temp_id)}
                              className="w-4 h-4 accent-primary-600"
                              onClick={(e) => e.stopPropagation()}
                            />
                            <span className="text-sm font-medium text-slate-700">생성 문항 {index + 1}</span>
                            <AIBadge />
                          </div>
                          <span className="text-xs text-slate-400">
                            신뢰도: {(item.metadata.confidence_score * 100).toFixed(0)}%
                          </span>
                        </div>
                        <div className="p-3">
                          <QtiItemViewer
                            item={item.assessment_item}
                            showAnswer={true}
                            showExplanation={true}
                          />
                          {item.variation_note && (
                            <p className="text-xs text-primary-600 mt-2 pt-2 border-t border-slate-100">
                              변형: {item.variation_note}
                            </p>
                          )}
                        </div>
                      </motion.div>
                    ))}
                  </div>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="shrink-0 px-4 py-3 border-t border-slate-200 bg-slate-50 flex items-center justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-200 transition-fast"
            disabled={isSaving}
          >
            취소
          </button>
          <button
            onClick={handleSave}
            disabled={selectedIds.size === 0 || isSaving}
            className="btn btn-primary px-6 py-2 text-sm flex items-center gap-2 disabled:opacity-50"
          >
            {isSaving ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                저장 중...
              </>
            ) : (
              <>
                선택 문항 추가 ({selectedIds.size})
              </>
            )}
          </button>
        </div>
      </motion.div>
    </motion.div>
  )
}
