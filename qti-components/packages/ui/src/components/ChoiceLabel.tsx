import { clsx } from 'clsx'

export interface ChoiceLabelProps {
  /** Index of the choice (0-based) */
  index: number
  /** Label style */
  style?: 'alpha' | 'number' | 'roman' | 'circle'
  /** Whether the choice is selected */
  selected?: boolean
  /** Status for scoring display */
  status?: 'correct' | 'incorrect' | 'neutral'
  className?: string
}

const ALPHA_LABELS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
const ROMAN_NUMERALS = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X']

function getLabel(index: number, style: ChoiceLabelProps['style']): string {
  switch (style) {
    case 'number':
      return String(index + 1)
    case 'roman':
      return ROMAN_NUMERALS[index] ?? String(index + 1)
    case 'circle':
      return String.fromCharCode(0x2460 + index) // ①②③...
    case 'alpha':
    default:
      return ALPHA_LABELS[index] ?? String(index + 1)
  }
}

export function ChoiceLabel({
  index,
  style = 'alpha',
  selected = false,
  status = 'neutral',
  className,
}: ChoiceLabelProps) {
  const label = getLabel(index, style)

  return (
    <span
      className={clsx(
        'inline-flex items-center justify-center w-5 h-5 rounded',
        'text-xs font-semibold flex-shrink-0 transition-colors leading-none',
        {
          // Default state
          'bg-gray-100 text-gray-600': !selected && status === 'neutral',
          // Selected state
          'bg-qti-primary text-white': selected && status === 'neutral',
          // Correct state
          'bg-qti-correct text-white': status === 'correct',
          // Incorrect state
          'bg-qti-incorrect text-white': status === 'incorrect',
        },
        className
      )}
    >
      {label}
    </span>
  )
}

ChoiceLabel.displayName = 'ChoiceLabel'
