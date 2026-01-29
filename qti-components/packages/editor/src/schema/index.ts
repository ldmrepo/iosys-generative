/**
 * QTI Editor Schema
 */

import { Schema } from 'prosemirror-model'
import * as nodes from './nodes'
import * as marks from './marks'

export const qtiSchema = new Schema({
  nodes: {
    doc: nodes.doc,
    paragraph: nodes.paragraph,
    heading: nodes.heading,
    hardBreak: nodes.hardBreak,
    text: nodes.text,
    image: nodes.image,
    math: nodes.math,
    // QTI Interactions
    choiceInteraction: nodes.choiceInteraction,
    simpleChoice: nodes.simpleChoice,
    textEntryInteraction: nodes.textEntryInteraction,
    extendedTextInteraction: nodes.extendedTextInteraction,
  },
  marks: {
    bold: marks.bold,
    italic: marks.italic,
    underline: marks.underline,
    strikethrough: marks.strikethrough,
    superscript: marks.superscript,
    subscript: marks.subscript,
    link: marks.link,
    code: marks.code,
  },
})

export { nodes, marks }
export type { NodeSpec, MarkSpec } from 'prosemirror-model'
