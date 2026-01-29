import { forwardRef, type TextareaHTMLAttributes } from 'react'
import { clsx } from 'clsx'

export interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  status?: 'correct' | 'incorrect' | 'neutral'
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, status = 'neutral', disabled, ...props }, ref) => {
    return (
      <textarea
        ref={ref}
        className={clsx(
          'w-full min-h-[120px] px-3 py-2 border rounded-lg resize-y',
          'outline-none focus:ring-2 focus:ring-offset-0 transition-colors',
          {
            'border-gray-300 focus:border-qti-primary focus:ring-blue-100': status === 'neutral',
            'border-qti-correct focus:ring-green-100': status === 'correct',
            'border-qti-incorrect focus:ring-red-100': status === 'incorrect',
          },
          disabled && 'opacity-60 cursor-not-allowed bg-gray-50',
          className
        )}
        disabled={disabled}
        {...props}
      />
    )
  }
)

Textarea.displayName = 'Textarea'
