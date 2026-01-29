import { SearchIcon } from '@/components/icons'

export function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center px-4">
      <div className="w-12 h-12 bg-slate-100 flex items-center justify-center mb-4 text-slate-400">
        <SearchIcon />
      </div>
      <h3 className="text-base font-medium text-slate-700 mb-1">문항 검색</h3>
      <p className="text-sm text-slate-400 max-w-sm">
        자연어로 원하는 문항을 검색하세요
      </p>
      <div className="mt-6 flex flex-wrap justify-center gap-1.5">
        {['이차방정식', '삼각비', '확률과 통계'].map((keyword) => (
          <span key={keyword} className="text-xs px-2.5 py-1 bg-slate-100 text-slate-500">
            {keyword}
          </span>
        ))}
      </div>
    </div>
  )
}

export function LoadingState() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh]">
      <div className="w-8 h-8 border-2 border-slate-200 border-t-primary-600 animate-spin mb-3" />
      <p className="text-sm text-slate-400">검색 중...</p>
    </div>
  )
}

export function NoResultsState({ query }: { query: string }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center px-4">
      <div className="w-12 h-12 bg-slate-100 flex items-center justify-center mb-4 text-slate-300">
        <SearchIcon />
      </div>
      <h3 className="text-base font-medium text-slate-600 mb-1">검색 결과 없음</h3>
      <p className="text-sm text-slate-400">
        &ldquo;{query}&rdquo;에 대한 결과가 없습니다
      </p>
    </div>
  )
}

export function SimilarItemsLoadingSkeleton() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
      {[1, 2, 3, 4, 5, 6].map((i) => (
        <div key={i} className="border border-slate-200 bg-white p-3">
          <div className="space-y-2">
            <div className="skeleton h-3 w-1/3"></div>
            <div className="skeleton h-4 w-full"></div>
            <div className="skeleton h-4 w-5/6"></div>
            <div className="skeleton h-4 w-2/3"></div>
          </div>
        </div>
      ))}
    </div>
  )
}
