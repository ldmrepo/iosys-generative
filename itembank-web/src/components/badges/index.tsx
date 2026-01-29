import { AIIcon } from '@/components/icons'

export function SimilarityBadge({ similarity }: { similarity: number }) {
  const percentage = (similarity * 100).toFixed(0)
  const color = similarity >= 0.8
    ? 'text-emerald-600'
    : similarity >= 0.6
    ? 'text-amber-600'
    : 'text-slate-400'

  return (
    <span className={`text-xs font-medium ${color}`}>
      {percentage}%
    </span>
  )
}

export function DifficultyBadge({ difficulty }: { difficulty: string }) {
  const color = difficulty === '상'
    ? 'text-red-600'
    : difficulty === '중'
    ? 'text-amber-600'
    : 'text-emerald-600'

  return <span className={`text-xs font-medium ${color}`}>{difficulty}</span>
}

export function AIBadge() {
  return (
    <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 text-[10px] font-medium bg-gradient-to-r from-purple-500 to-pink-500 text-white">
      <AIIcon />
      AI
    </span>
  )
}
