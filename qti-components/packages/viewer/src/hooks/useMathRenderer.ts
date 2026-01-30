import { useEffect, useRef, useCallback, type RefObject } from 'react'
import katex from 'katex'

/**
 * Hook to render LaTeX math elements within a container.
 * Finds all elements with class "math" and data-latex attribute,
 * then renders them using KaTeX.
 * Uses MutationObserver to handle dynamically added content.
 */
export function useMathRenderer<T extends HTMLElement>(): RefObject<T | null> {
  const containerRef = useRef<T>(null)

  const renderMathElements = useCallback((container: HTMLElement) => {
    const mathElements = container.querySelectorAll('.math[data-latex]:not([data-rendered])')

    mathElements.forEach((el) => {
      const latex = el.getAttribute('data-latex')
      if (!latex) return

      try {
        const displayMode = el.classList.contains('math-block')
        katex.render(latex, el as HTMLElement, {
          throwOnError: false,
          displayMode,
          output: 'html',
        })
        el.setAttribute('data-rendered', 'true')
      } catch (error) {
        console.warn('KaTeX render error:', error)
        el.textContent = latex
      }
    })
  }, [])

  useEffect(() => {
    if (!containerRef.current) return

    // Initial render
    renderMathElements(containerRef.current)

    // Observe for dynamically added content
    const observer = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
          renderMathElements(containerRef.current!)
          break
        }
      }
    })

    observer.observe(containerRef.current, {
      childList: true,
      subtree: true,
    })

    return () => observer.disconnect()
  }, [renderMathElements])

  return containerRef
}
