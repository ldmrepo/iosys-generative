/**
 * TextEntryNodeView - Renders text entry interaction as an input field
 */

import type { Node as ProseMirrorNode } from 'prosemirror-model'
import type { EditorView, NodeView } from 'prosemirror-view'

export class TextEntryNodeView implements NodeView {
  dom: HTMLElement
  node: ProseMirrorNode
  view: EditorView
  getPos: () => number | undefined

  constructor(
    node: ProseMirrorNode,
    view: EditorView,
    getPos: () => number | undefined
  ) {
    this.node = node
    this.view = view
    this.getPos = getPos

    // Create the container element
    this.dom = document.createElement('span')
    this.dom.className = 'qti-text-entry-node inline-block align-middle'
    this.dom.setAttribute('contenteditable', 'false')

    this.render()

    // Double-click to edit settings
    this.dom.addEventListener('dblclick', this.handleDoubleClick.bind(this))
  }

  render() {
    const expectedLength = this.node.attrs['expectedLength'] as number | null
    const placeholder = this.node.attrs['placeholderText'] as string

    const width = expectedLength ? `${Math.min(expectedLength * 12, 300)}px` : '100px'

    this.dom.innerHTML = `
      <span
        class="inline-flex items-center px-2 py-1 border border-gray-300 rounded bg-gray-50 text-gray-400 text-sm"
        style="min-width: ${width}"
      >
        <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <rect x="3" y="6" width="18" height="12" rx="2" stroke-width="2"/>
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 10v4"/>
        </svg>
        ${placeholder || '단답형 입력란'}
      </span>
    `
  }

  handleDoubleClick(event: MouseEvent) {
    event.preventDefault()
    event.stopPropagation()

    const currentLength = this.node.attrs['expectedLength'] as number | null
    const currentPlaceholder = this.node.attrs['placeholderText'] as string

    const lengthInput = window.prompt('예상 글자 수:', String(currentLength ?? 20))
    if (lengthInput === null) return

    const placeholderInput = window.prompt('플레이스홀더 텍스트:', currentPlaceholder)
    if (placeholderInput === null) return

    const pos = this.getPos()
    if (pos !== undefined) {
      const tr = this.view.state.tr.setNodeMarkup(pos, undefined, {
        ...this.node.attrs,
        expectedLength: parseInt(lengthInput, 10) || null,
        placeholderText: placeholderInput,
      })
      this.view.dispatch(tr)
    }
  }

  update(node: ProseMirrorNode): boolean {
    if (node.type !== this.node.type) return false

    this.node = node
    this.render()
    return true
  }

  selectNode() {
    this.dom.classList.add('ProseMirror-selectednode')
    this.dom.style.outline = '2px solid #3b82f6'
    this.dom.style.borderRadius = '4px'
  }

  deselectNode() {
    this.dom.classList.remove('ProseMirror-selectednode')
    this.dom.style.outline = ''
  }

  stopEvent() {
    return true
  }

  ignoreMutation() {
    return true
  }
}

export function textEntryNodeView(
  node: ProseMirrorNode,
  view: EditorView,
  getPos: () => number | undefined
): TextEntryNodeView {
  return new TextEntryNodeView(node, view, getPos)
}
