import { useEffect, useRef, type HTMLAttributes } from 'react'
import katex from 'katex'
import { clsx } from 'clsx'

export interface MathProps extends HTMLAttributes<HTMLSpanElement> {
  /** LaTeX expression */
  latex: string
  /** Display mode (block) vs inline */
  displayMode?: boolean
  /** Throw error on invalid LaTeX */
  throwOnError?: boolean
}

export function Math({
  latex,
  displayMode = false,
  throwOnError = false,
  className,
  ...props
}: MathProps) {
  const containerRef = useRef<HTMLSpanElement>(null)

  useEffect(() => {
    if (containerRef.current) {
      try {
        katex.render(latex, containerRef.current, {
          displayMode,
          throwOnError,
          errorColor: '#ef4444',
          strict: false,
        })
      } catch (error) {
        if (throwOnError) throw error
        if (containerRef.current) {
          containerRef.current.textContent = latex
          containerRef.current.style.color = '#ef4444'
        }
      }
    }
  }, [latex, displayMode, throwOnError])

  return (
    <span
      ref={containerRef}
      className={clsx(displayMode ? 'block my-2' : 'inline', className)}
      {...props}
    />
  )
}

Math.displayName = 'Math'
