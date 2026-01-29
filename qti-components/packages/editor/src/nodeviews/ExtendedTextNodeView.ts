/**
 * ExtendedTextNodeView - Renders extended text interaction as a textarea placeholder
 */

import type { Node as ProseMirrorNode } from 'prosemirror-model'
import type { EditorView, NodeView } from 'prosemirror-view'

export class ExtendedTextNodeView implements NodeView {
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
    this.dom = document.createElement('div')
    this.dom.className = 'qti-extended-text-node my-2'
    this.dom.setAttribute('contenteditable', 'false')

    this.render()

    // Double-click to edit settings
    this.dom.addEventListener('dblclick', this.handleDoubleClick.bind(this))
  }

  render() {
    const expectedLines = this.node.attrs['expectedLines'] as number
    const placeholder = this.node.attrs['placeholderText'] as string
    const format = this.node.attrs['format'] as string

    const height = Math.max(expectedLines * 24, 80)

    this.dom.innerHTML = `
      <div
        class="border border-dashed border-gray-300 rounded-lg bg-gray-50 p-3"
        style="min-height: ${height}px"
      >
        <div class="flex items-start gap-2 text-gray-400">
          <svg class="w-5 h-5 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <rect x="3" y="3" width="18" height="18" rx="2" stroke-width="2"/>
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 7h10M7 11h10M7 15h6"/>
          </svg>
          <div class="flex-1">
            <div class="text-sm font-medium">서술형 입력란</div>
            <div class="text-xs mt-1">
              ${placeholder || '서술형 답변을 입력하세요'}
              <span class="ml-2 text-gray-400">(${expectedLines}줄, ${format})</span>
            </div>
          </div>
          <button class="text-xs text-blue-500 hover:text-blue-700">설정</button>
        </div>
      </div>
    `
  }

  handleDoubleClick(event: MouseEvent) {
    event.preventDefault()
    event.stopPropagation()

    const currentLines = this.node.attrs['expectedLines'] as number
    const currentPlaceholder = this.node.attrs['placeholderText'] as string

    const linesInput = window.prompt('예상 줄 수:', String(currentLines ?? 5))
    if (linesInput === null) return

    const placeholderInput = window.prompt('플레이스홀더 텍스트:', currentPlaceholder)
    if (placeholderInput === null) return

    const pos = this.getPos()
    if (pos !== undefined) {
      const tr = this.view.state.tr.setNodeMarkup(pos, undefined, {
        ...this.node.attrs,
        expectedLines: parseInt(linesInput, 10) || 5,
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
    this.dom.style.borderRadius = '8px'
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

export function extendedTextNodeView(
  node: ProseMirrorNode,
  view: EditorView,
  getPos: () => number | undefined
): ExtendedTextNodeView {
  return new ExtendedTextNodeView(node, view, getPos)
}
