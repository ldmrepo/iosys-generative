'use client'

import { useState } from 'react'
import dynamic from 'next/dynamic'
import { GenerateIcon, ChevronUpIcon, ChevronDownIcon, TrashIcon } from '@/components/icons'
import { SimilarityBadge, DifficultyBadge, AIBadge } from '@/components/badges'
import { LazyQtiItemViewer } from '@/components/LazyQtiItemViewer'
import type { SearchResultItem } from '@/types/api'

const QtiItemViewer = dynamic(
  () => import('@/components/QtiItemViewer').then(mod => mod.QtiItemViewer),
  { ssr: false }
)

// Search Result Card Component (for grid view)
export function SearchResultCard({
  item,
  onClick,
  onGenerate,
  onDelete,
}: {
  item: SearchResultItem
  onClick: () => void
  onGenerate: (e: React.MouseEvent) => void
  onDelete?: (e: React.MouseEvent) => void
}) {
  return (
    <div
      onClick={onClick}
      className="relative border border-slate-200 bg-white hover:border-primary-400 hover:bg-slate-50 overflow-hidden transition-fast cursor-pointer h-full flex flex-col"
    >
      {/* Header */}
      <div className="px-3 py-1.5 border-b border-slate-100 bg-slate-50 flex items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-1">
          {item.subject && <span className="badge badge-primary">{item.subject}</span>}
          {item.grade && <span className="badge badge-primary">{item.grade}</span>}
          {item.difficulty && <DifficultyBadge difficulty={item.difficulty} />}
          {item.question_type && <span className="badge badge-neutral">{item.question_type}</span>}
          {item.has_image && <span className="badge badge-warning">이미지</span>}
        </div>
        <div className="flex items-center gap-1.5">
          <SimilarityBadge similarity={item.similarity} />
          <button
            onClick={onGenerate}
            className="p-1 text-slate-400 hover:text-amber-600 hover:bg-amber-50 transition-fast"
            title="유사문제 생성"
          >
            <GenerateIcon />
          </button>
          {item.is_ai_generated && onDelete && (
            <button
              onClick={onDelete}
              className="p-1 text-slate-400 hover:text-red-600 hover:bg-red-50 transition-fast"
              title="삭제"
            >
              <TrashIcon />
            </button>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="p-3 flex-1 overflow-hidden">
        <LazyQtiItemViewer itemId={item.item_id} />
      </div>

      {/* AI Badge - Bottom Right Overlay */}
      {item.is_ai_generated && (
        <div className="absolute bottom-2 right-2">
          <AIBadge />
        </div>
      )}
    </div>
  )
}

// Similar Item Card Component (compact for grid view)
export function SimilarItemCard({
  item,
  onClick,
  onGenerate,
  onDelete,
}: {
  item: SearchResultItem
  onClick: () => void
  onGenerate: (e: React.MouseEvent) => void
  onDelete?: (e: React.MouseEvent) => void
}) {
  return (
    <div
      onClick={onClick}
      className="relative border border-slate-200 bg-white hover:border-primary-400 hover:bg-slate-50 overflow-hidden transition-fast cursor-pointer h-full flex flex-col"
    >
      {/* Header - Compact */}
      <div className="px-2 py-1.5 border-b border-slate-100 bg-slate-50 flex items-center justify-between gap-1">
        <div className="flex flex-wrap items-center gap-1">
          {item.subject && <span className="badge badge-primary text-[10px] px-1.5 py-0.5">{item.subject}</span>}
          {item.difficulty && <DifficultyBadge difficulty={item.difficulty} />}
        </div>
        <div className="flex items-center gap-1.5">
          <SimilarityBadge similarity={item.similarity} />
          <button
            onClick={onGenerate}
            className="p-1 text-slate-400 hover:text-amber-600 hover:bg-amber-50 transition-fast"
            title="유사문제 생성"
          >
            <GenerateIcon />
          </button>
          {item.is_ai_generated && onDelete && (
            <button
              onClick={onDelete}
              className="p-1 text-slate-400 hover:text-red-600 hover:bg-red-50 transition-fast"
              title="삭제"
            >
              <TrashIcon />
            </button>
          )}
        </div>
      </div>

      {/* Content - Fixed height with overflow */}
      <div className="p-2 flex-1 overflow-hidden">
        <div className="text-sm line-clamp-6">
          <LazyQtiItemViewer itemId={item.item_id} forceLoad />
        </div>
      </div>

      {/* AI Badge - Bottom Right Overlay */}
      {item.is_ai_generated && (
        <div className="absolute bottom-2 right-2">
          <AIBadge />
        </div>
      )}
    </div>
  )
}

// Selected Item Card with Answer Toggle
export function SelectedItemCard({
  item,
  onGenerate,
  onDelete,
}: {
  item: SearchResultItem
  onGenerate: (e: React.MouseEvent) => void
  onDelete?: (e: React.MouseEvent) => void
}) {
  const [showAnswer, setShowAnswer] = useState(false)

  return (
    <div className="relative border border-primary-300 bg-primary-50/30 overflow-hidden">
      {/* Header */}
      <div className="px-3 py-2 border-b border-primary-200 bg-primary-50">
        <div className="flex flex-wrap items-center gap-1">
          {item.subject && <span className="badge badge-primary">{item.subject}</span>}
          {item.grade && <span className="badge badge-primary">{item.grade}</span>}
          {item.difficulty && <DifficultyBadge difficulty={item.difficulty} />}
          {item.question_type && <span className="badge badge-neutral">{item.question_type}</span>}
        </div>
      </div>

      {/* Content */}
      <div className="p-3">
        <QtiItemViewer
          itemId={item.item_id}
          showAnswer={showAnswer}
          showExplanation={showAnswer}
        />
      </div>

      {/* Actions */}
      <div className="border-t border-primary-200 flex">
        <button
          onClick={() => setShowAnswer(!showAnswer)}
          className="flex-1 px-3 py-2 text-sm font-medium text-primary-600 hover:bg-primary-50 flex items-center justify-center gap-1.5 transition-fast cursor-pointer"
        >
          {showAnswer ? '정답/해설 숨기기' : '정답/해설 보기'}
          {showAnswer ? <ChevronUpIcon /> : <ChevronDownIcon />}
        </button>
        <div className="w-px bg-primary-200" />
        <button
          onClick={onGenerate}
          className="px-3 py-2 text-sm font-medium text-amber-600 hover:bg-amber-50 flex items-center justify-center gap-1.5 transition-fast cursor-pointer"
        >
          <GenerateIcon />
          <span>유사문제 생성</span>
        </button>
        {item.is_ai_generated && onDelete && (
          <>
            <div className="w-px bg-primary-200" />
            <button
              onClick={onDelete}
              className="px-3 py-2 text-sm font-medium text-red-600 hover:bg-red-50 flex items-center justify-center gap-1.5 transition-fast cursor-pointer"
            >
              <TrashIcon />
              <span>삭제</span>
            </button>
          </>
        )}
      </div>

      {/* AI Badge - Bottom Right Overlay */}
      {item.is_ai_generated && (
        <div className="absolute bottom-12 right-2">
          <AIBadge />
        </div>
      )}
    </div>
  )
}

// Item Card Component (unused but kept for reference)
export function ItemCard({
  item,
  isSelected,
  onClick,
}: {
  item: SearchResultItem
  isSelected: boolean
  onClick: () => void
}) {
  return (
    <div
      onClick={onClick}
      className={`
        border overflow-hidden transition-fast cursor-pointer
        ${isSelected
          ? 'border-primary-500 bg-primary-50/30'
          : 'border-slate-200 bg-white hover:border-primary-400 hover:bg-slate-50'
        }
      `}
    >
      {/* Header - Compact */}
      <div className={`px-3 py-1.5 border-b flex items-center justify-between gap-2 ${isSelected ? 'border-primary-200 bg-primary-50' : 'border-slate-100 bg-slate-50'}`}>
        <div className="flex flex-wrap items-center gap-1">
          {item.is_ai_generated && <AIBadge />}
          {item.subject && <span className="badge badge-primary">{item.subject}</span>}
          {item.grade && <span className="badge badge-primary">{item.grade}</span>}
          {item.difficulty && <DifficultyBadge difficulty={item.difficulty} />}
          {item.question_type && <span className="badge badge-neutral">{item.question_type}</span>}
          {item.has_image && <span className="badge badge-warning">이미지</span>}
        </div>
        <SimilarityBadge similarity={item.similarity} />
      </div>

      {/* Content */}
      <div className="p-3">
        <LazyQtiItemViewer itemId={item.item_id} />
      </div>
    </div>
  )
}
