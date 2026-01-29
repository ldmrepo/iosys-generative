import { useCallback } from 'react'
import type { TextEntryInteraction, ResponseValue } from '@iosys/qti-core'
import { Input } from '@iosys/qti-ui'

export interface TextEntryInputProps {
  interaction: TextEntryInteraction
  /** Current response value */
  value?: ResponseValue | undefined
  /** Callback when response changes */
  onChange: (value: ResponseValue) => void
  /** Disabled state */
  disabled?: boolean | undefined
  /** Inline display mode */
  inline?: boolean | undefined
}

export function TextEntryInput({
  interaction,
  value,
  onChange,
  disabled = false,
  inline = true,
}: TextEntryInputProps) {
  const { expectedLength, placeholderText, patternMask } = interaction

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      onChange(e.target.value)
    },
    [onChange]
  )

  return (
    <Input
      type="text"
      value={value ? String(value) : ''}
      onChange={handleChange}
      placeholder={placeholderText ?? '답을 입력하세요'}
      maxLength={expectedLength}
      pattern={patternMask}
      disabled={disabled}
      inline={inline}
      className={inline ? 'min-w-[120px]' : 'w-full max-w-md'}
    />
  )
}

TextEntryInput.displayName = 'TextEntryInput'
