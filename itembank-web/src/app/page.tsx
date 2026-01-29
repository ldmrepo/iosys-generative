'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { api } from '@/lib/api'
import { useAppStore } from '@/lib/store'
import type { SearchResultItem } from '@/types/api'

// Components
import { SearchIcon, SparklesIcon, ChevronLeftIcon } from '@/components/icons'
import { EmptyState, LoadingState, NoResultsState, SimilarItemsLoadingSkeleton } from '@/components/StateViews'
import { SearchResultCard, SimilarItemCard, SelectedItemCard } from '@/components/cards'
import { GenerationModal } from '@/components/modals/GenerationModal'

export default function HomePage() {
  const [inputValue, setInputValue] = useState('')
  const [isHydrated, setIsHydrated] = useState(false)
  const hasInitializedRef = useRef(false)
  const urlInitializedRef = useRef(false)
  const searchParams = useSearchParams()
  const router = useRouter()
  const {
    selectedItem,
    setSelectedItem,
    searchQuery,
    setSearchQuery,
    addToHistory
  } = useAppStore()

  // Generation modal state
  const [generationModalOpen, setGenerationModalOpen] = useState(false)
  const [generationSourceItem, setGenerationSourceItem] = useState<SearchResultItem | null>(null)
  const queryClient = useQueryClient()

  // Update URL when selectedItem changes
  const updateUrl = useCallback((itemId: string | null) => {
    const params = new URLSearchParams(searchParams.toString())
    if (itemId) {
      params.set('selected', itemId)
    } else {
      params.delete('selected')
    }
    const newUrl = params.toString() ? `?${params.toString()}` : '/'
    router.replace(newUrl, { scroll: false })
  }, [searchParams, router])

  // Restore selected item from URL on page load
  useEffect(() => {
    if (urlInitializedRef.current) return
    const selectedId = searchParams.get('selected')
    if (selectedId && !selectedItem) {
      api.getItem(selectedId).then((item) => {
        if (item) {
          setSelectedItem({
            item_id: item.item_id,
            similarity: 1.0,
            subject: item.metadata?.subject,
            grade: item.metadata?.grade,
            difficulty: item.difficulty,
            question_type: item.question_type,
            has_image: item.has_image,
          })
        }
        urlInitializedRef.current = true
      }).catch(() => {
        urlInitializedRef.current = true
        updateUrl(null)
      })
    } else {
      urlInitializedRef.current = true
    }
  }, [searchParams, selectedItem, setSelectedItem, updateUrl])

  // Sync URL when selectedItem changes (after initialization)
  useEffect(() => {
    if (!urlInitializedRef.current) return
    updateUrl(selectedItem?.item_id ?? null)
  }, [selectedItem, updateUrl])

  // Hydrate input value from persisted searchQuery
  useEffect(() => {
    if (!hasInitializedRef.current && searchQuery) {
      setInputValue(searchQuery)
      hasInitializedRef.current = true
    }
    setIsHydrated(true)
  }, [searchQuery])

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
      setSelectedItem(null)
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

  const handleSimilarItemClick = (item: SearchResultItem) => {
    setSelectedItem(item)
  }

  const handleGenerateSimilar = (item: SearchResultItem, e: React.MouseEvent) => {
    e.stopPropagation()
    setGenerationSourceItem(item)
    setGenerationModalOpen(true)
  }

  const handleCloseGenerationModal = () => {
    setGenerationModalOpen(false)
    setGenerationSourceItem(null)
  }

  const handleSaveSuccess = async () => {
    // Clear cache and refetch all queries after saving new items
    queryClient.removeQueries({ queryKey: ['iml'] })
    queryClient.removeQueries({ queryKey: ['search'] })
    queryClient.removeQueries({ queryKey: ['similar'] })
  }

  const handleDeleteItem = async (item: SearchResultItem, e: React.MouseEvent) => {
    e.stopPropagation()

    if (!item.is_ai_generated) {
      alert('AI 생성 문항만 삭제할 수 있습니다.')
      return
    }

    if (!confirm(`"${item.item_id}" 문항을 삭제하시겠습니까?`)) {
      return
    }

    try {
      await api.deleteItem(item.item_id)

      // If the deleted item was selected, clear selection
      if (selectedItem?.item_id === item.item_id) {
        setSelectedItem(null)
      }

      // Refresh queries
      queryClient.invalidateQueries({ queryKey: ['search'] })
      queryClient.invalidateQueries({ queryKey: ['similar'] })

      alert('문항이 삭제되었습니다.')
    } catch (error) {
      alert(`삭제 실패: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  return (
    <div className="flex flex-col h-screen bg-slate-50 overflow-hidden">
      {/* Header with Search */}
      <header className="shrink-0 bg-slate-700 border-b-2 border-slate-600 px-4 py-2">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center gap-4">
            {/* Logo */}
            <div className="flex items-center gap-2 shrink-0">
              <div className="w-7 h-7 bg-primary-600 flex items-center justify-center">
                <span className="text-white font-semibold text-sm">Q</span>
              </div>
              <span className="text-sm font-medium text-white hidden sm:block">문항은행</span>
            </div>

            {/* Search Form */}
            <form onSubmit={handleSearch} className="flex-1 flex gap-2">
              <div className="relative flex-1">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                  <SearchIcon />
                </div>
                <input
                  type="text"
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  placeholder="자연어로 문항 검색..."
                  className="w-full pl-10 pr-3 py-2 text-sm bg-slate-600 text-white placeholder:text-slate-400 border border-slate-500 focus:outline-none focus:border-slate-400 transition-fast"
                />
              </div>
              <button
                type="submit"
                disabled={isSearching || !inputValue.trim()}
                className="btn btn-primary px-4 py-2 text-sm disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isSearching ? (
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white animate-spin" />
                ) : (
                  <SearchIcon />
                )}
              </button>
            </form>

            {/* Search Stats */}
            {searchResults && (
              <div className="hidden md:flex items-center gap-2 text-xs text-slate-300 shrink-0">
                <span className="font-medium text-white">
                  {searchResults.total_count.toLocaleString()}건
                </span>
                <span className="text-slate-500">|</span>
                <span>{searchResults.query_time_ms.toFixed(0)}ms</span>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 overflow-hidden">
        <AnimatePresence mode="wait">
          {selectedItem ? (
            // Selected Item View: 1:3 layout
            <motion.div
              key="selected-view"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="flex h-full max-w-7xl mx-auto"
            >
              {/* Selected Item Panel - 1/4 width */}
              <motion.div
                className="w-1/4 min-w-[280px] h-full overflow-y-auto border-r border-slate-200 bg-white"
                initial={{ x: -20, opacity: 0 }}
                animate={{ x: 0, opacity: 1 }}
                transition={{ duration: 0.3, ease: 'easeOut' }}
              >
                <div className="p-4">
                  <button
                    onClick={() => setSelectedItem(null)}
                    className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 mb-3 transition-fast"
                  >
                    <ChevronLeftIcon />
                    검색 결과로
                  </button>
                  <SelectedItemCard
                    item={selectedItem}
                    onGenerate={(e) => handleGenerateSimilar(selectedItem, e)}
                    onDelete={(e) => handleDeleteItem(selectedItem, e)}
                  />
                </div>
              </motion.div>

              {/* Similar Items Panel - 3/4 width */}
              <motion.div
                className="flex-1 h-full overflow-y-auto bg-slate-50"
                initial={{ x: 20, opacity: 0 }}
                animate={{ x: 0, opacity: 1 }}
                transition={{ duration: 0.3, ease: 'easeOut', delay: 0.1 }}
              >
                <div className="p-4">
                  <div className="flex items-center gap-1.5 mb-4">
                    <SparklesIcon />
                    <h3 className="text-sm font-medium text-slate-600">유사 문항</h3>
                    {similarResults && (
                      <span className="text-xs text-slate-400 ml-1">
                        ({similarResults.results.filter(i => i.item_id !== selectedItem.item_id).length}건)
                      </span>
                    )}
                  </div>

                  {isSimilarLoading ? (
                    <SimilarItemsLoadingSkeleton />
                  ) : similarResults?.results.filter(i => i.item_id !== selectedItem.item_id).length === 0 ? (
                    <p className="text-sm text-slate-400 text-center py-8">유사 문항이 없습니다</p>
                  ) : (
                    <motion.div
                      className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3"
                      initial="hidden"
                      animate="visible"
                      variants={{
                        visible: { transition: { staggerChildren: 0.05 } },
                      }}
                    >
                      {similarResults?.results
                        .filter((item) => item.item_id !== selectedItem.item_id)
                        .slice(0, 9)
                        .map((item) => (
                          <motion.div
                            key={item.item_id}
                            variants={{
                              hidden: { opacity: 0, y: 20 },
                              visible: { opacity: 1, y: 0 },
                            }}
                            transition={{ duration: 0.3 }}
                          >
                            <SimilarItemCard
                              item={item}
                              onClick={() => handleSimilarItemClick(item)}
                              onGenerate={(e) => handleGenerateSimilar(item, e)}
                              onDelete={(e) => handleDeleteItem(item, e)}
                            />
                          </motion.div>
                        ))}
                    </motion.div>
                  )}
                </div>
              </motion.div>
            </motion.div>
          ) : (
            // Search Results View: Full width grid
            <motion.div
              key="search-view"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="h-full overflow-y-auto"
            >
              <div className="p-4 max-w-7xl mx-auto">
                {!searchQuery ? (
                  <EmptyState />
                ) : isSearching ? (
                  <LoadingState />
                ) : searchResults?.results.length === 0 ? (
                  <NoResultsState query={searchQuery} />
                ) : (
                  <motion.div
                    className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3"
                    initial="hidden"
                    animate="visible"
                    variants={{
                      visible: { transition: { staggerChildren: 0.03 } },
                    }}
                  >
                    {searchResults?.results.map((item) => (
                      <motion.div
                        key={item.item_id}
                        variants={{
                          hidden: { opacity: 0, y: 10 },
                          visible: { opacity: 1, y: 0 },
                        }}
                        transition={{ duration: 0.2 }}
                      >
                        <SearchResultCard
                          item={item}
                          onClick={() => handleItemClick(item)}
                          onGenerate={(e) => handleGenerateSimilar(item, e)}
                          onDelete={(e) => handleDeleteItem(item, e)}
                        />
                      </motion.div>
                    ))}
                  </motion.div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      {/* Generation Modal */}
      <AnimatePresence>
        {generationModalOpen && generationSourceItem && (
          <GenerationModal
            sourceItem={generationSourceItem}
            onClose={handleCloseGenerationModal}
            onSaveSuccess={handleSaveSuccess}
          />
        )}
      </AnimatePresence>
    </div>
  )
}
