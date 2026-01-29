/**
 * ProseMirror Node Specifications for QTI Editor
 */

import type { NodeSpec } from 'prosemirror-model'

// Document
export const doc: NodeSpec = {
  content: 'block+',
}

// Text
export const text: NodeSpec = {
  group: 'inline',
}

// Paragraph
export const paragraph: NodeSpec = {
  content: 'inline*',
  group: 'block',
  parseDOM: [{ tag: 'p' }],
  toDOM() {
    return ['p', 0]
  },
}

// Heading
export const heading: NodeSpec = {
  attrs: { level: { default: 1 } },
  content: 'inline*',
  group: 'block',
  defining: true,
  parseDOM: [
    { tag: 'h1', attrs: { level: 1 } },
    { tag: 'h2', attrs: { level: 2 } },
    { tag: 'h3', attrs: { level: 3 } },
    { tag: 'h4', attrs: { level: 4 } },
  ],
  toDOM(node) {
    return ['h' + String(node.attrs['level']), 0]
  },
}

// Hard break
export const hardBreak: NodeSpec = {
  inline: true,
  group: 'inline',
  selectable: false,
  parseDOM: [{ tag: 'br' }],
  toDOM() {
    return ['br']
  },
}

// Image
export const image: NodeSpec = {
  inline: true,
  attrs: {
    src: {},
    alt: { default: null },
    title: { default: null },
    width: { default: null },
    height: { default: null },
  },
  group: 'inline',
  draggable: true,
  parseDOM: [
    {
      tag: 'img[src]',
      getAttrs(dom) {
        const el = dom as HTMLElement
        return {
          src: el.getAttribute('src'),
          alt: el.getAttribute('alt'),
          title: el.getAttribute('title'),
          width: el.getAttribute('width'),
          height: el.getAttribute('height'),
        }
      },
    },
  ],
  toDOM(node) {
    const { src, alt, title, width, height } = node.attrs as Record<string, string | null>
    return ['img', { src, alt, title, width, height }]
  },
}

// Math (KaTeX)
export const math: NodeSpec = {
  attrs: {
    latex: { default: '' },
    display: { default: 'inline' },
  },
  inline: true,
  group: 'inline',
  atom: true,
  parseDOM: [
    {
      tag: 'span.math',
      getAttrs(dom) {
        const el = dom as HTMLElement
        return {
          latex: el.getAttribute('data-latex') ?? '',
          display: el.getAttribute('data-display') ?? 'inline',
        }
      },
    },
  ],
  toDOM(node) {
    return [
      'span',
      {
        class: 'math',
        'data-latex': node.attrs['latex'],
        'data-display': node.attrs['display'],
      },
    ]
  },
}

// -------------------
// QTI Interactions
// -------------------

// Choice Interaction
export const choiceInteraction: NodeSpec = {
  attrs: {
    responseIdentifier: { default: 'RESPONSE' },
    shuffle: { default: false },
    maxChoices: { default: 1 },
    minChoices: { default: 0 },
    orientation: { default: 'vertical' },
  },
  content: 'simpleChoice+',
  group: 'block',
  defining: true,
  parseDOM: [
    {
      tag: 'div.qti-choice-interaction',
      getAttrs(dom) {
        const el = dom as HTMLElement
        return {
          responseIdentifier: el.getAttribute('data-response-identifier') ?? 'RESPONSE',
          shuffle: el.getAttribute('data-shuffle') === 'true',
          maxChoices: parseInt(el.getAttribute('data-max-choices') ?? '1', 10),
          minChoices: parseInt(el.getAttribute('data-min-choices') ?? '0', 10),
          orientation: el.getAttribute('data-orientation') ?? 'vertical',
        }
      },
    },
  ],
  toDOM(node) {
    return [
      'div',
      {
        class: 'qti-choice-interaction',
        'data-response-identifier': node.attrs['responseIdentifier'],
        'data-shuffle': String(node.attrs['shuffle']),
        'data-max-choices': String(node.attrs['maxChoices']),
        'data-min-choices': String(node.attrs['minChoices']),
        'data-orientation': node.attrs['orientation'],
      },
      0,
    ]
  },
}

// Simple Choice (child of choiceInteraction)
export const simpleChoice: NodeSpec = {
  attrs: {
    identifier: { default: null },
    isCorrect: { default: false },
    fixed: { default: false },
  },
  content: 'paragraph block*',
  group: 'block',
  draggable: true,
  isolating: true,
  parseDOM: [
    {
      tag: 'div.qti-simple-choice',
      getAttrs(dom) {
        const el = dom as HTMLElement
        return {
          identifier: el.getAttribute('data-identifier'),
          isCorrect: el.getAttribute('data-correct') === 'true',
          fixed: el.getAttribute('data-fixed') === 'true',
        }
      },
    },
  ],
  toDOM(node) {
    return [
      'div',
      {
        class: 'qti-simple-choice',
        'data-identifier': node.attrs['identifier'],
        'data-correct': String(node.attrs['isCorrect']),
        'data-fixed': String(node.attrs['fixed']),
      },
      0,
    ]
  },
}

// Text Entry Interaction (inline)
export const textEntryInteraction: NodeSpec = {
  attrs: {
    responseIdentifier: { default: 'RESPONSE' },
    expectedLength: { default: null },
    placeholderText: { default: '' },
  },
  inline: true,
  group: 'inline',
  atom: true,
  parseDOM: [
    {
      tag: 'span.qti-text-entry',
      getAttrs(dom) {
        const el = dom as HTMLElement
        return {
          responseIdentifier: el.getAttribute('data-response-identifier') ?? 'RESPONSE',
          expectedLength: el.getAttribute('data-expected-length')
            ? parseInt(el.getAttribute('data-expected-length')!, 10)
            : null,
          placeholderText: el.getAttribute('data-placeholder') ?? '',
        }
      },
    },
  ],
  toDOM(node) {
    return [
      'span',
      {
        class: 'qti-text-entry',
        'data-response-identifier': node.attrs['responseIdentifier'],
        'data-expected-length': node.attrs['expectedLength'],
        'data-placeholder': node.attrs['placeholderText'],
      },
    ]
  },
}

// Extended Text Interaction
export const extendedTextInteraction: NodeSpec = {
  attrs: {
    responseIdentifier: { default: 'RESPONSE' },
    expectedLines: { default: 5 },
    placeholderText: { default: '' },
    format: { default: 'plain' },
  },
  group: 'block',
  atom: true,
  parseDOM: [
    {
      tag: 'div.qti-extended-text',
      getAttrs(dom) {
        const el = dom as HTMLElement
        return {
          responseIdentifier: el.getAttribute('data-response-identifier') ?? 'RESPONSE',
          expectedLines: parseInt(el.getAttribute('data-expected-lines') ?? '5', 10),
          placeholderText: el.getAttribute('data-placeholder') ?? '',
          format: el.getAttribute('data-format') ?? 'plain',
        }
      },
    },
  ],
  toDOM(node) {
    return [
      'div',
      {
        class: 'qti-extended-text',
        'data-response-identifier': node.attrs['responseIdentifier'],
        'data-expected-lines': String(node.attrs['expectedLines']),
        'data-placeholder': node.attrs['placeholderText'],
        'data-format': node.attrs['format'],
      },
    ]
  },
}
