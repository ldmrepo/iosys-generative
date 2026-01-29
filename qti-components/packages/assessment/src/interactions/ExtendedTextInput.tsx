import { useCallback } from 'react'
import type { ExtendedTextInteraction, ResponseValue } from '@iosys/qti-core'
import { Textarea } from '@iosys/qti-ui'

export interface ExtendedTextInputProps {
  interaction: ExtendedTextInteraction
  /** Current response value */
  value?: ResponseValue | undefined
  /** Callback when response changes */
  onChange: (value: ResponseValue) => void
  /** Disabled state */
  disabled?: boolean | undefined
}

export function ExtendedTextInput({
  interaction,
  value,
  onChange,
  disabled = false,
}: ExtendedTextInputProps) {
  const { expectedLines, placeholderText, maxStrings } = interaction

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      onChange(e.target.value)
    },
    [onChange]
  )

  const textValue = value ? String(value) : ''

  return (
    <div className="space-y-2">
      <Textarea
        value={textValue}
        onChange={handleChange}
        placeholder={placeholderText ?? '답안을 작성하세요'}
        rows={expectedLines ?? 5}
        maxLength={maxStrings ? maxStrings * 1000 : undefined}
        disabled={disabled}
        className="w-full"
      />
      {maxStrings && (
        <div className="text-sm text-gray-500 text-right">
          {textValue.length} / {maxStrings * 1000}자
        </div>
      )}
    </div>
  )
}

ExtendedTextInput.displayName = 'ExtendedTextInput'
