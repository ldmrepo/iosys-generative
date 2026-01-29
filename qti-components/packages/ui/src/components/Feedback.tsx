import { type ReactNode } from 'react'
import { clsx } from 'clsx'

export interface FeedbackProps {
  /** Feedback type */
  type: 'correct' | 'incorrect' | 'partial' | 'info'
  /** Feedback content */
  children: ReactNode
  /** Optional title */
  title?: string
  className?: string
}

const ICONS = {
  correct: (
    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
      <path
        fillRule="evenodd"
        d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
        clipRule="evenodd"
      />
    </svg>
  ),
  incorrect: (
    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
      <path
        fillRule="evenodd"
        d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
        clipRule="evenodd"
      />
    </svg>
  ),
  partial: (
    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
      <path
        fillRule="evenodd"
        d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-11a1 1 0 10-2 0v3.586L7.707 9.293a1 1 0 00-1.414 1.414l3 3a1 1 0 001.414 0l3-3a1 1 0 00-1.414-1.414L11 10.586V7z"
        clipRule="evenodd"
      />
    </svg>
  ),
  info: (
    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
      <path
        fillRule="evenodd"
        d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
        clipRule="evenodd"
      />
    </svg>
  ),
}

export function Feedback({ type, children, title, className }: FeedbackProps) {
  return (
    <div
      className={clsx(
        'flex gap-3 p-4 rounded-lg border',
        {
          'bg-green-50 border-qti-correct text-green-800': type === 'correct',
          'bg-red-50 border-qti-incorrect text-red-800': type === 'incorrect',
          'bg-amber-50 border-qti-warning text-amber-800': type === 'partial',
          'bg-blue-50 border-blue-300 text-blue-800': type === 'info',
        },
        className
      )}
      role="alert"
    >
      <span className="flex-shrink-0">{ICONS[type]}</span>
      <div className="flex-1">
        {title && <div className="font-medium mb-1">{title}</div>}
        <div>{children}</div>
      </div>
    </div>
  )
}

Feedback.displayName = 'Feedback'
