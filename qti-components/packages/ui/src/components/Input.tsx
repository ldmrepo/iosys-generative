import { forwardRef, type InputHTMLAttributes } from 'react'
import { clsx } from 'clsx'

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  status?: 'correct' | 'incorrect' | 'neutral'
  inline?: boolean
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, status = 'neutral', inline = false, disabled, ...props }, ref) => {
    return (
      <input
        ref={ref}
        className={clsx(
          'outline-none transition-colors',
          inline
            ? [
                'inline-block min-w-[100px] px-2 py-1 border-b-2 bg-transparent',
                {
                  'border-gray-300 focus:border-qti-primary': status === 'neutral',
                  'border-qti-correct': status === 'correct',
                  'border-qti-incorrect': status === 'incorrect',
                },
              ]
            : [
                'w-full px-3 py-2 border rounded-lg',
                'focus:ring-2 focus:ring-offset-0',
                {
                  'border-gray-300 focus:border-qti-primary focus:ring-blue-100':
                    status === 'neutral',
                  'border-qti-correct focus:ring-green-100': status === 'correct',
                  'border-qti-incorrect focus:ring-red-100': status === 'incorrect',
                },
              ],
          disabled && 'opacity-60 cursor-not-allowed bg-gray-50',
          className
        )}
        disabled={disabled}
        {...props}
      />
    )
  }
)

Input.displayName = 'Input'
