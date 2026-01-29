/**
 * ToolbarButton - Button component for editor toolbar
 */

import type { ReactNode } from 'react'

export interface ToolbarButtonProps {
  onClick: () => void
  active?: boolean | undefined
  disabled?: boolean | undefined
  title?: string | undefined
  children: ReactNode
}

export function ToolbarButton({
  onClick,
  active = false,
  disabled = false,
  title,
  children,
}: ToolbarButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={title}
      className={`
        p-1.5 rounded transition-colors
        ${active
          ? 'bg-qti-primary text-white'
          : 'text-gray-600 hover:bg-gray-100'}
        ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
      `}
    >
      {children}
    </button>
  )
}

ToolbarButton.displayName = 'ToolbarButton'
