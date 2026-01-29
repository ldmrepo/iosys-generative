import { forwardRef, type InputHTMLAttributes } from 'react'
import { clsx } from 'clsx'

export interface RadioProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label?: string
  status?: 'correct' | 'incorrect' | 'neutral'
}

export const Radio = forwardRef<HTMLInputElement, RadioProps>(
  ({ className, label, status = 'neutral', disabled, ...props }, ref) => {
    return (
      <label
        className={clsx(
          'inline-flex items-center gap-2 cursor-pointer',
          disabled && 'cursor-not-allowed opacity-60',
          className
        )}
      >
        <input
          ref={ref}
          type="radio"
          className={clsx(
            'w-4 h-4 border-2 rounded-full appearance-none cursor-pointer',
            'checked:border-4 transition-all',
            {
              'border-gray-300 checked:border-qti-primary': status === 'neutral',
              'border-qti-correct checked:border-qti-correct': status === 'correct',
              'border-qti-incorrect checked:border-qti-incorrect': status === 'incorrect',
            },
            disabled && 'cursor-not-allowed'
          )}
          disabled={disabled}
          {...props}
        />
        {label && <span className="text-gray-700">{label}</span>}
      </label>
    )
  }
)

Radio.displayName = 'Radio'
