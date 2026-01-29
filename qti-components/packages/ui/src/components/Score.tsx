import { clsx } from 'clsx'

export interface ScoreProps {
  /** Earned score */
  score: number
  /** Maximum score */
  maxScore: number
  /** Show as percentage */
  showPercentage?: boolean
  className?: string
}

export function Score({ score, maxScore, showPercentage = false, className }: ScoreProps) {
  const percentage = maxScore > 0 ? (score / maxScore) * 100 : 0
  const status = percentage === 100 ? 'perfect' : percentage > 0 ? 'partial' : 'zero'

  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium',
        {
          'bg-green-100 text-green-800': status === 'perfect',
          'bg-amber-100 text-amber-800': status === 'partial',
          'bg-red-100 text-red-800': status === 'zero',
        },
        className
      )}
    >
      {showPercentage ? (
        <span>{Math.round(percentage)}%</span>
      ) : (
        <span>
          {score} / {maxScore}
        </span>
      )}
    </span>
  )
}

Score.displayName = 'Score'
