/**
 * MathNodeView - Renders math nodes with KaTeX
 */

import type { Node as ProseMirrorNode } from 'prosemirror-model'
import type { EditorView, NodeView } from 'prosemirror-view'
import katex from 'katex'

export class MathNodeView implements NodeView {
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
    this.dom.className = 'qti-math-node'
    this.dom.setAttribute('contenteditable', 'false')

    this.render()

    // Double-click to edit
    this.dom.addEventListener('dblclick', this.handleDoubleClick.bind(this))
  }

  render() {
    const latex = this.node.attrs['latex'] as string
    const display = this.node.attrs['display'] as string

    this.dom.className = `qti-math-node ${display === 'block' ? 'block' : 'inline-block'}`

    if (!latex) {
      this.dom.innerHTML = '<span class="text-gray-400 italic">수식을 입력하세요</span>'
      return
    }

    try {
      katex.render(latex, this.dom, {
        displayMode: display === 'block',
        throwOnError: false,
        errorColor: '#ef4444',
      })
    } catch (error) {
      this.dom.innerHTML = `<span class="text-red-500">수식 오류: ${latex}</span>`
    }
  }

  handleDoubleClick(event: MouseEvent) {
    event.preventDefault()
    event.stopPropagation()

    const currentLatex = this.node.attrs['latex'] as string
    const newLatex = window.prompt('LaTeX 수식을 입력하세요:', currentLatex)

    if (newLatex !== null && newLatex !== currentLatex) {
      const pos = this.getPos()
      if (pos !== undefined) {
        const tr = this.view.state.tr.setNodeMarkup(pos, undefined, {
          ...this.node.attrs,
          latex: newLatex,
        })
        this.view.dispatch(tr)
      }
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

export function mathNodeView(
  node: ProseMirrorNode,
  view: EditorView,
  getPos: () => number | undefined
): MathNodeView {
  return new MathNodeView(node, view, getPos)
}
