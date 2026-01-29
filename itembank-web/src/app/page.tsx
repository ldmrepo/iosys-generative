'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { useAppStore } from '@/lib/store'
import { MathText } from '@/components/MathText'
import { QtiItemViewer } from '@/components/QtiItemViewer'
import type { SearchResultItem } from '@/types/api'

export default function HomePage() {
  const [inputValue, setInputValue] = useState('')
  const {
    selectedItem,
    setSelectedItem,
    searchQuery,
    setSearchQuery,
    addToHistory
  } = useAppStore()

  // Search query
  const { data: searchResults, isLoading: isSearching } = useQuery({
    queryKey: ['search', searchQuery],
    queryFn: () => api.searchText(searchQuery, 20),
    enabled: searchQuery.length > 0,
  })

  // Similar items query
  const { data: similarResults, isLoading: isSimilarLoading } = useQuery({
    queryKey: ['similar', selectedItem?.item_id],
    queryFn: () => api.searchSimilar(selectedItem!.item_id, 10),
    enabled: !!selectedItem,
  })

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (inputValue.trim()) {
      setSearchQuery(inputValue.trim())
      addToHistory(inputValue.trim())
    }
  }

  const handleItemClick = (item: SearchResultItem) => {
    if (selectedItem?.item_id === item.item_id) {
      setSelectedItem(null)
    } else {
      setSelectedItem(item)
    }
  }

  return (
    <div className="flex flex-col h-screen">
      {/* Header with Search */}
      <header className="bg-white border-b px-4 py-3 shadow-sm">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-xl font-bold text-gray-900 mb-3">IOSYS 문항은행</h1>
          <form onSubmit={handleSearch} className="flex gap-2">
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="자연어로 문항을 검색하세요 (예: 삼각형의 넓이를 구하는 문제)"
              className="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              type="submit"
              disabled={isSearching}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              {isSearching ? '검색 중...' : '검색'}
            </button>
          </form>
          {searchResults && (
            <p className="mt-2 text-sm text-gray-500">
              {searchResults.total_count}개 결과 ({searchResults.query_time_ms.toFixed(1)}ms)
            </p>
          )}
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 overflow-hidden">
        <div className={`h-full flex ${selectedItem ? 'divide-x' : ''}`}>
          {/* Search Results */}
          <div className={`${selectedItem ? 'w-1/2' : 'w-full'} overflow-y-auto p-4 transition-all`}>
            {!searchQuery ? (
              <div className="flex items-center justify-center h-full text-gray-400">
                <p>검색어를 입력하세요</p>
              </div>
            ) : isSearching ? (
              <div className="flex items-center justify-center h-full">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
              </div>
            ) : searchResults?.results.length === 0 ? (
              <div className="flex items-center justify-center h-full text-gray-400">
                <p>검색 결과가 없습니다</p>
              </div>
            ) : (
              <div className="space-y-3">
                <h2 className="font-semibold text-gray-700 sticky top-0 bg-gray-50 py-2">
                  검색 결과
                </h2>
                {searchResults?.results.map((item) => (
                  <ItemCard
                    key={item.item_id}
                    item={item}
                    isSelected={selectedItem?.item_id === item.item_id}
                    onClick={() => handleItemClick(item)}
                  />
                ))}
              </div>
            )}
          </div>

          {/* Selected Item Detail & Similar Items Panel */}
          {selectedItem && (
            <div className="w-1/2 overflow-y-auto p-4 bg-gray-100">
              <div className="flex items-center justify-between mb-3 sticky top-0 bg-gray-100 py-2 z-10">
                <h2 className="font-semibold text-gray-700">문항 상세</h2>
                <button
                  onClick={() => setSelectedItem(null)}
                  className="text-gray-400 hover:text-gray-600 text-xl leading-none"
                >
                  ✕
                </button>
              </div>

              {/* Selected Item Full View */}
              <ItemDetailView item={selectedItem} />

              {/* Similar Items */}
              <div className="mt-6">
                <h3 className="font-semibold text-gray-700 mb-3">유사 문항</h3>
                {isSimilarLoading ? (
                  <div className="flex items-center justify-center h-32">
                    <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600" />
                  </div>
                ) : similarResults?.results.length === 0 ? (
                  <p className="text-gray-400 text-center py-8">유사 문항이 없습니다</p>
                ) : (
                  <div className="space-y-3">
                    {similarResults?.results
                      .filter((item) => item.item_id !== selectedItem.item_id)
                      .map((item) => (
                        <ItemCard
                          key={item.item_id}
                          item={item}
                          isSelected={false}
                          onClick={() => setSelectedItem(item)}
                          compact
                        />
                      ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}

// Item Detail View Component
function ItemDetailView({ item }: { item: SearchResultItem }) {
  const [showAnswer, setShowAnswer] = useState(false)

  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
      {/* Header with metadata */}
      <div className="px-4 py-3 border-b bg-gray-50 rounded-t-lg">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-mono text-gray-500">{item.item_id}</span>
          <span className={`
            text-xs px-2 py-0.5 rounded-full
            ${item.similarity >= 0.8 ? 'bg-green-100 text-green-700' :
              item.similarity >= 0.6 ? 'bg-yellow-100 text-yellow-700' :
              'bg-gray-100 text-gray-600'}
          `}>
            유사도 {(item.similarity * 100).toFixed(1)}%
          </span>
        </div>
        <div className="flex flex-wrap gap-1">
          {item.subject && (
            <span className="text-xs px-2 py-0.5 bg-blue-100 text-blue-700 rounded">
              {item.subject}
            </span>
          )}
          {item.grade && (
            <span className="text-xs px-2 py-0.5 bg-blue-100 text-blue-700 rounded">
              {item.grade}
            </span>
          )}
          {item.difficulty && (
            <span className={`text-xs px-2 py-0.5 rounded
              ${item.difficulty === '상' ? 'bg-red-100 text-red-700' :
                item.difficulty === '중' ? 'bg-yellow-100 text-yellow-700' :
                'bg-green-100 text-green-700'}
            `}>
              난이도: {item.difficulty}
            </span>
          )}
          {item.question_type && (
            <span className="text-xs px-2 py-0.5 bg-purple-100 text-purple-700 rounded">
              {item.question_type}
            </span>
          )}
          {item.unit_large && (
            <span className="text-xs px-2 py-0.5 bg-gray-100 text-gray-600 rounded">
              {item.unit_large}
            </span>
          )}
        </div>
      </div>

      {/* QTI Viewer - Full item rendering */}
      <div className="p-4">
        <QtiItemViewer
          itemId={item.item_id}
          showAnswer={showAnswer}
          showExplanation={showAnswer}
        />
      </div>

      {/* Answer & Explanation Toggle */}
      <div className="border-t">
        <button
          onClick={() => setShowAnswer(!showAnswer)}
          className="w-full px-4 py-2 text-sm text-blue-600 hover:bg-blue-50 flex items-center justify-center gap-1"
        >
          {showAnswer ? '정답/해설 숨기기' : '정답/해설 보기'}
          <span className="text-xs">{showAnswer ? '▲' : '▼'}</span>
        </button>
      </div>
    </div>
  )
}

// Item Card Component - Full content view
function ItemCard({
  item,
  isSelected,
  onClick,
  compact = false,
}: {
  item: SearchResultItem
  isSelected: boolean
  onClick: () => void
  compact?: boolean
}) {
  return (
    <div
      onClick={onClick}
      className={`
        rounded-lg border cursor-pointer transition-all overflow-hidden
        ${isSelected
          ? 'border-blue-500 ring-2 ring-blue-200'
          : 'border-gray-200 bg-white hover:border-gray-300 hover:shadow-sm'
        }
      `}
    >
      {/* Header with metadata */}
      <div className={`px-3 py-2 border-b ${isSelected ? 'bg-blue-50' : 'bg-gray-50'}`}>
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs font-mono text-gray-400">
            {item.item_id.slice(0, 8)}...
          </span>
          <span className={`
            text-xs px-2 py-0.5 rounded-full
            ${item.similarity >= 0.8 ? 'bg-green-100 text-green-700' :
              item.similarity >= 0.6 ? 'bg-yellow-100 text-yellow-700' :
              'bg-gray-100 text-gray-600'}
          `}>
            {(item.similarity * 100).toFixed(1)}%
          </span>
        </div>
        <div className="flex flex-wrap gap-1">
          {item.subject && (
            <span className="text-xs px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded">
              {item.subject}
            </span>
          )}
          {item.grade && (
            <span className="text-xs px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded">
              {item.grade}
            </span>
          )}
          {item.difficulty && (
            <span className={`text-xs px-1.5 py-0.5 rounded
              ${item.difficulty === '상' ? 'bg-red-100 text-red-700' :
                item.difficulty === '중' ? 'bg-yellow-100 text-yellow-700' :
                'bg-green-100 text-green-700'}
            `}>
              {item.difficulty}
            </span>
          )}
          {item.question_type && (
            <span className="text-xs px-1.5 py-0.5 bg-purple-100 text-purple-700 rounded">
              {item.question_type}
            </span>
          )}
          {item.has_image && (
            <span className="text-xs px-1.5 py-0.5 bg-orange-100 text-orange-700 rounded">
              이미지
            </span>
          )}
        </div>
      </div>

      {/* Content */}
      <div className={`p-3 ${isSelected ? 'bg-blue-50/50' : 'bg-white'} ${compact ? 'text-sm' : ''}`}>
        {/* Question */}
        <div className="mb-3">
          <h4 className="text-xs font-semibold text-gray-500 mb-1">물음</h4>
          <div className={`text-gray-800 leading-relaxed ${compact ? 'line-clamp-3' : ''}`}>
            {item.question_text ? (
              <MathText text={item.question_text} />
            ) : (
              <span className="text-gray-400">(문항 내용 없음)</span>
            )}
          </div>
        </div>

        {/* Choices (for 선택형) */}
        {item.choices && item.choices.length > 0 && !compact && (
          <div className="mb-3">
            <h4 className="text-xs font-semibold text-blue-600 mb-1">선택지</h4>
            <ol className="list-none space-y-1 text-sm text-gray-700">
              {item.choices.map((choice, idx) => (
                <li key={idx} className="flex gap-2">
                  <span className="text-gray-400 w-5 flex-shrink-0">{'①②③④⑤⑥⑦⑧⑨⑩'[idx] || (idx + 1)}</span>
                  <MathText text={choice} />
                </li>
              ))}
            </ol>
          </div>
        )}

        {/* Answer */}
        {item.answer_text && !compact && (
          <div className="mb-3">
            <h4 className="text-xs font-semibold text-green-600 mb-1">정답</h4>
            <div className="p-2 bg-green-50 rounded text-gray-800 text-sm">
              <MathText text={item.answer_text} />
            </div>
          </div>
        )}

        {/* Explanation */}
        {item.explanation_text && !compact && (
          <div>
            <h4 className="text-xs font-semibold text-amber-600 mb-1">해설</h4>
            <div className="p-2 bg-amber-50 rounded text-gray-800 text-sm leading-relaxed">
              <MathText text={item.explanation_text} />
            </div>
          </div>
        )}

        {/* Compact mode: show indicator if has answer/explanation/choices */}
        {compact && (item.answer_text || item.explanation_text || item.choices) && (
          <div className="text-xs text-gray-400 mt-2">
            {item.choices && `${item.choices.length}지선다 `}
            {item.answer_text && '| 정답 '}
            {item.explanation_text && '| 해설'}
          </div>
        )}
      </div>
    </div>
  )
}
