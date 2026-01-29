import { useCallback } from 'react'
import type { ChoiceInteraction, ResponseValue } from '@iosys/qti-core'
import { ChoiceLabel } from '@iosys/qti-ui'

export interface ChoiceInputProps {
  interaction: ChoiceInteraction
  /** Current response value */
  value?: ResponseValue | undefined
  /** Callback when response changes */
  onChange: (value: ResponseValue) => void
  /** Disabled state */
  disabled?: boolean | undefined
}

export function ChoiceInput({
  interaction,
  value,
  onChange,
  disabled = false,
}: ChoiceInputProps) {
  const { simpleChoices, orientation = 'vertical', maxChoices = 1 } = interaction
  const isMultiple = maxChoices !== 1

  // Normalize value to array
  const selectedIds: string[] = Array.isArray(value)
    ? value.filter((v): v is string => typeof v === 'string')
    : value
      ? [String(value)]
      : []

  const handleSelect = useCallback(
    (choiceId: string) => {
      if (disabled) return

      if (isMultiple) {
        // Toggle selection for multiple choice
        const newSelected = selectedIds.includes(choiceId)
          ? selectedIds.filter(id => id !== choiceId)
          : [...selectedIds, choiceId]

        // Respect maxChoices limit
        if (maxChoices > 0 && newSelected.length > maxChoices) {
          return
        }

        onChange(newSelected)
      } else {
        // Single choice
        onChange(choiceId)
      }
    },
    [disabled, isMultiple, selectedIds, maxChoices, onChange]
  )

  return (
    <div
      className={
        orientation === 'horizontal' ? 'flex flex-wrap gap-2' : 'flex flex-col gap-1'
      }
      role={isMultiple ? 'group' : 'radiogroup'}
    >
      {simpleChoices.map((choice, index) => {
        const isSelected = selectedIds.includes(choice.identifier)

        return (
          <button
            key={choice.identifier}
            type="button"
            role={isMultiple ? 'checkbox' : 'radio'}
            aria-checked={isSelected}
            disabled={disabled}
            onClick={() => handleSelect(choice.identifier)}
            className={`
              flex items-baseline gap-2 py-1 px-1.5 -mx-1.5 rounded text-left transition-colors
              ${isSelected ? 'bg-blue-50' : 'hover:bg-gray-50'}
              ${disabled ? 'opacity-60 cursor-not-allowed' : 'cursor-pointer'}
            `}
          >
            <ChoiceLabel
              index={index}
              style="number"
              selected={isSelected}
            />
            <div
              className="flex-1 prose prose-sm max-w-none [&>p]:my-0"
              dangerouslySetInnerHTML={{ __html: choice.content }}
            />
          </button>
        )
      })}
    </div>
  )
}

ChoiceInput.displayName = 'ChoiceInput'
