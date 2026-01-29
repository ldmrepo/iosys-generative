/**
 * ProseMirror Mark Specifications for QTI Editor
 */

import type { MarkSpec } from 'prosemirror-model'

// Bold
export const bold: MarkSpec = {
  parseDOM: [
    { tag: 'strong' },
    { tag: 'b' },
    {
      style: 'font-weight',
      getAttrs: value => {
        if (typeof value === 'string') {
          return /^(bold(er)?|[5-9]\d{2,})$/.test(value) ? null : false
        }
        return false
      },
    },
  ],
  toDOM() {
    return ['strong', 0]
  },
}

// Italic
export const italic: MarkSpec = {
  parseDOM: [{ tag: 'i' }, { tag: 'em' }, { style: 'font-style=italic' }],
  toDOM() {
    return ['em', 0]
  },
}

// Underline
export const underline: MarkSpec = {
  parseDOM: [{ tag: 'u' }, { style: 'text-decoration=underline' }],
  toDOM() {
    return ['u', 0]
  },
}

// Strikethrough
export const strikethrough: MarkSpec = {
  parseDOM: [{ tag: 's' }, { tag: 'del' }, { style: 'text-decoration=line-through' }],
  toDOM() {
    return ['s', 0]
  },
}

// Superscript
export const superscript: MarkSpec = {
  parseDOM: [{ tag: 'sup' }],
  toDOM() {
    return ['sup', 0]
  },
  excludes: 'subscript',
}

// Subscript
export const subscript: MarkSpec = {
  parseDOM: [{ tag: 'sub' }],
  toDOM() {
    return ['sub', 0]
  },
  excludes: 'superscript',
}

// Link
export const link: MarkSpec = {
  attrs: {
    href: {},
    title: { default: null },
    target: { default: '_blank' },
  },
  inclusive: false,
  parseDOM: [
    {
      tag: 'a[href]',
      getAttrs(dom) {
        const el = dom as HTMLElement
        return {
          href: el.getAttribute('href'),
          title: el.getAttribute('title'),
          target: el.getAttribute('target'),
        }
      },
    },
  ],
  toDOM(mark) {
    const { href, title, target } = mark.attrs as Record<string, string | null>
    return ['a', { href, title, target, rel: 'noopener noreferrer' }, 0]
  },
}

// Code
export const code: MarkSpec = {
  parseDOM: [{ tag: 'code' }],
  toDOM() {
    return ['code', 0]
  },
}
