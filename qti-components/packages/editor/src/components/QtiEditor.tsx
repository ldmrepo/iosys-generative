import { useEffect, useRef, useCallback, useState } from 'react'
import { EditorState } from 'prosemirror-state'
import { EditorView } from 'prosemirror-view'
import { DOMParser, DOMSerializer, Node as ProseMirrorNode } from 'prosemirror-model'
import { history, undo, redo } from 'prosemirror-history'
import { keymap } from 'prosemirror-keymap'
import { baseKeymap, toggleMark } from 'prosemirror-commands'
import { dropCursor } from 'prosemirror-dropcursor'
import { gapCursor } from 'prosemirror-gapcursor'

import { qtiSchema } from '../schema'
import { EditorToolbar } from './toolbar'
import { mathNodeView, textEntryNodeView, extendedTextNodeView } from '../nodeviews'

export interface QtiEditorProps {
  /** Initial HTML content */
  value?: string | undefined
  /** Called when content changes */
  onChange?: ((html: string) => void) | undefined
  /** Placeholder text */
  placeholder?: string | undefined
  /** Disabled state */
  disabled?: boolean | undefined
  /** Custom class name */
  className?: string | undefined
}

export function QtiEditor({
  value = '',
  onChange,
  placeholder = '문항 내용을 입력하세요...',
  disabled = false,
  className,
}: QtiEditorProps) {
  const editorRef = useRef<HTMLDivElement>(null)
  const viewRef = useRef<EditorView | null>(null)
  const [editorView, setEditorView] = useState<EditorView | null>(null)

  // Parse HTML to ProseMirror doc
  const parseHTML = useCallback((html: string) => {
    const container = document.createElement('div')
    container.innerHTML = html || `<p></p>`
    return DOMParser.fromSchema(qtiSchema).parse(container)
  }, [])

  // Serialize ProseMirror doc to HTML
  const serializeHTML = useCallback((doc: ProseMirrorNode): string => {
    const fragment = DOMSerializer.fromSchema(qtiSchema).serializeFragment(doc.content)
    const container = document.createElement('div')
    container.appendChild(fragment)
    return container.innerHTML
  }, [])

  // Initialize editor
  useEffect(() => {
    if (!editorRef.current) return

    const doc = parseHTML(value)

    // Text formatting keymaps
    const markKeymap: Record<string, (state: EditorState) => boolean> = {}
    if (qtiSchema.marks['bold']) {
      markKeymap['Mod-b'] = toggleMark(qtiSchema.marks['bold'])
    }
    if (qtiSchema.marks['italic']) {
      markKeymap['Mod-i'] = toggleMark(qtiSchema.marks['italic'])
    }
    if (qtiSchema.marks['underline']) {
      markKeymap['Mod-u'] = toggleMark(qtiSchema.marks['underline'])
    }

    const state = EditorState.create({
      doc,
      schema: qtiSchema,
      plugins: [
        history(),
        keymap({ 'Mod-z': undo, 'Mod-y': redo, 'Mod-Shift-z': redo }),
        keymap(markKeymap),
        keymap(baseKeymap),
        dropCursor(),
        gapCursor(),
      ],
    })

    const view = new EditorView(editorRef.current, {
      state,
      editable: () => !disabled,
      dispatchTransaction(transaction) {
        const newState = view.state.apply(transaction)
        view.updateState(newState)

        if (transaction.docChanged && onChange) {
          const html = serializeHTML(newState.doc)
          onChange(html)
        }
      },
      nodeViews: {
        math: mathNodeView,
        textEntryInteraction: textEntryNodeView,
        extendedTextInteraction: extendedTextNodeView,
      },
      attributes: {
        class: 'qti-editor-content prose prose-lg max-w-none focus:outline-none min-h-[200px] p-4',
        'data-placeholder': placeholder,
      },
    })

    viewRef.current = view
    setEditorView(view)

    return () => {
      view.destroy()
      viewRef.current = null
      setEditorView(null)
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Update editable state when disabled changes
  useEffect(() => {
    if (viewRef.current) {
      viewRef.current.setProps({ editable: () => !disabled })
    }
  }, [disabled])

  return (
    <div
      className={`qti-editor border border-gray-200 rounded-lg bg-white ${className ?? ''} ${
        disabled ? 'opacity-60' : ''
      }`}
    >
      {/* Editor Toolbar */}
      <div className="border-b border-gray-200 px-3 py-2 bg-gray-50 overflow-x-auto">
        <EditorToolbar editorView={editorView} disabled={disabled} />
      </div>

      {/* Editor content */}
      <div ref={editorRef} />

      {/* Placeholder styles */}
      <style>{`
        .qti-editor-content:empty::before {
          content: attr(data-placeholder);
          color: #9ca3af;
          pointer-events: none;
          position: absolute;
        }
        .qti-editor-content {
          position: relative;
        }
        .ProseMirror-focused {
          outline: none;
        }
        .ProseMirror p.is-editor-empty:first-child::before {
          content: attr(data-placeholder);
          float: left;
          color: #9ca3af;
          pointer-events: none;
          height: 0;
        }
      `}</style>
    </div>
  )
}

QtiEditor.displayName = 'QtiEditor'
