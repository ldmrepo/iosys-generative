/**
 * OrderInput - Interactive ordering interaction component
 * Allows users to reorder items via drag-and-drop or up/down buttons
 */

import { useState, useCallback, useRef } from 'react'
import type { OrderInteraction } from '@iosys/qti-core'

export interface OrderInputProps {
  interaction: OrderInteraction
  /** Current response value (ordered list of identifiers) */
  value: string[]
  /** Callback when response changes */
  onChange: (value: string[]) => void
  /** Whether the input is disabled */
  disabled?: boolean | undefined
}

export function OrderInput({
  interaction,
  value = [],
  onChange,
  disabled = false,
}: OrderInputProps) {
  const { simpleChoices, shuffle } = interaction

  // Initialize with shuffled or original order if no value
  const getInitialOrder = useCallback(() => {
    if (value.length > 0) return value

    const ids = simpleChoices.map(c => c.identifier)
    if (shuffle) {
      // Fisher-Yates shuffle
      const shuffled = [...ids]
      for (let i = shuffled.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1))
        const temp = shuffled[i]!
        shuffled[i] = shuffled[j]!
        shuffled[j] = temp
      }
      return shuffled
    }
    return ids
  }, [simpleChoices, shuffle, value])

  // Current order state
  const [order, setOrder] = useState<string[]>(() => getInitialOrder())

  // Drag state
  const [draggedIndex, setDraggedIndex] = useState<number | null>(null)
  const [dragOverIndex, setDragOverIndex] = useState<number | null>(null)
  const dragCounter = useRef(0)

  // Update order and notify parent
  const updateOrder = useCallback(
    (newOrder: string[]) => {
      setOrder(newOrder)
      onChange(newOrder)
    },
    [onChange]
  )

  // Move item up
  const moveUp = (index: number) => {
    if (disabled || index === 0) return
    const newOrder = [...order]
    const temp = newOrder[index - 1]!
    newOrder[index - 1] = newOrder[index]!
    newOrder[index] = temp
    updateOrder(newOrder)
  }

  // Move item down
  const moveDown = (index: number) => {
    if (disabled || index === order.length - 1) return
    const newOrder = [...order]
    const temp = newOrder[index]!
    newOrder[index] = newOrder[index + 1]!
    newOrder[index + 1] = temp
    updateOrder(newOrder)
  }

  // Get choice content by ID
  const getChoiceContent = (id: string): string => {
    const choice = simpleChoices.find(c => c.identifier === id)
    return choice?.content ?? id
  }

  // Drag handlers
  const handleDragStart = (e: React.DragEvent, index: number) => {
    if (disabled) {
      e.preventDefault()
      return
    }
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.setData('text/plain', String(index))
    setDraggedIndex(index)
  }

  const handleDragEnd = () => {
    setDraggedIndex(null)
    setDragOverIndex(null)
    dragCounter.current = 0
  }

  const handleDragEnter = (e: React.DragEvent, index: number) => {
    e.preventDefault()
    dragCounter.current++
    setDragOverIndex(index)
  }

  const handleDragLeave = () => {
    dragCounter.current--
    if (dragCounter.current === 0) {
      setDragOverIndex(null)
    }
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
  }

  const handleDrop = (e: React.DragEvent, dropIndex: number) => {
    e.preventDefault()
    const dragIndex = parseInt(e.dataTransfer.getData('text/plain'), 10)

    if (dragIndex === dropIndex) {
      handleDragEnd()
      return
    }

    const newOrder = [...order]
    const removed = newOrder.splice(dragIndex, 1)[0]
    if (removed) {
      newOrder.splice(dropIndex, 0, removed)
      updateOrder(newOrder)
    }
    handleDragEnd()
  }

  return (
    <div className="space-y-2">
      <div className="text-sm text-gray-500 mb-2">
        항목을 드래그하거나 화살표 버튼을 사용하여 순서를 정하세요:
      </div>

      {order.map((id, index) => {
        const isDragging = draggedIndex === index
        const isDragOver = dragOverIndex === index && draggedIndex !== index

        return (
          <div
            key={id}
            draggable={!disabled}
            onDragStart={(e) => handleDragStart(e, index)}
            onDragEnd={handleDragEnd}
            onDragEnter={(e) => handleDragEnter(e, index)}
            onDragLeave={handleDragLeave}
            onDragOver={handleDragOver}
            onDrop={(e) => handleDrop(e, index)}
            className={`
              flex items-center gap-3 p-3 rounded-lg border bg-white
              transition-all duration-150
              ${isDragging ? 'opacity-50 border-dashed border-qti-primary' : 'border-gray-200'}
              ${isDragOver ? 'border-qti-primary bg-blue-50' : ''}
              ${disabled ? 'opacity-50' : 'cursor-grab active:cursor-grabbing'}
            `}
          >
            {/* Position number */}
            <span
              className={`
                flex items-center justify-center w-7 h-7 rounded-full text-sm font-medium
                bg-qti-primary text-white
              `}
            >
              {index + 1}
            </span>

            {/* Drag handle */}
            {!disabled && (
              <span className="text-gray-400 cursor-grab">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 8h16M4 16h16"
                  />
                </svg>
              </span>
            )}

            {/* Content */}
            <div
              className="flex-1 prose prose-sm max-w-none"
              dangerouslySetInnerHTML={{ __html: getChoiceContent(id) }}
            />

            {/* Up/Down buttons */}
            {!disabled && (
              <div className="flex flex-col gap-1">
                <button
                  type="button"
                  onClick={() => moveUp(index)}
                  disabled={index === 0}
                  className={`
                    p-1 rounded transition-colors
                    ${index === 0
                      ? 'text-gray-300 cursor-not-allowed'
                      : 'text-gray-500 hover:text-qti-primary hover:bg-gray-100'}
                  `}
                  title="위로 이동"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                  </svg>
                </button>
                <button
                  type="button"
                  onClick={() => moveDown(index)}
                  disabled={index === order.length - 1}
                  className={`
                    p-1 rounded transition-colors
                    ${index === order.length - 1
                      ? 'text-gray-300 cursor-not-allowed'
                      : 'text-gray-500 hover:text-qti-primary hover:bg-gray-100'}
                  `}
                  title="아래로 이동"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>
              </div>
            )}
          </div>
        )
      })}

      {/* Reset button */}
      {!disabled && value.length > 0 && (
        <button
          type="button"
          onClick={() => {
            const ids = simpleChoices.map(c => c.identifier)
            setOrder(ids)
            onChange([]) // Clear response
          }}
          className="text-sm text-gray-500 hover:text-qti-primary transition-colors"
        >
          순서 초기화
        </button>
      )}
    </div>
  )
}

OrderInput.displayName = 'OrderInput'
