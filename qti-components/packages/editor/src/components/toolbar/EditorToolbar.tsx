/**
 * EditorToolbar - Main toolbar component for QTI Editor
 */

import { useCallback } from 'react'
import type { EditorView } from 'prosemirror-view'
import type { EditorState, Transaction } from 'prosemirror-state'
import { toggleMark, setBlockType } from 'prosemirror-commands'
import { undo, redo } from 'prosemirror-history'

import { qtiSchema } from '../../schema'
import { ToolbarButton } from './ToolbarButton'
import {
  BoldIcon,
  ItalicIcon,
  UnderlineIcon,
  StrikeIcon,
  SuperscriptIcon,
  SubscriptIcon,
  CodeIcon,
  LinkIcon,
  ImageIcon,
  MathIcon,
  HeadingIcon,
  ParagraphIcon,
  UndoIcon,
  RedoIcon,
  ChoiceIcon,
  TextEntryIcon,
  ExtendedTextIcon,
} from './icons'

export interface EditorToolbarProps {
  editorView: EditorView | null
  disabled?: boolean | undefined
}

export function EditorToolbar({ editorView, disabled = false }: EditorToolbarProps) {
  // Execute a ProseMirror command
  const runCommand = useCallback(
    (cmd: (state: EditorState, dispatch?: (tr: Transaction) => void) => boolean) => {
      if (!editorView || disabled) return
      cmd(editorView.state, editorView.dispatch)
      editorView.focus()
    },
    [editorView, disabled]
  )

  // Check if a mark is active
  const isMarkActive = useCallback(
    (markType: string): boolean => {
      if (!editorView) return false
      const { from, $from, to, empty } = editorView.state.selection
      const mark = qtiSchema.marks[markType]
      if (!mark) return false

      if (empty) {
        return !!mark.isInSet(editorView.state.storedMarks || $from.marks())
      } else {
        return editorView.state.doc.rangeHasMark(from, to, mark)
      }
    },
    [editorView]
  )

  // Check if a block type is active
  const isBlockTypeActive = useCallback(
    (nodeType: string, attrs?: Record<string, unknown>): boolean => {
      if (!editorView) return false
      const { $from } = editorView.state.selection
      const node = qtiSchema.nodes[nodeType]
      if (!node) return false

      for (let d = $from.depth; d >= 0; d--) {
        const n = $from.node(d)
        if (n.type === node) {
          if (!attrs) return true
          return Object.keys(attrs).every(key => n.attrs[key] === attrs[key])
        }
      }
      return false
    },
    [editorView]
  )

  // Toggle mark command
  const toggleMarkCommand = useCallback(
    (markType: string) => {
      const mark = qtiSchema.marks[markType]
      if (!mark) return
      runCommand(toggleMark(mark))
    },
    [runCommand]
  )

  // Set block type command
  const setBlockTypeCommand = useCallback(
    (nodeType: string, attrs?: Record<string, unknown>) => {
      const node = qtiSchema.nodes[nodeType]
      if (!node) return
      runCommand(setBlockType(node, attrs))
    },
    [runCommand]
  )

  // Insert node
  const insertNode = useCallback(
    (nodeType: string, attrs?: Record<string, unknown>) => {
      if (!editorView || disabled) return

      const node = qtiSchema.nodes[nodeType]
      if (!node) return

      const newNode = node.create(attrs)
      const { state, dispatch } = editorView
      const tr = state.tr.replaceSelectionWith(newNode)
      dispatch(tr)
      editorView.focus()
    },
    [editorView, disabled]
  )

  // Insert image with prompt
  const insertImage = useCallback(() => {
    const src = window.prompt('이미지 URL을 입력하세요:')
    if (!src) return

    const alt = window.prompt('대체 텍스트 (선택):') || undefined
    insertNode('image', { src, alt })
  }, [insertNode])

  // Insert math with prompt
  const insertMath = useCallback(() => {
    const latex = window.prompt('LaTeX 수식을 입력하세요:')
    if (!latex) return

    insertNode('math', { latex, display: 'inline' })
  }, [insertNode])

  // Insert link
  const insertLink = useCallback(() => {
    if (!editorView || disabled) return

    const { from, to, empty } = editorView.state.selection
    if (empty) {
      alert('링크를 추가할 텍스트를 먼저 선택하세요.')
      return
    }

    const href = window.prompt('링크 URL을 입력하세요:')
    if (!href) return

    const mark = qtiSchema.marks['link']
    if (!mark) return

    const tr = editorView.state.tr.addMark(from, to, mark.create({ href }))
    editorView.dispatch(tr)
    editorView.focus()
  }, [editorView, disabled])

  // Insert choice interaction
  const insertChoiceInteraction = useCallback(() => {
    if (!editorView || disabled) return

    const { state, dispatch } = editorView
    const choiceInteraction = qtiSchema.nodes['choiceInteraction']
    const simpleChoice = qtiSchema.nodes['simpleChoice']
    const paragraph = qtiSchema.nodes['paragraph']

    if (!choiceInteraction || !simpleChoice || !paragraph) return

    // Create choice interaction with 4 default choices
    const choices = [1, 2, 3, 4].map(i =>
      simpleChoice.create(
        { identifier: `choice_${i}`, isCorrect: i === 1 },
        paragraph.create(null, qtiSchema.text(`선택지 ${i}`))
      )
    )

    const interaction = choiceInteraction.create(
      { responseIdentifier: 'RESPONSE', maxChoices: 1 },
      choices
    )

    const tr = state.tr.replaceSelectionWith(interaction)
    dispatch(tr)
    editorView.focus()
  }, [editorView, disabled])

  // Insert text entry interaction
  const insertTextEntry = useCallback(() => {
    insertNode('textEntryInteraction', {
      responseIdentifier: 'RESPONSE',
      expectedLength: 20,
      placeholderText: '답을 입력하세요',
    })
  }, [insertNode])

  // Insert extended text interaction
  const insertExtendedText = useCallback(() => {
    insertNode('extendedTextInteraction', {
      responseIdentifier: 'RESPONSE',
      expectedLines: 5,
      placeholderText: '서술형 답변을 입력하세요',
    })
  }, [insertNode])

  // Separator component
  const Separator = () => <div className="w-px h-6 bg-gray-300 mx-1" />

  return (
    <div className="flex items-center gap-1 flex-wrap">
      {/* History */}
      <ToolbarButton
        onClick={() => runCommand(undo)}
        disabled={disabled}
        title="실행 취소 (Ctrl+Z)"
      >
        <UndoIcon />
      </ToolbarButton>
      <ToolbarButton
        onClick={() => runCommand(redo)}
        disabled={disabled}
        title="다시 실행 (Ctrl+Y)"
      >
        <RedoIcon />
      </ToolbarButton>

      <Separator />

      {/* Block types */}
      <ToolbarButton
        onClick={() => setBlockTypeCommand('paragraph')}
        active={isBlockTypeActive('paragraph')}
        disabled={disabled}
        title="단락"
      >
        <ParagraphIcon />
      </ToolbarButton>
      <ToolbarButton
        onClick={() => setBlockTypeCommand('heading', { level: 1 })}
        active={isBlockTypeActive('heading', { level: 1 })}
        disabled={disabled}
        title="제목 1"
      >
        <HeadingIcon level={1} />
      </ToolbarButton>
      <ToolbarButton
        onClick={() => setBlockTypeCommand('heading', { level: 2 })}
        active={isBlockTypeActive('heading', { level: 2 })}
        disabled={disabled}
        title="제목 2"
      >
        <HeadingIcon level={2} />
      </ToolbarButton>
      <ToolbarButton
        onClick={() => setBlockTypeCommand('heading', { level: 3 })}
        active={isBlockTypeActive('heading', { level: 3 })}
        disabled={disabled}
        title="제목 3"
      >
        <HeadingIcon level={3} />
      </ToolbarButton>

      <Separator />

      {/* Text formatting */}
      <ToolbarButton
        onClick={() => toggleMarkCommand('bold')}
        active={isMarkActive('bold')}
        disabled={disabled}
        title="굵게 (Ctrl+B)"
      >
        <BoldIcon />
      </ToolbarButton>
      <ToolbarButton
        onClick={() => toggleMarkCommand('italic')}
        active={isMarkActive('italic')}
        disabled={disabled}
        title="기울임 (Ctrl+I)"
      >
        <ItalicIcon />
      </ToolbarButton>
      <ToolbarButton
        onClick={() => toggleMarkCommand('underline')}
        active={isMarkActive('underline')}
        disabled={disabled}
        title="밑줄 (Ctrl+U)"
      >
        <UnderlineIcon />
      </ToolbarButton>
      <ToolbarButton
        onClick={() => toggleMarkCommand('strikethrough')}
        active={isMarkActive('strikethrough')}
        disabled={disabled}
        title="취소선"
      >
        <StrikeIcon />
      </ToolbarButton>
      <ToolbarButton
        onClick={() => toggleMarkCommand('superscript')}
        active={isMarkActive('superscript')}
        disabled={disabled}
        title="위 첨자"
      >
        <SuperscriptIcon />
      </ToolbarButton>
      <ToolbarButton
        onClick={() => toggleMarkCommand('subscript')}
        active={isMarkActive('subscript')}
        disabled={disabled}
        title="아래 첨자"
      >
        <SubscriptIcon />
      </ToolbarButton>
      <ToolbarButton
        onClick={() => toggleMarkCommand('code')}
        active={isMarkActive('code')}
        disabled={disabled}
        title="코드"
      >
        <CodeIcon />
      </ToolbarButton>

      <Separator />

      {/* Insert elements */}
      <ToolbarButton
        onClick={insertLink}
        active={isMarkActive('link')}
        disabled={disabled}
        title="링크 추가"
      >
        <LinkIcon />
      </ToolbarButton>
      <ToolbarButton
        onClick={insertImage}
        disabled={disabled}
        title="이미지 삽입"
      >
        <ImageIcon />
      </ToolbarButton>
      <ToolbarButton
        onClick={insertMath}
        disabled={disabled}
        title="수식 삽입"
      >
        <MathIcon />
      </ToolbarButton>

      <Separator />

      {/* QTI Interactions */}
      <ToolbarButton
        onClick={insertChoiceInteraction}
        disabled={disabled}
        title="선다형 문항 삽입"
      >
        <ChoiceIcon />
      </ToolbarButton>
      <ToolbarButton
        onClick={insertTextEntry}
        disabled={disabled}
        title="단답형 빈칸 삽입"
      >
        <TextEntryIcon />
      </ToolbarButton>
      <ToolbarButton
        onClick={insertExtendedText}
        disabled={disabled}
        title="서술형 입력란 삽입"
      >
        <ExtendedTextIcon />
      </ToolbarButton>
    </div>
  )
}

EditorToolbar.displayName = 'EditorToolbar'
