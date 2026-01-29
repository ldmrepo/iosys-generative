'use client'

import { useMemo } from 'react'
import katex from 'katex'
import 'katex/dist/katex.min.css'

interface MathTextProps {
  text: string
  className?: string
}

/**
 * Renders text with inline LaTeX math expressions ($...$)
 */
export function MathText({ text, className }: MathTextProps) {
  const html = useMemo(() => {
    if (!text) return ''

    // Split by $ delimiters for inline math
    const parts = text.split(/(\$[^$]+\$)/g)

    return parts
      .map((part) => {
        // Check if this is a math expression
        if (part.startsWith('$') && part.endsWith('$')) {
          const math = part.slice(1, -1)
          try {
            return katex.renderToString(math, {
              throwOnError: false,
              displayMode: false,
            })
          } catch {
            return part
          }
        }
        // Escape HTML and preserve newlines
        return part
          .replace(/&/g, '&amp;')
          .replace(/</g, '&lt;')
          .replace(/>/g, '&gt;')
          .replace(/\n/g, '<br/>')
      })
      .join('')
  }, [text])

  return (
    <span
      className={className}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  )
}
